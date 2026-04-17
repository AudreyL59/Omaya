from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter(prefix="/agenda-recrutement", tags=["vendeur-agenda-recrutement"])


@router.get("")
def get_agenda_recrutement(user: UserToken = Depends(get_current_user)):
    return {"page": "agenda_recrutement", "user": user.id_salarie}
