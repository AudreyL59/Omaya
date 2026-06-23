"""
Router Fen_SuiviMutuelle (ADM Salaries -> Adhesion mutuelle entreprise).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import suivi_mutuelle as svc


router = APIRouter(prefix="/suivi-mutuelle", tags=["adm-suivi-mutuelle"])


@router.get("/actifs")
def get_actifs(_user: UserToken = Depends(get_current_user)):
    return svc.list_actifs()


@router.get("/sortants")
def get_sortants(_user: UserToken = Depends(get_current_user)):
    return svc.list_sortants()


class MutuelleFlags(BaseModel):
    mutuelle_dossier: bool = False
    mutuelle_att_ss: bool = False
    mutuelle_rib: bool = False
    mutuelle_doc_envoyes: bool = False
    mutuelle_recep_certif: bool = False


@router.put("/{id_salarie}")
def put_flags(
    id_salarie: int,
    payload: MutuelleFlags,
    user: UserToken = Depends(get_current_user),
):
    return svc.update_flags(id_salarie, payload.model_dump(), user.id_salarie)
