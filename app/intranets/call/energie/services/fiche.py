"""
Service Call Energie - chargement de la fiche d'un ticket (popup).

Transposition du code WinDev `PAGE_TicketFicheEnergie` (code init serveur).

Differences vs Fibre :
- Tables TK_Call / TK_Call_Panier (sans suffixe SFR)
- Pas de Mobile2, pas de MobPropoVend, pas de bloc anomalie / vente differee
- Panier : colonnes specifiques Energie (IDproduit, Partenaire, OPT_*, Opt_Mandat,
  FormatNumerique) -> pas de TYPE/portabilite/Num*/TestEligibilite
- Documents : _PieceIdentite.* (CIN), _CIN.jpg (fallback), _KBIS.*, et nouveau _Justif.*
- Login/MDP Ohm dynamique selon descendance de l'agence Power Ohm
  (ID racine 20260324120238233)

Phase 1 = lecture seule, colonne gauche (infos client + vendeur).
Phases ulterieures : panier + colonne droite variable selon partenaire,
save, verrou ope, actions.
"""

import shutil
import sys
import traceback
import urllib.request
import time as _time_mod
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

from app.core.config import DOCS_BASE_PATH
from app.core.database import get_connection
from app.intranets.call.fibre.services.tickets import (
    _capitalize,
    _format_nom_client,
    _format_ville,
    _iso,
    _str_id,
    _to_int,
)


# --- Constantes -----------------------------------------------------------

DOC_BASE_URL = "https://rest.omaya.fr/DocOmaya"
REP_OHM = DOCS_BASE_PATH / "Call_OhmEnergie"

# Agence Power Ohm : si le vendeur est descendant de cette racine, on
# utilise des credentials portail Ohm Energie differents (admin vs std).
ID_ORGA_POWER_OHM = 20260324120238233


# --- Helpers --------------------------------------------------------------

def _iso_date(v: Any) -> str:
    """HFSQL Date (compact 8 chars) ou DateTime (>= 14 chars) -> 'YYYY-MM-DD'."""
    if not v:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    s = str(v).strip()
    if not s or s.startswith("0000"):
        return ""
    if len(s) >= 8 and s[:8].isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return ""


def _mask_phone(num: str) -> str:
    """'0612345678' -> '06123456xx'. Vide si num vide."""
    s = (num or "").strip()
    if not s:
        return ""
    if len(s) <= 2:
        return "xx"
    return s[:-2] + "xx"


def _bool(v: Any) -> bool:
    return bool(v) and v not in (0, "0", "")


# --- HEAD HTTP avec cache 60s + parallel -----------------------------------

_URL_HEAD_CACHE: dict[str, tuple[bool, float]] = {}
_URL_HEAD_TTL = 60.0


def _url_exists(url: str, timeout: float = 1.5) -> bool:
    """HEAD HTTP : True si le fichier existe. Cache 60s."""
    now = _time_mod.monotonic()
    cached = _URL_HEAD_CACHE.get(url)
    if cached is not None and now - cached[1] < _URL_HEAD_TTL:
        return cached[0]
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            exists = 200 <= resp.status < 300
    except Exception:
        exists = False
    _URL_HEAD_CACHE[url] = (exists, now)
    return exists


def _first_existing(*urls: str) -> tuple[str, str]:
    """Retourne (url, kind) du premier fichier existant (HEAD en parallele)."""
    valid_urls = [u for u in urls if u]
    if not valid_urls:
        return "", ""
    with ThreadPoolExecutor(max_workers=min(len(valid_urls), 4)) as pool:
        results = list(pool.map(_url_exists, valid_urls))
    for url, exists in zip(valid_urls, results):
        if exists:
            kind = "pdf" if url.lower().endswith(".pdf") else "image"
            return url, kind
    return "", ""


# Cache des descendants de chaque racine d'organigramme (5min).
_ORGA_DESCENDANTS_CACHE: dict[int, tuple[set[int], float]] = {}
_ORGA_DESCENDANTS_TTL = 300.0


def _orga_descendants_set(db_rh, id_racine: int) -> set[int]:
    """Retourne tous les descendants d'une racine d'organigramme (BFS).

    Inclut la racine elle-meme. Cache 5min.
    """
    cached = _ORGA_DESCENDANTS_CACHE.get(id_racine)
    now = _time_mod.monotonic()
    if cached and now - cached[1] < _ORGA_DESCENDANTS_TTL:
        return cached[0]
    # On charge l'organigramme entier (parent -> enfants) et on fait un BFS.
    rows = db_rh.query("SELECT IDOrganigramme, IdPARENT FROM Organigramme")
    children: dict[int, list[int]] = {}
    for r in rows:
        pid = _to_int(r.get("IdPARENT"))
        cid = _to_int(r.get("IDOrganigramme"))
        if pid and cid:
            children.setdefault(pid, []).append(cid)
    visited: set[int] = {id_racine}
    queue: list[int] = [id_racine]
    while queue:
        node = queue.pop(0)
        for c in children.get(node, []):
            if c not in visited:
                visited.add(c)
                queue.append(c)
    _ORGA_DESCENDANTS_CACHE[id_racine] = (visited, now)
    return visited


# --- Chargement de la fiche -----------------------------------------------

