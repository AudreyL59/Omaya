"""
Bibliotheque des procs Ticket Call (Energie + Fibre) portees en PG.

Chaque proc remplace un webservice WinDev (WebRest_Omayapp) au fur et
a mesure que le user fournit la spec. Cf.
`docs/tickets_call_screens_analysis.md` pour la liste complete des 27
endpoints proxy actuels.

Traduction depuis WinDev/WLangage :
- `HExécuteRequête + HLitPremier/HLitSuivant` -> `db.query(...)`.
- `Encode(bytea, encodeBASE64)` -> `base64.b64encode(bytea).decode()`.
- `RVB(r, v, b)` -> `r + v*256 + b*65536` (entier compose WinDev).
- Structures WLangage (`St_Part`, `ST_Ville`, etc.) -> dict Python
  avec les memes cles.
- La verification UUID token (`vérifUUID(idToken)`) est retiree :
  l'authentification est deja faite au niveau du router Vendeur via
  `require_intranet('vendeur')` + les droits (TkCALL / BS_SFR).

Cf. `d:/Claude/WinDev/WebServices/` pour les .txt source.
"""
from __future__ import annotations

import base64
import logging
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

from app.core.config import WEBREST_BASE_URL
from app.core.database.pg import get_pg_connection


logger = logging.getLogger(__name__)


# --------------------------------------------------------------------
# Types de demande (cf. WinDev TK_TypeDemande)
# --------------------------------------------------------------------

IDTK_TYPE_DEMANDE_CALL_ENERGIE = 22
IDTK_TYPE_DEMANDE_CALL_FIBRE = 20

# Statut "en cours de saisie panier" (avant validation client par SMS)
IDTK_STATUT_EN_COURS = 28

# Statut "a traiter" (le panier vient d'etre valide par le client)
IDTK_STATUT_A_TRAITER = 1


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _rvb(r: int | None, v: int | None, b: int | None) -> int:
    """Reproduit RVB(r, v, b) de WinDev : entier compose (couleur 0..16M)."""
    return int(r or 0) + (int(v or 0) << 8) + (int(b or 0) << 16)


def _b64(raw) -> str:
    """Encode bytea en base64 (retourne '' si vide/None)."""
    if not raw:
        return ""
    if isinstance(raw, memoryview):
        raw = bytes(raw)
    if not isinstance(raw, (bytes, bytearray)):
        return ""
    return base64.b64encode(raw).decode("ascii")


