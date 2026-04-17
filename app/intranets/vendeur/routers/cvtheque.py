from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter(prefix="/cvtheque", tags=["vendeur-cvtheque"])


@router.get("")
def get_cvtheque(user: UserToken = Depends(get_current_user)):
    return {"page": "cvtheque", "user": user.id_salarie}