def load_fiche(id_tk_liste: int, current_user_id: int = 0) -> dict:
    """Charge toutes les donnees de la fiche d'un ticket Call Energie.

    Phase 1 : colonne gauche (infos client + vendeur) + panier brut (sans
    detail). Les colonnes centre/droite seront enrichies en Phase 2/3.
    """
    db_ticket = get_connection("ticket")
    db_bo = get_connection("ticket_bo")
    db_rh = get_connection("rh")
    db_adv = get_connection("adv")

    # Vague 1 : TK_Liste + TK_Call en parallele
    sql_liste = """SELECT
            IDTK_Liste AS id_tk_liste,
            Datecrea AS date_crea,
            IDTK_Statut AS id_tk_statut,
            OPCrea AS op_crea,
            Cloturée AS cloturee,
            DateCloture AS date_cloture
        FROM TK_Liste
        WHERE IDTK_Liste = ?"""
    sql_call = """SELECT
            IDtk_Call, IDTK_Liste, IDSalarie,
            CivilitéClient, NomClient, NomMaritalClient, PrenomClient,
            DATENAISS, DEPNAISS, TypeLogement, ADRESSE1, ADRESSE2, CP, VILLE,
            adrMail, Mobile1,
            AppelEnCours, DateH_Appel, OpéAppel, RefAppel,
            MotifAnnulation, DateDeb_PriseEnCharge, DateFin_PriseEnCharge,
            InterventionVend, InfoVente,
            Opt_Rappel, Opt_Partenaire,
            ClientPro, ClientRS, ClientSiret
        FROM TK_Call
        WHERE IDTK_Liste = ?
          AND ModifELEM NOT LIKE '%suppr%'"""
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_liste = pool.submit(db_ticket.query, sql_liste, (id_tk_liste,))
        f_call = pool.submit(db_bo.query, sql_call, (id_tk_liste,))
        rows_liste = f_liste.result()
        rows_call = f_call.result()
    if not rows_liste:
        return {"error": "Ticket introuvable"}
    tk_liste = rows_liste[0]
    if not rows_call:
        return {"error": "Pas de TK_Call pour ce ticket"}
    tc = rows_call[0]

    id_call = _to_int(tc.get("IDtk_Call"))
    id_salarie = _to_int(tc.get("IDSalarie"))
    id_tk_statut = _to_int(tk_liste.get("id_tk_statut"))
    appel_en_cours = _bool(tc.get("AppelEnCours"))
    ope_appel_id = _to_int(tc.get("OpéAppel"))

    is_my_call = appel_en_cours and ope_appel_id == current_user_id

    mobile1_raw = (tc.get("Mobile1") or "").strip()
    mobile1 = mobile1_raw if is_my_call else _mask_phone(mobile1_raw)

    # Vague 2 : Salarie + Salarie_Coordonnees + Panier en parallele
    nom_vend = ""
    prenom_vend = ""
    gsm_vend_raw = ""
    ope_en_cours_nom = ""
    # Si un AUTRE ope a un appel en cours sur ce ticket, on recupere son nom
    # (pour la boite d'alerte affichee a l'ouverture de la fiche).
    need_ope = appel_en_cours and ope_appel_id and not is_my_call
    with ThreadPoolExecutor(max_workers=4) as pool:
        f_sal = pool.submit(
            db_rh.query, "SELECT Nom, Prenom FROM Salarie WHERE IDSalarie = ?", (id_salarie,)
        ) if id_salarie else None
        f_coord = pool.submit(
            db_rh.query, "SELECT TélMob FROM Salarie_Coordonnees WHERE IDSalarie = ?", (id_salarie,)
        ) if id_salarie else None
        f_ope = pool.submit(
            db_rh.query, "SELECT Nom, Prenom FROM Salarie WHERE IDSalarie = ?", (ope_appel_id,)
        ) if need_ope else None
        f_panier = pool.submit(
            db_bo.query,
            """SELECT
                IDTK_Call_Panier, IDproduit, Partenaire,
                OPT_EnergieVerteElec, OPT_Reforestation, OPT_EnergieVerteGaz,
                OPT_Mail, Opt_Mandat, FormatNumérique,
                OPT_AcceptComParte, OPT_ConsentConsultDistri, Opt_Maintenance,
                OPT_eCommunication, OPT_eFacture, OPT_optinCommercial,
                DateEntrée, Observations,
                MotifAnnulation, StatutProd, NumBS, Num_DateSaisie
            FROM TK_Call_Panier
            WHERE IDtk_Call = ?
              AND ModifElem NOT LIKE '%suppr%'""",
            (id_call,),
        )
        rows_sal = f_sal.result() if f_sal else []
        rows_coord = f_coord.result() if f_coord else []
        rows_ope = f_ope.result() if f_ope else []
        rows_panier = f_panier.result()
    if rows_sal:
        s = rows_sal[0]
        nom_vend = (s.get("Nom") or "").strip()
        prenom_vend = _capitalize((s.get("Prenom") or "").strip())
    if rows_coord:
        gsm_vend_raw = (rows_coord[0].get("TélMob") or "").strip()
    if rows_ope:
        o = rows_ope[0]
        ope_en_cours_nom = f"{(o.get('Nom') or '').strip()} {_capitalize((o.get('Prenom') or '').strip())}".strip()
    gsm_vend = gsm_vend_raw if is_my_call else _mask_phone(gsm_vend_raw)

    # Panier brut (Phase 1 : on l'expose tel quel, pas de catalogue produit
    # joint pour avoir Lib_Offre. A enrichir en Phase 2 selon besoin.)
    # Charge les partenaires actifs pour mapper le prefix BDD au Lib_Partenaire
    # (nom complet affiche dans la fiche).
    from app.intranets.call.energie.services.tickets import _load_partenaires_actifs
    partenaires_list = _load_partenaires_actifs(db_adv)
    prefix_to_lib = {p["prefix"]: p["lib"] for p in partenaires_list}

    panier = []
    for p in rows_panier:
        prefix = (p.get("Partenaire") or "").strip()
        panier.append({
            "id": _str_id(p.get("IDTK_Call_Panier")),
            "id_produit": _to_int(p.get("IDproduit")),
            "partenaire": prefix,  # prefixe BDD : "OEN", "PRO", "ENI", "VAL", "STR", ...
            "partenaire_lib": prefix_to_lib.get(prefix, prefix),  # nom complet
            "opt_energie_verte_elec": _bool(p.get("OPT_EnergieVerteElec")),
            "opt_energie_verte_gaz": _bool(p.get("OPT_EnergieVerteGaz")),
            "opt_reforestation": _bool(p.get("OPT_Reforestation")),
            "opt_mail": _bool(p.get("OPT_Mail")),
            "opt_mandat": _bool(p.get("Opt_Mandat")),
            "format_numerique": _bool(p.get("FormatNumérique")),
            # Options ENI (Engie) : PLENICOACH DEPANNAGE PREMIUM + AcceptComParte + ConsentConsultDistri
            "opt_maintenance": _bool(p.get("Opt_Maintenance")),
            "opt_accept_com_parte": _bool(p.get("OPT_AcceptComParte")),
            "opt_consent_consult_distri": _bool(p.get("OPT_ConsentConsultDistri")),
            # Autres options
            "opt_e_communication": _bool(p.get("OPT_eCommunication")),
            "opt_e_facture": _bool(p.get("OPT_eFacture")),
            "opt_optin_commercial": _bool(p.get("OPT_optinCommercial")),
            "statut_prod": _to_int(p.get("StatutProd")),
            "motif_annulation": (p.get("MotifAnnulation") or "").strip(),
            "num_bs": (p.get("NumBS") or "").strip(),
            "num_date_saisie": _iso(p.get("Num_DateSaisie")),
            # OEN : "Date Activ" = DateEntrée (Date), "Ref Client" = Observations (memo texte)
            "date_activ": _iso_date(p.get("DateEntrée")),
            "ref_client_oen": (p.get("Observations") or "").strip(),
        })

    # Credentials portail Ohm Energie (cf. code WinDev) : si le vendeur est
    # descendant de l'agence Power Ohm (ID racine ID_ORGA_POWER_OHM) -> admin,
    # sinon credentials standard.
    ohm_login = "Power_distribExo_Sup"
    ohm_mdp = "U8uDym72"
    if id_salarie:
        # Recupere l'orga d'affectation du vendeur
        try:
            row_aff = db_rh.query(
                """SELECT TOP 1 IDOrganigramme FROM Salarie_Organigramme
                WHERE IDSalarie = ?
                  AND ModifELEM NOT LIKE '%suppr%'
                  AND (DateFin = '' OR DateFin >= ?)
                ORDER BY DateDébut DESC""",
                (id_salarie, datetime.now().strftime("%Y%m%d")),
            )
            id_orga_vendeur = _to_int(row_aff[0].get("IDOrganigramme")) if row_aff else 0
            # Si dans l'arborescence Power Ohm
            if id_orga_vendeur:
                power_ohm_set = _orga_descendants_set(db_rh, ID_ORGA_POWER_OHM)
                if id_orga_vendeur in power_ohm_set:
                    ohm_login = "Power_distrib_admin"
                    ohm_mdp = "Jbrk5Q78"
        except Exception:
            pass  # garde les defaults

    # Statuts vente (transposition WinDev : 0=Non defini, 1=Validé, 2=Annulé,
    # 3=Num BS ajouté, 4=Validé Différé si statut TK_Liste=15)
    statuts_vente = [
        {"id": 0, "label": "Non défini"},
        {"id": 1, "label": "Validé"},
        {"id": 2, "label": "Annulé"},
        {"id": 3, "label": "Num BS ajouté"},
    ]
    if id_tk_statut == 15:
        statuts_vente.append({"id": 4, "label": "Validé - Différé"})

    # Compteurs panier
    nb_prod_total = len(panier)
    nb_prod_valide = sum(1 for p in panier if p["statut_prod"] in (1, 3))
    nb_prod_annule = sum(1 for p in panier if p["statut_prod"] == 2)
    btn_valider_actif = nb_prod_valide > 0 and (nb_prod_valide + nb_prod_annule) == nb_prod_total
    btn_annuler_actif = nb_prod_total > 0 and nb_prod_annule == nb_prod_total

    return {
        "id_ticket": _str_id(id_tk_liste),
        "id_call": _str_id(id_call),
        "id_tk_statut": id_tk_statut,
        "is_cloture": _bool(tk_liste.get("cloturee")),
        "is_my_call": is_my_call,
        "appel_en_cours": appel_en_cours,
        "ope_en_cours_nom": ope_en_cours_nom,
        "client": {
            "civilite": _to_int(tc.get("CivilitéClient")),
            "nom": (tc.get("NomClient") or "").strip(),
            "nom_marital": (tc.get("NomMaritalClient") or "").strip(),
            "prenom": (tc.get("PrenomClient") or "").strip(),
            "nom_format": _format_nom_client(
                _to_int(tc.get("CivilitéClient")),
                tc.get("NomClient"),
                tc.get("NomMaritalClient"),
                tc.get("PrenomClient"),
            ),
            "date_naiss": _iso_date(tc.get("DATENAISS")),
            "dep_naiss": _to_int(tc.get("DEPNAISS")),
            "type_logement": _to_int(tc.get("TypeLogement")),
            "adresse1": (tc.get("ADRESSE1") or "").strip(),
            "adresse2": (tc.get("ADRESSE2") or "").strip(),
            "cp": (tc.get("CP") or "").strip(),
            "ville": _format_ville(tc.get("VILLE") or ""),
            "email": (tc.get("adrMail") or "").strip(),
            "mobile1": mobile1,
            "opt_rappel": _bool(tc.get("Opt_Rappel")),
            "opt_partenaire": _bool(tc.get("Opt_Partenaire")),
            "client_pro": _bool(tc.get("ClientPro")),
            "client_rs": (tc.get("ClientRS") or "").strip(),
            "client_siret": (tc.get("ClientSiret") or "").strip(),
        },
        "vendeur": {
            "id_salarie": id_salarie,
            "nom": nom_vend,
            "prenom": prenom_vend,
            "gsm": gsm_vend,
            "lib_affectation": "",  # TODO : affectationTerrainVendeur(IDSalarie)
        },
        "vente": {
            "ref_appel": (tc.get("RefAppel") or "").strip(),
            "intervention_vendeur": _bool(tc.get("InterventionVend")),
            "info_vente": (tc.get("InfoVente") or "").strip(),
        },
        "panier": panier,
        "nb_prod_total": nb_prod_total,
        "nb_prod_valide": nb_prod_valide,
        "nb_prod_annule": nb_prod_annule,
        "btn_valider_actif": btn_valider_actif,
        "btn_annuler_actif": btn_annuler_actif,
        "statuts_vente": statuts_vente,
        # Credentials Ohm Energie (utilises uniquement pour la colonne droite
        # quand le partenaire est STR / dans un futur fournisseur dependant).
        "ohm_login": ohm_login,
        "ohm_mdp": ohm_mdp,
    }


