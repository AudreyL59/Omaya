"""Router public (sans auth) pour la confirmation de RDV par le candidat.

Monte sur /public/rdv. Aucune dependance d'authentification.
Securite : l'id_rdv est un timestamp sur 8 octets (impossible a deviner
par bruteforce).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.shared.recrutement.services import public_rdv as svc
from app.shared.recrutement.services.public_rdv import (
    ConfirmPayload, PublicRdvDetail,
)


router = APIRouter(prefix="/public/rdv", tags=["public-rdv"])


@router.get("/{id_rdv}", response_model=PublicRdvDetail)
def get_rdv(id_rdv: int):
    f = svc.get_rdv_public(id_rdv)
    if not f:
        raise HTTPException(404, "RDV introuvable")
    return f


@router.post("/{id_rdv}/confirm")
def post_confirm(id_rdv: int, payload: ConfirmPayload):
    res = svc.confirm_rdv(id_rdv)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "confirm_failed")
    return res
