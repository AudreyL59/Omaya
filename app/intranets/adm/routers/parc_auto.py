"""
Router Fen_TdbUlease (ADM Ulease -> Suivi du Parc Auto).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import parc_auto as svc


router = APIRouter(prefix="/parc-auto", tags=["adm-parc-auto"])


@router.get("/vehicules")
def get_vehicules(_user: UserToken = Depends(get_current_user)):
    """Tableau de bord : tous les vehicules en circulation + alertes."""
    return svc.list_vehicules_actifs()