# --- Save (UPDATE TK_Call + TK_Call_Panier) -------------------------------

def _sql_str(s: Any) -> str:
    """Escape SQL HFSQL : double les simple quotes."""
    if s is None:
        return ""
    return str(s).replace("'", "''")


def _sql_now() -> str:
    """DateTime HFSQL compact pour ModifDate."""
    return datetime.now().strftime("%Y%m%d%H%M%S")


def _sql_bool(b: Any) -> int:
    return 1 if _bool(b) else 0


def _date_to_compact(s: str | None) -> str:
    """ISO 'YYYY-MM-DD' -> compact 'YYYYMMDD'. Vide si non parsable."""
    if not s:
        return ""
    s = str(s).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:4] + s[5:7] + s[8:10]
    if len(s) == 8 and s.isdigit():
        return s
    return ""


def save_vente_infos(id_tk_liste: int, payload: dict) -> dict:
    """UPDATE TK_Call avec les infos client + vente modifiees.

    Transposition du bouton "Enregistrer les infos Client" WinDev.
    """
    db_bo = get_connection("ticket_bo")
    c = payload.get("client", {}) or {}
    v = payload.get("vente", {}) or {}
    now_wd = _sql_now()
    sql = f"""UPDATE TK_Call SET
        CivilitéClient = {_to_int(c.get('civilite'))},
        NomClient = '{_sql_str(c.get('nom'))}',
        NomMaritalClient = '{_sql_str(c.get('nom_marital'))}',
        PrenomClient = '{_sql_str(c.get('prenom'))}',
        DATENAISS = '{_sql_str(_date_to_compact(c.get('date_naiss')))}',
        DEPNAISS = {_to_int(c.get('dep_naiss'))},
        TypeLogement = {_to_int(c.get('type_logement'))},
        ADRESSE1 = '{_sql_str(c.get('adresse1'))}',
        ADRESSE2 = '{_sql_str(c.get('adresse2'))}',
        CP = '{_sql_str(c.get('cp'))}',
        VILLE = '{_sql_str(c.get('ville'))}',
        adrMail = '{_sql_str(c.get('email'))}',
        InfoVente = '{_sql_str(v.get('info_vente'))}',
        RefAppel = '{_sql_str(v.get('ref_appel'))}',
        InterventionVend = {1 if _bool(v.get('intervention_vendeur')) else 2},
        ModifDate = '{now_wd}'
    WHERE IDTK_Liste = {_to_int(id_tk_liste)}
      AND ModifELEM NOT LIKE '%suppr%'"""
    db_bo.query(sql)
    return {"ok": True}


