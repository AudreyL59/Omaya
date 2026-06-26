"""Service Fen_ChoixImports + suivi des imports automatiques (ADM).

Hub des imports manuels par partenaire + lecture en continu (polling)
de adv.pgt_importautosuivi (jauges d'avancement).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection
from app.shared.recrutement.services.recherche_cv import _int, _str


class PartenaireImport(BaseModel):
    id_partenaire: str
    prefixe_bdd: str         # ex: 'SFR', 'OEN'
    lib_partenaire: str
    is_actif: bool = True


class ImportAutoSuivi(BaseModel):
    type: str
    total: int
    avancement: int
    pourcent: float
    date_import: str = ""
    modif_date: str = ""


def list_partenaires() -> list[PartenaireImport]:
    """Liste des partenaires (tous, actifs en premier) pour la combo
    de choix d'import manuel."""
    db = get_pg_connection("adv")
    rows = db.query(
        """SELECT id_partenaire, prefixe_bdd, lib_partenaire, is_actif
             FROM pgt_partenaire
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
              AND COALESCE(NULLIF(prefixe_bdd, ''), '') <> ''
         ORDER BY is_actif DESC, lib_partenaire ASC"""
    ) or []
    return [PartenaireImport(
        id_partenaire=str(_int(r["id_partenaire"])),
        prefixe_bdd=_str(r["prefixe_bdd"]),
        lib_partenaire=_str(r["lib_partenaire"]),
        is_actif=bool(r.get("is_actif")),
    ) for r in rows]


def list_imports_auto_suivi() -> list[ImportAutoSuivi]:
    """Suivi des imports automatiques : ligne par type avec jauge."""
    db = get_pg_connection("adv")
    rows = db.query(
        """SELECT type, total, avancement, dateimport, modif_date
             FROM adv.pgt_importautosuivi
         ORDER BY modif_date DESC NULLS LAST"""
    ) or []
    out: list[ImportAutoSuivi] = []
    seen: set[str] = set()
    for r in rows:
        t = _str(r.get("type"))
        if t in seen:
            continue
        seen.add(t)
        total = _int(r.get("total")) or 0
        avc = _int(r.get("avancement")) or 0
        pct = (avc / total * 100) if total > 0 else 0.0
        di = r.get("dateimport")
        md = r.get("modif_date")
        out.append(ImportAutoSuivi(
            type=t,
            total=total,
            avancement=avc,
            pourcent=round(pct, 1),
            date_import=di.isoformat() if di else "",
            modif_date=md.isoformat(sep=" ")[:19] if md else "",
        ))
    return out
