from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter(prefix="/organigramme", tags=["vendeur-organigramme"])


@router.get("")
def get_organigramme(user: UserToken = Depends(get_current_user)):
    return {"page": "organigramme", "user": user.id_salarie}
