from fastapi import APIRouter, Depends

from app.core.auth.dependencies import require_intranet
from app.intranets.call.energie.menu import router as menu_router
from app.intranets.call.energie.routers.tickets import router as tickets_router

router = APIRouter(
    prefix="/call/energie",
    tags=["call-energie"],
    dependencies=[Depends(require_intranet("call_energie"))],
)

# Menu dynamique
router.include_router(menu_router)

# Tickets (page principale)
router.include_router(tickets_router)


@router.get("/ping")
def ping():
    return {"intranet": "call_energie", "status": "ok"}
