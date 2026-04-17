from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter(prefix="/production", tags=["vendeur-production"])


@router.get("")
def get_production(user: UserToken = Depends(get_current_user)):
    return {"page": "production", "user": user.id_salarie}
