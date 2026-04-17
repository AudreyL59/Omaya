from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter(prefix="/mon-compte", tags=["vendeur-mon-compte"])


@router.get("")
def get_mon_compte(user: UserToken = Depends(get_current_user)):
    """Retourne les infos du compte de l'utilisateur connecté."""
    return {
        "id_salarie": user.id_salarie,
        "nom": user.nom,
        "prenom": user.prenom,
        "login": user.login,
        "gsm": user.gsm,
        "is_actif": user.is_actif,
        "prof_poste": user.prof_poste,
    }
