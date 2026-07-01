"""Router ADM > Fen_ListeSociete (icone building du header)."""

from fastapi import APIRouter, Depends, HTTPException

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


@router.post("/{id_societe_auto}/duplicate")
def post_duplicate_societe(
    id_societe_auto: int,
    u: UserToken = Depends(get_current_user),
):
    try:
        new_auto = svc.duplicate_societe(id_societe_auto, u.id_salarie)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"ok": True, "id_societe_auto": str(new_auto)}


@router.delete("/{id_societe_auto}")
def delete_societe(
    id_societe_auto: int,
    u: UserToken = Depends(get_current_user),
):
    svc.delete_societe(id_societe_auto, u.id_salarie)
    return {"ok": True}


@router.post("/{id_societe_auto}/archive")
def post_archive_societe(
    id_societe_auto: int,
    u: UserToken = Depends(get_current_user),
):
    svc.archive_societe(id_societe_auto, u.id_salarie)
    return {"ok": True}
