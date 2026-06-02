from fastapi import APIRouter, Depends

from app.core.auth.dependencies import require_intranet
from app.intranets.call.energie.menu import router as menu_router

router = APIRouter(
    prefix="/call/energie",
    tags=["call-energie"],
    dependencies=[Depends(require_intranet("call_energie"))],
)

# Menu dynamique
router.include_router(menu_router)


@router.get("/ping")
def ping():
    return {"intranet": "call_energie", "status": "ok"}
