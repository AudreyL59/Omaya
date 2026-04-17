from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter(prefix="/clusters", tags=["vendeur-clusters"])


@router.get("")
def get_clusters(user: UserToken = Depends(get_current_user)):
    return {"page": "clusters", "user": user.id_salarie}
