"""
Router shared : envoi d'emails depuis le frontend (Fen_EnvoieEmail WinDev).

Endpoint POST /api/shared/email/send
  Body JSON : {
    to: list[str],
    cc?: list[str],
    cci?: list[str],
    sujet: str,
    html: str,
    expediteur?: str,                   # 'fpe@exosphere.fr' -> SMTP FPE, sinon SMTP RH
    attachments?: list[{name: str, content_b64: str}]
  }

Auth : utilisateur connecte (Bearer token, n'importe quel intranet).
"""

import base64
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.shared.notifications.mail import envoi_mail

router = APIRouter(prefix="/api/shared/email", tags=["shared-email"])


class AttachmentPayload(BaseModel):
    name: str
    content_b64: str = Field(..., description="Contenu binaire encode en base64")


class SendEmailPayload(BaseModel):
    to: list[str] = Field(default_factory=list)
    cc: list[str] = Field(default_factory=list)
    cci: list[str] = Field(default_factory=list)
    sujet: str = ""
    html: str = ""
    expediteur: Optional[str] = None
    attachments: list[AttachmentPayload] = Field(default_factory=list)


class SendEmailResponse(BaseModel):
    ok: bool
    sent_to: list[str] = Field(default_factory=list)


@router.post("/send", response_model=SendEmailResponse)
def send_email(
    payload: SendEmailPayload,
    user: UserToken = Depends(get_current_user),
):
    if not payload.to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun destinataire (champ 'to' vide).",
        )

    # Decode des pieces jointes (base64 -> bytes)
    attachments: list[tuple[str, bytes]] = []
    for att in payload.attachments:
        try:
            data = base64.b64decode(att.content_b64)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PJ '{att.name}' : contenu base64 invalide ({exc})",
            )
        attachments.append((att.name, data))

    # Expediteur par defaut = email du user connecte (cf. WinDev usersLogin)
    expe = (payload.expediteur or user.email or "").strip()

    try:
        ok = envoi_mail(
            sujet=payload.sujet,
            html=payload.html,
            destinataires=payload.to,
            cc=payload.cc or None,
            cci=payload.cci or None,
            expediteur=expe,
            attachments=attachments or None,
        )
    except RuntimeError as exc:
        # Config SMTP manquante
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if not ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="L'envoi du mail a echoue (SMTP).",
        )

    return SendEmailResponse(ok=True, sent_to=payload.to)
