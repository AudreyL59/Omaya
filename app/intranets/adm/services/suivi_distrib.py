"""
Service Suivi Distributeurs (transposition Fen_SuiviDistrib + FI_DetailDistributeur).

Ecran WinDev :
- Liste des societes IDTypeOrga=3 (distributeurs) avec toggle actif/inactif
- Detail par societe : 4 blocs
    1. Docs uniques  (pgt_type_doc_distributeur.rappel_annuel = 0)
    2. Docs annuels  (pgt_type_doc_distributeur.rappel_annuel > 0) filtres par annee
    3. Suivi Facturation (pgt_tk_demande_facturation_distrib)
    4. Suivi ADM (pgt_salarie_suivi_adm sur id_gerant)

Tables PG :
  - rh.pgt_societe (id_ste, raison_sociale, siret, id_type_orga, is_actif,
    id_gerant, num_orias, date_creation, rs_interne, modif_elem)
  - rh.pgt_doc_distrib (id_doc_distrib, id_ste, id_gerant,
    id_type_doc_distributeur, date_prevue, date_depot, nom_fichier,
    modif_date, modif_op, modif_elem)
  - rh.pgt_type_doc_distributeur (id_type_doc_distributeur, lib_doc,
    rappel_annuel, obligatoire_dem, afaire_signer, id_doc_courtage)
  - rh.pgt_salarie / pgt_salarie_embauche (fallback DateCreation)
  - ticket_bo.pgt_tk_liste + pgt_tk_demande_doc_distrib +
    pgt_tk_demande_facturation_distrib + pgt_tk_demande_ctt_courtage
  - rh.pgt_societe_doc_courtage (JOIN sur AfaireSigner=1)
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from app.core.database.pg import get_pg_connection
from app.core.utils.sentinel_dates import is_sentinel, to_iso

logger = logging.getLogger(__name__)


def _new_id() -> int:
    """ID 8 octets base sur DateHeureSys (equiv WinDev idEntierDateHeureSys)."""
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


def _now_iso() -> str:
    """DateHeureSys() -> 'YYYY-MM-DD HH:MM:SS' pour timestamp PG."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _clean_id(v) -> str:
    """Retourne '' pour 0/None, sinon str(int)."""
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _to_iso(v) -> str:
    """Convertit une date/datetime PG en 'YYYY-MM-DD' ou ''.
    Ecrase la sentinelle 1900-01-01.
    """
    if v is None:
        return ""
    if is_sentinel(v):
        return ""
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    s = str(v)[:10]
    return s if not is_sentinel(s) else ""


def _cap_prenom(p: str) -> str:
    """Capitalise('marie-jean') -> 'Marie-Jean' (equiv WinDev capitalise)."""
    if not p:
        return ""
    return "-".join(x[:1].upper() + x[1:].lower() for x in p.split("-"))


def _nom_gerant(rh, id_gerant: int) -> str:
    """Nom + Capitalise(Prenom) du gerant, ou '' si absent."""
    if not id_gerant:
        return ""
    try:
        s = rh.query_one(
            "SELECT nom, prenom FROM pgt_salarie WHERE id_salarie = ?",
            (int(id_gerant),),
        )
    except Exception:
        return ""
    if not s:
        return ""
    return f"{(s.get('nom') or '').strip()} {_cap_prenom((s.get('prenom') or '').strip())}".strip()


# --------------------------------------------------------------------
# LISTE SOCIETES (Fen_SuiviDistrib.Table_ListeSTE)
# --------------------------------------------------------------------

def list_societes(actif: bool = True) -> list[dict]:
    """Liste des distributeurs (id_type_orga=3) avec toggle actif/inactif.

    Retour : dicts avec id_ste, raison_sociale, siret, date_creation (iso),
    num_orias, id_gerant, nom_gerant (calcule).
    Ordre : RS_Interne ASC (cf WinDev).
    """
    rh = get_pg_connection("rh")
    rows = rh.query(
        """SELECT id_ste, raison_sociale, rs_interne, siret, is_actif,
                  id_gerant, num_orias, date_creation
             FROM pgt_societe
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
              AND id_type_orga = 3
              AND is_actif = ?
            ORDER BY rs_interne ASC NULLS LAST""",
        (bool(actif),),
    ) or []
    out = []
    for r in rows:
        id_g = int(r.get("id_gerant") or 0)
        out.append({
            "id_ste": _clean_id(r.get("id_ste")),
            "raison_sociale": (r.get("raison_sociale") or "").strip(),
            "rs_interne": (r.get("rs_interne") or "").strip(),
            "siret": (r.get("siret") or "").strip(),
            "is_actif": bool(r.get("is_actif")),
            "id_gerant": _clean_id(id_g),
            "nom_gerant": _nom_gerant(rh, id_g),
            "num_orias": (r.get("num_orias") or "").strip(),
            "date_creation": _to_iso(r.get("date_creation")),
        })
    return out


# --------------------------------------------------------------------
# DETAIL SOCIETE - bootstrap (FI_DetailDistributeur.Code Init)
# --------------------------------------------------------------------

