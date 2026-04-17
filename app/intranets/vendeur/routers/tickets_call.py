from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter(prefix="/tickets-call", tags=["vendeur-tickets-call"])


@router.get("")
def get_tickets_call(user: UserToken = Depends(get_current_user)):
    """Suivi des tickets call."""
    return {"page": "tickets_call_suivi", "user": user.id_salarie}


@router.get("/energie")
def get_tickets_call_energie(user: UserToken = Depends(get_current_user)):
    """Ajout ticket énergie."""
    return {"page": "tickets_call_energie", "user": user.id_salarie}


@router.get("/fibre")
def get_tickets_call_fibre(user: UserToken = Depends(get_current_user)):
    """Ajout ticket fibre."""
    return {"page": "tickets_call_fibre", "user": user.id_salarie}