def save_offre(id_panier: int, payload: dict) -> dict:
    print(f"[save-offre panier={id_panier}] payload_keys={list(payload.keys())} statut_prod={payload.get('statut_prod')!r}", file=sys.stderr)
    """UPDATE TK_Call_Panier avec les modifs d'une ligne d'offre.

    Met a jour les champs communs (StatutProd, NumBS) + les options
    speciﬁques (Opt_Mandat, FormatNumérique, OPT_AcceptComParte,
    OPT_ConsentConsultDistri, OPT_eCommunication, OPT_eFacture,
    OPT_optinCommercial, OPT_EnergieVerteElec, OPT_EnergieVerteGaz,
    OPT_Reforestation, OPT_Mail).
    Les champs absents du payload restent inchanges (via COALESCE pattern :
    on n'update que ce qui est passe).

    Pour STR : pas de champs supplementaires dans TK_Call_Panier (les
    credentials Login/MDP sont calcules cote backend selon le vendeur,
    Date Activ + Ref Client + Code Vendeur seraient dans une autre table -
    a confirmer avec le user en Phase 3 si besoin de save).
    """
    db_bo = get_connection("ticket_bo")
    now_wd = _sql_now()

    # On construit SET dynamique pour ne toucher que les champs fournis.
    sets = [f"ModifDate = '{now_wd}'"]
    if "statut_prod" in payload:
        sets.append(f"StatutProd = {_to_int(payload.get('statut_prod'))}")
    if "num_bs" in payload:
        sets.append(f"NumBS = '{_sql_str(payload.get('num_bs'))}'")
        # Si on saisit le NumBS pour la 1ere fois -> note Num_DateSaisie
        if payload.get("num_bs"):
            sets.append(f"Num_DateSaisie = '{now_wd}'")
    if "opt_mandat" in payload:
        sets.append(f"Opt_Mandat = {_sql_bool(payload.get('opt_mandat'))}")
    if "opt_maintenance" in payload:
        sets.append(f"Opt_Maintenance = {_sql_bool(payload.get('opt_maintenance'))}")
    if "format_numerique" in payload:
        sets.append(f"FormatNumérique = {_sql_bool(payload.get('format_numerique'))}")
    if "opt_accept_com_parte" in payload:
        sets.append(f"OPT_AcceptComParte = {_sql_bool(payload.get('opt_accept_com_parte'))}")
    if "opt_consent_consult_distri" in payload:
        sets.append(f"OPT_ConsentConsultDistri = {_sql_bool(payload.get('opt_consent_consult_distri'))}")
    if "opt_e_communication" in payload:
        sets.append(f"OPT_eCommunication = {_sql_bool(payload.get('opt_e_communication'))}")
    if "opt_e_facture" in payload:
        sets.append(f"OPT_eFacture = {_sql_bool(payload.get('opt_e_facture'))}")
    if "opt_optin_commercial" in payload:
        sets.append(f"OPT_optinCommercial = {_sql_bool(payload.get('opt_optin_commercial'))}")
    if "opt_energie_verte_elec" in payload:
        sets.append(f"OPT_EnergieVerteElec = {_sql_bool(payload.get('opt_energie_verte_elec'))}")
    if "opt_energie_verte_gaz" in payload:
        sets.append(f"OPT_EnergieVerteGaz = {_sql_bool(payload.get('opt_energie_verte_gaz'))}")
    if "opt_reforestation" in payload:
        sets.append(f"OPT_Reforestation = {_sql_bool(payload.get('opt_reforestation'))}")
    if "opt_mail" in payload:
        sets.append(f"OPT_Mail = {_sql_bool(payload.get('opt_mail'))}")
    if "date_activ" in payload:
        # DateEntrée (champ Date) -> compact YYYYMMDD
        d = _date_to_compact(payload.get('date_activ'))
        sets.append(f"DateEntrée = '{d}'")
    if "ref_client_oen" in payload:
        sets.append(f"Observations = '{_sql_str(payload.get('ref_client_oen'))}'")

    sql = f"""UPDATE TK_Call_Panier SET {', '.join(sets)}
    WHERE IDTK_Call_Panier = {_to_int(id_panier)}"""
    db_bo.query(sql)

    # Cas WinDev OEN : si nouveau statut = 1 ou 3, partenaire OEN et fichier
    # de clarification existe, copier le PDF dans Call_OhmEnergie avec un nom
    # base sur la Ref Client (Observations) + DUAL/MONO selon le produit.
    if "statut_prod" in payload:
        try:
            _copy_clarif_to_ohm_if_oen(id_panier, _to_int(payload.get("statut_prod")))
        except Exception:
            # Effet de bord : un echec de copie ne doit pas faire echouer le save.
            traceback.print_exc(file=sys.stderr)

    return {"ok": True}


