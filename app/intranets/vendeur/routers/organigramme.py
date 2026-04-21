from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.vendeur.schemas.organigramme import OrgaTreeNode
from app.intranets.vendeur.services.organigramme import get_organigramme

router = APIRouter(prefix="/organigramme", tags=["vendeur-organigramme"])


@router.get("", response_model=list[OrgaTreeNode])
def get_tree(user: UserToken = Depends(get_current_user)):
    """
    Retourne l'arborescence complète accessible à l'utilisateur avec
    les salariés actifs de chaque orga.
    """
    return get_organigramme(
        id_salarie_user=user.id_salarie,
        droits=user.droits,
        is_resp=user.is_resp,
    )
