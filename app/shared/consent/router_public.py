"""Router public (sans auth) pour la page de consentement client Call.

Monte sous /public/consent-client. Aucune dependance d'authentification.
Securite : l'id_ticket est un timestamp 8 octets (impossible a deviner
par bruteforce, pattern identique a ConfRdvPage).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.shared.consent.services import consent_client as svc
from app.shared.consent.services.consent_client import (
    PublicConsent, ValidatePayload,
)


router = APIRouter(prefix="/public/consent-client", tags=["public-consent"])


@router.get("", response_model=PublicConsent)
def get_consent(p: str = Query(..., description="TypeTK+IDTK_Liste, ex SFR20220315...")):
    """Detail du ticket + panier + statut de consentement."""
    c = svc.get_consent_public(p)
    if not c:
        raise HTTPException(404, "Ticket introuvable")
    return c


@router.post("/validate")
def post_validate(payload: ValidatePayload,
                   p: str = Query(..., description="TypeTK+IDTK_Liste")):
    """Valide le consentement du client (Opt_Rappel + Opt_Partenaire).

    Retourne {ok, code_valid, deja_valide} - le front bascule sur le
    plan 2 (affichage du CodeValid) si opt_rappel=True.
    """
    res = svc.validate_consent(
        p,
        opt_rappel=payload.opt_rappel,
        opt_oppose_partenaire=payload.opt_oppose_partenaire,
    )
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "validate_failed")
    return res