_INVALID_FILENAME_CHARS = '<>:"/\\|?*'

def _sanitize_filename(name: str) -> str:
    """Remplace les caracteres interdits dans un nom de fichier Windows."""
    cleaned = "".join("_" if c in _INVALID_FILENAME_CHARS else c for c in name)
    # Strip + max 200 chars pour eviter le path limit Windows
    return cleaned.strip()[:200] or "sans_nom"


def _copy_clarif_to_ohm_if_oen(id_panier: int, statut_prod: int) -> None:
    """Copie le PDF de clarification vers Call_OhmEnergie/<RefClient> (DUAL|MONO).pdf.

    Conditions (transposition WinDev) :
    - Nouveau statut = 1 (Validee) ou 3 (Validee bureau)
    - Partenaire de la ligne = "OEN"
    - Fichier <id_panier>_Clarification.pdf existe dans DOCS_BASE_PATH

    Nom cible : RefClientOen (= TK_Call_Panier.Observations)
              + " (DUAL)" si Lib_produit contient DUAL
              + " (MONO <SousFAM>)" sinon
    Source : OEN_produit (base adv) joint sur IDproduit.
    """
    tag = f"[clarif-oen panier={id_panier}]"
    print(f"{tag} debut statut={statut_prod}", file=sys.stderr)
    if statut_prod not in (1, 3):
        print(f"{tag} skip : statut pas dans (1,3)", file=sys.stderr)
        return

    src = DOCS_BASE_PATH / f"{id_panier}_Clarification.pdf"
    print(f"{tag} src={src} exists={src.exists()}", file=sys.stderr)
    if not src.exists():
        return

    db_bo = get_connection("ticket_bo")
    rows = db_bo.query(
        "SELECT Partenaire, IDproduit, Observations FROM TK_Call_Panier "
        "WHERE IDTK_Call_Panier = ?",
        (id_panier,),
    )
    if not rows:
        print(f"{tag} skip : ligne panier introuvable", file=sys.stderr)
        return
    r = rows[0]
    partenaire = (r.get("Partenaire") or "").upper()
    print(f"{tag} partenaire={partenaire!r}", file=sys.stderr)
    if partenaire != "OEN":
        return

    ref_client = (r.get("Observations") or "").strip()
    print(f"{tag} ref_client={ref_client!r}", file=sys.stderr)
    if not ref_client:
        return  # Pas de ref client -> pas de nom de fichier coherent
    id_produit = _to_int(r.get("IDproduit"))

    # Lib_produit + SousFAM via OEN_produit (base adv)
    lib_produit = ""
    sous_fam = ""
    if id_produit:
        db_adv = get_connection("adv")
        prod_rows = db_adv.query(
            "SELECT Lib_produit, SousFAM FROM OEN_produit WHERE IDproduit = ?",
            (id_produit,),
        )
        if prod_rows:
            lib_produit = (prod_rows[0].get("Lib_produit") or "").strip()
            sous_fam = (prod_rows[0].get("SousFAM") or "").strip()
    print(f"{tag} id_produit={id_produit} lib_produit={lib_produit!r} sous_fam={sous_fam!r}", file=sys.stderr)

    if "DUAL" in lib_produit.upper():
        new_nom = f"{ref_client} (DUAL)"
    else:
        new_nom = f"{ref_client} (MONO {sous_fam})"

    REP_OHM.mkdir(parents=True, exist_ok=True)
    dst = REP_OHM / f"{_sanitize_filename(new_nom)}.pdf"
    print(f"{tag} copy {src} -> {dst}", file=sys.stderr)
    shutil.copy2(src, dst)
    print(f"{tag} OK", file=sys.stderr)


