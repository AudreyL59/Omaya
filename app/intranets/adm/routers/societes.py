"""Router ADM > Fen_ListeSociete (icone building du header)."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

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


@router.get("/formes-juri", response_model=list[svc.FormeJuri])
def get_formes_juri(_u: UserToken = Depends(get_current_user)):
    return svc.list_formes_juri()


@router.get("/{id_societe_auto}", response_model=svc.SocieteDetail)
def get_societe(
    id_societe_auto: int,
    _u: UserToken = Depends(get_current_user),
):
    d = svc.get_societe(id_societe_auto)
    if not d:
        raise HTTPException(404, "Société introuvable")
    return d


@router.post("", response_model=svc.SocieteDetail)
def post_societe(
    payload: svc.SocietePayload,
    u: UserToken = Depends(get_current_user),
):
    new_auto = svc.create_societe(payload, u.id_salarie)
    return svc.get_societe(new_auto)


@router.put("/{id_societe_auto}", response_model=svc.SocieteDetail)
def put_societe(
    id_societe_auto: int,
    payload: svc.SocietePayload,
    u: UserToken = Depends(get_current_user),
):
    svc.update_societe(id_societe_auto, payload, u.id_salarie)
    d = svc.get_societe(id_societe_auto)
    if not d:
        raise HTTPException(404, "Société introuvable")
    return d


@router.get("/{id_societe_auto}/image/{champ}")
def get_societe_image(
    id_societe_auto: int,
    champ: str,
    _u: UserToken = Depends(get_current_user),
):
    """Renvoie l'image (bytes + Content-Type detecte).
    champ ∈ {logo, guimmick, cachet_cial, gerant_paraphe, gerant_signature}."""
    if champ not in svc.IMAGE_COLS:
        raise HTTPException(400, "Champ image invalide")
    res = svc.get_societe_image(id_societe_auto, champ)
    if not res:
        raise HTTPException(404, "Image absente")
    raw, mime = res
    return Response(content=raw, media_type=mime,
                     headers={"Cache-Control": "no-cache"})


@router.post("/{id_societe_auto}/image/{champ}")
async def post_societe_image(
    id_societe_auto: int,
    champ: str,
    file: UploadFile = File(...),
    u: UserToken = Depends(get_current_user),
):
    """Upload une image dans une des 5 colonnes bytea de pgt_societe."""
    if champ not in svc.IMAGE_COLS:
        raise HTTPException(400, "Champ image invalide")
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Fichier vide")
    svc.update_societe_image(id_societe_auto, champ, raw, u.id_salarie)
    return {"ok": True, "champ": champ, "size": len(raw)}


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
