from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.organigramme import OrgaTreeNode
from app.intranets.adm.services.organigramme import get_organigramme_adm

router = APIRouter(prefix="/organigramme", tags=["adm-organigramme"])


@router.get("", response_model=list[OrgaTreeNode])
def get_tree(user: UserToken = Depends(get_current_user)):
    """Arborescence complète (accès global pour l'intranet ADM)."""
    return get_organigramme_adm()
