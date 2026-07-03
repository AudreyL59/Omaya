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

from datetime import date, datetime
from typing import Optional

from app.core.database.pg import get_pg_connection
from app.core.utils.sentinel_dates import is_sentinel, to_iso


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
                     FROM pgt_tk_demande_ctt_courtage tcc
                     JOIN pgt_tk_liste tl
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
                     FROM pgt_tk_demande_doc_distrib tdd
                     JOIN pgt_tk_liste tl
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
    """
    tk_bo = get_pg_connection("ticket_bo")
    rows = tk_bo.query(
        """SELECT tl.id_tk_liste, tl.date_crea, tl.cloturee, tl.op_crea,
                  fd.id_gerant, fd.fic_facture, fd.fic_preuve_virement,
                  fd.date_virement, fd.montant
             FROM pgt_tk_liste tl
             JOIN pgt_tk_demande_facturation_distrib fd
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
