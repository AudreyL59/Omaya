"""
Helpers communs SDTC (Fen_SDTC WinDev).

Centralise les petites procedures globales reutilisees par les autres
modules du package sdtc :
  - _str / _int / _num / _iso : conversions defensives
  - _capitalize : "robert" -> "Robert"
  - _fr_date : datetime -> "DD/MM/YYYY"
  - _esc : echappement HTML basique
  - normalize_nom_produit : extrait avant '(' et regroupe HACHETTE
  - donne_fam_prod_sfr : transposition DonneFamProdSFR WinDev
  - new_id : equivalent idEntierDateHeureSys (YYYYMMDDHHMMSSmmm)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


# Sigles HACHETTE - cf. WinDev : TELE 7 JOUR / ELLE / PARIS MATCH -> HACHETTE
_PRESS_NAMES = {"TELE 7 JOUR", "ELLE", "PARIS MATCH"}


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _num(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _iso(v: Any) -> str:
    """Date / datetime -> ISO 'YYYY-MM-DD'. Vide si None."""
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _capitalize(s: str) -> str:
    if not s:
        return ""
    return s[0].upper() + s[1:].lower()


def _fr_date(v: Any) -> str:
    """datetime/date/string -> 'DD/MM/YYYY' (maskDateSysteme WinDev)."""
    if v is None or v == "":
        return ""
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
    if len(s) >= 8 and s[:8].isdigit():
        return f"{s[6:8]}/{s[4:6]}/{s[0:4]}"
    return s


def _yyyymm(v: Any) -> str:
    """Date / datetime / 'YYYYMMDD' -> 'YYYY-MM' (mois de paiement)."""
    if v is None or v == "":
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m")
    s = str(v)
    if len(s) >= 7 and s[4] == "-":
        return s[:7]
    if len(s) >= 6 and s.isdigit():
        return f"{s[0:4]}-{s[4:6]}"
    return ""


def _esc(v: Any) -> str:
    """Echappement HTML basique pour le bloc InfoSalarie."""
    s = _str(v)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _winrgb_to_hex(r: Any, g: Any, b: Any) -> str:
    """RVB(R,V,B) WinDev -> '#RRGGBB'."""
    R, G, B = _int(r), _int(g), _int(b)
    return f"#{max(0, min(255, R)):02X}{max(0, min(255, G)):02X}{max(0, min(255, B)):02X}"


def normalize_nom_produit(lib_produit: str) -> str:
    """Extrait avant '(' et regroupe la presse Hachette.

    Cf. WinDev btn 'Valider la selection' :
      nomProd = ExtraitChaine(Lib_Produit, 1, "(")
      si nomProd in {"TELE 7 JOUR","ELLE","PARIS MATCH"}: nomProd = "HACHETTE"
    """
    nom = (lib_produit or "").split("(", 1)[0].strip()
    if nom.upper() in _PRESS_NAMES:
        return "HACHETTE"
    return nom


def normalize_nom_produit_recap(lib_produit: str) -> str:
    """Variante du recap : extrait avant '(' ET avant '+' (box SFR)."""
    nom = (lib_produit or "").split("(", 1)[0].split("+", 1)[0].strip()
    if nom.upper() in _PRESS_NAMES:
        return "HACHETTE"
    return nom


def donne_fam_prod_sfr(famille: str, type_vente: Any) -> str:
    """Transposition DonneFamProdSFR(Fam, TypeVente) WinDev.

    Retourne 'FIB CQ' / 'FIB MIG' / 'MOB CQ' / 'MOB MIG' etc.
      FamSFR = Gauche(Fam, 3) + " " + ("CQ" si TypeVente in {1,2} sinon "MIG")
    """
    fam = (famille or "")[:3]
    tv = _int(type_vente)
    suffix = "CQ" if tv in (1, 2) else "MIG"
    return f"{fam} {suffix}".strip()


def new_id() -> int:
    """Equivalent idEntierDateHeureSys WinDev : YYYYMMDDHHMMSSmmm en bigint."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")
