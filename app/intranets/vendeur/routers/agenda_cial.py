from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.vendeur.schemas.agenda_cial import (
    AgendaCialRDV,
    CommercialItem,
)
from app.intranets.vendeur.services.agenda_cial import (
    lister_rdvs_cial,
    rechercher_commerciaux,
)

router = APIRouter(prefix="/agenda-cial", tags=["vendeur-agenda-cial"])


@router.get("", response_model=list[AgendaCialRDV])
def get_agenda_cial(
    date_from: str,
    date_to: str,
    id_commercial: int = 0,
    user: UserToken = Depends(get_current_user),
):
    """
    Liste les RDV de l'agenda commercial d'un commercial entre deux dates.
    date_from / date_to : format YYYYMMDD.
    """
    cid = id_commercial or user.id_salarie
    return lister_rdvs_cial(cid, date_from, date_to)


@router.get("/commerciaux", response_model=list[CommercialItem])
def get_commerciaux(q: str = "", user: UserToken = Depends(get_current_user)):
    """
    Recherche les commerciaux accessibles à l'utilisateur :
    salariés avec droit AgendaCial OU ayant au moins 1 RDV dans AgendaCommercial.
    """
    acces_global = "ProdRezo" in user.droits
    is_resp = user.is_resp or "ProdGR" in user.droits
    results = rechercher_commerciaux(
        user.id_salarie, q, acces_global=acces_global, is_resp=is_resp
    )
    return [
        {"id_salarie": r["id_salarie"], "nom": r["nom"], "prenom": r["prenom"]}
        for r in results
    ]
