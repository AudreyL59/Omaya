"""
Onglet 'Declaratif' de la fiche salarie ADM.

Transposition de la fenetre WinDev FI_SalarieDeclaratif (lecture seule).

Tableau filtre par 2 dates (Du / Au) :
  - DATE | Presence (booleen) | Motif Absence (lib si absent)
  - INNER JOIN pgt_salarie_decl_presence + pgt_type_absence sur motifabsence
  - Tri date DESC.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _iso(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def load_declaratif(
    id_salarie: int, date_du: str, date_au: str
) -> list[dict]:
    """Liste les declarations de presence du salarie entre 2 dates.

    Retourne {date, presence, motif_absence (lib_absence si absent)}.
    """
    if not date_du or not date_au:
        return []
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT sdp.date, sdp.presence, sdp.motifabsence,
                  ta.lib_absence
           FROM rh.pgt_salarie_decl_presence sdp
           INNER JOIN rh.pgt_type_absence ta
             ON ta.id_type_absence = sdp.motifabsence
           WHERE sdp.id_salarie = ?
             AND sdp.date BETWEEN ?::date AND ?::date
             AND sdp.modif_elem <> 'suppr'
           ORDER BY sdp.date DESC""",
        (int(id_salarie), date_du, date_au),
    )
    out = []
    for r in rows or []:
        presence = bool(r.get("presence"))
        # Cf. WinDev : si Presence = Faux -> Motif_Absence = lib_absence
        motif = "" if presence else _str(r.get("lib_absence"))
        out.append({
            "date": _iso(r.get("date")),
            "presence": presence,
            "motif_absence": motif,
        })
    return out
