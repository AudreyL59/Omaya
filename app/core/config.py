from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

# App
APP_NAME = os.getenv("APP_NAME", "ERP Omaya")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1")

# CORS
CORS_ORIGINS = [
    "https://sos.adm.omaya.fr",
    "https://newadm.omaya.fr",
    "http://localhost:5173",
]

# Chemins fichiers (serveur Windows)
DOCS_BASE_PATH = Path(os.getenv("DOCS_BASE_PATH", r"D:\Profil\Documents\Mes_Docs_OMAYA"))
DOCS_URL = os.getenv("DOCS_URL", "https://interne.omaya.fr/")
REP_BO = DOCS_BASE_PATH / "BO"
REP_RH = DOCS_BASE_PATH / "RH"
REP_DPAE = DOCS_BASE_PATH / "DPAE"

# FTP
FTP_HOST = os.getenv("FTP_HOST", "192.168.1.202")
FTP_USER = os.getenv("FTP_USER", "OMAYA")
FTP_PASSWORD = os.getenv("FTP_PASSWORD", "")

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

# SMS API
SMS_API_KEY = os.getenv("SMS_API_KEY", "")
SMS_API_URL = os.getenv("SMS_API_URL", "api-new.smsmode.com")

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
