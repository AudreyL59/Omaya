"""
Onglet 'Absences' de la fiche salarie ADM.

Transposition de la fenetre WinDev FI_SalarieAbsences :
  - Tableau hierarchique groupe par Periode (AnneeConge, du 1er juin N
    au 31 mai N+1) puis par Type d'absence (IDTypeAbsence).
  - Colonnes : Motif | Du | Au | Nb Jours calendaires (NBJ) | Nb Jours
    ouvres Hors Samedi (NBJ_OUVRES) | nb Samedi.
  - Boutons : Nouveau / Modifier (popup Fen_SalarieAbsence) / Dupliquer
    (copie avec nouvel id) / Supprimer (soft delete via modif_elem).
"""

from __future__ import annotations

from datetime import datetime
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


def _iso(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _new_id() -> int:
    """ID 8 octets timestamp (cf. WinDev idEntierDateHeureSys)."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


def load_absences(id_salarie: int) -> list[dict]:
    """Liste les absences du salarie, triees par periode desc puis par
    type d'absence puis par date debut desc.
    """
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT
              a.id_absence, a.id_type_absence,
              a.date_debut, a.date_fin,
              a.nbj, a.nbj_ouvres, a.nb_samedi,
              a.periode,
              ta.lib_absence
           FROM rh.pgt_absence a
           LEFT JOIN rh.pgt_type_absence ta
             ON ta.id_type_absence = a.id_type_absence
           WHERE a.id_salarie = ?
             AND a.modif_elem NOT LIKE '%suppr%'
           ORDER BY a.periode DESC NULLS LAST,
                    a.id_type_absence ASC,
                    a.date_debut DESC NULLS LAST""",
        (int(id_salarie),),
    )
    return [
        {
            "id_absence": str(r.get("id_absence") or ""),
            "id_type_absence": _int(r.get("id_type_absence")),
            "lib_absence": _str(r.get("lib_absence")),
            "date_debut": _iso(r.get("date_debut")),
            "date_fin": _iso(r.get("date_fin")),
            "nbj": _int(r.get("nbj")),
            "nbj_ouvres": _int(r.get("nbj_ouvres")),
            "nb_samedi": _int(r.get("nb_samedi")),
            "periode": _str(r.get("periode")),
        }
        for r in rows
    ]


def duplicate_absence(id_absence: int, op_id: int) -> dict:
    """Btn 'Dupliquer' : copie l'absence avec un nouvel id (modif_elem='new')."""
    db = get_pg_connection("rh")
    row = db.query_one(
        """SELECT id_salarie, id_type_absence, date_debut, date_fin,
                  nbj, nbj_ouvres, nb_samedi, periode
           FROM rh.pgt_absence WHERE id_absence = ?""",
        (int(id_absence),),
    )
    if not row:
        return {"ok": False, "error": "Absence introuvable"}

    new_id = _new_id()
    db.query(
        """INSERT INTO rh.pgt_absence
              (id_absence, id_salarie, id_type_absence,
               date_debut, date_fin, nbj, nbj_ouvres, nb_samedi, periode,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id,
            _int(row.get("id_salarie")),
            _int(row.get("id_type_absence")),
            row.get("date_debut"),
            row.get("date_fin"),
            _int(row.get("nbj")),
            _int(row.get("nbj_ouvres")),
            _int(row.get("nb_samedi")),
            _str(row.get("periode")),
            _int(op_id),
        ),
    )
    return {"ok": True, "id_absence": str(new_id)}


def soft_delete_absence(id_absence: int, op_id: int) -> dict:
    """Btn 'Supprimer' : passe modif_elem='suppr'."""
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_absence SET
              modif_date = NOW(),
              modif_op = ?,
              modif_elem = 'suppr'
            WHERE id_absence = ?""",
        (_int(op_id), int(id_absence)),
    )
    return {"ok": True}
