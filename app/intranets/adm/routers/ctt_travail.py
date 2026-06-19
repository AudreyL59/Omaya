"""
Router Fen_ListeDocRH (ADM Salaries -> Liste des contrats de travail).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import ctt_travail as svc


router = APIRouter(prefix="/ctt-travail", tags=["adm-ctt-travail"])


@router.get("/list")
def get_list(
    actif: int = 1,
    _user: UserToken = Depends(get_current_user),
):
    """Liste des docs RH (actifs ou archives). actif: 1=actif, 0=archive."""
    return svc.list_docs(doc_actif=bool(actif))


@router.post("/{id_doc_rh}/duplicate")
def post_duplicate(
    id_doc_rh: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Dupliquer (+ mail a marie@exosphere.fr si non admin)."""
    return svc.duplicate_doc(
        id_doc_rh, user.id_salarie,
        user_login=user.login, user_prenom=user.prenom,
    )


@router.post("/{id_doc_rh}/archive")
def post_archive(
    id_doc_rh: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Archiver : doc_actif=False."""
    return svc.archive_doc(id_doc_rh, user.id_salarie)


@router.post("/{id_doc_rh}/restore")
def post_restore(
    id_doc_rh: int,
    user: UserToken = Depends(get_current_user),
):
    """Re-active un doc archive."""
    return svc.restore_doc(id_doc_rh, user.id_salarie)


@router.delete("/{id_doc_rh}")
def delete_doc(
    id_doc_rh: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Supprimer : soft delete."""
    return svc.delete_doc(id_doc_rh, user.id_salarie)
