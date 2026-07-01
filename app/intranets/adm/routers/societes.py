"""Router ADM > Fen_ListeSociete (icone building du header)."""

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import societes as svc

router = APIRouter(prefix="/societes", tags=["adm-societes"])


@router.get("", response_model=list[svc.SocieteItem])
def get_list_societes(
    type_orga: int = svc.TYPE_ORGA_INTERNE,   # 1=interne | 3=distributeur
    archivees: bool = False,
    _u: UserToken = Depends(get_current_user),
):
    return svc.list_societes(type_orga, archivees)
