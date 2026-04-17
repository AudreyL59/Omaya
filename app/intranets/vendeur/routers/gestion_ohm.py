from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter(prefix="/gestion-ohm", tags=["vendeur-gestion-ohm"])


@router.get("")
def get_gestion_ohm(user: UserToken = Depends(get_current_user)):
    return {"page": "gestion_ohm", "user": user.id_salarie}
