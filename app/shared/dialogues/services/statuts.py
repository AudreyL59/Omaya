"""Portage WinDev Dialogue_Statuts : liste des statuts (référentiel)."""

from __future__ import annotations

import logging

from app.core.database.pg import get_pg_connection
from app.shared.dialogues.schemas.dialogues import DialogueStatut

logger = logging.getLogger(__name__)


def liste_statuts() -> list[DialogueStatut]:
    db = get_pg_connection("divers")
    try:
        rows = db.query(
            """SELECT id_dialogue_statut, lib_statut, couleur_statut
                 FROM divers.pgt_dialoguestatut
                WHERE modif_elem IS NULL OR modif_elem <> 'suppr'
                ORDER BY id_dialogue_statut ASC""",
        ) or []
    except Exception:
        logger.exception("liste_statuts")
        return []
    return [
        DialogueStatut(
            IdStatut=int(r.get("id_dialogue_statut") or 0),
            LibStatut=r.get("lib_statut") or "",
            CouleurStatut=int(r.get("couleur_statut") or 0),
        )
        for r in rows
    ]