def _bool(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    return str(v).strip().lower() in ("true", "1", "vrai", "t", "y", "yes")


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _now_wd() -> datetime:
    """DateHeureSys() de WinDev, cote PG : retourne un objet `datetime`
    (le driver PG le convertit en timestamp natif). Cf. memoire
    feedback_pg_dates_iso : PG refuse le format compact WinDev sur
    colonnes timestamp.
    """
    return datetime.now()


def _new_id_wd() -> int:
    """idEntierDateHeureSys() de WinDev : entier 8 octets base sur
    la date+heure du systeme. On produit 'YYYYMMDDHHMMSSMMM' comme int.
    """
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


def _doc_exists(id_ticket: int, kind: str) -> bool:
    """Test HEAD HTTP sur rest.omaya.fr/DocOmaya/{id}_{kind}.png ou .pdf.

    Remplace la verification `fFichierExiste(cheminParDefaut+...)` qui
    testait le FS local du serveur WinDev. HEAD HTTP est robuste et
    fonctionne quel que soit le serveur d'execution.
    """
    for ext in ("png", "pdf"):
        url = f"{WEBREST_BASE_URL.rstrip('/')}/DocOmaya/{id_ticket}_{kind}.{ext}"
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if 200 <= resp.status < 300:
                    return True
        except urllib.error.HTTPError as e:
            if e.code in (200, 206):
                return True
        except Exception:
            pass
    return False


# Mapping table produits par prefixe partenaire (part_produit dynamique WinDev)
_TABLE_PRODUIT_PAR_PART: dict[str, str] = {
    "OEN": "adv.pgt_oen_produit",
    "ENI": "adv.pgt_eni_produit",
    "STR": "adv.pgt_str_produit",
    "VAL": "adv.pgt_val_produit",
    "PRO": "adv.pgt_pro_produit",
}


def _tab_lib_partenaires() -> dict[str, str]:
    """Reproduit TabLibPartenaires WinDev : {prefixe: lib_partenaire}."""
    db = get_pg_connection("adv")
    try:
        rows = db.query(
            """SELECT prefixe_bdd, lib_partenaire
                 FROM adv.pgt_partenaire""",
        ) or []
    except Exception:
        return {}
    return {
        (r.get("prefixe_bdd") or "").strip(): (r.get("lib_partenaire") or "").strip()
        for r in rows
        if (r.get("prefixe_bdd") or "").strip()
    }


# --------------------------------------------------------------------
# ENERGIE
# --------------------------------------------------------------------

def list_part_call() -> list[dict]:
    """WS `POST /PartCall` -> liste des partenaires actifs pour Call.

    Portage WinDev/WLangage source :
      SELECT * FROM Partenaire
       WHERE IsActif = 1 AND TkCall = 1
       ORDER BY Lib_Partenaire ASC

    Retour : liste de St_Part {Nom, Bdd, Logo (base64), Couleur (RVB)}.
    """
    db = get_pg_connection("adv")
    try:
        rows = db.query(
            """SELECT lib_partenaire, prefixe_bdd, logo,
                      couleur_r, couleur_v, couleur_b
                 FROM adv.pgt_partenaire
                WHERE COALESCE(is_actif, FALSE) = TRUE
                  AND COALESCE(tk_call, FALSE) = TRUE
                ORDER BY lib_partenaire ASC""",
        ) or []
    except Exception:
        logger.exception("list_part_call")
        return []
    return [
        {
            "Nom": (r.get("lib_partenaire") or "").strip(),
            "Bdd": (r.get("prefixe_bdd") or "").strip(),
            "Logo": _b64(r.get("logo")),
            "Couleur": _rvb(r.get("couleur_r"), r.get("couleur_v"),
                             r.get("couleur_b")),
        }
        for r in rows
    ]


# --------------------------------------------------------------------
# WS : POST /Call/ClientsNonFinalises/{idVend}
# --------------------------------------------------------------------

def liste_clients_non_finalises(id_vend: int) -> list[dict]:
    """WS `POST /Call/ClientsNonFinalises/{idVend}`.

    Portage WinDev :
      SELECT ... FROM TK_Liste, TK_Call
       WHERE TypeDemande=22 AND Statut=28 AND !cloturee AND !suppr
         AND TK_Call.IDSalarie = idVend
         AND TK_Call.IDTK_Liste = TK_Liste.IDTK_Liste

    PhotoOK / KbisOK : verification HTTP HEAD sur DocOmaya (remplace
    le test filesystem WinDev, cf. _doc_exists).

    Retour : liste de STTKCall (champs client + PhotoOK + KbisOK).
    """
    db_tk = get_pg_connection("ticket")
    db_bo = get_pg_connection("ticket_bo")
    try:
        rows_liste = db_tk.query(
            """SELECT id_tk_liste FROM ticket.pgt_tk_liste
                WHERE id_tk_type_demande = ?
                  AND id_tk_statut = ?
                  AND COALESCE(cloturee, FALSE) = FALSE
                  AND (modif_elem IS NULL
                       OR modif_elem NOT LIKE '%suppr%')""",
            (IDTK_TYPE_DEMANDE_CALL_ENERGIE, IDTK_STATUT_EN_COURS),
        ) or []
    except Exception:
        logger.exception("liste_clients_non_finalises: pgt_tk_liste")
        return []
    if not rows_liste:
        return []
    ids_sql = ",".join(str(_to_int(r.get("id_tk_liste"))) for r in rows_liste)
    try:
        rows = db_bo.query(
            f"""SELECT id_tk_call, id_tk_liste, id_salarie,
                       civilite_client, nom_client, nom_marital_client,
                       prenom_client, date_naiss, dep_naiss,
                       adresse1, adresse2, cp, ville, adr_mail,
                       mobile1, code_valid, type_logement,
                       client_pro, client_rs, client_siret
                  FROM ticket_bo.pgt_tk_call
                 WHERE id_tk_liste IN ({ids_sql})
                   AND id_salarie = ?""",
            (int(id_vend),),
        ) or []
    except Exception:
        logger.exception("liste_clients_non_finalises: pgt_tk_call")
        return []
    out = []
    for r in rows:
        id_tk = _to_int(r.get("id_tk_liste"))
        out.append({
            "IDTK_Liste": id_tk,
            "CiviliteClient": _to_int(r.get("civilite_client")),
            "NomClient": r.get("nom_client") or "",
            "NomMaritalClient": r.get("nom_marital_client") or "",
            "PrenomClient": r.get("prenom_client") or "",
            "DATENAISS": str(r.get("date_naiss") or ""),
            "DEPNAISS": _to_int(r.get("dep_naiss")),
            "ADRESSE1": r.get("adresse1") or "",
            "ADRESSE2": r.get("adresse2") or "",
            "CP": r.get("cp") or "",
            "VILLE": r.get("ville") or "",
            "adrMail": r.get("adr_mail") or "",
            "Mobile1": r.get("mobile1") or "",
            "TypeLogement": _to_int(r.get("type_logement")),
            "Code": r.get("code_valid") or "",
            "PhotoOK": _doc_exists(id_tk, "PieceIdentite"),
            "KbisOK": _doc_exists(id_tk, "KBIS"),
            "ClientPro": _bool(r.get("client_pro")),
            "ClientRS": r.get("client_rs") or "",
            "ClientSiret": r.get("client_siret") or "",
        })
    return out


# --------------------------------------------------------------------
# WS : POST /Call/ClientsNonFinalises/Panier/{idTicket}
# --------------------------------------------------------------------

def contenu_panier_call(id_ticket: int) -> list[dict]:
    """WS `POST /Call/ClientsNonFinalises/Panier/{idTicket}`.

    Portage :
      SELECT ... FROM TK_Call_Panier WHERE IDTK_Liste = ?
      -> resolution lib_offre par partenaire (SELECT dyn sur part_produit).

    OHM : lib hardcode 'Pompe a chaleur'.
    """
    db_bo = get_pg_connection("ticket_bo")
    db_adv = get_pg_connection("adv")
    lib_partenaires = _tab_lib_partenaires()
    try:
        rows = db_bo.query(
            """SELECT id_tk_call_panier, id_tk_call, id_tk_liste,
                      partenaire, id_produit, num_bs,
                      opt_energie_verte_elec, opt_reforestation,
                      opt_energie_verte_gaz, opt_mail, opt_mandat,
                      format_numerique
                 FROM ticket_bo.pgt_tk_call_panier
                WHERE id_tk_liste = ?""",
            (int(id_ticket),),
        ) or []
    except Exception:
        logger.exception("contenu_panier_call")
        return []
    out = []
    for r in rows:
        part = (r.get("partenaire") or "").strip().upper()
        id_prod = _to_int(r.get("id_produit"))
        lib_offre = ""
        if part == "OHM":
            lib_offre = "Pompe à chaleur"
        elif part in _TABLE_PRODUIT_PAR_PART and id_prod:
            table = _TABLE_PRODUIT_PAR_PART[part]
            try:
                p = db_adv.query_one(
                    f"SELECT lib_produit FROM {table} WHERE id_produit = ?",
                    (id_prod,),
                )
                lib_offre = ((p or {}).get("lib_produit") or "").strip()
            except Exception:
                logger.exception("lib_produit lookup part=%s", part)
        out.append({
            "IDtk_Call_Panier": _to_int(r.get("id_tk_call_panier")),
            "Part": lib_partenaires.get(part, part),
            "IDProduit": id_prod,
            "LibOffre": lib_offre,
            "NumBS": r.get("num_bs") or "",
        })
    return out


# --------------------------------------------------------------------
# WS : POST /Call/ClientsNonFinalises/Suppr/{idVend}
# --------------------------------------------------------------------

def supprimer_ticket_call(id_tk_liste: int, id_vendeur: int) -> dict:
    """WS `POST /Call/ClientsNonFinalises/Suppr/{idVend}`.

    Portage WinDev SupprClientNonFinalise :
      UPDATE TK_Liste SET ModifDate=now, ModifOP=idVend, ModifELEM='suppr'
       WHERE IDTK_Liste = ?

    Suppression LOGIQUE (pas de DELETE physique). Le ticket disparaitra
    de la liste des non-finalises car liste_clients_non_finalises filtre
    sur `modif_elem NOT LIKE '%suppr%'`.
    """
    db_tk = get_pg_connection("ticket")
    now = _now_wd()
    try:
        db_tk.query(
            """UPDATE ticket.pgt_tk_liste
                  SET modif_elem = 'suppr',
                      modif_date = ?,
                      modif_op = ?
                WHERE id_tk_liste = ?""",
            (now, int(id_vendeur), int(id_tk_liste)),
        )
        return {"nIdDemande": 0}   # WinDev renvoie 0 en cas de succes
    except Exception as e:
        logger.exception("supprimer_ticket_call")
        return {"nIdDemande": 0, "sInfoData": str(e)}


# ====================================================================
# FIBRE SFR
# ====================================================================

# --------------------------------------------------------------------
# WS : POST /CallSFR/ClientsNonFinalises/{idVend}
# --------------------------------------------------------------------

def sfr_liste_clients_non_finalises(id_vend: int) -> list[dict]:
    """WS `POST /CallSFR/ClientsNonFinalises/{idVend}`.

    Portage WinDev Liste_ClientsNonFinalisés (Fibre) :
      SELECT ... FROM TK_CallSFR INNER JOIN TK_Liste
       WHERE TypeDemande=20 AND Statut=28 AND !cloturee AND !suppr
         AND TK_CallSFR.IDSalarie = idVend

    PhotoOK / KbisOK : HEAD HTTP DocOmaya (identique cote Energie).
    """
    db_tk = get_pg_connection("ticket")
    db_bo = get_pg_connection("ticket_bo")
    try:
        rows = db_bo.query(
            """SELECT tc.id_tk_call_sfr, tc.id_tk_liste, tc.id_salarie,
                      tc.civilite_client, tc.nom_client, tc.nom_marital_client,
                      tc.prenom_client, tc.date_naiss, tc.dep_naiss,
                      tc.adresse1, tc.adresse2, tc.cp, tc.ville, tc.adr_mail,
                      tc.mobile1, tc.mobile2, tc.code_valid, tc.type_logement,
                      tc.client_pro, tc.client_rs, tc.client_siret
                 FROM ticket_bo.pgt_tk_call_sfr tc
                 INNER JOIN ticket.pgt_tk_liste tl
                   ON tl.id_tk_liste = tc.id_tk_liste
                WHERE tl.id_tk_type_demande = ?
                  AND tl.id_tk_statut = ?
                  AND COALESCE(tl.cloturee, FALSE) = FALSE
                  AND (tl.modif_elem IS NULL
                       OR tl.modif_elem NOT LIKE '%suppr%')
                  AND tc.id_salarie = ?""",
            (IDTK_TYPE_DEMANDE_CALL_FIBRE, IDTK_STATUT_EN_COURS, int(id_vend)),
        ) or []
    except Exception:
        logger.exception("sfr_liste_clients_non_finalises")
        return []
    _ = db_tk  # keep import stable
    out = []
    for r in rows:
        id_tk = _to_int(r.get("id_tk_liste"))
        out.append({
            "IDTK_Liste": id_tk,
            "CiviliteClient": _to_int(r.get("civilite_client")),
            "NomClient": r.get("nom_client") or "",
            "NomMaritalClient": r.get("nom_marital_client") or "",
            "PrenomClient": r.get("prenom_client") or "",
            "DATENAISS": str(r.get("date_naiss") or ""),
            "DEPNAISS": _to_int(r.get("dep_naiss")),
            "ADRESSE1": r.get("adresse1") or "",
            "ADRESSE2": r.get("adresse2") or "",
            "CP": r.get("cp") or "",
            "VILLE": r.get("ville") or "",
            "adrMail": r.get("adr_mail") or "",
            "Mobile1": r.get("mobile1") or "",
            "Mobile2": r.get("mobile2") or "",
            "TypeLogement": _to_int(r.get("type_logement")),
            "Code": r.get("code_valid") or "",
            "PhotoOK": _doc_exists(id_tk, "PieceIdentite"),
            "KbisOK": _doc_exists(id_tk, "KBIS"),
            "ClientPro": _bool(r.get("client_pro")),
            "ClientRS": r.get("client_rs") or "",
            "ClientSiret": r.get("client_siret") or "",
        })
    return out


# --------------------------------------------------------------------
# WS : GET /CallSFR/AnomalieListe
# --------------------------------------------------------------------

def sfr_liste_anomalie() -> list[dict]:
    """WS `GET /CallSFR/AnomalieListe`.

    Portage :
      SELECT id_tk_call_sfr_type_anomalie, lib_type_anomalie
        FROM pgt_tk_callsfr_typeanomalie
       WHERE modif_elem NOT LIKE '%suppr%'
         AND id_tk_call_sfr_type_anomalie <> 0
       ORDER BY id_tk_call_sfr_type_anomalie ASC

    Note : nom PG = pgt_tk_callsfr_typeanomalie (sans underscore
    entre call/sfr et type/anomalie).
    """
    db = get_pg_connection("ticket_bo")
    try:
        rows = db.query(
            """SELECT id_tk_call_sfr_type_anomalie, lib_type_anomalie
                 FROM ticket_bo.pgt_tk_callsfr_typeanomalie
                WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                  AND id_tk_call_sfr_type_anomalie <> 0
                ORDER BY id_tk_call_sfr_type_anomalie ASC""",
        ) or []
    except Exception:
        logger.exception("sfr_liste_anomalie")
        return []
    return [
        {
            "IDtk_CallSFR_Anomalie": _to_int(r.get("id_tk_call_sfr_type_anomalie")),
            "LibTypeAnomalie": r.get("lib_type_anomalie") or "",
        }
        for r in rows
    ]


# --------------------------------------------------------------------
# WS : POST /CallSFR/ClientsNonFinalises/Panier/{idTicket}
# --------------------------------------------------------------------

def sfr_contenu_panier(id_ticket: int) -> list[dict]:
    """WS `POST /CallSFR/ClientsNonFinalises/Panier/{idTicket}`.

    Portage :
      SELECT tp.*, o.lib_offre, o.prix_offre
        FROM TK_CallSFR_Panier tp, SFR_OffresProvad o
       WHERE tp.IDTK_Liste = ? AND tp.IDOffres_SFR = o.IDOffres_SFR
         AND tp.ModifELEM <> 'suppr'
       ORDER BY tp.TYPE ASC, o.Lib_Offre ASC
    """
    db = get_pg_connection("ticket_bo")
    try:
        rows = db.query(
            """SELECT tp.id_tk_call_sfr_panier, tp.id_tk_call_sfr,
                      tp.id_tk_liste, tp.type, tp.id_offres_sfr,
                      tp.num_portabilite, tp.num,
                      o.lib_offre, o.prix_offre
                 FROM ticket_bo.pgt_tk_call_sfr_panier tp
                 JOIN adv.pgt_sfr_offres_provad o
                   ON o.id_offres_sfr = tp.id_offres_sfr
                WHERE tp.id_tk_liste = ?
                  AND (tp.modif_elem IS NULL OR tp.modif_elem <> 'suppr')
                ORDER BY tp.type ASC, o.lib_offre ASC""",
            (int(id_ticket),),
        ) or []
    except Exception:
        logger.exception("sfr_contenu_panier")
        return []
    return [
        {
            "IDtk_CallSFR_Panier": _to_int(r.get("id_tk_call_sfr_panier")),
            "Type": r.get("type") or "",
            "IDOffres_SFR": _to_int(r.get("id_offres_sfr")),
            "LibOffre": r.get("lib_offre") or "",
            "MontantOffre": float(r.get("prix_offre") or 0),
            "NumPortabilite": r.get("num_portabilite") or "",
        }
        for r in rows
    ]


# --------------------------------------------------------------------
# WS : POST /CallSFR/ClientsNonFinalises/Suppr/{idVend}
# --------------------------------------------------------------------

def sfr_supprimer_ticket(id_tk_liste: int, id_vendeur: int) -> dict:
    """WS `POST /CallSFR/ClientsNonFinalises/Suppr/{idVend}`.

    IDENTIQUE a la version Energie (impl WinDev commune) :
      UPDATE TK_Liste SET modif_elem='suppr', modif_op, modif_date
    """
    return supprimer_ticket_call(id_tk_liste, id_vendeur)


# --------------------------------------------------------------------
# WS : GET /SFR/ListerOffres/{type}/{avecTV}
# --------------------------------------------------------------------

def sfr_lister_offres(type_offre: str, avec_tv: bool) -> list[dict]:
    """WS `GET /SFR/ListerOffres/{type}/{avecTV}`.

    Portage : SELECT sur pgt_sfr_offres_provad WHERE type=? +
    formatage Lib_Offre (remplace 'standard' -> 'STD', supprime 'offre ')
    + ajoute ' SE' si engagement contient 'Sans engagement' +
    prefixe 'Engagement : ' si absent.

    Pour type FIBRE|FIB PRO : filtre les offres selon avecTV
    (Lib_Offre contient 'TV' ou 'High Tech' == avecTV).
    """
    db = get_pg_connection("adv")
    try:
        rows = db.query(
            """SELECT id_offres_sfr, type, lib_offre, debit_down, debit_up,
                      prix_offre, recurrence, prix_pro_ttc, engagement,
                      en_promo, info_promo, service_inclus, online
                 FROM adv.pgt_sfr_offres_provad
                WHERE type = ?
                  AND COALESCE(online, FALSE) = TRUE
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY lib_offre ASC""",
            (type_offre,),
        ) or []
    except Exception:
        logger.exception("sfr_lister_offres type=%s", type_offre)
        return []
    out = []
    for r in rows:
        lib_offre = (r.get("lib_offre") or "").strip()
        # Formatage identique WinDev
        lib_offre = _replace_ci(lib_offre, "standard", "STD")
        lib_offre = _replace_ci(lib_offre, "offre ", "")
        engagement = (r.get("engagement") or "").strip()
        if "sans engagement" in engagement.lower():
            lib_offre += " SE"
        if "engagement" not in engagement.lower():
            engagement = f"Engagement : {engagement}" if engagement else ""

        # Filtre TV : Lib_Offre contient 'TV' ou 'High Tech'
        if type_offre in ("FIBRE", "FIB PRO"):
            has_tv = ("tv" in lib_offre.lower()
                      or "high tech" in lib_offre.lower())
            if has_tv != bool(avec_tv):
                continue
        out.append({
            "IDOffres_SFR": _to_int(r.get("id_offres_sfr")),
            "Type": r.get("type") or "",
            "Lib_Offre": lib_offre,
            "DebitDown": r.get("debit_down") or "",
            "DebitUp": r.get("debit_up") or "",
            "PrixOffre": float(r.get("prix_offre") or 0),
            "Recurrence": r.get("recurrence") or "",
            "PrixProTTC": r.get("prix_pro_ttc") or "",
            "Engagement": engagement,
            "EnPromo": _bool(r.get("en_promo")),
            "InfoPromo": r.get("info_promo") or "",
            "ServiceInclus": r.get("service_inclus") or "",
            "Online": _bool(r.get("online")),
        })
    return out


def _replace_ci(s: str, old: str, new: str) -> str:
    """Remplacement insensible a la casse (WinDev Remplace(SansCasse))."""
    import re
    return re.sub(re.escape(old), new, s, flags=re.IGNORECASE)


# --------------------------------------------------------------------
# WS : POST /CallSFR/ClientsNonFinalises/Panier/Produit/Ajout
# --------------------------------------------------------------------

def sfr_ajouter_produit_panier(payload: dict) -> dict:
    """WS `POST /CallSFR/.../Panier/Produit/Ajout`.

    Portage AjoutProdSFR : INSERT dans pgt_tk_call_sfr_panier.

    NOTE : le rename du fichier LettreResil {id}_LettreResil.pdf ->
    {id}_{panier}_LettreResil.pdf (cf. WinDev) est SKIPPE ici. Le
    fichier est sur DocOmaya (serveur distant) et notre backend Vendeur
    n'a pas d'acces filesystem direct. A traiter en Phase 3+ si besoin
    via un endpoint dedie POST /rest.omaya.fr/rename ou similaire.
    """
    db = get_pg_connection("ticket_bo")
    id_panier = _new_id_wd()
    now = _now_wd()
    try:
        db.query(
            """INSERT INTO ticket_bo.pgt_tk_call_sfr_panier (
                  id_tk_call_sfr_panier, id_tk_call_sfr, id_tk_liste,
                  id_offres_sfr, opt_tv, type,
                  portabilite, num_portabilite, num_prise_rio,
                  num_prise_optique, opt_choisies, type_vente,
                  num, num_date_saisie, statut_prod, motif_annulation,
                  modif_date, modif_op, modif_elem
              ) VALUES (
                  ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?, ?,
                  '', NULL, 0, '',
                  ?, ?, 'new'
              )""",
            (
                id_panier,
                _to_int(payload.get("IDtk_CallSFR")),
                _to_int(payload.get("IDTK_Liste")),
                _to_int(payload.get("IDOffres_SFR")),
                _bool(payload.get("Opt_TV")),
                payload.get("Type") or "",
                _bool(payload.get("Portabilite")),
                payload.get("NumPortabilite") or "",
                payload.get("NumPrise_RIO") or "",
                payload.get("NumPriseOptique") or "",
                payload.get("OptionsChoisies") or "",
                _to_int(payload.get("TypeVente")),
                now, _to_int(payload.get("IDSalarie")),
            ),
        )
        return {"nIdDemande": id_panier}
    except Exception as e:
        logger.exception("sfr_ajouter_produit_panier")
        return {"nIdDemande": 0, "sInfoData": str(e)}


# --------------------------------------------------------------------
# WS : POST /CallSFR/ClientsNonFinalises/Panier/Produit/Suppr
# --------------------------------------------------------------------

def sfr_supprimer_produit_panier(id_tk_call_sfr_panier: int) -> dict:
    """WS `POST /CallSFR/.../Panier/Produit/Suppr`.

    Portage SuppProdPanierSFR : UPDATE modif_elem='suppr' + modif_date
    (suppression LOGIQUE contrairement au Panier Energie qui fait un
    DELETE physique — divergence WinDev).
    """
    db = get_pg_connection("ticket_bo")
    now = _now_wd()
    try:
        db.query(
            """UPDATE ticket_bo.pgt_tk_call_sfr_panier
                  SET modif_elem = 'suppr', modif_date = ?
                WHERE id_tk_call_sfr_panier = ?""",
            (now, int(id_tk_call_sfr_panier)),
        )
        return {"nIdDemande": 0}
    except Exception as e:
        logger.exception("sfr_supprimer_produit_panier")
        return {"nIdDemande": 0, "sInfoData": str(e)}


# --------------------------------------------------------------------
# WS : POST /CallSFR/ClientsNonFinalises/EnvoiLien/{code}
# --------------------------------------------------------------------

def sfr_envoi_lien_client(id_tk_liste: int, code: str) -> dict:
    """WS `POST /CallSFR/.../EnvoiLien/{code}`.

    Portage identique a la version Energie mais avec :
    - UPDATE sur pgt_tk_call_sfr
    - Lien : ...?P1=**SFR**{id} (vs ENI pour Energie)
    """
    db = get_pg_connection("ticket_bo")
    now = _now_wd()
    try:
        db.query(
            """UPDATE ticket_bo.pgt_tk_call_sfr
                  SET code_valid = ?, modif_date = ?
                WHERE id_tk_liste = ?""",
            (str(code)[:6], now, int(id_tk_liste)),
        )
        r = db.query_one(
            """SELECT mobile1, adr_mail, nom_client, prenom_client
                 FROM ticket_bo.pgt_tk_call_sfr WHERE id_tk_liste = ?""",
            (int(id_tk_liste),),
        )
    except Exception as e:
        logger.exception("sfr_envoi_lien_client")
        return {"nIdDemande": 0, "sInfoData": str(e)}
    if not r:
        return {"nIdDemande": 0, "sInfoData": "Ticket introuvable"}
    lien = (
        f"https://groupe-exo.omaya.fr/PAGESEXTERNES_WEB/FR/"
        f"Page-ConsentClient.awp?P1=SFR{id_tk_liste}"
    )
    mobile = (r.get("mobile1") or "").strip()
    mail = (r.get("adr_mail") or "").strip()
    nom = r.get("nom_client") or ""
    prenom = r.get("prenom_client") or ""
    if mobile:
        try:
            from app.shared.notifications.sms import envoi_sms
            texte = (
                "Bonjour,\n"
                "Veuillez cliquer sur le lien suivant pour obtenir "
                f"le code de validation.\n{lien}"
            )
            envoi_sms(texte, mobile, emetteur="Code-Verify")
        except Exception:
            logger.exception("envoi_sms sfr")
    try:
        _envoyer_mail_code_validation(mail, nom, prenom, lien)
    except Exception:
        logger.exception("_envoyer_mail_code_validation sfr")
    return {"nIdDemande": id_tk_liste}


# --------------------------------------------------------------------
# WS : POST /CallSFR/ClientsNonFinalises/Validation/{idVend}
# --------------------------------------------------------------------

def sfr_validation_tk_call(id_tk_liste: int, id_vend: int) -> dict:
    """WS `POST /CallSFR/.../Validation/{idVend}`.

    Portage ValidTkCallSFR :
      UPDATE TK_Liste SET IDTK_Statut=1, DATECREA=now, ModifDate=now,
                          ModifOP=idVend
       WHERE IDTK_Liste = ?

    NOTE : le WinDev fait aussi une conversion PieceIdentite.png ->
    CIN.jpg via dChargeImage + dSauveImageJPEG. Skip cote Python
    (acces FS distant), non critique fonctionnellement.
    """
    db = get_pg_connection("ticket")
    try:
        db.query(
            """UPDATE ticket.pgt_tk_liste
                  SET id_tk_statut = ?, date_crea = ?,
                      modif_date = ?, modif_op = ?
                WHERE id_tk_liste = ?""",
            (IDTK_STATUT_A_TRAITER, datetime.now(),
             datetime.now(), int(id_vend), int(id_tk_liste)),
        )
        return {"nIdDemande": id_tk_liste}
    except Exception as e:
        logger.exception("sfr_validation_tk_call")
        return {"nIdDemande": 0, "sInfoData": str(e)}


# --------------------------------------------------------------------
# WS : GET /CallSFR/ClientsNonFinalises/VerifPhoto/{idTicket}/{type}
# --------------------------------------------------------------------

def sfr_verif_photo(id_tk_liste: int, nom_photo: str) -> dict:
    """WS `GET /CallSFR/.../VerifPhoto/{id}/{type}`. Identique Energie."""
    return verif_photo(id_tk_liste, nom_photo)


# --------------------------------------------------------------------
# WS : POST /CallSFR/NouveauTK/{idVend}
# --------------------------------------------------------------------

def sfr_crea_modif_tk_call(payload: dict, id_vend: int) -> dict:
    """WS `POST /CallSFR/NouveauTK/{idVend}` (AjoutTicketCallSFR).

    Portage : identique a la version Energie mais avec :
    - Insertion dans pgt_tk_call_sfr (Fibre) au lieu de pgt_tk_call
    - Mobile1 + Mobile2 (les 2 sont formates ChaîneFormate sans
      ponctuation / espace)
    - Meme validations metier (anti-doublon tel client / salarie,
      blocage > 75 ans, mail alerte 'ALERT CALL SFR' au lieu de 'ALERT
      CALL Energie')
    - type_demande = 20 (Fibre)

    """
    from datetime import date as _date
    db_bo = get_pg_connection("ticket_bo")
    db_tk = get_pg_connection("ticket")
    db_rh = get_pg_connection("rh")

    id_ticket = _new_id_wd()
    nom_client = (payload.get("NomClient") or "").strip()
    prenom_client = (payload.get("PrenomClient") or "").strip()
    mobile1 = _format_num_tel(payload.get("Mobile1") or "")
    mobile2 = _format_num_tel(payload.get("Mobile2") or "")

    # Recup nom vendeur
    nom_vend = ""
    try:
        r = db_rh.query_one(
            "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ?",
            (int(id_vend),),
        )
        if r:
            nom_vend = (
                (r.get("nom") or "").strip() + " "
                + (r.get("prenom") or "").strip().capitalize()
            ).strip()
    except Exception:
        logger.exception("sfr_crea_modif_tk_call: nom_vend")

    alert_mail = ""
    info_blocage = ""

    # 1. Anti-doublon tel client (pgt_tk_call_sfr)
    for mob in (mobile1, mobile2):
        if not mob:
            continue
        try:
            r_dup = db_bo.query_one(
                """SELECT nom_client, prenom_client, adresse1, cp, ville
                     FROM ticket_bo.pgt_tk_call_sfr
                    WHERE mobile1 = ?""",
                (mob,),
            )
        except Exception:
            r_dup = None
        if r_dup:
            aff = _affectation_terrain_vendeur(id_vend)
            nom1 = (
                (r_dup.get("nom_client") or "") + " "
                + (r_dup.get("prenom_client") or "").capitalize()
            ).strip()
            adr1 = " ".join([
                r_dup.get("adresse1") or "",
                r_dup.get("cp") or "",
                r_dup.get("ville") or "",
            ]).strip()
            nom2 = f"{nom_client} {prenom_client.capitalize()}".strip()
            adr2 = f"{payload.get('ADRESSE1') or ''} {payload.get('CP') or ''} {payload.get('VILLE') or ''}".strip()
            alert_mail += (
                f"<p>Attention, {nom_vend} ({aff}) fait un ticket CALL avec "
                f"un numéro de tél client déjà utilisé.</p>"
                f"<p>Info Client en base : {nom1} {adr1}</p>"
                f"<p>Info Client en cours : {nom2} {adr2}</p>"
            )
            break

    # 2. Anti-doublon tel salarie
    for mob in (mobile1, mobile2):
        if not mob:
            continue
        try:
            r_sal = db_rh.query_one(
                """SELECT s.id_salarie, s.nom, s.prenom
                     FROM rh.pgt_salarie_coordonnees sc
                     JOIN rh.pgt_salarie s ON s.id_salarie = sc.id_salarie
                    WHERE sc.tel_mob = ?""",
                (mob,),
            )
        except Exception:
            r_sal = None
        if r_sal:
            aff = _affectation_terrain_vendeur(id_vend)
            if _to_int(r_sal.get("id_salarie")) == int(id_vend):
                alert_mail += (
                    f"<p>Attention, {nom_vend} ({aff}) fait un ticket CALL "
                    f"avec son propre numéro de tél.</p>"
                )
                info_blocage = "REFUS TICKET : Il est INTERDIT d'utiliser son numéro de téléphone !"
            else:
                nom_v = (
                    (r_sal.get("nom") or "") + " "
                    + (r_sal.get("prenom") or "").capitalize()
                ).strip()
                aff_v = _affectation_terrain_vendeur(_to_int(r_sal.get("id_salarie")))
                alert_mail += (
                    f"<p>Attention, {nom_vend} ({aff}) fait un ticket CALL "
                    f"avec le numéro de tél de {nom_v} ({aff_v}).</p>"
                )
            break

    # 3. Blocage > 75 ans
    dnaiss_raw = (payload.get("DATENAISS") or "").strip()
    if dnaiss_raw and len(dnaiss_raw) >= 8:
        try:
            dt = _date(int(dnaiss_raw[0:4]), int(dnaiss_raw[4:6]),
                        int(dnaiss_raw[6:8]))
            today = _date.today()
            age = today.year - dt.year - (
                (today.month, today.day) < (dt.month, dt.day)
            )
            if age > 75:
                info_blocage = (
                    "REFUS TICKET : Il est INTERDIT de faire signer une "
                    "personne de plus de 75 ans !"
                )
                aff = _affectation_terrain_vendeur(id_vend)
                nom2 = f"{nom_client} {prenom_client.capitalize()}".strip()
                adr2 = f"{payload.get('ADRESSE1') or ''} {payload.get('CP') or ''} {payload.get('VILLE') or ''}".strip()
                dnaiss_fr = f"{dnaiss_raw[6:8]}/{dnaiss_raw[4:6]}/{dnaiss_raw[0:4]}"
                alert_mail += (
                    f"<p>Attention, {nom_vend} ({aff}) fait un ticket CALL "
                    f"avec à une personne de plus de 75 ans.</p>"
                    f"<p>Info Client : {nom2}</p>"
                    f"<p>Adresse : {adr2}</p>"
                    f"<p>Date naiss : {dnaiss_fr}</p>"
                )
        except (ValueError, TypeError):
            pass

    if alert_mail:
        _envoyer_alert_sfr(alert_mail)

    # 5. INSERT pgt_tk_call_sfr + pgt_tk_liste
    now = _now_wd()
    try:
        db_bo.query(
            """INSERT INTO ticket_bo.pgt_tk_call_sfr (
                  id_tk_call_sfr, id_tk_liste, id_salarie,
                  civilite_client, nom_client, nom_marital_client,
                  prenom_client, date_naiss, dep_naiss,
                  adresse1, adresse2, cp, ville, adr_mail,
                  mobile1, mobile2,
                  type_logement, client_pro, client_rs, client_siret,
                  intervention_vend, mob_propo_vend, info_vente,
                  code_valid, opt_rappel, opt_partenaire,
                  anomalie_mobile, id_tk_call_sfr_type_anomalie,
                  id_tk_liste_ref_anomalie, info_cplt_anomalie,
                  ticket_diff, motif_annulation,
                  modif_op, modif_date, modif_elem
              ) VALUES (
                  ?, ?, ?, ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?,
                  ?, ?,
                  ?, ?, ?, ?,
                  FALSE, FALSE, '',
                  '', FALSE, FALSE,
                  FALSE, 0,
                  0, '',
                  FALSE, '',
                  ?, ?, 'new'
              )""",
            (
                id_ticket, id_ticket, int(id_vend),
                _to_int(payload.get("CiviliteClient")),
                nom_client,
                payload.get("NomMaritalClient") or "",
                prenom_client,
                dnaiss_raw or None,
                _to_int(payload.get("DEPNAISS")),
                payload.get("ADRESSE1") or "",
                payload.get("ADRESSE2") or "",
                payload.get("CP") or "",
                payload.get("VILLE") or "",
                payload.get("adrMail") or "",
                mobile1, mobile2,
                _to_int(payload.get("TypeLogement")),
                _bool(payload.get("ClientPro")),
                payload.get("ClientRS") or "",
                payload.get("ClientSiret") or "",
                int(id_vend),
                now,
            ),
        )
    except Exception as e:
        logger.exception("sfr_crea_modif_tk_call: INSERT pgt_tk_call_sfr")
        return {"nIdDemande": 0, "sInfoData": str(e)}

    try:
        db_tk.query(
            """INSERT INTO ticket.pgt_tk_liste (
                  id_tk_liste, date_crea, op_crea, op_dest, service,
                  id_tk_type_demande, id_tk_statut, cloturee,
                  modif_date, modif_op, modif_elem
              ) VALUES (
                  ?, ?, ?, ?, 'BO', ?, ?, FALSE, ?, ?, 'new'
              )""",
            (
                id_ticket, datetime.now(), int(id_vend), int(id_vend),
                IDTK_TYPE_DEMANDE_CALL_FIBRE, IDTK_STATUT_EN_COURS,
                datetime.now(), int(id_vend),
            ),
        )
    except Exception as e:
        logger.exception("sfr_crea_modif_tk_call: INSERT pgt_tk_liste")
        return {"nIdDemande": 0, "sInfoData": str(e)}

    return {"nIdDemande": id_ticket, "sInfoData": info_blocage}


# --------------------------------------------------------------------
# WS : POST /CallSFR/ClientsNonFinalises/AnomalieMobile/{idVend}/{type}
# --------------------------------------------------------------------

def sfr_vente_mobile_diff(
    id_tk_liste: int,
    id_tk_call_sfr_anomalie: int,
    info_cplt_anomalie: str,
    id_vendeur: int,
    type_val: int,
) -> dict:
    """WS `POST /CallSFR/.../AnomalieMobile/{idVend}/{type}`.

    Portage WinDev VenteMobileDiff_ClientNonFinalise :
      UPDATE TK_CallSFR
         SET AnomalieMobile = type,
             IDTK_CallSFR_TypeAnomalie = idAnomalie,
             InfoCpltAnomalie = infoCplt,
             ModifDate = now, ModifOP = idVend, ModifELEM = 'modif'
       WHERE IDTK_Liste = ?

    Le param `type` (0 = init bascule vente differee, 1 = update motif)
    va dans la colonne `anomalie_mobile` (semantique 'flag actif').
    """
    db = get_pg_connection("ticket_bo")
    now = _now_wd()
    try:
        db.query(
            """UPDATE ticket_bo.pgt_tk_call_sfr
                  SET anomalie_mobile = ?,
                      id_tk_call_sfr_type_anomalie = ?,
                      info_cplt_anomalie = ?,
                      modif_date = ?,
                      modif_op = ?,
                      modif_elem = 'modif'
                WHERE id_tk_liste = ?""",
            (
                _bool(type_val),
                int(id_tk_call_sfr_anomalie),
                info_cplt_anomalie or "",
                now,
                int(id_vendeur),
                int(id_tk_liste),
            ),
        )
        return {"nIdDemande": 0}
    except Exception as e:
        logger.exception("sfr_vente_mobile_diff")
        return {"nIdDemande": 0, "sInfoData": str(e)}


def _envoyer_alert_sfr(alert_html: str) -> None:
    """Mail 'ALERT CALL SFR' (idem alert Energie mais sujet different)."""
    from app.shared.notifications.mail import envoi_mail
    try:
        envoi_mail(
            sujet="ALERT CALL SFR",
            html=(
                "<font face='arial' style='font-size:10pt;'><p>Bonjour,</p>"
                f"{alert_html}"
                "<p>Cdt<br/>Service INTRANET</p></font>"
            ),
            destinataires=["bo@exosphere.fr", "a.loudieux@exosphere.fr"],
            cci=["intranet@omaya.fr"],
            expediteur="intranet@omaya.fr",
        )
    except Exception:
        logger.exception("_envoyer_alert_sfr")


# --------------------------------------------------------------------
# WS : POST /Call/ProduitActifs/{part}
# --------------------------------------------------------------------

def liste_produit_actif_by_part(part: str) -> list[dict]:
    """WS `POST /Call/ProduitActifs/{part}`.

    Portage : SELECT * FROM {part}_produit
      WHERE modif_elem <> 'suppr' AND pro_actif = 1

    Retour : liste de STProduitSte {IDProduit, LibProd}.
    """
    part_up = (part or "").strip().upper()
    table = _TABLE_PRODUIT_PAR_PART.get(part_up)
    if not table:
        return []
    db = get_pg_connection("adv")
    try:
        rows = db.query(
            f"""SELECT id_produit, lib_produit FROM {table}
                 WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
                   AND COALESCE(pro_actif, 0) = 1""",
        ) or []
    except Exception:
        logger.exception("liste_produit_actif_by_part part=%s", part_up)
        return []
    return [
        {
            "IDProduit": _to_int(r.get("id_produit")),
            "LibProd": r.get("lib_produit") or "",
        }
        for r in rows
    ]


# --------------------------------------------------------------------
# WS : GET /Call/OHM/ListeTypeInstall
# --------------------------------------------------------------------

def ohm_liste_type_install() -> list[dict]:
    """WS `GET /Call/OHM/ListeTypeInstall`.

    Liste HARDCODEE cote WinDev (4 types) : chaudiere gaz, chauffage
    elec, poele granule/bois, chaudiere fioul.
    """
    types = [
        (1, "Chaudière à gaz"),
        (2, "Chauffage électrique"),
        (3, "Poêle granule/bois"),
        (4, "Chaudière fioul"),
    ]
    return [
        {
            "idLead": 0,
            "TypeInstall": type_id,
            "LibTypeInstall": lib,
            "Chauffage": False,
            "EauChaude": False,
        }
        for type_id, lib in types
    ]


# --------------------------------------------------------------------
# WS : POST /Call/ClientsNonFinalises/Panier/Produit/Ajout
# --------------------------------------------------------------------

def ajouter_produit_panier_call(payload: dict) -> dict:
    """WS `POST /Call/ClientsNonFinalises/Panier/Produit/Ajout`.

    Portage : INSERT dans pgt_tk_call_panier (+ pgt_ohm_leads_type_install
    si OHM — table absente du schema PG interne, insertion skip si
    absente).

    NOTE : la colonne opt_maintenance est absente du schema PG interne
    (existe cote HFSQL OVH) — la valeur du payload est ignoree
    silencieusement (voir aussi tickets_call_actions_energie.py).
    """
    db = get_pg_connection("ticket_bo")
    new_id = _new_id_wd()
    now = _now_wd()
    id_tk_liste = _to_int(payload.get("IDTK_Liste"))
    num_bs = (payload.get("NumBS") or "").strip()
    try:
        db.query(
            """INSERT INTO ticket_bo.pgt_tk_call_panier (
                  id_tk_call_panier, id_tk_call, id_tk_liste,
                  partenaire, id_produit, num_bs, num_date_saisie,
                  opt_energie_verte_elec, opt_reforestation,
                  opt_energie_verte_gaz, opt_mail, opt_e_communication,
                  opt_e_facture, opt_optin_commercial,
                  opt_consent_consult_distri, opt_accept_com_parte,
                  opt_mandat, format_numerique,
                  motif_annulation, statut_prod,
                  nb_pers_foyer, sit_pro, rfr, date_entree,
                  annee_construction, annee_installation, supercie,
                  autre_install, autre_installation,
                  chauffage_appoint, isolation_combles,
                  montant_mens_elec, montant_mens_gaz, observations,
                  modif_date, modif_elem
              ) VALUES (
                  ?, ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                  ?, ?,
                  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                  ?, 'new'
              )""",
            (
                new_id, id_tk_liste, id_tk_liste,
                payload.get("Part") or "",
                _to_int(payload.get("IDProduit")),
                num_bs,
                now if num_bs else None,
                _bool(payload.get("OPT_EnergieVerteElec")),
                _bool(payload.get("OPT_Reforestation")),
                _bool(payload.get("OPT_EnergieVerteGaz")),
                _bool(payload.get("OPT_Mail")),
                _bool(payload.get("OPT_eCommunication")),
                _bool(payload.get("OPT_eFacture")),
                _bool(payload.get("OPT_optinCommercial")),
                _bool(payload.get("OPT_ConsentDistri")),
                _bool(payload.get("OPT_CialPart")),
                _bool(payload.get("Opt_Mandat")),
                _bool(payload.get("FormatNumerique")),
                "", 0,
                _to_int(payload.get("NBPersFoyer")),
                payload.get("SitPro") or "",
                _to_int(payload.get("RFR")),
                payload.get("DateEntree") or None,
                _to_int(payload.get("AnneeConstruction")),
                _to_int(payload.get("AnneeInstallation")),
                _to_int(payload.get("Supercie")),   # typo preservee
                _bool(payload.get("AutreInstall")),
                payload.get("AutreInstallation") or "",
                _bool(payload.get("ChauffageAppoint")),
                _bool(payload.get("IsolationCombles")),
                _to_int(payload.get("MontantMensELEC")),
                _to_int(payload.get("MontantMensGAZ")),
                payload.get("Observations") or "",
                now,
            ),
        )
        # OHM : insertion dans OHM_LeadsTypeIntall skipppee (table
        # absente du schema PG interne pour l'instant).
        return {"nIdDemande": new_id}
    except Exception as e:
        logger.exception("ajouter_produit_panier_call")
        return {"nIdDemande": 0, "sInfoData": str(e)}


# --------------------------------------------------------------------
# WS : POST /Call/ClientsNonFinalises/Panier/Produit/Suppr
# --------------------------------------------------------------------

def supprimer_produit_panier_call(id_tk_call_panier: int) -> dict:
    """WS `POST /Call/ClientsNonFinalises/Panier/Produit/Suppr`.

    Portage : DELETE physique (cf. WinDev HSupprime).
    """
    db = get_pg_connection("ticket_bo")
    try:
        db.query(
            """DELETE FROM ticket_bo.pgt_tk_call_panier
                WHERE id_tk_call_panier = ?""",
            (int(id_tk_call_panier),),
        )
        return {"nIdDemande": 0}
    except Exception as e:
        logger.exception("supprimer_produit_panier_call")
        return {"nIdDemande": 0, "sInfoData": str(e)}


# --------------------------------------------------------------------
# WS : POST /Call/ClientsNonFinalises/EnvoiLien/{code}
# --------------------------------------------------------------------

def envoi_lien_client_call(id_tk_liste: int, code: str) -> dict:
    """WS `POST /Call/ClientsNonFinalises/EnvoiLien/{code}`.

    Portage :
      1. UPDATE TK_Call.CodeValid = code
      2. SELECT Mobile1, adrMail, NomClient, PrenomClient
      3. Envoi SMS avec lien https://groupe-exo.omaya.fr/PAGESEXTERNES_WEB
         /FR/Page-ConsentClient.awp?P1=ENI{IDTK_Liste}
      4. Envoi mail HTML avec bouton vers le meme lien

    Utilise app.shared.notifications.sms + envoi mail helper.
    """
    db = get_pg_connection("ticket_bo")
    now = _now_wd()
    try:
        db.query(
            """UPDATE ticket_bo.pgt_tk_call
                  SET code_valid = ?, modif_date = ?
                WHERE id_tk_liste = ?""",
            (str(code), now, int(id_tk_liste)),
        )
        r = db.query_one(
            """SELECT mobile1, adr_mail, nom_client, prenom_client
                 FROM ticket_bo.pgt_tk_call WHERE id_tk_liste = ?""",
            (int(id_tk_liste),),
        )
    except Exception as e:
        logger.exception("envoi_lien_client_call")
        return {"nIdDemande": 0, "sInfoData": str(e)}
    if not r:
        return {"nIdDemande": 0, "sInfoData": "Ticket introuvable"}
    lien = (
        f"https://groupe-exo.omaya.fr/PAGESEXTERNES_WEB/FR/"
        f"Page-ConsentClient.awp?P1=ENI{id_tk_liste}"
    )
    mobile = (r.get("mobile1") or "").strip()
    mail = (r.get("adr_mail") or "").strip()
    nom = r.get("nom_client") or ""
    prenom = r.get("prenom_client") or ""
    if mobile:
        try:
            from app.shared.notifications.sms import envoi_sms
            texte = (
                "Bonjour,\n"
                "Veuillez cliquer sur le lien suivant pour obtenir "
                f"le code de validation.\n{lien}"
            )
            envoi_sms(texte, mobile, emetteur="Code-Verify")
        except Exception:
            logger.exception("envoi_sms")
    # Envoi mail HTML
    try:
        _envoyer_mail_code_validation(mail, nom, prenom, lien)
    except Exception:
        logger.exception("_envoyer_mail_code_validation")
    return {"nIdDemande": id_tk_liste}


def _envoyer_mail_code_validation(mail_dest: str, nom: str,
                                    prenom: str, lien: str) -> None:
    """Envoi mail HTML avec bouton 'Cliquez ici pour obtenir le code'.

    Fallback destinataire : intranet@omaya.fr si mail_dest invalide.
    """
    from app.shared.notifications.mail import envoi_mail
    prenom_cap = prenom.capitalize() if prenom else ""
    bouton = (
        f'<table width="250px" border="0" cellspacing="0" cellpadding="0" '
        f'style="border-radius:10px; padding:15px 40px; background-color:#202021;">'
        f'<tr><td bgcolor="#202021" style="padding:15px 40px;">'
        f'<p style="margin:0; font-family:Arial; font-size:12px; text-align:center; color:#FFF; letter-spacing:4px;">'
        f'<a href="{lien}" target="_blank" style="color:#FFF; text-decoration:none;">'
        f'Cliquez ici pour obtenir le code</a>'
        f'</p></td></tr></table>'
    )
    html = (
        f"<font face='arial' style='font-size:10pt;'>"
        f"Bonjour {prenom_cap} {nom},<br/>"
        f"<p>Veuillez cliquer sur ce bouton pour obtenir le code de validation.</p>"
        f"{bouton}"
        f"<p>Cordialement.</p><br/>"
        f"<b>Le Service Validation</b><br/>"
        f"<i>Ceci est un mail automatique, ne pas y répondre.</i></font>"
    )
    dest = mail_dest.strip() if mail_dest and "@" in mail_dest else "intranet@omaya.fr"
    cci = ["intranet@omaya.fr", "bo@exosphere.fr"] if dest != "intranet@omaya.fr" else []
    envoi_mail(
        sujet="Code de validation",
        html=html,
        destinataires=[dest],
        cci=cci,
        expediteur="intranet@omaya.fr",
    )


# --------------------------------------------------------------------
# WS : POST /Call/ClientsNonFinalises/Validation/{idVend}
# --------------------------------------------------------------------

def validation_tk_call(id_tk_liste: int, id_vend: int) -> dict:
    """WS `POST /Call/ClientsNonFinalises/Validation/{idVend}`.

    Portage :
      UPDATE TK_Liste SET IDTK_Statut = 1, opModif = idVend,
             ModifDate = now, Datecrea = now
       WHERE IDTK_Liste = ?
    """
    db = get_pg_connection("ticket")
    now = _now_wd()
    try:
        db.query(
            """UPDATE ticket.pgt_tk_liste
                  SET id_tk_statut = ?, op_modif = ?,
                      modif_date = ?, date_crea = ?
                WHERE id_tk_liste = ?""",
            (IDTK_STATUT_A_TRAITER, int(id_vend),
             datetime.now(), datetime.now(), int(id_tk_liste)),
        )
        return {"nIdDemande": id_tk_liste}
    except Exception as e:
        logger.exception("validation_tk_call")
        return {"nIdDemande": 0, "sInfoData": str(e)}


# --------------------------------------------------------------------
# WS : GET /Call/ClientsNonFinalises/VerifPhoto/{idTicket}/{type}
# --------------------------------------------------------------------

def verif_photo(id_tk_liste: int, nom_photo: str) -> dict:
    """WS `GET /Call/ClientsNonFinalises/VerifPhoto/{idTicket}/{type}`.

    Retourne {nIdDemande: id_ticket} si le fichier {id}_{type}.png ou
    .pdf existe sur DocOmaya (HEAD HTTP, cf. _doc_exists), sinon
    {nIdDemande: 0}.
    """
    exists = _doc_exists(int(id_tk_liste), nom_photo)
    return {"nIdDemande": id_tk_liste if exists else 0}


# --------------------------------------------------------------------
# WS : POST /Call/NouveauTK/{idVend}   (AjoutTicketCall)
# --------------------------------------------------------------------

def _format_num_tel(tel: str) -> str:
    """FormateNumTel WinDev : garde les chiffres. Preserve les +."""
    if not tel:
        return ""
    return "".join(c for c in tel if c.isdigit() or c == "+")


def _affectation_terrain_vendeur(id_salarie: int) -> str:
    """Renvoie le libelle de l'orga d'affectation du vendeur (ou '')."""
    if not id_salarie:
        return ""
    db = get_pg_connection("rh")
    try:
        r = db.query_one(
            """SELECT o.lib_orga
                 FROM pgt_salarie_organigramme so
                 LEFT JOIN pgt_organigramme o
                   ON o.idorganigramme = so.idorganigramme
                WHERE so.id_salarie = ?
                  AND COALESCE(so.aff_actif, FALSE) = TRUE
                  AND (so.modif_elem IS NULL
                       OR so.modif_elem NOT LIKE '%suppr%')
                ORDER BY so.date_debut DESC
                LIMIT 1""",
            (int(id_salarie),),
        )
    except Exception:
        return ""
    return (r or {}).get("lib_orga") or ""


def _envoyer_alert_call(alert_html: str) -> None:
    """Envoi le mail 'ALERT CALL Energie' aux destinataires standards."""
    from app.shared.notifications.mail import envoi_mail
    try:
        envoi_mail(
            sujet="ALERT CALL Energie",
            html=(
                "<font face='arial' style='font-size:10pt;'><p>Bonjour,</p>"
                f"{alert_html}"
                "<p>Cdt<br/>Service INTRANET</p></font>"
            ),
            destinataires=["bo@exosphere.fr", "a.loudieux@exosphere.fr"],
            cci=["intranet@omaya.fr"],
            expediteur="intranet@omaya.fr",
        )
    except Exception:
        logger.exception("_envoyer_alert_call")


def crea_modif_tk_call(payload: dict, id_vend: int) -> dict:
    """WS `POST /Call/NouveauTK/{idVend}` (CreaModifTKCall + AjoutTicketCall).

    Portage :
      1. Genere un nouvel idTicket (WinDev idEntierDateHeureSys).
      2. Verifie si le mobile1/mobile2 existe deja en base
         (pgt_tk_call_sfr.mobile1|mobile2) -> mail d'alerte.
      3. Verifie si le mobile est celui d'un salarie
         (pgt_salarie_coordonnees.tel_mob) -> mail + eventuel BLOCAGE
         si c'est le propre num du vendeur.
      4. Verifie l'age du client via DATENAISS -> BLOCAGE si > 75 ans.
      5. INSERT pgt_tk_call + pgt_tk_liste (statut=28, type=22).
      6. Retour : {nIdDemande: idTicket, sInfoData: InfoBlocage}.

    NOTE : les helpers WinDev creaLogIntranet + FormateNumTel + Age +
    envoiMail sont adaptes ou skippes selon disponibilite.
    """
    from datetime import date as _date
    db_bo = get_pg_connection("ticket_bo")
    db_tk = get_pg_connection("ticket")
    db_rh = get_pg_connection("rh")

    id_ticket = _new_id_wd()
    nom_client = (payload.get("NomClient") or "").strip()
    prenom_client = (payload.get("PrenomClient") or "").strip()
    mobile1_raw = (payload.get("Mobile1") or "").strip()
    mobile2_raw = (payload.get("Mobile2") or "").strip()
    mobile1 = _format_num_tel(mobile1_raw)
    mobile2 = _format_num_tel(mobile2_raw)

    # Recup nom vendeur (pour les alertes mail)
    nom_vend = ""
    try:
        r = db_rh.query_one(
            "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ?",
            (int(id_vend),),
        )
        if r:
            nom_vend = (
                (r.get("nom") or "").strip() + " "
                + (r.get("prenom") or "").strip().capitalize()
            ).strip()
    except Exception:
        logger.exception("crea_modif_tk_call: nom_vend lookup")

    alert_mail = ""
    info_blocage = ""
    test_blocage = False

    # 1. Anti-doublon mobile client (SELECT sur pgt_tk_call_sfr)
    def _has_client_with_mobile(mob: str) -> dict | None:
        if not mob:
            return None
        try:
            return db_bo.query_one(
                """SELECT nom_client, prenom_client,
                          adresse1, cp, ville
                     FROM ticket_bo.pgt_tk_call_sfr
                    WHERE mobile1 = ?""",
                (mob,),
            )
        except Exception:
            return None

    for mob in (mobile1, mobile2):
        if not mob:
            continue
        r_dup = _has_client_with_mobile(mob)
        if r_dup:
            aff = _affectation_terrain_vendeur(id_vend)
            nom_clt1 = (
                (r_dup.get("nom_client") or "") + " "
                + (r_dup.get("prenom_client") or "").capitalize()
            ).strip()
            adr_clt1 = " ".join([
                r_dup.get("adresse1") or "",
                r_dup.get("cp") or "",
                r_dup.get("ville") or "",
            ]).strip()
            nom_clt2 = f"{nom_client} {prenom_client.capitalize()}".strip()
            adr_clt2 = f"{payload.get('ADRESSE1') or ''} {payload.get('CP') or ''} {payload.get('VILLE') or ''}".strip()
            alert_mail += (
                f"<p>Attention, {nom_vend} ({aff}) fait un ticket CALL avec "
                f"un numéro de tél client déjà utilisé.</p>"
                f"<p>Info Client en base : {nom_clt1} {adr_clt1}</p>"
                f"<p>Info Client en cours : {nom_clt2} {adr_clt2}</p>"
            )
            break

    # 2. Anti-doublon tel salarie (SELECT sur pgt_salarie_coordonnees)
    def _has_salarie_with_mobile(mob: str) -> dict | None:
        if not mob:
            return None
        try:
            return db_rh.query_one(
                """SELECT s.id_salarie, s.nom, s.prenom
                     FROM rh.pgt_salarie_coordonnees sc
                     JOIN rh.pgt_salarie s ON s.id_salarie = sc.id_salarie
                    WHERE sc.tel_mob = ?""",
                (mob,),
            )
        except Exception:
            return None

    for mob in (mobile1, mobile2):
        if not mob:
            continue
        r_sal = _has_salarie_with_mobile(mob)
        if r_sal:
            aff = _affectation_terrain_vendeur(id_vend)
            if _to_int(r_sal.get("id_salarie")) == int(id_vend):
                alert_mail += (
                    f"<p>Attention, {nom_vend} ({aff}) fait un ticket CALL "
                    f"avec son propre numéro de tél.</p>"
                )
                info_blocage = "REFUS TICKET : Il est INTERDIT d'utiliser son numéro de téléphone !"
                test_blocage = True
            else:
                nom_v = (
                    (r_sal.get("nom") or "") + " "
                    + (r_sal.get("prenom") or "").capitalize()
                ).strip()
                aff_v = _affectation_terrain_vendeur(_to_int(r_sal.get("id_salarie")))
                alert_mail += (
                    f"<p>Attention, {nom_vend} ({aff}) fait un ticket CALL "
                    f"avec le numéro de tél de {nom_v} ({aff_v}).</p>"
                )
            break

    # 3. Age > 75 ans -> BLOCAGE
    dnaiss_raw = (payload.get("DATENAISS") or "").strip()
    if dnaiss_raw and len(dnaiss_raw) >= 8:
        try:
            # Format compact YYYYMMDD (fournit par le frontend via fmtDateApi)
            dt = _date(
                int(dnaiss_raw[0:4]),
                int(dnaiss_raw[4:6]),
                int(dnaiss_raw[6:8]),
            )
            today = _date.today()
            age = today.year - dt.year - (
                (today.month, today.day) < (dt.month, dt.day)
            )
            if age > 75:
                test_blocage = True
                info_blocage = (
                    "REFUS TICKET : Il est INTERDIT de faire signer une "
                    "personne de plus de 75 ans !"
                )
                aff = _affectation_terrain_vendeur(id_vend)
                nom_clt2 = f"{nom_client} {prenom_client.capitalize()}".strip()
                adr_clt2 = f"{payload.get('ADRESSE1') or ''} {payload.get('CP') or ''} {payload.get('VILLE') or ''}".strip()
                dnaiss_fr = f"{dnaiss_raw[6:8]}/{dnaiss_raw[4:6]}/{dnaiss_raw[0:4]}"
                alert_mail += (
                    f"<p>Attention, {nom_vend} ({aff}) fait un ticket CALL "
                    f"avec à une personne de plus de 75 ans.</p>"
                    f"<p>Info Client : {nom_clt2}</p>"
                    f"<p>Adresse : {adr_clt2}</p>"
                    f"<p>Date naiss : {dnaiss_fr}</p>"
                )
        except (ValueError, TypeError):
            pass

    # Envoi mail d'alerte s'il y en a un
    if alert_mail:
        _envoyer_alert_call(alert_mail)

    # 5. INSERT pgt_tk_call + pgt_tk_liste
    now = _now_wd()
    try:
        db_bo.query(
            """INSERT INTO ticket_bo.pgt_tk_call (
                  id_tk_call, id_tk_liste, id_salarie, id_client,
                  civilite_client, nom_client, nom_marital_client,
                  prenom_client, date_naiss, dep_naiss,
                  adresse1, adresse2, cp, ville, adr_mail, mobile1,
                  type_logement, client_pro, client_rs, client_siret,
                  appel_en_cours, opt_rappel, opt_partenaire,
                  motif_annulation, modif_op, modif_date, modif_elem
              ) VALUES (
                  ?, ?, ?, 0,
                  ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?,
                  FALSE, FALSE, FALSE,
                  '', ?, ?, 'new'
              )""",
            (
                id_ticket, id_ticket, int(id_vend),
                _to_int(payload.get("CiviliteClient")),
                nom_client,
                payload.get("NomMaritalClient") or "",
                prenom_client,
                dnaiss_raw or None,
                _to_int(payload.get("DEPNAISS")),
                payload.get("ADRESSE1") or "",
                payload.get("ADRESSE2") or "",
                payload.get("CP") or "",
                payload.get("VILLE") or "",
                payload.get("adrMail") or "",
                mobile1,
                _to_int(payload.get("TypeLogement")),
                _bool(payload.get("ClientPro")),
                payload.get("ClientRS") or "",
                payload.get("ClientSiret") or "",
                int(id_vend),
                now,
            ),
        )
    except Exception as e:
        logger.exception("crea_modif_tk_call: INSERT pgt_tk_call")
        return {"nIdDemande": 0, "sInfoData": str(e)}

    try:
        db_tk.query(
            """INSERT INTO ticket.pgt_tk_liste (
                  id_tk_liste, date_crea, op_crea, op_dest, service,
                  id_tk_type_demande, id_tk_statut, cloturee,
                  modif_date, modif_op, modif_elem
              ) VALUES (
                  ?, ?, ?, ?, 'BO', ?, ?, FALSE,
                  ?, ?, 'new'
              )""",
            (
                id_ticket, datetime.now(), int(id_vend), int(id_vend),
                IDTK_TYPE_DEMANDE_CALL_ENERGIE, IDTK_STATUT_EN_COURS,
                datetime.now(), int(id_vend),
            ),
        )
    except Exception as e:
        logger.exception("crea_modif_tk_call: INSERT pgt_tk_liste")
        # Le tk_call est deja cree — on retourne l'erreur mais l'id
        # partiellement cree existe.
        return {"nIdDemande": 0, "sInfoData": str(e)}

    return {"nIdDemande": id_ticket, "sInfoData": info_blocage}


