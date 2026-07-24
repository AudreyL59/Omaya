from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

# App
APP_NAME = os.getenv("APP_NAME", "ERP Omaya")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1")

# CORS — liste séparée par virgules dans l'env, fallback = valeurs historiques
_default_cors = ",".join(
    [
        "https://sos.adm.omaya.fr",
        "https://newadm.omaya.fr",
        "https://sos.groupe-exo.omaya.fr",
        "http://localhost:5173",
    ]
)
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", _default_cors).split(",")
    if o.strip()
]

# Chemins fichiers (serveur Windows)
DOCS_BASE_PATH = Path(os.getenv("DOCS_BASE_PATH", r"D:\Profil\Documents\Mes_Docs_OMAYA"))
DOCS_URL = os.getenv("DOCS_URL", "https://interne.omaya.fr/")
REP_BO = DOCS_BASE_PATH / "BO"
REP_RH = DOCS_BASE_PATH / "RH"
REP_DPAE = DOCS_BASE_PATH / "DPAE"

# Extractions de production (fichiers Parquet générés par le worker)
PRODUCTION_EXTRACTS_DIR = Path(
    os.getenv("PRODUCTION_EXTRACTS_DIR", r"D:\Sites\groupeOmaya\production-extracts")
)
# Rétention en jours (purge par le worker au démarrage)
PRODUCTION_EXTRACTS_RETENTION_DAYS = int(
    os.getenv("PRODUCTION_EXTRACTS_RETENTION_DAYS", "90")
)

# FTP
FTP_HOST = os.getenv("FTP_HOST", "192.168.1.202")
FTP_USER = os.getenv("FTP_USER", "OMAYA")
FTP_PASSWORD = os.getenv("FTP_PASSWORD", "")
FTP_PHOTO_DPAE_PATH = os.getenv("FTP_PHOTO_DPAE_PATH", "/OMAYA/PhotoDPAE")
# Dossier des contrats signés (par salarié) sur le FTP
FTP_GESTION_RH_PATH = os.getenv("FTP_GESTION_RH_PATH", "/OMAYA/gestionRH")
# Dossier des PJ de tickets (réservations, etc.) : <base>/<idTicket>/
FTP_DOC_TICKET_PATH = os.getenv("FTP_DOC_TICKET_PATH", "/OMAYA/DocTicket")

# LibreOffice (conversion docx -> PDF, headless)
SOFFICE_BIN = os.getenv(
    "SOFFICE_BIN",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
)
# URLs des images de signature dématérialisée (fallback si mémo vide)
CTTW_SIGN_URL = os.getenv("CTTW_SIGN_URL", "https://rest.omaya.fr/sign")
CTTW_SIGN_URL_FALLBACK = os.getenv(
    "CTTW_SIGN_URL_FALLBACK", "https://sos.rest.omaya.fr/sign"
)

# Base URL des WebService WinDev (WebRest_Omayapp) utilises par les
# ecrans Ticket Call Energie + Fibre (proxy Phase 2, cf.
# docs/tickets_call_screens_analysis.md).
# Bascule progressive vers PG au fur et a mesure (Phase 3).
WEBREST_BASE_URL = os.getenv("WEBREST_BASE_URL", "https://rest.omaya.fr")

# Emails de service
MAIL_SUPPORT = os.getenv("MAIL_SUPPORT", "intranet@omaya.fr")
MAIL_TECH = os.getenv("MAIL_TECH", "a.loudieux@exosphere.fr")
MAIL_TABLETTE = os.getenv("MAIL_TABLETTE", "tablettes@omaya.fr")
MAIL_RESP_RH = os.getenv("MAIL_RESP_RH", "")
MAIL_RH = os.getenv("MAIL_RH", "")
MAIL_DPAE = os.getenv("MAIL_DPAE", "")
MAIL_RESP_BO = os.getenv("MAIL_RESP_BO", "")
MAIL_BO = os.getenv("MAIL_BO", "")
MAIL_RESP_JURISTE = os.getenv("MAIL_RESP_JURISTE", "")
MAIL_JURISTE_1 = os.getenv("MAIL_JURISTE_1", "")
MAIL_JURISTE_2 = os.getenv("MAIL_JURISTE_2", "")

# SMS API (smsmode.com)
SMS_API_KEY = os.getenv("SMS_API_KEY", "")
SMS_API_URL = os.getenv("SMS_API_URL", "api-old.smsmode.com")

# SMTP Gmail RH (envoi par defaut, transposition WinDev "envoiMailGmailRH")
SMTP_RH_HOST = os.getenv("SMTP_RH_HOST", "smtp.gmail.com")
SMTP_RH_PORT = int(os.getenv("SMTP_RH_PORT", "465"))
SMTP_RH_USER = os.getenv("SMTP_RH_USER", "noreply.gestionrh@gmail.com")
SMTP_RH_PASSWORD = os.getenv("SMTP_RH_PASSWORD", "")
SMTP_RH_FROM = os.getenv("SMTP_RH_FROM", "gestion.dpae@omaya.fr")

# SMTP OVH FPE (utilise quand l'expediteur = fpe@exosphere.fr, cf. Fen_EnvoieEmail WinDev)
SMTP_FPE_HOST = os.getenv("SMTP_FPE_HOST", "ssl0.ovh.net")
SMTP_FPE_PORT = int(os.getenv("SMTP_FPE_PORT", "465"))
SMTP_FPE_USER = os.getenv("SMTP_FPE_USER", "fpe@exosphere.fr")
SMTP_FPE_PASSWORD = os.getenv("SMTP_FPE_PASSWORD", "")
SMTP_FPE_FROM = os.getenv("SMTP_FPE_FROM", "fpe@exosphere.fr")

# SMTP OVH salaire@omaya.fr (Fen_FicheSalaires - envoi FDP)
SMTP_SALAIRE_HOST = os.getenv("SMTP_SALAIRE_HOST", "ssl0.ovh.net")
SMTP_SALAIRE_PORT = int(os.getenv("SMTP_SALAIRE_PORT", "465"))
SMTP_SALAIRE_USER = os.getenv("SMTP_SALAIRE_USER", "salaire@omaya.fr")
SMTP_SALAIRE_PASSWORD = os.getenv("SMTP_SALAIRE_PASSWORD", "")

# Cle pour derivation MDP salarie (cf. WinDev :
# bufCle = HashChaine(HA_MD5_128, HASH_SECRET_KEY) + DecrypteStandard AES-128)
HASH_SECRET_KEY = os.getenv("HASH_SECRET_KEY", "")

# HMAC secret pour signer les liens publics de cooptation
# (page /PageExterne/coopt?c=<id>&s=<hmac_sha256(id, secret)>)
COOPT_HMAC_SECRET = os.getenv("COOPT_HMAC_SECRET", "")

# Google Maps
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
GOOGLE_MAPS_SECRET = os.getenv("GOOGLE_MAPS_SECRET", "")

# Hash
HASH_SECRET_KEY = os.getenv("HASH_SECRET_KEY", "")

# HFSQL Bridge
HFSQL_BRIDGE_PATH = os.getenv("HFSQL_BRIDGE_PATH", r"D:\Claude\Projet Omaya\bridge\Dll_ODBC.exe")
HFSQL_HOST = os.getenv("HFSQL_HOST", "localhost")
HFSQL_PORT = os.getenv("HFSQL_PORT", "4901")
HFSQL_USER = os.getenv("HFSQL_USER", "admin")
HFSQL_PASSWORD = os.getenv("HFSQL_PASSWORD", "")
HFSQL_DB_PASSWORD = os.getenv("HFSQL_DB_PASSWORD", "")
