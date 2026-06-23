"""
Router Fen_ListeDocUlease (ADM Ulease -> Liste des documents Ulease).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import ctt_ulease as svc


router = APIRouter(prefix="/ctt-ulease", tags=["adm-ctt-ulease"])


@router.get("/list")
def get_list(
    actif: int = 1,
    _user: UserToken = Depends(get_current_user),
):
    """Liste des docs Ulease (actifs ou archives). actif: 1=actif, 0=archive."""
    return svc.list_docs(doc_actif=bool(actif))


@router.post("/{id_doc_ulease}/duplicate")
def post_duplicate(
    id_doc_ulease: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Dupliquer (+ mail a marie@exosphere.fr si non admin)."""
    return svc.duplicate_doc(
        id_doc_ulease, user.id_salarie,
        user_login=user.login, user_prenom=user.prenom,
    )


@router.post("/{id_doc_ulease}/archive")
def post_archive(
    id_doc_ulease: int,
    user: UserToken = Depends(get_current_user),
):
    return svc.archive_doc(id_doc_ulease, user.id_salarie)


@router.post("/{id_doc_ulease}/restore")
def post_restore(
    id_doc_ulease: int,
    user: UserToken = Depends(get_current_user),
):
    return svc.restore_doc(id_doc_ulease, user.id_salarie)


@router.delete("/{id_doc_ulease}")
def delete_doc(
    id_doc_ulease: int,
    user: UserToken = Depends(get_current_user),
):
    return svc.delete_doc(id_doc_ulease, user.id_salarie)


@router.get("/lookups")
def get_lookups(_user: UserToken = Depends(get_current_user)):
    """Combo Type Doc."""
    return {"types_doc": svc.list_types_doc()}
