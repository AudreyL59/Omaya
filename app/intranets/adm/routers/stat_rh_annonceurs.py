from fastapi import APIRouter, Depends, Query

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.stat_rh_annonceurs import StatAnnonceursResponse
from app.intranets.adm.services.stat_rh_annonceurs import calculer_stats_annonceurs

router = APIRouter(prefix="/stat-rh", tags=["adm-stat-rh"])


@router.get("/annonceurs", response_model=StatAnnonceursResponse)
def get_stats_annonceurs(
    date_du: str = Query(..., description="YYYYMMDD"),
    date_au: str = Query(..., description="YYYYMMDD"),
    id_annonceur: str | None = Query(None, description="ID annonceur specifique ou vide pour tous"),
    user: UserToken = Depends(get_current_user),
):
    """
    Stats Annonceurs : CV saisis via annonceurs sur une periode.
    Filtre optionnel sur un annonceur specifique.
    """
    id_ann_int: int | None = None
    if id_annonceur:
        try:
            v = int(id_annonceur)
            if v > 0:
                id_ann_int = v
        except ValueError:
            pass

    return calculer_stats_annonceurs(
        date_debut=date_du,
        date_fin=date_au,
        id_annonceur=id_ann_int,
    )
