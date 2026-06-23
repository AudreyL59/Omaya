"""Router shared Recrutement / Recherche CV.

Pattern factory : chaque intranet (ADM, Vendeur, Call RH) inclut son
propre router via :
    router.include_router(get_recherche_cv_router("adm"))

`intranet_key` permet :
- de filtrer automatiquement la liste (ex: Vendeur ne voit que ses CV)
- de logger les actions cote audit
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.shared.recrutement.schemas.recherche_cv import (
    CommuneItem, ComboItem, CVRow, SearchCVFiltres,
)
from app.shared.recrutement.services import recherche_cv as svc


def get_recherche_cv_router(intranet_key: str) -> APIRouter:
    """Construit le router /recrutement/cv pour un intranet donne.

    intranet_key : "adm", "vendeur", "call_rh"
    """
    router = APIRouter(prefix="/recrutement/cv", tags=["recrutement-cv"])

    @router.get("/sources", response_model=list[ComboItem])
    def get_sources(_user: UserToken = Depends(get_current_user)):
        return svc.list_sources()

    @router.get("/statuts", response_model=list[ComboItem])
    def get_statuts(_user: UserToken = Depends(get_current_user)):
        return svc.list_statuts()

    @router.get("/postes", response_model=list[ComboItem])
    def get_postes(_user: UserToken = Depends(get_current_user)):
        return svc.list_postes()

    @router.get("/annonceurs", response_model=list[ComboItem])
    def get_annonceurs(_user: UserToken = Depends(get_current_user)):
        return svc.list_annonceurs()

    @router.get("/societes", response_model=list[ComboItem])
    def get_societes(_user: UserToken = Depends(get_current_user)):
        return svc.list_societes()

    @router.get("/communes", response_model=list[CommuneItem])
    def get_communes(
        q: str = Query(..., min_length=2),
        limit: int = Query(50, ge=1, le=200),
        _user: UserToken = Depends(get_current_user),
    ):
        return svc.search_communes(q, limit)

    @router.post("/search", response_model=list[CVRow])
    def post_search(
        filtres: SearchCVFiltres,
        user: UserToken = Depends(get_current_user),
    ):
        # Filtre auto Vendeur : force id_cvsource=1 + id_elem_source=user
        if intranet_key == "vendeur":
            filtres.id_cvsource = "1"
            filtres.id_elem_source = str(user.id_salarie)
        return svc.search_cv(filtres)

    return router
