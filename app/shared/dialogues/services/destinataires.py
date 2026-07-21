"""Portage WinDev Dialogue_ListeDest : salariés destinataires possibles.

Filtre : salariés en activité qui ont le droit `IntraConvDR`.
"""

from __future__ import annotations

import logging

from app.core.database.pg import get_pg_connection
from app.shared.dialogues.schemas.dialogues import SalarieDest

logger = logging.getLogger(__name__)


def _capitalise(v: str) -> str:
    """Portage WinDev capitalise() : 1re lettre majuscule, reste minuscule."""
    if not v:
        return ""
    return v[:1].upper() + v[1:].lower()


def liste_destinataires() -> list[SalarieDest]:
    db_rh = get_pg_connection("rh")
    try:
        rows = db_rh.query(
            """SELECT DISTINCT s.id_salarie, s.nom, s.prenom
                 FROM rh.pgt_salarie s
                 JOIN rh.pgt_salarie_embauche se ON se.id_salarie = s.id_salarie
                 JOIN rh.pgt_salarie_droit_acces sd ON sd.id_salarie = s.id_salarie
                 JOIN rh.pgt_type_droit_acces td
                   ON td.id_type_droit_acces = sd.id_type_droit_acces
                WHERE COALESCE(sd.droit_actif, FALSE) = TRUE
                  AND td.code_interne = 'IntraConvDR'
                  AND COALESCE(se.en_activite, FALSE) = TRUE
                  AND (s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')
                ORDER BY s.nom ASC, s.prenom ASC""",
        ) or []
    except Exception:
        logger.exception("liste_destinataires")
        return []
    return [
        SalarieDest(
            ID=str(int(r.get("id_salarie") or 0)) if r.get("id_salarie") else "",
            Nom=r.get("nom") or "",
            Prenom=_capitalise(r.get("prenom") or ""),
        )
        for r in rows
    ]
