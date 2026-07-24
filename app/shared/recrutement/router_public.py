"""Router public (sans auth) - RDV entretien + saisie cooptation.

Monte sous /public/*. Aucune dependance d'authentification.
Securite :
  - /public/rdv/{id_rdv} : l'id_rdv est un timestamp sur 8 octets
    (impossible a deviner par bruteforce).
  - /public/coopt/*      : verification signature HMAC_SHA256 sur
    l'id du coopteur (COOPT_HMAC_SECRET).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.shared.recrutement.services import public_coopt as coopt_svc
from app.shared.recrutement.services import public_rdv as svc
from app.shared.recrutement.services.public_coopt import (
    PublicCoopteurInfo, PublicVilleItem, verify_coopt_signature,
)
from app.shared.recrutement.services.public_rdv import (
    ConfirmPayload, PublicRdvDetail,
)


router = APIRouter(prefix="/public", tags=["public"])


# ---------------------------------------------------------------------------
#  RDV entretien
# ---------------------------------------------------------------------------

@router.get("/rdv/{id_rdv}", response_model=PublicRdvDetail)
def get_rdv(id_rdv: int):
    f = svc.get_rdv_public(id_rdv)
    if not f:
        raise HTTPException(404, "RDV introuvable")
    return f


@router.post("/rdv/{id_rdv}/confirm")
def post_confirm(id_rdv: int, payload: ConfirmPayload):
    res = svc.confirm_rdv(id_rdv)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "confirm_failed")
    return res


# ---------------------------------------------------------------------------
#  Cooptation publique (lien partage par le coopteur)
# ---------------------------------------------------------------------------

def _check_signature(c: int, s: str) -> None:
    """Verifie signature ou 401. c=id coopteur, s=hmac."""
    if not verify_coopt_signature(c, s):
        raise HTTPException(401, "Signature invalide")


@router.get("/coopt/coopteur", response_model=PublicCoopteurInfo)
def get_coopteur(c: int = Query(..., description="ID du coopteur"),
                  s: str = Query(..., description="Signature HMAC hexa")):
    """Retourne {id, nom, prenom} du coopteur si la signature HMAC
    matche. 401 si signature invalide, 404 si coopteur inconnu."""
    _check_signature(c, s)
    info = coopt_svc.get_coopteur_info(c)
    if not info:
        raise HTTPException(404, "Coopteur introuvable")
    return info


@router.get("/coopt/villes/{cp}", response_model=list[PublicVilleItem])
def get_villes(cp: str,
               c: int = Query(..., description="ID du coopteur"),
               s: str = Query(..., description="Signature HMAC hexa")):
    """Autocomplete villes par CP (endpoint protege par la meme
    signature que le coopteur)."""
    _check_signature(c, s)
    return coopt_svc.liste_villes_by_cp(cp)
