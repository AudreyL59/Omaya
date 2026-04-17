from fastapi import APIRouter, Depends

from app.core.auth.dependencies import require_intranet

router = APIRouter(
    prefix="/call/rh",
    tags=["call-rh"],
    dependencies=[Depends(require_intranet("call_rh"))],
)


@router.get("/ping")
def ping():
    return {"intranet": "call_rh", "status": "ok"}
