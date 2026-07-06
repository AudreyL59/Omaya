"""
Onglet 'Suivi ADM' de la fiche salarie ADM.

Transposition de la fenetre WinDev FI_SalarieSuiviADM :
  - Liste des memos deposes sur le salarie (pgt_salarie_suivi_adm)
  - Bouton Ajouter (insert seulement, pas de modif/suppression cote UI)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection
from app.core.utils.sentinel_dates import is_sentinel
from app.shared.tickets.service import rtf_to_text


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _iso_dt(v: Any) -> str:
    if v is None or is_sentinel(v):
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    s = str(v)
    if len(s) >= 19 and s[4] == "-" and s[7] == "-":
        return s[:19]
    return s


def _new_id() -> int:
    """ID 8 octets timestamp (cf. WinDev idEntierDateHeureSys)."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


def _capitalize_first(s: str) -> str:
    if not s:
        return ""
    return s[0].upper() + s[1:].lower()


def load_suivi_adm(id_salarie: int) -> list[dict]:
    """Liste des memos deposes sur le salarie, triee par date desc.

    Retourne {id, date_crea, op_crea_id, op_crea_nom, description}.
    """
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT s.id_salarie_suivi_adm, s.op_crea, s.description, s.date_crea,
                  op.nom AS op_nom, op.prenom AS op_prenom
           FROM rh.pgt_salarie_suivi_adm s
           LEFT JOIN rh.pgt_salarie op ON op.id_salarie = s.op_crea
           WHERE s.id_salarie = ?
             AND s.modif_elem NOT LIKE '%suppr%'
           ORDER BY s.date_crea DESC""",
        (int(id_salarie),),
    )
    return [
        {
            "id_salarie_suivi_adm": str(r.get("id_salarie_suivi_adm") or ""),
            "op_crea_id": str(r.get("op_crea") or ""),
            "op_crea_nom": (
                f"{_str(r.get('op_nom'))} {_capitalize_first(_str(r.get('op_prenom')))}"
            ).strip(),
            # cf. WinDev : description stockee en RTF (edit_rich WinDev).
            # rtf_to_text convertit vers texte brut lisible.
            "description": rtf_to_text(_str(r.get("description"))),
            "date_crea": _iso_dt(r.get("date_crea")),
        }
        for r in rows
    ]


def add_suivi_adm(id_salarie: int, description: str, op_id: int) -> dict:
    """Insert un nouveau memo (cf. WinDev Btn 'Ajouter')."""
    if not description.strip():
        return {"ok": False, "error": "Description vide"}

    db = get_pg_connection("rh")
    new_id = _new_id()
    db.query(
        """INSERT INTO rh.pgt_salarie_suivi_adm
              (id_salarie_suivi_adm, id_salarie, op_crea, description,
               date_crea, modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, NOW(), NOW(), ?, 'new')""",
        (
            new_id,
            _int(id_salarie),
            _int(op_id),
            description.strip(),
            _int(op_id),
        ),
    )
    return {"ok": True, "id_salarie_suivi_adm": str(new_id)}
