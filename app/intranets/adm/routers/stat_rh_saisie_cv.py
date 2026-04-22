from fastapi import APIRouter, Depends, Query

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.stat_rh_saisie_cv import StatSaisieCvResponse
from app.intranets.adm.services.stat_rh_saisie_cv import calculer_stats_saisie_cv

router = APIRouter(prefix="/stat-rh", tags=["adm-stat-rh"])


@router.get("/saisie-cv", response_model=StatSaisieCvResponse)
def get_stats_saisie_cv(
    date_du: str = Query(..., description="YYYYMMDD"),
    date_au: str = Query(..., description="YYYYMMDD"),
    type_recherche: str = Query("service", description="service ou personne"),
    id_salarie: int | None = Query(None, description="ID operateur (mode personne)"),
    user: UserToken = Depends(get_current_user),
):
    """
    Stats Saisie et Traitement des CV sur une periode.

    - type_recherche = 'service' : tous les operateurs, Origine CVtheque = 1 (requiert StatsRHGr)
    - type_recherche = 'personne' : filtre sur un operateur (toutes origines).
    """
    # Service complet requiert StatsRHGr
    if type_recherche == "service" and "StatsRHGr" not in user.droits:
        type_recherche = "personne"

    op_filter: int | None = None
    if type_recherche == "personne":
        if id_salarie is not None and id_salarie > 0:
            if id_salarie != user.id_salarie and "StatsRHGr" not in user.droits:
                op_filter = user.id_salarie
            else:
                op_filter = id_salarie
        else:
            op_filter = user.id_salarie

    return calculer_stats_saisie_cv(
        date_debut=date_du,
        date_fin=date_au,
        type_recherche=type_recherche,
        id_ope_filter=op_filter,
    )