# --- Phase 3 : verrou ope + actions panier --------------------------------

def _parse_dt(v: Any):
    """Wrapper local pour eviter import circulaire avec tickets.py."""
    from app.intranets.call.energie.services.tickets import _parse_dt as _pdt
    return _pdt(v)


def peek_verrou(id_tk_liste: int) -> dict:
    """Etat actuel du verrou ope sur un ticket Energie."""
    db_bo = get_connection("ticket_bo")
    db_rh = get_connection("rh")
    rows = db_bo.query(
        """SELECT IDtk_Call, AppelEnCours, OpéAppel, DateH_Appel
        FROM TK_Call
        WHERE IDTK_Liste = ? AND ModifELEM NOT LIKE '%suppr%'""",
        (id_tk_liste,),
    )
    if not rows:
        return {"error": "Ticket introuvable"}
    r = rows[0]
    appel_en_cours = _bool(r.get("AppelEnCours"))
    ope_appel_id = _to_int(r.get("OpéAppel"))
    date_h_appel_iso = _iso(r.get("DateH_Appel"))
    nom_ope = ""
    if ope_appel_id:
        rs = db_rh.query(
            "SELECT Nom, Prenom FROM Salarie WHERE IDSalarie = ?",
            (ope_appel_id,),
        )
        if rs:
            nom_ope = f"{(rs[0].get('Nom') or '').strip()} {_capitalize((rs[0].get('Prenom') or '').strip())}".strip()
    minutes = 0
    seconds = 0
    dt = _parse_dt(r.get("DateH_Appel"))
    if dt is not None:
        delta = datetime.now() - dt
        total = max(0, int(delta.total_seconds()))
        minutes = total // 60
        seconds = total % 60
    return {
        "appel_en_cours": appel_en_cours,
        "ope_appel_id": ope_appel_id,
        "ope_appel_nom": nom_ope,
        "date_h_appel": date_h_appel_iso,
        "duree_minutes": minutes,
        "duree_secondes": seconds,
    }


def prendre_appel(id_tk_liste: int, user_id: int, force: bool = False) -> dict:
    """Pose le verrou ope sur un ticket Call Energie.

    Si pris par un autre, renvoie needs_confirm=True avec peek. Si force=True,
    ecrase. Envoie un SMS au vendeur.
    """
    db_bo = get_connection("ticket_bo")
    db_rh = get_connection("rh")
    rows = db_bo.query(
        """SELECT IDtk_Call, IDSalarie, AppelEnCours, OpéAppel, DateH_Appel,
            DateDeb_PriseEnCharge, NomClient, NomMaritalClient, PrenomClient
        FROM TK_Call
        WHERE IDTK_Liste = ? AND ModifELEM NOT LIKE '%suppr%'""",
        (id_tk_liste,),
    )
    if not rows:
        return {"error": "Ticket introuvable"}
    r = rows[0]
    id_call = _to_int(r.get("IDtk_Call"))
    id_salarie = _to_int(r.get("IDSalarie"))

    if not force:
        appel_en_cours = _bool(r.get("AppelEnCours"))
        ope_appel_id = _to_int(r.get("OpéAppel"))
        date_h_appel = _parse_dt(r.get("DateH_Appel"))
        if (appel_en_cours and ope_appel_id and ope_appel_id != user_id) or (
            not appel_en_cours and date_h_appel is not None and ope_appel_id != user_id
        ):
            return {"needs_confirm": True, "peek": peek_verrou(id_tk_liste)}

    now_wd = _sql_now()
    db_bo.query(
        f"""UPDATE TK_Call SET
            AppelEnCours = 1,
            OpéAppel = {_to_int(user_id)},
            DateH_Appel = '{now_wd}',
            ModifDate = '{now_wd}'
        WHERE IDtk_Call = {id_call}"""
    )
    if not _parse_dt(r.get("DateDeb_PriseEnCharge")):
        db_bo.query(
            f"""UPDATE TK_Call SET
                DateDeb_PriseEnCharge = '{now_wd}',
                ModifDate = '{now_wd}'
            WHERE IDtk_Call = {id_call}"""
        )

    sms_result = _envoyer_sms_prise_appel(
        db_rh, id_salarie, user_id,
        r.get("NomClient"), r.get("NomMaritalClient"), r.get("PrenomClient"),
    )
    return {"ok": True, "sms": sms_result}


def lacher_appel(id_tk_liste: int) -> dict:
    """Libere le verrou ope."""
    db_bo = get_connection("ticket_bo")
    rows = db_bo.query(
        "SELECT IDtk_Call, DateFin_PriseEnCharge FROM TK_Call WHERE IDTK_Liste = ?",
        (id_tk_liste,),
    )
    if not rows:
        return {"error": "Ticket introuvable"}
    r = rows[0]
    id_call = _to_int(r.get("IDtk_Call"))
    now_wd = _sql_now()
    sets = ["AppelEnCours = 0", f"ModifDate = '{now_wd}'"]
    if not _parse_dt(r.get("DateFin_PriseEnCharge")):
        sets.append(f"DateFin_PriseEnCharge = '{now_wd}'")
    db_bo.query(
        f"""UPDATE TK_Call SET {', '.join(sets)}
        WHERE IDtk_Call = {id_call}"""
    )
    return {"ok": True}


def _format_nom_client_sms(nom: str, nom_marital: str, prenom: str) -> str:
    parts = [(nom or "").strip()]
    if (nom_marital or "").strip():
        parts.append(f"ep {nom_marital.strip()}")
    parts.append(_capitalize((prenom or "").strip()))
    return " ".join(p for p in parts if p)


