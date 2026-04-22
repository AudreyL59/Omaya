"""
Recherche de salaries — commune a l'intranet ADM.

Utilisee par les pickers de salarie dans les pages Stats RH, Factures, etc.
Pas de filtre de scope : l'intranet ADM a acces a tous les salaries actifs.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.core.database import get_connection

router = APIRouter(prefix="/salaries", tags=["adm-salaries"])


class SalarieItem(BaseModel):
    id_salarie: str
    nom: str
    prenom: str


@router.get("/search", response_model=list[SalarieItem])
def search_salaries(
    q: str = Query(..., min_length=1),
    user: UserToken = Depends(get_current_user),
):
    """
    Recherche les salaries actifs par nom (LIKE 'q%'). Case-insensitive cote HFSQL :
    on met q en majuscules car la colonne NOM est stockee en majuscules.
    """
    search = q.strip().upper()
    if not search:
        return []

    db = get_connection("rh")
    like = f"{search}%"
    rows = db.query(
        """SELECT DISTINCT s.IDSalarie, s.NOM, s.PRENOM
        FROM salarie s
        INNER JOIN salarie_embauche se ON s.IDSalarie = se.IDSalarie
        WHERE se.EnActivité = 1
          AND s.NOM LIKE ?
        ORDER BY s.NOM, s.PRENOM""",
        (like,),
    )
    return [
        {
            "id_salarie": str(r.get("IDSalarie")),
            "nom": (r.get("NOM") or "").strip(),
            "prenom": (r.get("PRENOM") or "").strip(),
        }
        for r in rows
    ]
