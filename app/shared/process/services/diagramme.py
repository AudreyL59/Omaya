"""Lecture / ecriture du diagramme (JSON tldraw) d'un process.

Le champ `diagramme_json` (text) est ajoute par le patch
migration/patches/add_process_diagramme_json.sql. L'ancien champ
`diagramme` (bytea WinDev) reste en base pour recuperation ulterieure
mais n'est pas expose par cet API.
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.core.database.pg import get_pg_connection

logger = logging.getLogger(__name__)


def get_diagramme(id_process: int) -> str:
    """Retourne le JSON tldraw (chaine vide si absent)."""
    if not id_process:
        return ""
    db = get_pg_connection("divers")
    try:
        row = db.query_one(
            """SELECT diagramme_json
                 FROM divers.pgt_process
                WHERE id_process = ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                LIMIT 1""",
            (int(id_process),),
        )
    except Exception:
        logger.exception("get_diagramme id=%s", id_process)
        return ""
    return (row or {}).get("diagramme_json") or ""


def save_diagramme(id_process: int, json_str: str, user_id: int) -> bool:
    """Ecrit le JSON tldraw. Retourne True si succes.

    On accepte une chaine vide -> reset (SET diagramme_json = NULL) pour
    permettre au user d'effacer le diagramme.
    """
    if not id_process:
        return False
    db = get_pg_connection("divers")
    now = datetime.now()
    value = json_str if json_str and json_str.strip() else None
    try:
        db.query(
            """UPDATE divers.pgt_process
                  SET diagramme_json = ?,
                      derniere_modif = ?,
                      ope_modif = ?,
                      modif_date = ?, modif_op = ?, modif_elem = 'modif'
                WHERE id_process = ?""",
            (value, now, int(user_id), now, int(user_id), int(id_process)),
        )
        return True
    except Exception:
        logger.exception("save_diagramme id=%s", id_process)
        return False
