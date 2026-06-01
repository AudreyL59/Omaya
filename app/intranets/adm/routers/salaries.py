"""
Recherche de salaries — commune a l'intranet ADM.

Utilisee par les pickers de salarie dans les pages Stats RH, Factures, etc.
Pas de filtre de scope : l'intranet ADM a acces a tous les salaries actifs.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.core.database.pg import get_pg_connection

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
    Recherche les salaries actifs par nom (LIKE 'q%'). Les noms sont stockes
    en majuscules en base : on uppercase la saisie pour matcher.
    """
    search = q.strip().upper()
    if not search:
        return []

    db = get_pg_connection("rh")
    like = f"{search}%"
    rows = db.query(
        """SELECT DISTINCT s.id_salarie, s.nom, s.prenom
        FROM pgt_salarie s
        INNER JOIN pgt_salarie_embauche se ON s.id_salarie = se.id_salarie
        WHERE se.en_activite = TRUE
          AND s.nom LIKE ?
        ORDER BY s.nom, s.prenom""",
        (like,),
    )
    return [
        {
            "id_salarie": str(r.get("id_salarie")),
            "nom": (r.get("nom") or "").strip(),
            "prenom": (r.get("prenom") or "").strip(),
        }
        for r in rows
    ]
