from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter(prefix="/agenda-cial", tags=["vendeur-agenda-cial"])


@router.get("")
def get_agenda_cial(user: UserToken = Depends(get_current_user)):
    return {"page": "agenda_cial", "user": user.id_salarie}
