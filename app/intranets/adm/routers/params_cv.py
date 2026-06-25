"""Router Fen_ParamCV (ADM Recrutement -> Parametres CVtheque).

Endpoints :
  GET    /params-cv/{entity}                  -> liste
  POST   /params-cv/{entity}                  -> create/update (id=0 = create)
  DELETE /params-cv/{entity}/{id}             -> soft delete
  GET    /params-cv/cv-annonceur/{id}/logo    -> stream PNG/JPEG du logo
  POST   /params-cv/cv-annonceur/{id}/logo    -> upload logo (multipart)

entity parmi : cv_source, cv_annonceur, cv_poste, salon_visio, cv_statut.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import params_cv as svc


router = APIRouter(prefix="/params-cv", tags=["adm-params-cv"])


@router.get("/{entity}")
def get_entity(
    entity: str,
    _user: UserToken = Depends(get_current_user),
):
    return svc.list_entity(entity)


@router.post("/{entity}")
def post_entity(
    entity: str,
    payload: dict,
    user: UserToken = Depends(get_current_user),
):
    res = svc.save_entity(entity, payload, user.id_salarie)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec")
    return res


@router.delete("/{entity}/{id_v}")
def delete_entity(
    entity: str,
    id_v: int,
    user: UserToken = Depends(get_current_user),
):
    return svc.delete_entity(entity, id_v, user.id_salarie)


# ---- Logo cv_annonceur (upload + stream) ----------------------------------


@router.get("/cv-annonceur/{id_v}/logo")
def get_logo(
    id_v: int,
    _user: UserToken = Depends(get_current_user),
):
    logo = svc.get_logo_annonceur(id_v)
    if not logo:
        raise HTTPException(404, "Pas de logo")
    # Detection rapide MIME (par les magic bytes)
    mime = "application/octet-stream"
    if logo[:3] == b"\xff\xd8\xff":
        mime = "image/jpeg"
    elif logo[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    elif logo[:4] == b"GIF8":
        mime = "image/gif"
    return Response(content=bytes(logo), media_type=mime)


@router.post("/cv-annonceur/{id_v}/logo")
async def post_logo(
    id_v: int,
    file: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    content = await file.read()
    res = svc.upload_logo_annonceur(id_v, content, user.id_salarie)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec")
    return res
