"""Dependencies FastAPI pour l'authentification mobile.

Un seul header `Authorization: Bearer <token>` qui accepte les 2
formats :
  - JWT (retourne par /VerifIdentifiant dans access_token)
  - UUID256 = 64 hex chars (retourne par /Auth/RenewToken dans sToken,
    stocke dans divers.pgt_uuid_connexion pour matching)

Sans header ou token invalide -> HTTP 401.
"""

from __future__ import annotations

import logging
import re

from fastapi import Header, HTTPException

from app.core.auth.security import decode_access_token
from app.core.database.pg import get_pg_connection

logger = logging.getLogger(__name__)

# UUID256 = 64 caracteres hex (voir /Auth/RenewToken -> secrets.token_hex(32))
_UUID256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _try_jwt(token: str) -> int:
    """Essaie de decoder un JWT ; retourne id_salarie ou 0."""
    try:
        payload = decode_access_token(token)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0
    sub = payload.get("sub")
    try:
        return int(sub) if sub else 0
    except (TypeError, ValueError):
        return 0


def _try_uuid(token: str) -> int:
    """Essaie de matcher un UUID256 dans pgt_uuid_connexion ;
    retourne id_salarie ou 0."""
    if not _UUID256_RE.match(token or ""):
        return 0
    db = get_pg_connection("divers")
    try:
        row = db.query_one(
            """SELECT id_salarie FROM divers.pgt_uuid_connexion
                WHERE id_uuid_connexion = ? LIMIT 1""",
            (token,),
        )
    except Exception:
        logger.exception("_try_uuid: query")
        return 0
    if not row:
        return 0
    try:
        return int(row.get("id_salarie") or 0)
    except (TypeError, ValueError):
        return 0


def mobile_auth(authorization: str | None = Header(default=None)) -> int:
    """Dependency qui retourne l'id_salarie authentifie.

    Header attendu : `Authorization: Bearer <token>`
    Token = JWT OU UUID256 (64 hex chars).
    Rejette avec 401 si absent ou invalide.
    """
    if not authorization:
        raise HTTPException(401, "Authorization header manquant")
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(401, "Authorization doit etre 'Bearer <token>'")
    token = parts[1].strip()
    if not token:
        raise HTTPException(401, "Token vide")

    # 1. Tenter JWT
    id_sal = _try_jwt(token)
    if id_sal:
        return id_sal
    # 2. Fallback UUID
    id_sal = _try_uuid(token)
    if id_sal:
        return id_sal
    raise HTTPException(401, "Token invalide (ni JWT valide, ni UUID connu)")


def mobile_auth_optional(
    authorization: str | None = Header(default=None),
) -> int:
    """Meme chose que mobile_auth mais retourne 0 au lieu de 401 si
    absent/invalide. Pour les endpoints qui doivent rester ouverts en
    compat WinDev mais loguer l'user si dispo."""
    if not authorization:
        return 0
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return 0
    token = parts[1].strip()
    if not token:
        return 0
    return _try_jwt(token) or _try_uuid(token)
