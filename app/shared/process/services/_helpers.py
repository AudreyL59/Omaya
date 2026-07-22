"""Helpers communs au module Process : profil user + regles de visibilite."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection

logger = logging.getLogger(__name__)


# Rang hierarchique de la filiere FDV. Les autres profils (STAFF/CALL/
# CALLRH) sont hors de ce dict (pas de relation d'ordre).
FDV_RANKS: dict[str, int] = {
    "FDV VRP": 1,
    "FDV MAN": 2,
    "FDV DA": 3,
    "FDV DR": 4,
}

PROFILS_KNOWN = ("STAFF", "FDV VRP", "FDV MAN", "FDV DA", "FDV DR", "CALL", "CALLRH")


def _new_id_wd() -> int:
    """idEntierDateHeureSys() WinDev : entier 8 octets YYYYMMDDHHMMSSMMM."""
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


def _str_id(v: Any) -> str:
    """IDs 8 octets exposes en string (JS Number depasse 2^53)."""
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _capitalise(v: str) -> str:
    return v[:1].upper() + v[1:].lower() if v else ""


def _iso_datetime(dt: Any) -> str:
    if not dt:
        return ""
    if isinstance(dt, str):
        return dt
    try:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(dt)


def profil_user(id_salarie: int) -> str:
    """Retourne le code profil du salarie (categorie de son type de poste)
    ou "" si non trouve / pas d'embauche active.
    """
    if not id_salarie:
        return ""
    rh = get_pg_connection("rh")
    try:
        row = rh.query_one(
            """SELECT tp.categorie
                 FROM rh.pgt_salarie_embauche se
                 JOIN rh.pgt_type_poste tp
                        ON tp.id_type_poste = se.id_type_poste
                WHERE se.id_salarie = ?
                  AND COALESCE(se.en_activite, FALSE) = TRUE
                LIMIT 1""",
            (int(id_salarie),),
        )
    except Exception:
        logger.exception("profil_user id=%s", id_salarie)
        return ""
    return (row or {}).get("categorie") or ""


def societe_user(id_salarie: int) -> int:
    """Retourne l'id_ste du salarie (via salarie_embauche actif) ou 0."""
    if not id_salarie:
        return 0
    rh = get_pg_connection("rh")
    try:
        row = rh.query_one(
            """SELECT id_ste
                 FROM rh.pgt_salarie_embauche
                WHERE id_salarie = ?
                  AND COALESCE(en_activite, FALSE) = TRUE
                LIMIT 1""",
            (int(id_salarie),),
        )
    except Exception:
        logger.exception("societe_user id=%s", id_salarie)
        return 0
    return int((row or {}).get("id_ste") or 0)


def profil_visible(user_profil: str, target_profil: str) -> bool:
    """Regle de visibilite (niveau mini hierarchique).

    - STAFF voit tout.
    - Un process cible STAFF n'est visible qu'a STAFF.
    - Meme filiere FDV : rang user >= rang target
      (FDV VRP < FDV MAN < FDV DA < FDV DR).
    - Filiere CALL / CALLRH : match exact (pas de hierarchie).
    - Filieres non croisees (FDV ne voit pas CALL et vice-versa).
    """
    if not target_profil:
        return False
    if user_profil == "STAFF":
        return True
    if target_profil == "STAFF":
        return False
    if user_profil in FDV_RANKS and target_profil in FDV_RANKS:
        return FDV_RANKS[user_profil] >= FDV_RANKS[target_profil]
    if user_profil in ("CALL", "CALLRH"):
        return user_profil == target_profil
    return False


def profils_visibles_pour(user_profil: str) -> set[str]:
    """Ensemble des target_profil qu'un user donne peut voir.

    Utile pour construire une clause WHERE type_profil IN (...) plutot
    que d'evaluer profil_visible ligne par ligne cote Python.
    """
    if user_profil == "STAFF":
        return set(PROFILS_KNOWN)
    out: set[str] = set()
    for p in PROFILS_KNOWN:
        if profil_visible(user_profil, p):
            out.add(p)
    return out


def nom_salarie(id_salarie: int) -> str:
    """Retourne 'NOM Prenom' du salarie (prenom capitalise), '' si absent."""
    if not id_salarie:
        return ""
    rh = get_pg_connection("rh")
    try:
        row = rh.query_one(
            "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
            (int(id_salarie),),
        )
    except Exception:
        return ""
    if not row:
        return ""
    return f"{row.get('nom') or ''} {_capitalise(row.get('prenom') or '')}".strip()
