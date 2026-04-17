from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter(prefix="/tickets", tags=["vendeur-tickets"])


@router.get("")
def get_tickets(user: UserToken = Depends(get_current_user)):
    return {"page": "tickets", "user": user.id_salarie}