def _get_gsm_vendeur(db_rh, id_vendeur: int) -> str:
    """Recupere le GSM du vendeur depuis Salarie_Coordonnees."""
    rows = db_rh.query(
        "SELECT TélMob FROM Salarie_Coordonnees WHERE IDSalarie = ?",
        (id_vendeur,),
    )
    if not rows:
        return ""
    gsm = (rows[0].get("TélMob") or "").strip()
    return "".join(c for c in gsm if c.isdigit() or c == "+")


def _envoyer_sms_prise_appel(
    db_rh, id_vendeur: int, id_ope: int,
    nom_client: str, nom_marital: str, prenom_client: str,
) -> str:
    """SMS 'Attention, vous allez bientot recevoir un appel...'"""
    from app.shared.notifications.sms import envoi_sms
    gsm = _get_gsm_vendeur(db_rh, id_vendeur)
    if not gsm:
        return "Pas de GSM vendeur"
    nom_clt = _format_nom_client_sms(nom_client, nom_marital, prenom_client)
    texte = f"Attention, vous allez bientot recevoir un appel du CALL pour votre client {nom_clt}."
    return envoi_sms(texte, gsm, emetteur="Omaya-Call")


def _envoyer_sms_renvoi_complement(
    db_rh, id_vendeur: int,
    nom_client: str, nom_marital: str, prenom_client: str,
) -> str:
    from app.shared.notifications.sms import envoi_sms
    gsm = _get_gsm_vendeur(db_rh, id_vendeur)
    if not gsm:
        return "Pas de GSM vendeur"
    nom_clt = _format_nom_client_sms(nom_client, nom_marital, prenom_client)
    texte = f"Attention, votre panier pour le client {nom_clt} est renvoye pour complement."
    return envoi_sms(texte, gsm, emetteur="Omaya-Call")


def _envoyer_sms_renvoi_clarification(
    db_rh, id_vendeur: int,
    nom_client: str, nom_marital: str, prenom_client: str,
) -> str:
    """SMS specifique : 'panier renvoye car il manque la fiche de clarification'."""
    from app.shared.notifications.sms import envoi_sms
    gsm = _get_gsm_vendeur(db_rh, id_vendeur)
    if not gsm:
        return "Pas de GSM vendeur"
    nom_clt = _format_nom_client_sms(nom_client, nom_marital, prenom_client)
    texte = f"Attention, votre panier pour le client {nom_clt} est renvoye car il manque la fiche de clarification."
    return envoi_sms(texte, gsm, emetteur="Omaya-Call")


# --- Actions panier -------------------------------------------------------

def annuler_ligne_panier(id_panier: int, motifs: list[str], precisions: str) -> dict:
    """UPDATE TK_Call_Panier StatutProd=2 + MotifAnnulation (concat)."""
    if not motifs:
        return {"error": "Merci d'ajouter un motif d'annulation"}
    motif_str = "Motif(s) d'annulation :\n" + "\n".join(f"  - {m}" for m in motifs)
    if (precisions or "").strip():
        motif_str += f"\nInformations complementaires:\n{precisions.strip()}"
    db_bo = get_connection("ticket_bo")
    now_wd = _sql_now()
    db_bo.query(
        f"""UPDATE TK_Call_Panier SET
            StatutProd = 2,
            MotifAnnulation = '{_sql_str(motif_str)}',
            ModifDate = '{now_wd}'
        WHERE IDTK_Call_Panier = {_to_int(id_panier)}"""
    )
    return {"ok": True}


def _action_vente_finale(
    id_tk_liste: int,
    payload: dict,
    new_statut: int,
    sms_kind: str = "",  # "" / "renvoi_complement" / "renvoi_clarification"
    extra_info_vente: str = "",  # texte a appendre dans InfoVente avant save
) -> dict:
    """Logique commune Annul / Valide / Renvoi / Renvoi clarification.

    1. Si extra_info_vente : prepend a payload.vente.info_vente
    2. Si payload : save_vente_infos (UPDATE TK_Call)
    3. UPDATE TK_Liste IDTK_Statut = new_statut
    4. Si verrou actif : libere
    5. SMS optionnel
    """
    db_bo = get_connection("ticket_bo")
    db_ticket = get_connection("ticket")
    db_rh = get_connection("rh")
    now_wd = _sql_now()

    # 0. Si extra_info_vente, on l'ajoute a InfoVente (recup l'ancien, append, save)
    if extra_info_vente:
        rows_cur = db_bo.query(
            "SELECT InfoVente FROM TK_Call WHERE IDTK_Liste = ?",
            (id_tk_liste,),
        )
        prev = (rows_cur[0].get("InfoVente") or "").strip() if rows_cur else ""
        new_info = (prev + "\n" if prev else "") + extra_info_vente
        if payload:
            v = payload.setdefault("vente", {}) or {}
            v["info_vente"] = new_info
        else:
            # Pas de save vente complet -> UPDATE direct InfoVente
            db_bo.query(
                f"""UPDATE TK_Call SET
                    InfoVente = '{_sql_str(new_info)}',
                    ModifDate = '{now_wd}'
                WHERE IDTK_Liste = {_to_int(id_tk_liste)}
                  AND ModifELEM NOT LIKE '%suppr%'"""
            )

    # 1. Save infos vente si payload fourni
    if payload and ("client" in payload or "vente" in payload):
        save_vente_infos(id_tk_liste, payload)

    # 2. Recupere infos pour le SMS
    rows_call = db_bo.query(
        """SELECT IDtk_Call, IDSalarie, AppelEnCours,
            NomClient, NomMaritalClient, PrenomClient
        FROM TK_Call WHERE IDTK_Liste = ?""",
        (id_tk_liste,),
    )
    if not rows_call:
        return {"error": "Ticket introuvable"}
    r_call = rows_call[0]
    id_call = _to_int(r_call.get("IDtk_Call"))
    id_salarie = _to_int(r_call.get("IDSalarie"))
    appel_en_cours = _bool(r_call.get("AppelEnCours"))
    nom_client = r_call.get("NomClient") or ""
    nom_marital = r_call.get("NomMaritalClient") or ""
    prenom_client = r_call.get("PrenomClient") or ""

    # 3. UPDATE TK_Liste IDTK_Statut
    db_ticket.query(
        f"""UPDATE TK_Liste SET
            IDTK_Statut = {new_statut},
            ModifDate = '{now_wd}'
        WHERE IDTK_Liste = {_to_int(id_tk_liste)}"""
    )

    # 4. Libere verrou si actif
    if appel_en_cours:
        db_bo.query(
            f"""UPDATE TK_Call SET
                AppelEnCours = 0,
                DateFin_PriseEnCharge = '{now_wd}',
                ModifDate = '{now_wd}'
            WHERE IDtk_Call = {id_call}"""
        )

    # 5. SMS optionnel
    sms_result = ""
    if sms_kind == "renvoi_complement":
        sms_result = _envoyer_sms_renvoi_complement(
            db_rh, id_salarie, nom_client, nom_marital, prenom_client,
        )
    elif sms_kind == "renvoi_clarification":
        sms_result = _envoyer_sms_renvoi_clarification(
            db_rh, id_salarie, nom_client, nom_marital, prenom_client,
        )

    return {"ok": True, "sms": sms_result}


