"""
Router Vendeur - Endpoints Ticket Call communs aux 2 ecrans
(Energie + Fibre) : recherche ville par CP + upload de fichier.

- /ticket-call/villes/{cp} : deja porte en PG cote services/communes.py
  (pas de proxy WS - Phase 3 deja faite pour cet endpoint).
- /ticket-call/upload-fichier : proxy multipart vers /RecepFichier
  (WinDev). Phase 2.

Droit d'acces : union TkCALL + BS_SFR (chaque ecran a son propre droit
mais les endpoints communs sont accessibles a l'un ou l'autre).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.vendeur.services import communes
from app.intranets.vendeur.services.ws_client import (
    WSError, post_multipart_windev,
)


router = APIRouter(
    prefix="/ticket-call",
    tags=["vendeur-ticket-call-commun"],
)


def _require_call(user: UserToken) -> None:
    droits = user.droits or []
    if "TkCALL" not in droits and "BS_SFR" not in droits:
        raise HTTPException(403, "Droit manquant : TkCALL ou BS_SFR")


@router.get("/villes/{cp}")
def villes_by_cp(
    cp: str,
    user: UserToken = Depends(get_current_user),
):
    """GET /ticket-call/villes/{cp}
    -> Liste des villes matchant le CP (deja porte en PG).
    Retour : [{id, nom_ville, cp}]."""
    _require_call(user)
    return communes.rechercher_par_cp(cp)


@router.post("/upload-fichier")
async def upload_fichier(
    file: UploadFile = File(...),
    file_name: str | None = Form(None),
    user: UserToken = Depends(get_current_user),
):
    """POST /ticket-call/upload-fichier
    Recoit un fichier multipart et le reforward vers WinDev /RecepFichier
    avec le boundary specifique (----WinDevBoundary{ms}).

    - `file` : fichier binaire.
    - `file_name` (optionnel) : nom cible cote serveur DocOmaya
      (ex: '{IDTicket}_PieceIdentite.pdf'). Si absent, on prend le
      filename original.
    """
    _require_call(user)
    data = await file.read()
    fn = file_name or file.filename or "upload.bin"
    ct = file.content_type or "application/octet-stream"
    try:
        return post_multipart_windev("/RecepFichier", fn, data, content_type=ct)
    except WSError as e:
        raise HTTPException(502, str(e))
