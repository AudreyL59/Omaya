"""
Recherche d'organigrammes (agences / equipes) pour les pickers ADM.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.core.database import get_connection

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

    db = get_connection("rh")
    like = f"%{search}%"
    rows = db.query(
        """SELECT a.idorganigramme, a.Lib_ORGA, a.IdPARENT,
            n.Lib_Niveau,
            b.Lib_ORGA AS Lib_Parent
        FROM organigramme a
        LEFT JOIN TypeNiveauOrga n ON a.IDTypeNiveauOrga = n.IDTypeNiveauOrga
        LEFT JOIN organigramme b ON a.IdPARENT = b.idorganigramme
        WHERE a.ModifELEM <> 'suppr'
          AND a.Lib_ORGA LIKE ?
        ORDER BY a.Lib_ORGA""",
        (like,),
    )
    return [
        {
            "id_orga": str(r.get("idorganigramme")),
            "lib_orga": r.get("Lib_ORGA") or "",
            "lib_niveau": r.get("Lib_Niveau") or "",
            "lib_parent": r.get("Lib_Parent") or "",
        }
        for r in rows
        if r.get("idorganigramme") and int(r.get("idorganigramme")) > 0
    ]
