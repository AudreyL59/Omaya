"""Router Fen_DistribCttCourtage (Docs Dematerialises d'une societe)."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import distrib_courtage as svc

router = APIRouter(prefix="/distrib-courtage", tags=["adm-distrib-courtage"])


@router.get("/{id_ste}/infos", response_model=svc.DistribInfos)
def get_distrib_infos(
    id_ste: int,
    _u: UserToken = Depends(get_current_user),
):
    d = svc.get_distrib_infos(id_ste)
    if not d:
        raise HTTPException(404, "Société introuvable")
    return d


@router.get("/{id_distrib}/groupes-rem",
            response_model=list[svc.GroupeRemItem])
def get_distrib_groupes_rem(
    id_distrib: int,
    _u: UserToken = Depends(get_current_user),
):
    return svc.list_groupes_rem(id_distrib)


@router.get("/{id_distrib}/editions",
            response_model=list[svc.EditionCttItem])
def get_distrib_editions(
    id_distrib: int,
    _u: UserToken = Depends(get_current_user),
):
    return svc.list_editions_ctt(id_distrib)
