from fastapi import APIRouter, Depends, Query

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.stat_rh_rdv import StatRdvResponse
from app.intranets.adm.services.stat_rh_rdv import calculer_stats_rdv

router = APIRouter(prefix="/stat-rh", tags=["adm-stat-rh"])


@router.get("/rdv", response_model=StatRdvResponse)
def get_stats_rdv(
    date_du: str = Query(..., description="YYYYMMDD"),
    date_au: str = Query(..., description="YYYYMMDD"),
    type_date: str = Query("planif", description="planif ou rdv"),
    type_recherche: str = Query("service", description="service ou personne"),
    user: UserToken = Depends(get_current_user),
):
    """
    Stats de prise de RDV sur une periode.

    - type_date = 'planif' : filtre sur CvSuivi.Datecrea (date de planification)
    - type_date = 'rdv'    : filtre sur AgendaEvenement.DateDebut (date effective du RDV)
    - type_recherche = 'service' : tous les operateurs (requiert droit StatsRHGr)
    - type_recherche = 'personne' : uniquement les RDV de l'utilisateur connecte
    """
    # Controle de droit : service complet requis StatsRHGr ; sinon fallback sur 'personne'
    if type_recherche == "service" and "StatsRHGr" not in user.droits:
        type_recherche = "personne"

    op_filter = user.id_salarie if type_recherche == "personne" else None

    return calculer_stats_rdv(
        date_debut=date_du,
        date_fin=date_au,
        type_date=type_date,
        op_crea_filter=op_filter,
    )
