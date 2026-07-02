"""Convention sentinelle 1900-01-01 pour les dates 'vides' cote HFSQL/PG.

Le pont HFSQL->PG (sync_engine.wl) ne peut pas ecrire NULL de facon
fiable sur les colonnes DATE/timestamp : `..NULL = True` est ignore si
la rubrique n'est pas declaree nullable dans l'analyse WinDev, et le
driver PG WinDev peut reserialiser une chaine vide en '0000-01-01'
(refuse par PG car hors limites).

**Convention** : le sync ecrit **1900-01-01** comme date sentinelle
'vide'. Cote applicatif (Python + affichage frontend), on doit :
  - traiter 1900-01-01 comme None/vide
  - ne pas afficher '01/01/1900' dans les UI
  - ne pas la compter dans les calculs (anciennete, filtres BETWEEN,
    etc.)

Ce module fournit :
  - SENTINEL_DATE  : la valeur constante
  - is_sentinel(v) : True si v est la sentinelle
  - clean(v)       : None si sentinelle, sinon v
  - null_if(col)   : fragment SQL pour lecture directe SELECT
                     (equivalent NULLIF(col, DATE '1900-01-01'))
"""

from datetime import date, datetime
from typing import Any

SENTINEL_DATE = date(1900, 1, 1)

# Chaines qu'on veut aussi ignorer (formats WinDev / ISO)
_SENTINEL_STRINGS = {
    "1900-01-01",
    "19000101",
    "1900-01-01 00:00:00",
    "1900-01-01T00:00:00",
    "01/01/1900",
    "0000-00-00",
    "00000000",
}


def is_sentinel(v: Any) -> bool:
    """True si la valeur est la sentinelle 1900-01-01 (date, datetime
    ou chaine formatee)."""
    if v is None:
        return False
    if isinstance(v, datetime):
        return v.date() == SENTINEL_DATE
    if isinstance(v, date):
        return v == SENTINEL_DATE
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return False
        if s in _SENTINEL_STRINGS:
            return True
        # Normalise ISO avec T ou espace : 1900-01-01... = sentinelle
        if s.startswith("1900-01-01"):
            return True
    return False


def clean(v: Any) -> Any:
    """Renvoie None si la valeur est la sentinelle, sinon la valeur
    telle quelle. A utiliser sur toute date lue en base avant sa
    serialisation vers le frontend."""
    return None if is_sentinel(v) else v


def null_if(col: str) -> str:
    """Fragment SQL pour un SELECT : transforme la sentinelle en NULL
    au moment de la lecture. Exemple :
        SELECT null_if('ctt_debut') AS ctt_debut FROM ...
        -> 'NULLIF(ctt_debut, DATE \\'1900-01-01\\') AS ctt_debut'
    Utile quand on veut que la valeur soit directement NULL cote
    Python sans passer par clean()."""
    return f"NULLIF({col}, DATE '1900-01-01')"


def to_iso(v: Any) -> str:
    """Date/datetime/str -> 'YYYY-MM-DD' ou '' (sentinelle 1900 = '')."""
    if v is None or v == "" or is_sentinel(v):
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    s = str(v).strip()
    if not s or s.startswith("0000"):
        return ""
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def to_iso_dt(v: Any) -> str:
    """datetime -> 'YYYY-MM-DD HH:MM:SS' ou '' (sentinelle 1900 = '')."""
    if v is None or v == "" or is_sentinel(v):
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d 00:00:00")
    s = str(v).strip()
    if not s or s.startswith("0000") or s.startswith("1900"):
        return ""
    return s


def to_fr(v: Any) -> str:
    """Date -> 'DD/MM/YYYY' ou '' (sentinelle 1900 = '')."""
    if v is None or v == "" or is_sentinel(v):
        return ""
    if isinstance(v, (date, datetime)):
        return v.strftime("%d/%m/%Y")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
    return ""
