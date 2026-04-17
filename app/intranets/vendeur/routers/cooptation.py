from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter(prefix="/cooptation", tags=["vendeur-cooptation"])


@router.get("")
def get_cooptation(user: UserToken = Depends(get_current_user)):
    return {"page": "cooptation", "user": user.id_salarie}
