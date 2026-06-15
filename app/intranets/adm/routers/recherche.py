"""
Router pour le module Fen_RecherchePOO (recherche multi-cibles ADM).

Endpoint unique : POST /adm/recherche/{mode}
  mode in {client, contrat, salarie, cv}

Body :
  {
    "nom": "...",
    "prenom": "...",
    "tel": "...",
    "mail": "...",
    "id": "...",
    "num_bs": "...",   // mode client (option) + mode contrat (obligatoire)
  }
"""

from __future__ import annotations

import sys
import traceback

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import recherche as svc


router = APIRouter(prefix="/recherche", tags=["adm-recherche"])


VALID_MODES = {"client", "contrat", "salarie", "cv"}


class CriteresPayload(BaseModel):
    nom: str = ""
    prenom: str = ""
    tel: str = ""
    mail: str = ""
    id: str = ""
    num_bs: str = ""


@router.post("/{mode}")
def post_recherche(
    payload: CriteresPayload,
    mode: str = Path(..., description="client / contrat / salarie / cv"),
    user: UserToken = Depends(get_current_user),
):
    """Recherche selon le mode et les criteres. Retourne une liste de
    dicts uniformes {origine, id, att1..att7, att_aff}."""
    mode_l = (mode or "").lower()
    if mode_l not in VALID_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"Mode invalide : {mode}. Attendu : {sorted(VALID_MODES)}",
        )
    try:
        return svc.search(mode_l, payload.model_dump())
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(
            status_code=500, detail=f"{type(e).__name__}: {e}"
        )
