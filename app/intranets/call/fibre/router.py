from fastapi import APIRouter, Depends

from app.core.auth.dependencies import require_intranet
from app.intranets.call.fibre.menu import router as menu_router
from app.intranets.call.fibre.routers.tickets import router as tickets_router

router = APIRouter(
    prefix="/call/fibre",
    tags=["call-fibre"],
    dependencies=[Depends(require_intranet("call_fibre"))],
)

# Menu dynamique
router.include_router(menu_router)

# Tickets (page principale : tableau haut + bas + stats)
router.include_router(tickets_router)


@router.get("/ping")
def ping():
    return {"intranet": "call_fibre", "status": "ok"}
