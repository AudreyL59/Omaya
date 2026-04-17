from fastapi import APIRouter, Depends

from app.core.auth.dependencies import require_intranet

router = APIRouter(
    prefix="/call/energie",
    tags=["call-energie"],
    dependencies=[Depends(require_intranet("call_energie"))],
)


@router.get("/ping")
def ping():
    return {"intranet": "call_energie", "status": "ok"}