def annuler_vente(id_tk_liste: int, payload: dict) -> dict:
    """POPUP_AnnulVente : TK_Liste statut=14 + save vente + lacher verrou."""
    return _action_vente_finale(id_tk_liste, payload, new_statut=14)


def valider_vente(id_tk_liste: int, payload: dict) -> dict:
    """POPUP_ValideVente : TK_Liste statut=15 + save vente + lacher verrou."""
    return _action_vente_finale(id_tk_liste, payload, new_statut=15)


def renvoyer_complement(id_tk_liste: int) -> dict:
    """POPUP_RenvoiPanier : TK_Liste statut=28 + lacher verrou + SMS."""
    return _action_vente_finale(
        id_tk_liste, payload={}, new_statut=28, sms_kind="renvoi_complement",
    )


def renvoyer_clarification(id_tk_liste: int, user_nom: str, user_prenom: str) -> dict:
    """Bouton 'Renvoyer pour fiche clarification' (specifique Energie).

    UPDATE TK_Call.InfoVente : append "Ticket renvoye pour fiche clarification
    le {now} par {user}". Puis TK_Liste statut=28 + lacher verrou + SMS specifique.
    """
    info_to_append = (
        f"Ticket renvoye pour fiche clarification le "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')} "
        f"par {user_nom} {_capitalize(user_prenom)}"
    )
    return _action_vente_finale(
        id_tk_liste, payload={}, new_statut=28,
        sms_kind="renvoi_clarification",
        extra_info_vente=info_to_append,
    )


# --- Documents (CIN, KBIS, Justif) ----------------------------------------

def load_clarification(id_panier: int) -> dict:
    """Detecte la fiche de clarification PDF pour une ligne de panier.

    URL (cf. code WinDev) : <DOC_BASE_URL>/{IDTK_Call_Panier}_Clarification.pdf
    Utilise sur la fiche OEN (Ohm Energie).
    """
    url, kind = _first_existing(
        f"{DOC_BASE_URL}/{id_panier}_Clarification.pdf",
    )
    return {"url": url, "kind": kind}


def load_documents(id_tk_liste: int, client_pro: bool = False) -> dict:
    """Detecte les documents disponibles pour un ticket Energie.

    URLs (cf. code WinDev) :
    - CIN    : <idCall>_PieceIdentite.png > <idCall>_CIN.jpg (fallback)
               + <idTicket>_PieceIdentite.pdf (note : par idTicket, pas idCall)
    - KBIS   : <idTicket>_KBIS.png > <idTicket>_KBIS.pdf  (si Pro)
    - Justif : <idCall>_Justif.png > <idCall>_Justif.jpg  (specifique Energie)
    """
    db_bo = get_connection("ticket_bo")
    rows = db_bo.query(
        "SELECT IDtk_Call FROM TK_Call WHERE IDTK_Liste = ? AND ModifELEM NOT LIKE '%suppr%'",
        (id_tk_liste,),
    )
    id_call = _to_int(rows[0].get("IDtk_Call")) if rows else 0

    cin_url, cin_kind = "", ""
    if id_call:
        cin_url, cin_kind = _first_existing(
            f"{DOC_BASE_URL}/{id_tk_liste}_PieceIdentite.pdf",
            f"{DOC_BASE_URL}/{id_call}_PieceIdentite.png",
            f"{DOC_BASE_URL}/{id_call}_CIN.jpg",
        )

    kbis_url, kbis_kind = "", ""
    if client_pro:
        kbis_url, kbis_kind = _first_existing(
            f"{DOC_BASE_URL}/{id_tk_liste}_KBIS.pdf",
            f"{DOC_BASE_URL}/{id_tk_liste}_KBIS.png",
        )

    justif_url, justif_kind = "", ""
    if id_call:
        justif_url, justif_kind = _first_existing(
            f"{DOC_BASE_URL}/{id_call}_Justif.png",
            f"{DOC_BASE_URL}/{id_call}_Justif.jpg",
        )

    return {
        "cin": {"url": cin_url, "kind": cin_kind},
        "kbis": {"url": kbis_url, "kind": kbis_kind},
        "justif": {"url": justif_url, "kind": justif_kind},
    }
