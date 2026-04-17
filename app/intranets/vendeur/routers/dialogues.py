from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter(prefix="/dialogues", tags=["vendeur-dialogues"])


@router.get("")
def get_dialogues(user: UserToken = Depends(get_current_user)):
    return {"page": "dialogues", "user": user.id_salarie}
