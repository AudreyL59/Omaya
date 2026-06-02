"""
Configuration du menu Intranet Call Energie.

Squelette etape 1 : juste un Dashboard. A enrichir quand les pages metier
seront branchees.
"""

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter()


@router.get("/menu")
def get_menu(user: UserToken = Depends(get_current_user)):
    """Menu Intranet Call Energie.

    Chaque element : {key, label, route, visible}
    Frontend filtre les non-visibles.
    """
    if not user.is_actif:
        return {
            "menu_visible": False,
            "items": [],
        }

    items = [
        {
            "key": "tickets_call",
            "label": "Tickets Call",
            "route": "/tickets-call",
            "visible": True,
        },
    ]

    return {
        "menu_visible": True,
        "items": items,
    }
