from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter(prefix="/scool", tags=["vendeur-scool"])


@router.get("")
def get_scool(user: UserToken = Depends(get_current_user)):
    return {"page": "scool", "user": user.id_salarie}
