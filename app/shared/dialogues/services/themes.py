"""Portage WinDev Dialogue_Themes : liste des thèmes (référentiel).

Port strict : renvoie TOUS les thèmes non supprimés, ordre alphabétique.
Le filtre par droits (CodeDroit) se fait côté UI si besoin.
"""

from __future__ import annotations

import logging

from app.core.database.pg import get_pg_connection
from app.shared.dialogues.schemas.dialogues import DialogueTheme

logger = logging.getLogger(__name__)


def liste_themes() -> list[DialogueTheme]:
    db = get_pg_connection("divers")
    try:
        rows = db.query(
            """SELECT id_dialogue_theme, lib_theme, code_droit
                 FROM divers.pgt_dialoguetheme
                WHERE modif_elem IS NULL OR modif_elem <> 'suppr'
                ORDER BY lib_theme ASC""",
        ) or []
    except Exception:
        logger.exception("liste_themes")
        return []
    return [
        DialogueTheme(
            IdTheme=int(r.get("id_dialogue_theme") or 0),
            LibTheme=r.get("lib_theme") or "",
            CodeDroit=r.get("code_droit") or "",
        )
        for r in rows
    ]
