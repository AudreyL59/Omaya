from fastapi import APIRouter, Depends

from app.core.auth.dependencies import require_intranet

router = APIRouter(
    prefix="/call/fibre",
    tags=["call-fibre"],
    dependencies=[Depends(require_intranet("call_fibre"))],
)


@router.get("/ping")
def ping():
    return {"intranet": "call_fibre", "status": "ok"}
