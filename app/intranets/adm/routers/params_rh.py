"""
Router Fen_ParamRH (ADM Salaries -> Parametres RH).

Endpoints :
  GET    /params-rh/{entity}                  -> liste
  POST   /params-rh/{entity}                  -> create/update (id=0 = create)
  DELETE /params-rh/{entity}/{id}             -> soft delete

  GET    /params-rh/type-produit/{id}/partenaires
  POST   /params-rh/type-produit/{id}/partenaires
  DELETE /params-rh/type-produit-partenaire/{id}
  POST   /params-rh/type-produit/{id}/logo (multipart)

  GET    /params-rh/partenaires (combo)

'entity' parmi : type_poste, type_ctt, type_horaire, type_sortie,
mutuelle, type_absence, type_ope_livret, type_produit.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import params_rh as svc


router = APIRouter(prefix="/params-rh", tags=["adm-params-rh"])


# Simple entites
@router.get("/{entity}")
def get_entity(entity: str, _user: UserToken = Depends(get_current_user)):
    if entity == "type_produit":
        return svc.list_type_produit()
    if entity == "partenaires":
        return svc.list_partenaires()
    if entity == "portail":
        return svc.list_portails()
    return svc.list_entity(entity)


class GenericPayload(BaseModel):
    id: str = "0"

    class Config:
        extra = "allow"


@router.post("/{entity}")
def post_entity(
    entity: str,
    payload: dict,
    user: UserToken = Depends(get_current_user),
):
    if entity == "type_produit":
        return svc.save_type_produit(payload, user.id_salarie)
    if entity == "portail":
        return svc.save_portail(payload, user.id_salarie)
    return svc.save_entity(entity, payload, user.id_salarie)


@router.delete("/{entity}/{id_v}")
def delete_entity(
    entity: str,
    id_v: int,
    user: UserToken = Depends(get_current_user),
):
    if entity == "type_produit":
        return svc.delete_type_produit(id_v, user.id_salarie)
    if entity == "type_produit_partenaire":
        return svc.delete_type_produit_partenaire(id_v, user.id_salarie)
    if entity == "portail":
        return svc.delete_portail(id_v, user.id_salarie)
    return svc.delete_entity(entity, id_v, user.id_salarie)


# ---- type_produit : sous-resource partenaires + upload logo ---------------


@router.get("/type-produit/{id_v}/partenaires")
def get_tp_partenaires(
    id_v: int,
    _user: UserToken = Depends(get_current_user),
):
    return svc.list_type_produit_partenaires(id_v)


class AddPartenaire(BaseModel):
    id_partenaire: int


@router.post("/type-produit/{id_v}/partenaires")
def post_tp_partenaires(
    id_v: int,
    payload: AddPartenaire,
    user: UserToken = Depends(get_current_user),
):
    return svc.add_type_produit_partenaire(
        id_v, payload.id_partenaire, user.id_salarie,
    )


@router.post("/type-produit/{id_v}/logo")
async def post_tp_logo(
    id_v: int,
    file: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    content = await file.read()
    res = svc.upload_logo_type_produit(id_v, content, user.id_salarie)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec")
    return res
