from fastapi import APIRouter, Depends

from app.core.auth.dependencies import require_intranet

router = APIRouter(
    prefix="/call/prise-rdv",
    tags=["call-prise-rdv"],
    dependencies=[Depends(require_intranet("call_prise_rdv"))],
)


@router.get("/ping")
def ping():
    return {"intranet": "call_prise_rdv", "status": "ok"}
