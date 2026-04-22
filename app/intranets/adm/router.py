from fastapi import APIRouter, Depends

from app.core.auth.dependencies import require_intranet
from app.intranets.adm.menu import router as menu_router
from app.intranets.adm.routers.stat_rh_rdv import router as stat_rh_rdv_router

router = APIRouter(
    prefix="/adm",
    tags=["adm"],
    dependencies=[Depends(require_intranet("adm"))],
)

router.include_router(menu_router)
router.include_router(stat_rh_rdv_router)


@router.get("/ping")
def ping():
    return {"intranet": "adm", "status": "ok"}
