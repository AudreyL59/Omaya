from fastapi import APIRouter, Depends

from app.core.auth.dependencies import require_intranet

router = APIRouter(
    prefix="/vendeur",
    tags=["vendeur"],
    dependencies=[Depends(require_intranet("vendeur"))],
)


@router.get("/ping")
def ping():
    return {"intranet": "vendeur", "status": "ok"}
