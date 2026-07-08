"""
Router Fen_ScoolPlanning.
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.scool_planning import (
    PlanningParams, PlanningResult,
)
from app.intranets.adm.services import scool_planning as svc

router = APIRouter(prefix="/scool", tags=["adm-scool-planning"])


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


@router.get("/planning", response_model=PlanningResult)
def get_planning(
    date_deb: str = Query(..., description="YYYY-MM-DD"),
    date_fin: str = Query(..., description="YYYY-MM-DD"),
    avec_sortis: bool = Query(False),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    return svc.build_planning(PlanningParams(
        date_deb=date_deb, date_fin=date_fin, avec_sortis=avec_sortis,
    ))
