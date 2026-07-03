"""
Envoi d'emails via SMTP.

Transposition des procédures WinDev envoiMailGmailRH(), etc.
"""

import logging
import smtplib
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from app.core.config import (
    SMTP_RH_HOST,
    SMTP_RH_PORT,
    SMTP_RH_USER,
    SMTP_RH_PASSWORD,
    SMTP_RH_FROM,
    SMTP_FPE_HOST,
    SMTP_FPE_PORT,
    SMTP_FPE_USER,
    SMTP_FPE_PASSWORD,
    SMTP_FPE_FROM,
)

logger = logging.getLogger(__name__)

# CCI systematique sur tous les envois (cf. WinDev Fen_EnvoieEmail :
# "Ajoute(MonMessage..Cci, 'intranet@omaya.fr')")
CCI_AUTO = "intranet@omaya.fr"

# Limites de taille pieces jointes (protection service SMTP)
MAX_ATTACHMENT_SIZE_MB = 15
MAX_TOTAL_ATTACHMENTS_SIZE_MB = 25
_MB = 1024 * 1024


class MailAttachmentTooLargeError(ValueError):
    """Une piece jointe (ou le total) depasse la limite autorisee."""


def _check_attachments_size(
    attachments: list[tuple[str, bytes]] | None,
) -> None:
    """Verifie les limites de taille sur les pieces jointes."""
    if not attachments:
        return
    total = 0
    for fname, content in attachments:
        size = len(content or b"")
        if size > MAX_ATTACHMENT_SIZE_MB * _MB:
            raise MailAttachmentTooLargeError(
                f"Piece jointe '{fname}' trop lourde : "
                f"{size / _MB:.1f} MB (max {MAX_ATTACHMENT_SIZE_MB} MB)"
            )
        total += size
    if total > MAX_TOTAL_ATTACHMENTS_SIZE_MB * _MB:
        raise MailAttachmentTooLargeError(
            f"Total pieces jointes trop lourd : "
            f"{total / _MB:.1f} MB "
            f"(max {MAX_TOTAL_ATTACHMENTS_SIZE_MB} MB)"
        )


def envoi_mail(
    sujet: str,
    html: str,
    destinataires: list[str],
    cc: list[str] | None = None,
    cci: list[str] | None = None,
    expediteur: str = "",
    attachments: list[tuple[str, bytes]] | None = None,
) -> bool:
    """
    Envoi generique. Si expediteur == 'fpe@exosphere.fr' -> SMTP OVH FPE,
    sinon -> SMTP Gmail RH (defaut). CCI 'intranet@omaya.fr' ajoute
    systematiquement (transposition WinDev Fen_EnvoieEmail).
    """
    if not destinataires:
        raise ValueError("Aucun destinataire")

    _check_attachments_size(attachments)

    use_fpe = (expediteur or "").strip().lower() == "fpe@exosphere.fr"
    if use_fpe:
        host, port, user, password = SMTP_FPE_HOST, SMTP_FPE_PORT, SMTP_FPE_USER, SMTP_FPE_PASSWORD
        from_addr = SMTP_FPE_FROM
    else:
        host, port, user, password = SMTP_RH_HOST, SMTP_RH_PORT, SMTP_RH_USER, SMTP_RH_PASSWORD
        from_addr = SMTP_RH_FROM

    if not password:
        raise RuntimeError(f"Mot de passe SMTP non configure ({'FPE' if use_fpe else 'RH'})")

    cci_full = list(cci or [])
    if CCI_AUTO not in cci_full:
        cci_full.append(CCI_AUTO)

    # Si on a un expediteur affiche different de la boite SMTP, l'utiliser
    # comme From (cf. WinDev MonMessage..Expediteur)
    display_from = expediteur if expediteur and expediteur != from_addr else from_addr

    if attachments:
        msg = MIMEMultipart("mixed")
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(html, "html", "utf-8"))
        msg.attach(alt)
        for fname, content in attachments:
            part = MIMEApplication(content, Name=fname)
            part["Content-Disposition"] = f'attachment; filename="{fname}"'
            msg.attach(part)
    else:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(html, "html", "utf-8"))

    # cf. WinDev ChaineVersUTF8(Mail_Objet) : encodage RFC 2047 pour
    # que les caracteres non-ASCII s'affichent correctement sous
    # Outlook et clients stricts.
    msg["Subject"] = Header(sujet, "utf-8")
    msg["From"] = formataddr(("", display_from))
    msg["To"] = ", ".join(destinataires)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if cci_full:
        msg["Bcc"] = ", ".join(cci_full)

    all_recipients = destinataires + (cc or []) + cci_full

    try:
        with smtplib.SMTP_SSL(host, port, timeout=15) as smtp:
            smtp.login(user, password)
            smtp.sendmail(from_addr, all_recipients, msg.as_string())
        logger.info(
            "Mail envoye [%s -> %d dest (+%d cc, +%d cci)] : %s",
            "FPE" if use_fpe else "RH",
            len(destinataires), len(cc or []), len(cci_full),
            sujet[:80],
        )
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error("SMTP auth KO (%s) : %s",
                     "FPE" if use_fpe else "RH", e)
        return False
    except smtplib.SMTPException as e:
        logger.error("SMTP erreur (%s) : %s",
                     "FPE" if use_fpe else "RH", e)
        return False
    except (TimeoutError, OSError) as e:
        logger.error("SMTP reseau/timeout (%s) : %s",
                     "FPE" if use_fpe else "RH", e)
        return False
    except Exception:
        logger.exception("SMTP erreur inattendue (%s)",
                         "FPE" if use_fpe else "RH")
        return False


def envoi_mail_rh(
    sujet: str,
    html: str,
    destinataires: list[str],
    cci: list[str] | None = None,
    expediteur: str = "",
    attachments: list[tuple[str, bytes]] | None = None,
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

    _check_attachments_size(attachments)

    if attachments:
        msg = MIMEMultipart("mixed")
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(html, "html", "utf-8"))
        msg.attach(alt)
        for fname, content in attachments:
            part = MIMEApplication(content, Name=fname)
            part["Content-Disposition"] = f'attachment; filename="{fname}"'
            msg.attach(part)
    else:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(html, "html", "utf-8"))
    # cf. WinDev ChaineVersUTF8(Mail_Objet) : encodage RFC 2047
    msg["Subject"] = Header(sujet, "utf-8")
    msg["From"] = expediteur or SMTP_RH_FROM
    msg["To"] = ", ".join(destinataires)
    if cci:
        msg["Bcc"] = ", ".join(cci)

    all_recipients = destinataires + (cci or [])

    try:
        with smtplib.SMTP_SSL(SMTP_RH_HOST, SMTP_RH_PORT, timeout=15) as smtp:
            smtp.login(SMTP_RH_USER, SMTP_RH_PASSWORD)
            smtp.sendmail(msg["From"], all_recipients, msg.as_string())
        logger.info(
            "Mail RH envoye [-> %d dest, %d cci] : %s",
            len(destinataires), len(cci or []), sujet[:80],
        )
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error("SMTP RH auth KO : %s", e)
        return False
    except smtplib.SMTPException as e:
        logger.error("SMTP RH erreur : %s", e)
        return False
    except (TimeoutError, OSError) as e:
        logger.error("SMTP RH reseau/timeout : %s", e)
        return False
    except Exception:
        logger.exception("SMTP RH erreur inattendue")
        return False


def verifier_email(adresse: str) -> bool:
    """Validation basique d'une adresse email."""
    if not adresse or "@" not in adresse:
        return False
    local, _, domain = adresse.rpartition("@")
    return bool(local) and "." in domain
