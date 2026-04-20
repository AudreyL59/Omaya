"""
Envoi SMS via smsmode.com.

Transposition de la procédure WinDev envoiSMS().
"""

import unicodedata
import urllib.parse
import urllib.request

from app.core.config import SMS_API_KEY, SMS_API_URL


def _strip_accents(text: str) -> str:
    """Retire les accents (équivalent ChaîneFormate ccSansAccent)."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def envoi_sms(texte: str, gsm: str, date_envoi: str = "", emetteur: str = "") -> str:
    """
    Envoie un SMS via smsmode.com.

    Retourne un message de résultat (succès ou erreur).
    """
    if not SMS_API_KEY:
        return "Clé API SMS non configurée"
    if not gsm:
        return "Numéro de GSM vide"

    texte = _strip_accents(texte).replace("\t", "")

    params = {
        "accessToken": SMS_API_KEY,
        "message": texte,
        "numero": gsm,
    }

    nb_c = len(texte)
    if 160 < nb_c <= 306:
        params["nbr_msg"] = "2"
    elif nb_c > 306:
        params["nbr_msg"] = "3"

    if date_envoi:
        params["date_envoi"] = date_envoi
    if emetteur:
        params["emetteur"] = emetteur

    url = f"https://{SMS_API_URL}/http/1.6/sendSMS.do?" + urllib.parse.urlencode(params)

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace").strip()
        code = body.split("|", 1)[0].strip()
        if code == "0":
            return "SMS envoyé avec succès"
        return f"Erreur SMS (code {code}) : {body}"
    except Exception as e:
        return f"Impossible d'envoyer le SMS : {e}"
