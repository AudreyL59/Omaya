"""
Dépendances FastAPI pour l'authentification et les droits d'accès.

Usage :
    # Récupérer l'utilisateur connecté
    @router.get("/me")
    def me(user: UserToken = Depends(get_current_user)):
        return user

    # Protéger tout un router par intranet
    router = APIRouter(
        prefix="/adm",
        dependencies=[Depends(require_intranet("adm"))],
    )
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.auth.security import decode_access_token
from app.core.auth.schemas import UserToken

_bearer_scheme = HTTPBearer()

# Mapping intranet -> code de droit requis
# None = pas de vérification de droit spécifique (juste l'auth)
INTRANET_DROIT_CODES = {
    "vendeur": None,          # accès à tous les actifs (+ inactifs en mode restreint)
    "adm": "IntraADM",
    "call_energie": "IntraCall",
    "call_fibre": "IntraCallFibre",
    "call_rh": "IntraCallRH",
    "call_prise_rdv": "IntraCallRDV",
}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> UserToken:
    """Décode le JWT et retourne l'utilisateur connecté."""
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
        )
    return UserToken(
        id_salarie=int(payload["sub"]),
        login=payload["login"],
        nom=payload["nom"],
        prenom=payload["prenom"],
        is_actif=payload["is_actif"],
        is_pause=payload["is_pause"],
        is_resp=payload.get("is_resp", False),
        agenda_actif=payload["agenda_actif"],
        active_log=payload["active_log"],
        gsm=payload["gsm"],
        id_ste=payload["id_ste"],
        prof_poste=payload["prof_poste"],
        droits=payload["droits"],
    )


def require_intranet(intranet_key: str):
    """
    Dépendance FastAPI qui vérifie l'accès à un intranet.

    Équivalent de VérifDroit() en WinDev.
    Pour l'intranet vendeur : vérifie juste que l'utilisateur est authentifié.
    Pour les autres : vérifie que le code de droit est dans la liste.
    Pour ADM : vérifie aussi que l'utilisateur est actif.
    """
    droit_code = INTRANET_DROIT_CODES.get(intranet_key)

    async def _check(user: UserToken = Depends(get_current_user)):
        # ADM exige en plus que l'utilisateur soit actif
        if intranet_key == "adm" and not user.is_actif:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé : utilisateur inactif",
            )

        # Vérification du droit spécifique
        if droit_code is not None and droit_code not in user.droits:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé à l'intranet {intranet_key}",
            )

        return user

    return _check


def require_actif(user: UserToken = Depends(get_current_user)) -> UserToken:
    """
    Dépendance pour les routes qui exigent un utilisateur actif.

    Usage sur l'intranet vendeur : les routes protégées (tout sauf Mon Compte)
    utilisent cette dépendance en plus de get_current_user.
    """
    if not user.is_actif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé : utilisateur inactif",
        )
    return user
