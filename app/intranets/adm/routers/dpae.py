"""
Router Fen_DPAE_* (ADM, section Salaries -> Nouvelle DPAE).

- POST /adm/dpae/recherche : recherche dans cvtheque + registre RH
  (transposition Btn Loupe Fen_DPAE_Recherche WinDev)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import dpae_recherche as svc


router = APIRouter(prefix="/dpae", tags=["adm-dpae"])


class DpaeRechercheRequest(BaseModel):
    nom: str = ""
    prenom: str = ""
    gsm: str = ""


@router.post("/recherche")
def post_recherche(
    req: DpaeRechercheRequest,
    _user: UserToken = Depends(get_current_user),
):
    """Btn Loupe Fen_DPAE_Recherche : combine cvtheque + registre RH."""
    return svc.search(req.nom, req.prenom, req.gsm)