def get_detail_bootstrap(id_ste: int) -> Optional[dict]:
    """Bootstrap de la fenetre interne detail.

    Cf. WinDev Code Init :
    - Lit pgt_societe.date_creation
    - Si date invalide -> fallback sur pgt_salarie_embauche.date_debut
    - Calcule la liste des annees possibles pour le combo AnneeDoc
    """
    rh = get_pg_connection("rh")
    ste = rh.query_one(
        """SELECT id_ste, raison_sociale, id_gerant, date_creation, siret,
                  num_orias, rs_interne
             FROM pgt_societe
            WHERE id_ste = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_ste),),
    )
    if not ste:
        return None

    id_gerant = int(ste.get("id_gerant") or 0)
    date_crea_iso = _to_iso(ste.get("date_creation"))

    # Fallback : date_debut de l'embauche du gerant
    if not date_crea_iso and id_gerant:
        try:
            emb = rh.query_one(
                """SELECT date_debut FROM pgt_salarie_embauche
                    WHERE id_salarie = ?
                      AND (modif_elem IS NULL
                           OR modif_elem NOT LIKE '%suppr%')
                    ORDER BY date_debut ASC NULLS LAST
                    LIMIT 1""",
                (id_gerant,),
            )
            if emb:
                date_crea_iso = _to_iso(emb.get("date_debut"))
        except Exception:
            pass

    # Combo AnneeDoc : de l'annee dateCreaSte a l'annee courante
    annee_courante = date.today().year
    annee_debut = int(date_crea_iso[:4]) if date_crea_iso else annee_courante
    annees = list(range(annee_debut, annee_courante + 1))

    return {
        "id_ste": str(int(ste["id_ste"])),
        "raison_sociale": (ste.get("raison_sociale") or "").strip(),
        "rs_interne": (ste.get("rs_interne") or "").strip(),
        "siret": (ste.get("siret") or "").strip(),
        "num_orias": (ste.get("num_orias") or "").strip(),
        "id_gerant": _clean_id(id_gerant),
        "nom_gerant": _nom_gerant(rh, id_gerant),
        "date_creation": date_crea_iso,
        "annee_selectionnee": annee_courante,
        "annees_disponibles": annees,
    }


# --------------------------------------------------------------------
# DOCS UNIQUES (Table_ReqDocSTeUnique)
# --------------------------------------------------------------------

def _lookup_ticket_for_doc(id_doc_distrib: int, id_doc_courtage: int,
                            afaire_signer: bool) -> tuple[int, bool]:
    """Retourne (id_tk_liste, cloture) du dernier ticket lie a ce doc.

    Cf. WinDev : si AfaireSigner=1 -> JOIN via societe_doc_courtage +
    tk_demande_ctt_courtage sinon -> JOIN via tk_demande_doc_distrib.
    """
    if not id_doc_distrib:
        return (0, False)

    if afaire_signer and id_doc_courtage:
        # Branche AfaireSigner : ticket via docCourtage
        tk_bo = get_pg_connection("ticket_bo")
        try:
            r = tk_bo.query_one(
                """SELECT tl.id_tk_liste, tl.cloturee
                     FROM ticket_bo.pgt_tk_demande_ctt_courtage tcc
                     JOIN ticket.pgt_tk_liste tl
                          ON tl.id_tk_liste = tcc.id_tk_liste
                     JOIN rh.pgt_societe_doc_courtage sdc
                          ON sdc.id_societe_doc_courtage
                             = tcc.id_societe_doc_courtage
                    WHERE sdc.id_doc_courtage = ?
                      AND (tl.modif_elem IS NULL
                           OR tl.modif_elem NOT LIKE '%suppr%')
                    ORDER BY tl.date_crea DESC NULLS LAST
                    LIMIT 1""",
                (int(id_doc_courtage),),
            )
        except Exception:
            r = None
    else:
        # Branche standard : ticket via tk_demande_doc_distrib
        tk_bo = get_pg_connection("ticket_bo")
        try:
            r = tk_bo.query_one(
                """SELECT tl.id_tk_liste, tl.cloturee
                     FROM ticket_bo.pgt_tk_demande_doc_distrib tdd
                     JOIN ticket.pgt_tk_liste tl
                          ON tl.id_tk_liste = tdd.id_tk_liste
                    WHERE tdd.id_doc_distrib = ?
                      AND (tl.modif_elem IS NULL
                           OR tl.modif_elem NOT LIKE '%suppr%')
                    ORDER BY tl.date_crea DESC NULLS LAST
                    LIMIT 1""",
                (int(id_doc_distrib),),
            )
        except Exception:
            r = None
    if not r:
        return (0, False)
    return (int(r.get("id_tk_liste") or 0), bool(r.get("cloturee")))


def _hydrate_doc(row: dict) -> dict:
    id_doc = int(row.get("id_doc_distrib") or 0)
    id_doc_courtage = int(row.get("id_doc_courtage") or 0)
    afaire = bool(row.get("afaire_signer"))
    id_tk, tk_clo = _lookup_ticket_for_doc(id_doc, id_doc_courtage, afaire)
    return {
        "id_doc_distrib": _clean_id(id_doc),
        "id_type_doc_distributeur": _clean_id(row.get("id_type_doc_distributeur")),
        "lib_doc": (row.get("lib_doc") or "").strip(),
        "date_prevue": _to_iso(row.get("date_prevue")),
        "date_depot": _to_iso(row.get("date_depot")),
        "nom_fichier": (row.get("nom_fichier") or "").strip(),
        "rappel_annuel": int(row.get("rappel_annuel") or 0),
        "obligatoire_dem": bool(row.get("obligatoire_dem")),
        "afaire_signer": afaire,
        "id_doc_courtage": _clean_id(id_doc_courtage),
        "id_tk": _clean_id(id_tk),
        "tk_cloture": tk_clo,
    }


def list_docs_unique(id_ste: int) -> list[dict]:
    """Docs uniques (rappel_annuel = 0) pour une societe."""
    rh = get_pg_connection("rh")
    rows = rh.query(
        """SELECT d.id_doc_distrib, d.id_type_doc_distributeur,
                  d.date_prevue, d.date_depot, d.nom_fichier,
                  t.rappel_annuel, t.obligatoire_dem, t.lib_doc,
                  t.afaire_signer, t.id_doc_courtage
             FROM pgt_doc_distrib d
             JOIN pgt_type_doc_distributeur t
                  ON t.id_type_doc_distributeur = d.id_type_doc_distributeur
            WHERE (d.modif_elem IS NULL OR d.modif_elem NOT LIKE 'suppr%')
              AND t.rappel_annuel = 0
              AND d.id_ste = ?
            ORDER BY t.lib_doc ASC NULLS LAST""",
        (int(id_ste),),
    ) or []
    return [_hydrate_doc(r) for r in rows]


def list_docs_annuel(id_ste: int, annee: int) -> list[dict]:
    """Docs annuels (rappel_annuel > 0) pour l'annee donnee."""
    annee_str = f"{int(annee):04d}"
    rh = get_pg_connection("rh")
    rows = rh.query(
        """SELECT d.id_doc_distrib, d.id_type_doc_distributeur,
                  d.date_prevue, d.date_depot, d.nom_fichier,
                  t.rappel_annuel, t.obligatoire_dem, t.lib_doc,
                  t.afaire_signer, t.id_doc_courtage
             FROM pgt_doc_distrib d
             JOIN pgt_type_doc_distributeur t
                  ON t.id_type_doc_distributeur = d.id_type_doc_distributeur
            WHERE (d.modif_elem IS NULL OR d.modif_elem NOT LIKE 'suppr%')
              AND t.rappel_annuel > 0
              AND LEFT(CAST(d.date_prevue AS TEXT), 4) = ?
              AND d.id_ste = ?
            ORDER BY d.date_prevue ASC NULLS LAST""",
        (annee_str, int(id_ste)),
    ) or []
    return [_hydrate_doc(r) for r in rows]


# --------------------------------------------------------------------
# FACTURATION (Table_reqFacturation)
# --------------------------------------------------------------------

def list_facturations(id_ste: int) -> list[dict]:
    """Liste des tickets de facturation pour une societe.

    Cf. WinDev : JOIN salarie + tk_liste + tk_demande_facturation_distrib
    ORDER BY datecrea DESC.

    Cross-schema : pgt_tk_liste est dans le schema `ticket`,
    pgt_tk_demande_facturation_distrib dans `ticket_bo`. On qualifie
    explicitement les tables (le search_path pointe sur ticket_bo).
    """
    tk_bo = get_pg_connection("ticket_bo")
    rows = tk_bo.query(
        """SELECT tl.id_tk_liste, tl.date_crea, tl.cloturee, tl.op_crea,
                  fd.id_gerant, fd.fic_facture, fd.fic_preuve_virement,
                  fd.date_virement, fd.montant
             FROM ticket.pgt_tk_liste tl
             JOIN ticket_bo.pgt_tk_demande_facturation_distrib fd
                  ON tl.id_tk_liste = fd.id_tk_liste
            WHERE (tl.modif_elem IS NULL
                   OR tl.modif_elem NOT LIKE '%suppr%')
              AND fd.id_ste = ?
            ORDER BY tl.date_crea DESC NULLS LAST""",
        (int(id_ste),),
    ) or []

    # Enrichissement OpCrea (rh.pgt_salarie.prenom)
    op_ids = {int(r.get("op_crea") or 0) for r in rows}
    op_ids.discard(0)
    prenoms = {}
    if op_ids:
        rh = get_pg_connection("rh")
        try:
            ids_sql = ",".join(str(i) for i in op_ids)
            for s in rh.query(
                f"SELECT id_salarie, prenom FROM pgt_salarie "
                f"WHERE id_salarie IN ({ids_sql})",
            ) or []:
                prenoms[int(s["id_salarie"])] = _cap_prenom(
                    (s.get("prenom") or "").strip()
                )
        except Exception:
            pass

    return [
        {
            "id_tk_liste": _clean_id(r.get("id_tk_liste")),
            "date_crea": _to_iso(r.get("date_crea")),
            "prenom_crea": prenoms.get(int(r.get("op_crea") or 0), ""),
            "id_gerant": _clean_id(r.get("id_gerant")),
            "fic_facture": (r.get("fic_facture") or "").strip(),
            "fic_preuve_virement": (
                r.get("fic_preuve_virement") or ""
            ).strip(),
            "date_virement": _to_iso(r.get("date_virement")),
            "montant": float(r.get("montant") or 0),
            "cloturee": bool(r.get("cloturee")),
        }
        for r in rows
    ]


# --------------------------------------------------------------------
# VERIF - auto-creation des Doc_Distrib manquants (cf. WinDev)
# --------------------------------------------------------------------

def _insert_doc_distrib(
    rh, id_ste: int, id_type: int, date_prevue: str, op_id: int,
) -> Optional[int]:
    """INSERT dans pgt_doc_distrib. Retourne id_doc_distrib ou None."""
    id_doc = _new_id()
    now = _now_iso()
    try:
        rh.query(
            """INSERT INTO pgt_doc_distrib
                 (id_doc_distrib, id_ste, id_gerant,
                  id_type_doc_distributeur, date_prevue, date_depot,
                  nom_fichier, modif_date, modif_op, modif_elem)
               VALUES (?, ?, 0, ?, ?, NULL, '', ?, ?, 'new')""",
            (id_doc, int(id_ste), int(id_type),
             date_prevue, now, int(op_id)),
        )
        return id_doc
    except Exception as e:
        logger.error("INSERT pgt_doc_distrib KO : %s", e)
        return None


def verif_docs_unique(id_ste: int, op_id: int) -> dict:
    """Cf. WinDev VerifDocUnique() : auto-creation d'un pgt_doc_distrib
    pour chaque type_doc_distributeur (rappel_annuel=0) absent de la
    societe. Date prevue = date_creation de la societe.
    """
    rh = get_pg_connection("rh")
    boot = get_detail_bootstrap(id_ste)
    if not boot:
        return {"ok": False, "error": "Societe introuvable"}
    date_crea = boot.get("date_creation") or date.today().isoformat()

    # Types de docs uniques existants
    types = rh.query(
        """SELECT id_type_doc_distributeur
             FROM pgt_type_doc_distributeur
            WHERE rappel_annuel = 0""",
    ) or []

    # Types deja presents pour cette societe
    already = rh.query(
        """SELECT id_type_doc_distributeur
             FROM pgt_doc_distrib
            WHERE id_ste = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE 'suppr%')""",
        (int(id_ste),),
    ) or []
    known = {int(r["id_type_doc_distributeur"]) for r in already}

    created = 0
    for t in types:
        tid = int(t["id_type_doc_distributeur"])
        if tid in known:
            continue
        if _insert_doc_distrib(rh, id_ste, tid, date_crea, op_id):
            created += 1
    return {"ok": True, "nb_created": created}


def verif_docs_annuel(id_ste: int, annee: int, op_id: int) -> dict:
    """Cf. WinDev VerifDocAnnuel() : pour chaque type_doc_distributeur
    (rappel_annuel > 0) absent pour l'annee donnee, cree N entrees
    (N = rappel_annuel) espacees de 12/N mois a partir du 2 janvier.
    """
    rh = get_pg_connection("rh")
    types = rh.query(
        """SELECT id_type_doc_distributeur, rappel_annuel
             FROM pgt_type_doc_distributeur
            WHERE rappel_annuel > 0""",
    ) or []

    # Existants pour cette societe/annee
    annee_str = f"{int(annee):04d}"
    already = rh.query(
        """SELECT id_type_doc_distributeur
             FROM pgt_doc_distrib
            WHERE id_ste = ?
              AND LEFT(CAST(date_prevue AS TEXT), 4) = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE 'suppr%')""",
        (int(id_ste), annee_str),
    ) or []
    known = {int(r["id_type_doc_distributeur"]) for r in already}

    created = 0
    for t in types:
        tid = int(t["id_type_doc_distributeur"])
        if tid in known:
            continue
        rappel = int(t.get("rappel_annuel") or 1)
        # Date de base : 2 janvier de l'annee (cf. WinDev jour=2)
        base = date(int(annee), 1, 2)
        if _insert_doc_distrib(rh, id_ste, tid, base.isoformat(), op_id):
            created += 1
        # Occurrences supplementaires (rappel_annuel > 1) : jour=1 des mois
        # espaces de 12/rappel
        if rappel > 1:
            diff = 12 // rappel
            cur = base
            for i in range(2, rappel + 1):
                # Ajoute diff mois
                m = cur.month + diff
                y = cur.year + (m - 1) // 12
                m = ((m - 1) % 12) + 1
                cur = date(y, m, 1)
                _insert_doc_distrib(rh, id_ste, tid, cur.isoformat(), op_id)
                created += 1
    return {"ok": True, "nb_created": created}


def add_doc_unique(id_ste: int, id_type: int, op_id: int) -> dict:
    """Cf. WinDev Btn '+' a cote de la combo : ajout manuel d'un doc
    unique avec DatePrevue = date_creation de la societe.
    """
    boot = get_detail_bootstrap(id_ste)
    if not boot:
        return {"ok": False, "error": "Societe introuvable"}
    date_crea = boot.get("date_creation") or date.today().isoformat()
    id_doc = _insert_doc_distrib(
        get_pg_connection("rh"), id_ste, id_type, date_crea, op_id,
    )
    if not id_doc:
        return {"ok": False, "error": "INSERT KO"}
    return {"ok": True, "id_doc_distrib": str(id_doc)}


def list_types_doc_unique() -> list[dict]:
    """Combo reqDocUnique : SELECT * FROM TypeDocDistributeur
    WHERE rappel_annuel = 0.
    """
    rh = get_pg_connection("rh")
    rows = rh.query(
        """SELECT id_type_doc_distributeur, lib_doc, obligatoire_dem,
                  afaire_signer
             FROM pgt_type_doc_distributeur
            WHERE rappel_annuel = 0
            ORDER BY lib_doc ASC NULLS LAST""",
    ) or []
    return [
        {
            "id_type_doc_distributeur": _clean_id(r.get("id_type_doc_distributeur")),
            "lib_doc": (r.get("lib_doc") or "").strip(),
            "obligatoire_dem": bool(r.get("obligatoire_dem")),
            "afaire_signer": bool(r.get("afaire_signer")),
        }
        for r in rows
    ]


# --------------------------------------------------------------------
# TICKETS DE RECLAMATION (Btn Ticket de reclam - HAUT/BAS)
# --------------------------------------------------------------------

def _envoyer_sms_reclam(
    gsm: str, lib_doc: str, id_tk_liste: int, op_id: int,
) -> str:
    """Envoi SMS de reclamation + INSERT histo (best-effort).

    Cf. WinDev Btn Ticket de reclam :
      envoiSMS_Rest(GSM, 'OMAYA-Info', texteSMS, 1, '')
      envoiSMS_HistoSave(monHref, 'TK_DemandeDocDistrib', 'IDTK_Liste', idNew)

    Retour : statut d'envoi (chaine, ex. 'SMS envoye avec succes').
    """
    from app.shared.notifications.sms import envoi_sms

    if not gsm:
        return "GSM inconnu"

    texte = (
        f"Bonjour, vous devez imperativement fournir votre {lib_doc}.\n"
        "Merci de vous rendre sur l'intranet ou sur l'appli mobile "
        "Omayapp pour envoyer ce document.\n"
        "Cdt"
    )

    statut = envoi_sms(texte, gsm, emetteur="OMAYA-Info") or ""

    # INSERT histo (divers.pgt_histo_sms). Best-effort.
    try:
        db_div = get_pg_connection("divers")
        db_div.query(
            """INSERT INTO divers.pgt_histo_sms
                  (id_histo_sms, destinataire, fichier, rubrique,
                   id_elem, contenu_envoye, statut, ope_envoi,
                   datecrea, modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?,
                       ?, ?, ?, ?,
                       NOW(), NOW(), ?, 'new')""",
            (
                _new_id(), gsm, "TK_DemandeDocDistrib", "IDTK_Liste",
                int(id_tk_liste), texte, statut, int(op_id), int(op_id),
            ),
        )
    except Exception:
        logger.exception("INSERT pgt_histo_sms (reclam)")

    return statut


def create_ticket_reclam(
    id_doc_distrib: int, id_gerant: int, op_id: int,
) -> dict:
    """Cf. WinDev Btn Ticket de reclam : cree un ticket type 31 (TK_Liste
    + TK_DemandeDocDistrib) + SMS de rappel au gerant + INSERT histo.

    Retour : {ok, id_tk_liste, lib_doc, id_gerant, gsm_gerant, sms_statut}
    """
    rh = get_pg_connection("rh")
    tk_bo = get_pg_connection("ticket_bo")
    tk = get_pg_connection("ticket")

    # Infos doc pour le SMS + le retour
    d = rh.query_one(
        """SELECT d.id_ste, d.id_type_doc_distributeur, t.lib_doc,
                  t.afaire_signer, t.id_doc_courtage
             FROM pgt_doc_distrib d
             JOIN pgt_type_doc_distributeur t
                  ON t.id_type_doc_distributeur = d.id_type_doc_distributeur
            WHERE d.id_doc_distrib = ?""",
        (int(id_doc_distrib),),
    )
    if not d:
        return {"ok": False, "error": "Doc introuvable"}
    lib_doc = (d.get("lib_doc") or "").strip()
    if bool(d.get("afaire_signer")):
        # cf. WinDev : si AfaireSign=1 -> ouverture Fen_SocieteDocCourtage
        # (workflow special deja implemente par le module doc_courtage).
        # On ne cree pas de ticket ici, on retourne l'indication au front.
        return {
            "ok": True,
            "afaire_signer": True,
            "lib_doc": lib_doc,
            "message": "Redirection Fen_SocieteDocCourtage requise",
        }

    id_tk = _new_id()
    now = _now_iso()
    try:
        tk_bo.query(
            """INSERT INTO pgt_tk_demande_doc_distrib
                 (id_tk_demande_doc_distrib, id_tk_liste, id_doc_distrib,
                  lien_fichier, motif_refus, modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, '', '', ?, ?, 'new')""",
            (_new_id(), id_tk, int(id_doc_distrib), now, int(op_id)),
        )
    except Exception as e:
        logger.error("INSERT pgt_tk_demande_doc_distrib KO : %s", e)
        return {"ok": False, "error": f"INSERT demande : {e}"}

    try:
        tk.query(
            """INSERT INTO pgt_tk_liste
                 (id_tk_liste, date_crea, op_crea, op_dest,
                  op_traitement_staff, ordre_traitement_staff,
                  service, id_tk_type_demande, id_tk_statut,
                  cloturee, modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, 0, '', 'JU', 31, 1,
                       FALSE, ?, ?, 'new')""",
            (id_tk, now, int(op_id), int(id_gerant), now, int(op_id)),
        )
    except Exception as e:
        logger.error("INSERT pgt_tk_liste KO : %s", e)
        return {"ok": False, "error": f"INSERT ticket : {e}"}

    # GSM du gerant pour envoi SMS + historisation
    gsm = ""
    try:
        c = rh.query_one(
            """SELECT tel_mob FROM pgt_salarie_coordonnees
                WHERE id_salarie = ?""",
            (int(id_gerant),),
        )
        gsm = ((c.get("tel_mob") if c else "") or "").strip()
        for ch in (".", " ", "/", "-"):
            gsm = gsm.replace(ch, "")
    except Exception:
        pass

    # Envoi SMS + histo (cf. WinDev envoiSMS_Rest + envoiSMS_HistoSave)
    sms_statut = _envoyer_sms_reclam(gsm, lib_doc, id_tk, op_id)

    return {
        "ok": True,
        "id_tk_liste": str(id_tk),
        "lib_doc": lib_doc,
        "id_gerant": str(id_gerant),
        "gsm_gerant": gsm,
        "sms_statut": sms_statut,
    }


# --------------------------------------------------------------------
# TICKET FACTURATION (Btn Ticket Facturation)
# --------------------------------------------------------------------

def _sanitize_filename(s: str) -> str:
    """cf. WinDev ChaineFormate + ccSansEspaceInterieur + ccSansAccent +
    ccSansEspace + ccSansPonctuationNiEspace.
    """
    import unicodedata
    if not s:
        return "STE"
    nfkd = unicodedata.normalize("NFKD", s)
    ascii_s = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Retire tout ce qui n'est pas alphanum
    return "".join(c for c in ascii_s if c.isalnum()) or "STE"


def create_ticket_facturation(
    id_ste: int, id_gerant: int, filename: str, content: bytes,
    montant: float, op_id: int,
) -> dict:
    """Cf. WinDev Btn Ticket Facturation :
    1. Upload PDF sur FTP gestionRH/<id_gerant>/Factures/
    2. Cree TK_Liste (type 28) + TK_DemandeFacturationDistrib
    3. Mail juristes (envoie a envoi_mail_rh)

    Retour : {ok, id_tk_liste, fic}
    """
    from app.core.config import FTP_GESTION_RH_PATH
    from app.shared.tickets.forms.cttw_pdf import ftp_upload
    from app.shared.notifications.mail import envoi_mail_rh

    # Recupere lib_ste pour le nommage + le mail
    rh = get_pg_connection("rh")
    ste = rh.query_one(
        "SELECT raison_sociale FROM pgt_societe WHERE id_ste = ?",
        (int(id_ste),),
    )
    lib_ste = (ste.get("raison_sociale") if ste else "") or "STE"

    # Nom du fichier (cf WinDev DateHeureSys+"_"+ChaineFormate(RS,...)+"_Facture"+ext)
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    fic = f"{ts}_{_sanitize_filename(lib_ste)}_Facture.{ext}"

    # Upload FTP
    try:
        ftp_upload(
            f"{FTP_GESTION_RH_PATH.rstrip('/')}/{id_gerant}/Factures",
            fic, content,
        )
    except Exception as e:
        return {"ok": False, "error": f"Upload FTP : {e}"}

    id_tk = _new_id()
    now = _now_iso()
    tk_bo = get_pg_connection("ticket_bo")
    tk = get_pg_connection("ticket")

    try:
        tk_bo.query(
            """INSERT INTO pgt_tk_demande_facturation_distrib
                 (id_tk_demande_facturation_distrib, id_tk_liste,
                  fic_facture, fic_preuve_virement, id_gerant, id_ste,
                  montant, date_virement, modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, '', ?, ?, ?, NULL, ?, ?, 'new')""",
            (_new_id(), id_tk, fic, int(id_gerant), int(id_ste),
             float(montant), now, int(op_id)),
        )
    except Exception as e:
        logger.error("INSERT pgt_tk_demande_facturation_distrib KO : %s", e)
        return {"ok": False, "error": f"INSERT demande : {e}"}

    try:
        tk.query(
            """INSERT INTO pgt_tk_liste
                 (id_tk_liste, date_crea, op_crea, op_dest,
                  op_traitement_staff, ordre_traitement_staff,
                  service, id_tk_type_demande, id_tk_statut,
                  cloturee, modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, 0, '', 'JU', 28, 1,
                       FALSE, ?, ?, 'new')""",
            (id_tk, now, int(op_id), int(op_id), now, int(op_id)),
        )
    except Exception as e:
        logger.error("INSERT pgt_tk_liste (fact) KO : %s", e)
        return {"ok": False, "error": f"INSERT ticket : {e}"}

    # Notification mail juristes (cf. WinDev)
    try:
        from app.core.config import MAIL_JURISTE_1, MAIL_RESP_JURISTE
        prenom = ""
        i = rh.query_one(
            "SELECT prenom FROM pgt_salarie WHERE id_salarie = ?",
            (int(op_id),),
        )
        if i:
            prenom = _cap_prenom((i.get("prenom") or "").strip())
        dest = [m for m in (MAIL_RESP_JURISTE, MAIL_JURISTE_1) if m]
        html = (
            "<font face='arial' style='font-size:10pt;'><p> Bonjour,</p>"
            f"<p>Un ticket de facturation vient d'être créé par {prenom} "
            f"pour la société {lib_ste} pour un montant de {montant:.2f}€.</p>"
            "<br/>---Cdt.<br/><p><i>PS : Ceci est un mail automatique, "
            "ne pas répondre. Merci.</i></p></font>"
        )
        if dest:
            envoi_mail_rh(f"Ticket Facture DISTRIB - {lib_ste}", html, dest)
    except Exception:
        logger.exception("Notification mail juristes")

    return {"ok": True, "id_tk_liste": str(id_tk), "fic_facture": fic}


def recharger_facture(
    id_tk_liste: int, filename: str, content: bytes, op_id: int,
) -> dict:
    """Cf. WinDev Btn Recharger la facture sur le Ticket :
    remplace le PDF sur FTP + UPDATE fic_facture + mail juristes.
    """
    from app.core.config import FTP_GESTION_RH_PATH
    from app.shared.tickets.forms.cttw_pdf import ftp_upload
    from app.shared.notifications.mail import envoi_mail_rh

    tk_bo = get_pg_connection("ticket_bo")
    d = tk_bo.query_one(
        """SELECT id_gerant, id_ste, montant
             FROM pgt_tk_demande_facturation_distrib
            WHERE id_tk_liste = ?""",
        (int(id_tk_liste),),
    )
    if not d:
        return {"ok": False, "error": "Ticket introuvable"}
    id_gerant = int(d.get("id_gerant") or 0)
    id_ste = int(d.get("id_ste") or 0)
    montant = float(d.get("montant") or 0)

    rh = get_pg_connection("rh")
    ste = rh.query_one(
        "SELECT raison_sociale FROM pgt_societe WHERE id_ste = ?",
        (id_ste,),
    )
    lib_ste = (ste.get("raison_sociale") if ste else "") or "STE"

    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    fic = f"{ts}_{_sanitize_filename(lib_ste)}_Facture.{ext}"

    try:
        ftp_upload(
            f"{FTP_GESTION_RH_PATH.rstrip('/')}/{id_gerant}/Factures",
            fic, content,
        )
    except Exception as e:
        return {"ok": False, "error": f"Upload FTP : {e}"}

    now = _now_iso()
    try:
        tk_bo.query(
            """UPDATE pgt_tk_demande_facturation_distrib
                  SET fic_facture = ?, modif_date = ?, modif_op = ?,
                      modif_elem = 'modif'
                WHERE id_tk_liste = ?""",
            (fic, now, int(op_id), int(id_tk_liste)),
        )
    except Exception as e:
        return {"ok": False, "error": f"UPDATE demande : {e}"}

    # Notification mail juristes
    try:
        from app.core.config import MAIL_JURISTE_1, MAIL_RESP_JURISTE
        prenom = ""
        i = rh.query_one(
            "SELECT prenom FROM pgt_salarie WHERE id_salarie = ?",
            (int(op_id),),
        )
        if i:
            prenom = _cap_prenom((i.get("prenom") or "").strip())
        dest = [m for m in (MAIL_RESP_JURISTE, MAIL_JURISTE_1) if m]
        html = (
            "<font face='arial' style='font-size:10pt;'><p> Bonjour,</p>"
            f"<p>Une facture pour la société {lib_ste} a été modifiée par "
            f"{prenom} sur le ticket de demande facturation pour un montant "
            f"de {montant:.2f}€.</p><br/>---Cdt.<br/>"
            "<p><i>PS : Ceci est un mail automatique, ne pas répondre. "
            "Merci.</i></p></font>"
        )
        if dest:
            envoi_mail_rh(
                f"Demande de facturation Distrib - {lib_ste}", html, dest,
            )
    except Exception:
        logger.exception("Notification mail juristes (recharge)")

    return {"ok": True, "fic_facture": fic}


# --------------------------------------------------------------------
# 5 boutons Doc (uniques + annuels : logique identique cote WinDev)
# --------------------------------------------------------------------

def _get_doc_row(id_doc: int) -> Optional[dict]:
    """Charge une ligne pgt_doc_distrib + lib_doc + id_ste + id_gerant.
    Retour : None si introuvable ou soft-deleted.
    """
    rh = get_pg_connection("rh")
    try:
        r = rh.query_one(
            """SELECT d.id_doc_distrib, d.id_ste, d.id_gerant,
                      d.id_type_doc_distributeur, d.date_prevue, d.date_depot,
                      d.nom_fichier, t.lib_doc, s.raison_sociale
                 FROM pgt_doc_distrib d
                 JOIN pgt_type_doc_distributeur t
                      ON t.id_type_doc_distributeur = d.id_type_doc_distributeur
                 LEFT JOIN pgt_societe s ON s.id_ste = d.id_ste
                WHERE d.id_doc_distrib = ?
                  AND (d.modif_elem IS NULL
                       OR d.modif_elem NOT LIKE 'suppr%')""",
            (int(id_doc),),
        )
    except Exception:
        r = None
    return r


def associer_doc_from_pc(
    id_doc: int, filename: str, content: bytes, op_id: int,
) -> dict:
    """Bouton 'Associer' (vert) - cas 1 : upload depuis le PC.

    Cf. WinDev : upload FTP /gestionRH/{IdGerant}/Fiches_Salaires/ puis
    UPDATE pgt_doc_distrib.nom_fichier + date_depot + id_gerant.
    Nom du fichier : {date}_{IdSte}_{LibDoc}<ext>.
    """
    from app.core.config import FTP_GESTION_RH_PATH
    from app.shared.tickets.forms.cttw_pdf import ftp_upload

    d = _get_doc_row(id_doc)
    if not d:
        return {"ok": False, "error": "Doc introuvable"}

    id_ste = int(d.get("id_ste") or 0)
    lib_doc = (d.get("lib_doc") or "").strip()

    # Recupere id_gerant depuis la societe (cf. WinDev : Id_Gerant est
    # le id_gerant de la societe, pas celui du doc).
    rh = get_pg_connection("rh")
    ste = rh.query_one(
        "SELECT id_gerant FROM pgt_societe WHERE id_ste = ?",
        (id_ste,),
    )
    id_gerant = int((ste or {}).get("id_gerant") or 0)
    if not id_gerant:
        return {"ok": False, "error": "Pas de gerant associe a la societe"}

    # Nom du fichier : cf. WinDev DateSys() + IdSte + LibDoc + extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    ymd = date.today().isoformat()
    fic = f"{ymd}_{id_ste}_{_sanitize_filename(lib_doc)}.{ext}"

    try:
        ftp_upload(
            f"{FTP_GESTION_RH_PATH.rstrip('/')}/{id_gerant}/Fiches_Salaires",
            fic, content,
        )
    except Exception as e:
        return {"ok": False, "error": f"Upload FTP : {e}"}

    now = _now_iso()
    try:
        rh.query(
            """UPDATE pgt_doc_distrib
                  SET id_gerant = ?, date_depot = ?, nom_fichier = ?,
                      modif_date = ?, modif_op = ?, modif_elem = 'modif'
                WHERE id_doc_distrib = ?""",
            (id_gerant, ymd, fic, now, int(op_id), int(id_doc)),
        )
    except Exception as e:
        return {"ok": False, "error": f"UPDATE : {e}"}

    return {"ok": True, "nom_fichier": fic}


def associer_doc_from_gerant(
    id_doc: int, nom_fichier: str, op_id: int,
) -> dict:
    """Bouton 'Associer' (vert) - cas 2 : selection depuis l'espace
    Doc du Gerant (Fen_DocGerant). On recoit juste le nom du fichier
    deja present sur le FTP.
    """
    d = _get_doc_row(id_doc)
    if not d:
        return {"ok": False, "error": "Doc introuvable"}
    if not nom_fichier:
        return {"ok": False, "error": "Nom de fichier manquant"}

    id_ste = int(d.get("id_ste") or 0)
    rh = get_pg_connection("rh")
    ste = rh.query_one(
        "SELECT id_gerant FROM pgt_societe WHERE id_ste = ?",
        (id_ste,),
    )
    id_gerant = int((ste or {}).get("id_gerant") or 0)

    now = _now_iso()
    try:
        rh.query(
            """UPDATE pgt_doc_distrib
                  SET id_gerant = ?, date_depot = ?, nom_fichier = ?,
                      modif_date = ?, modif_op = ?, modif_elem = 'modif'
                WHERE id_doc_distrib = ?""",
            (id_gerant, date.today().isoformat(), nom_fichier,
             now, int(op_id), int(id_doc)),
        )
    except Exception as e:
        return {"ok": False, "error": f"UPDATE : {e}"}
    return {"ok": True, "nom_fichier": nom_fichier}


def desassocier_doc(id_doc: int, op_id: int) -> dict:
    """Bouton 'Desassocier' (rouge) : vide nom_fichier + date_depot.
    Cf. WinDev : NomFichier = '', DateDepot = ''.
    """
    if not _get_doc_row(id_doc):
        return {"ok": False, "error": "Doc introuvable"}
    now = _now_iso()
    try:
        get_pg_connection("rh").query(
            """UPDATE pgt_doc_distrib
                  SET nom_fichier = '', date_depot = NULL,
                      modif_date = ?, modif_op = ?, modif_elem = 'modif'
                WHERE id_doc_distrib = ?""",
            (now, int(op_id), int(id_doc)),
        )
    except Exception as e:
        return {"ok": False, "error": f"UPDATE : {e}"}
    return {"ok": True}


def supprimer_doc(id_doc: int, op_id: int) -> dict:
    """Bouton 'Poubelle' : soft-delete modif_elem = 'suppr'."""
    if not _get_doc_row(id_doc):
        return {"ok": False, "error": "Doc introuvable"}
    now = _now_iso()
    try:
        get_pg_connection("rh").query(
            """UPDATE pgt_doc_distrib
                  SET modif_date = ?, modif_op = ?, modif_elem = 'suppr'
                WHERE id_doc_distrib = ?""",
            (now, int(op_id), int(id_doc)),
        )
    except Exception as e:
        return {"ok": False, "error": f"UPDATE : {e}"}
    return {"ok": True}


def toggle_rappel_doc(id_doc: int, op_id: int) -> dict:
    """Bouton 'Active/Deactive rappel' (cloche) : bascule le doc entre
    - nom_fichier = 'PAS RAPPEL' (rappel desactive)
    - nom_fichier = '' (rappel active, doc a fournir)

    Cf. WinDev selon NomFichier :
      '' -> 'PAS RAPPEL' (desactive)
      'PAS RAPPEL' -> '' (reactive)
      Autre (fichier deja associe) -> ne fait rien (cf. autres cas WinDev).
    """
    d = _get_doc_row(id_doc)
    if not d:
        return {"ok": False, "error": "Doc introuvable"}
    current = (d.get("nom_fichier") or "").strip()
    if current == "":
        new_val = "PAS RAPPEL"
    elif current == "PAS RAPPEL":
        new_val = ""
    else:
        # Fichier deja associe -> pas de bascule (cf. WinDev 'autres cas')
        return {"ok": True, "no_change": True}
    now = _now_iso()
    try:
        get_pg_connection("rh").query(
            """UPDATE pgt_doc_distrib
                  SET nom_fichier = ?,
                      modif_date = ?, modif_op = ?, modif_elem = 'modif'
                WHERE id_doc_distrib = ?""",
            (new_val, now, int(op_id), int(id_doc)),
        )
    except Exception as e:
        return {"ok": False, "error": f"UPDATE : {e}"}
    return {"ok": True, "nom_fichier": new_val}


# --------------------------------------------------------------------
# Suivi ADM (memos gerant)
# --------------------------------------------------------------------

def _gerant_and_libste(id_ste: int) -> tuple[int, str]:
    """Retourne (id_gerant, raison_sociale) pour une societe."""
    rh = get_pg_connection("rh")
    ste = rh.query_one(
        "SELECT id_gerant, raison_sociale FROM pgt_societe WHERE id_ste = ?",
        (int(id_ste),),
    )
    if not ste:
        return (0, "")
    return (
        int(ste.get("id_gerant") or 0),
        (ste.get("raison_sociale") or "").strip(),
    )


def list_suivi_adm(id_ste: int) -> list[dict]:
    """Journal salarie_suiviADM du gerant de la societe.

    Cf. WinDev Table_ReqSuiviADM :
      SELECT OPCrea, Description, Datecrea
      FROM salarie_suiviADM
      WHERE IDSalarie = Id_Gerant
        AND ModifElem NOT LIKE '%suppr%'
      ORDER BY Datecrea DESC
    """
    id_gerant, _ = _gerant_and_libste(id_ste)
    if not id_gerant:
        return []
    # Reutilise le helper deja teste dans factdistrib.py
    from app.shared.tickets.forms.factdistrib import _suivi_adm
    return _suivi_adm(id_gerant)


def add_memo_suivi_adm(
    id_ste: int, message: str, op_id: int,
) -> dict:
    """Cf. WinDev 'Suivi ADM - Btn Envoyer' : INSERT salarie_suiviADM
    (id_salarie = id_gerant) + mail juristes/BO (Ajout Memo Distrib).
    """
    message = (message or "").strip()
    if not message:
        return {"ok": False, "error": "Mémo vide"}

    id_gerant, lib_ste = _gerant_and_libste(id_ste)
    if not id_gerant:
        return {"ok": False, "error": "Pas de gérant associé à la société"}

    id_memo = _new_id()
    now = _now_iso()
    rh = get_pg_connection("rh")
    try:
        rh.query(
            """INSERT INTO pgt_salarie_suivi_adm
                 (id_salarie_suivi_adm, id_salarie, op_crea, description,
                  date_crea, modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'new')""",
            (id_memo, id_gerant, int(op_id), message,
             now, now, int(op_id)),
        )
    except Exception as e:
        logger.error("INSERT pgt_salarie_suivi_adm KO : %s", e)
        return {"ok": False, "error": f"INSERT : {e}"}

    # Mail juristes + BO (cf. WinDev)
    mail_statut = ""
    try:
        from app.core.config import (
            MAIL_BO, MAIL_JURISTE_1, MAIL_RESP_JURISTE,
        )
        from app.shared.notifications.mail import envoi_mail_rh

        prenom = ""
        i = rh.query_one(
            "SELECT prenom FROM pgt_salarie WHERE id_salarie = ?",
            (int(op_id),),
        )
        if i:
            prenom = _cap_prenom((i.get("prenom") or "").strip())
        dest = [m for m in (MAIL_RESP_JURISTE, MAIL_JURISTE_1, MAIL_BO) if m]
        html = (
            "<font face='arial' style='font-size:10pt;'><p> Bonjour,</p>"
            f"<p>Un mémo vient d'être déposé par {prenom} concernant "
            f"la société {lib_ste}.</p>"
            "<br/>---Cdt.<br/>"
            "<p><i>PS : Ceci est un mail automatique, ne pas répondre. "
            "Merci.</i></p></font>"
        )
        if dest:
            ok = envoi_mail_rh(
                f"Ajout Mémo Distrib - {lib_ste}", html, dest,
            )
            mail_statut = "envoye" if ok else "echec"
    except Exception:
        logger.exception("Notification mail juristes (memo distrib)")

    return {"ok": True, "id": str(id_memo), "mail_statut": mail_statut}


def download_doc(id_doc: int) -> Optional[dict]:
    """Bouton 'Telecharger' : recupere le fichier via FTP.

    Cf. WinDev URL : /gestionRH/{IdGerant}/Fiches_Salaires/{NomFichier}.
    Retour : {'filename': ..., 'content': bytes, 'lib_doc': ...} ou None.
    """
    from app.core.config import FTP_GESTION_RH_PATH
    from app.shared.tickets.forms.factdistrib import _ftp_download

    d = _get_doc_row(id_doc)
    if not d:
        return None
    fic = (d.get("nom_fichier") or "").strip()
    if not fic or fic == "PAS RAPPEL":
        return None
    id_gerant = int(d.get("id_gerant") or 0)
    if not id_gerant:
        return None

    path = f"{FTP_GESTION_RH_PATH.rstrip('/')}/{id_gerant}/Fiches_Salaires/{fic}"
    content = _ftp_download(path)
    if not content:
        return None
    return {
        "filename": fic,
        "content": content,
        "lib_doc": (d.get("lib_doc") or "").strip(),
    }
