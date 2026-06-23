"""
Service Fen_SuiviMutuelle (ADM Salaries -> Adhesion mutuelle entreprise).

Retourne 2 listes :
  - Actifs : salaries actifs sans docs envoyes ni pas-adhesion.
  - Sortants : salaries sortis (en_activite=False) mais sans docs.

Filtres communs :
  - societe.id_type_orga = 1 (FDV Interne)
  - id_ste >= 2 AND id_ste NOT IN (4, 11)
  - lib_poste NOT LIKE '%DISTRI%'
  - mutuelle_doc_envoyes = FALSE
  - mutuelle_pas_adhesion = FALSE
  - modif_elem NOT LIKE '%suppr%'
"""

from __future__ import annotations

from typing import Any

from app.core.database.pg import get_pg_connection


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


_BASE_SQL = """
SELECT s.id_salarie, s.nom, s.prenom,
       e.date_debut, e.id_ste, e.en_pause,
       sm.id_salarie_mutuelle,
       sm.mutuelle_dossier, sm.mutuelle_att_ss, sm.mutuelle_rib,
       sm.mutuelle_doc_envoyes, sm.mutuelle_recep_certif,
       so.id_type_orga, so.rs_interne, so.raison_sociale,
       tp.lib_poste
  FROM rh.pgt_salarie s
 INNER JOIN rh.pgt_salarie_embauche e ON e.id_salarie = s.id_salarie
 INNER JOIN rh.pgt_salarie_mutuelle sm ON sm.id_salarie = s.id_salarie
 INNER JOIN rh.pgt_societe so ON so.id_ste = e.id_ste
 INNER JOIN rh.pgt_type_poste tp ON tp.id_type_poste = e.id_type_poste
 WHERE (s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')
   AND COALESCE(e.en_activite, FALSE) = ?
   AND COALESCE(sm.mutuelle_doc_envoyes, FALSE) = FALSE
   AND COALESCE(sm.mutuelle_pas_adhesion, FALSE) = FALSE
   AND so.id_type_orga = 1
   AND e.id_ste >= 2
   AND e.id_ste NOT IN (4, 11)
   AND tp.lib_poste NOT ILIKE '%DISTRI%'
 ORDER BY e.date_debut ASC
"""


def _row_to_dict(r: dict) -> dict:
    prenom = _str(r.get("prenom")).strip()
    if prenom:
        prenom = prenom[:1].upper() + prenom[1:].lower()
    return {
        "id_salarie": str(_int(r.get("id_salarie"))),
        "id_salarie_mutuelle": str(_int(r.get("id_salarie_mutuelle"))),
        "nom": _str(r.get("nom")),
        "prenom": prenom,
        "date_debut": _str(r.get("date_debut"))[:10],
        "id_ste": _int(r.get("id_ste")),
        "rs_interne": _str(r.get("rs_interne")) or _str(r.get("raison_sociale")),
        "lib_poste": _str(r.get("lib_poste")),
        "en_pause": bool(r.get("en_pause")),
        "mutuelle_dossier": bool(r.get("mutuelle_dossier")),
        "mutuelle_att_ss": bool(r.get("mutuelle_att_ss")),
        "mutuelle_rib": bool(r.get("mutuelle_rib")),
        "mutuelle_doc_envoyes": bool(r.get("mutuelle_doc_envoyes")),
        "mutuelle_recep_certif": bool(r.get("mutuelle_recep_certif")),
    }


def list_actifs() -> list[dict]:
    db = get_pg_connection("rh")
    rows = db.query(_BASE_SQL, (True,)) or []
    return [_row_to_dict(r) for r in rows]


def list_sortants() -> list[dict]:
    db = get_pg_connection("rh")
    rows = db.query(_BASE_SQL, (False,)) or []
    return [_row_to_dict(r) for r in rows]


def update_flags(
    id_salarie: int, payload: dict, op_id: int,
) -> dict:
    """Permet de toggler les 4 checkboxes + la coche 'documents envoyes'
    sans changer le reste. Cocher tout = sortir de la liste."""
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_salarie_mutuelle
              SET mutuelle_dossier = ?,
                  mutuelle_att_ss = ?,
                  mutuelle_rib = ?,
                  mutuelle_doc_envoyes = ?,
                  mutuelle_recep_certif = ?,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_salarie = ?""",
        (
            bool(payload.get("mutuelle_dossier")),
            bool(payload.get("mutuelle_att_ss")),
            bool(payload.get("mutuelle_rib")),
            bool(payload.get("mutuelle_doc_envoyes")),
            bool(payload.get("mutuelle_recep_certif")),
            int(op_id), int(id_salarie),
        ),
    )
    return {"ok": True}
