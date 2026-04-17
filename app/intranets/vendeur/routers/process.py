from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter(prefix="/process", tags=["vendeur-process"])


@router.get("")
def get_process(user: UserToken = Depends(get_current_user)):
    return {"page": "process", "user": user.id_salarie}
