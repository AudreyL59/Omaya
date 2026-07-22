"""Endpoints d'authentification mobile (WebRest_Omayapp).

Endpoints du xlsx :
  - VerifIdentifiant       : login (email/pwd -> JWT ou UUID selon le
                              WS WinDev original — TXT a fournir)
  - Auth/RenewToken        : renouvellement du token
  - Auth/ChangerMotDePasse : changement de mot de passe

TODO : porter la logique iso-signature des WS WinDev une fois les
TXT recuperes dans D:\\Claude\\WinDev\\WebServices\\.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

router = APIRouter(tags=["mobile-auth"])


@router.post("/VerifIdentifiant")
def verif_identifiant(payload: dict = Body(...)):
    """Login mobile. Port a faire des que le TXT WinDev est fourni.

    Payload attendu (a confirmer avec le TXT) :
      { "identifiant": "...", "motDePasse": "..." }
    Reponse attendue (a confirmer) :
      { "token": "...", "usersCial": <int>, ... }
    """
    raise HTTPException(501, "Endpoint VerifIdentifiant non encore porte")


@router.post("/Auth/RenewToken")
def renew_token(payload: dict = Body(...)):
    """Renouvellement du token. Port a faire avec le TXT WinDev."""
    raise HTTPException(501, "Endpoint Auth/RenewToken non encore porte")


@router.post("/Auth/ChangerMotDePasse")
def changer_mot_de_passe(payload: dict = Body(...)):
    """Changement mot de passe. Port a faire avec le TXT WinDev."""
    raise HTTPException(501, "Endpoint Auth/ChangerMotDePasse non encore porte")
