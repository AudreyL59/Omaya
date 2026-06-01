"""
Recherche d'organigrammes (agences / equipes) pour les pickers ADM.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.core.database.pg import get_pg_connection

router = APIRouter(prefix="/organigrammes", tags=["adm-organigrammes"])


class OrgaItem(BaseModel):
    id_orga: str  # string pour preserver la precision (ids > 2^53)
    lib_orga: str
    lib_niveau: str = ""
    lib_parent: str = ""


@router.get("/search", response_model=list[OrgaItem])
def search_orgas(
    q: str = Query(..., min_length=1),
    user: UserToken = Depends(get_current_user),
):
    """
    Recherche les organigrammes actifs par libelle (LIKE '%q%').
    Retourne lib_orga + lib_niveau (Agence, Equipe, etc.) + lib_parent.
    """
    search = (q or "").strip()
    if not search:
        return []

    db = get_pg_connection("rh")
    like = f"%{search}%"
    rows = db.query(
        """SELECT a.idorganigramme, a.lib_orga, a.id_parent,
            n.lib_niveau,
            b.lib_orga AS lib_parent
        FROM pgt_organigramme a
        LEFT JOIN pgt_type_niveau_orga n ON a.id_type_niveau_orga = n.id_type_niveau_orga
        LEFT JOIN pgt_organigramme b ON a.id_parent = b.idorganigramme
        WHERE a.modif_elem <> 'suppr'
          AND a.lib_orga LIKE ?
        ORDER BY a.lib_orga""",
        (like,),
    )
    return [
        {
            "id_orga": str(r.get("idorganigramme")),
            "lib_orga": r.get("lib_orga") or "",
            "lib_niveau": r.get("lib_niveau") or "",
            "lib_parent": r.get("lib_parent") or "",
        }
        for r in rows
        if r.get("idorganigramme") and int(r.get("idorganigramme")) > 0
    ]
