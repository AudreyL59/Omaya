"""Router Fen_FacturesSuivi (ADM > Suivi des factures)."""

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import factures as svc

router = APIRouter(prefix="/factures", tags=["adm-factures"])


@router.get("/operateurs", response_model=list[svc.OperateurItem])
def get_operateurs(_u: UserToken = Depends(get_current_user)):
    return svc.list_operateurs_staff()


@router.get("/enseignes", response_model=list[svc.EnseigneItem])
def get_enseignes(_u: UserToken = Depends(get_current_user)):
    return svc.list_enseignes()


@router.get("/societes", response_model=list[svc.SocieteItem])
def get_societes(_u: UserToken = Depends(get_current_user)):
    return svc.list_societes()


@router.post("/search", response_model=list[svc.FactureLigne])
def post_search(
    filters: svc.FactureSearchFilters,
    _u: UserToken = Depends(get_current_user),
):
    return svc.search_factures(filters)
