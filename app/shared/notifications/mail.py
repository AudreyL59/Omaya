"""
Envoi d'emails via SMTP.

Transposition des procédures WinDev envoiMailGmailRH(), etc.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import (
    SMTP_RH_HOST,
    SMTP_RH_PORT,
    SMTP_RH_USER,
    SMTP_RH_PASSWORD,
    SMTP_RH_FROM,
)


def envoi_mail_rh(
    sujet: str,
    html: str,
    destinataires: list[str],
    cci: list[str] | None = None,
    expediteur: str = "",
) -> bool:
    """
    Envoie un mail via le SMTP Gmail RH (noreply.gestionrh@gmail.com).

    destinataires : liste d'adresses To
    cci : liste d'adresses Cci (optionnel)
    expediteur : adresse d'expéditeur affichée (par défaut gestion.dpae@omaya.fr)

    Retourne True si envoi OK.
    """
    if not SMTP_RH_PASSWORD:
        raise RuntimeError("SMTP_RH_PASSWORD non configuré dans .env")
    if not destinataires:
        raise ValueError("Aucun destinataire")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = sujet
    msg["From"] = expediteur or SMTP_RH_FROM
    msg["To"] = ", ".join(destinataires)
    if cci:
        msg["Bcc"] = ", ".join(cci)

    msg.attach(MIMEText(html, "html", "utf-8"))

    all_recipients = destinataires + (cci or [])

    try:
        with smtplib.SMTP_SSL(SMTP_RH_HOST, SMTP_RH_PORT, timeout=15) as smtp:
            smtp.login(SMTP_RH_USER, SMTP_RH_PASSWORD)
            smtp.sendmail(msg["From"], all_recipients, msg.as_string())
        return True
    except Exception:
        return False


def verifier_email(adresse: str) -> bool:
    """Validation basique d'une adresse email."""
    if not adresse or "@" not in adresse:
        return False
    local, _, domain = adresse.rpartition("@")
    return bool(local) and "." in domain
