from fastapi import APIRouter, Depends

from app.core.auth.dependencies import require_intranet

router = APIRouter(
    prefix="/adm",
    tags=["adm"],
    dependencies=[Depends(require_intranet("adm"))],
)


@router.get("/ping")
def ping():
    return {"intranet": "adm", "status": "ok"}
