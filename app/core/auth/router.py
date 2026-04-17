from fastapi import APIRouter, HTTPException, status, Depends

from app.core.auth.schemas import LoginRequest, LoginResponse, UserToken
from app.core.auth.service import authenticate_user
from app.core.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """
    Authentification par email + mot de passe.

    Le champ `intranet` indique depuis quel intranet l'utilisateur se connecte
    (utile pour le log de connexion, pas pour la vérification d'accès qui se
    fait côté router de chaque intranet).
    """
    result = authenticate_user(request.email, request.password)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    return result


@router.get("/me", response_model=UserToken)
def me(user: UserToken = Depends(get_current_user)):
    """Retourne les infos de l'utilisateur connecté."""
    return user
