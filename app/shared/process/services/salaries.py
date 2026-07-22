"""Recherche de salaries pour l'autocomplete des droits d'acces process."""

from __future__ import annotations

import logging

from app.core.database.pg import get_pg_connection
from app.shared.process.services._helpers import _capitalise

logger = logging.getLogger(__name__)


def search_salaries(q: str, limit: int = 20) -> list[dict]:
    """Retourne des salaries actifs qui matchent la query (nom ou prenom).

    Format : [{'ID': str, 'Nom': str, 'Prenom': str, 'Lib': 'NOM Prenom'}]
    """
    q = (q or "").strip()
    if len(q) < 2:
        return []
    rh = get_pg_connection("rh")
    pattern = f"%{q}%"
    try:
        rows = rh.query(
            """SELECT s.id_salarie, s.nom, s.prenom
                 FROM rh.pgt_salarie s
                 JOIN rh.pgt_salarie_embauche se ON se.id_salarie = s.id_salarie
                WHERE COALESCE(se.en_activite, FALSE) = TRUE
                  AND (s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')
                  AND (s.nom ILIKE ? OR s.prenom ILIKE ?)
                ORDER BY s.nom ASC, s.prenom ASC
                LIMIT ?""",
            (pattern, pattern, int(limit)),
        ) or []
    except Exception:
        logger.exception("search_salaries q=%s", q)
        return []
    out = []
    for r in rows:
        sid = int(r.get("id_salarie") or 0)
        if not sid:
            continue
        nom = (r.get("nom") or "").strip()
        prenom = _capitalise((r.get("prenom") or "").strip())
        out.append({
            "ID": str(sid),
            "Nom": nom,
            "Prenom": prenom,
            "Lib": f"{nom} {prenom}".strip(),
        })
    return out
