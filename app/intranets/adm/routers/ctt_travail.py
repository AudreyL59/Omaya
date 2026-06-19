"""
Router Fen_ListeDocRH (ADM Salaries -> Liste des contrats de travail).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel

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


# ---------------------------------------------------------------------------
# Fen_EditionDocRH
# ---------------------------------------------------------------------------


@router.get("/lookups")
def get_lookups(_user: UserToken = Depends(get_current_user)):
    """Combos Fen_EditionDocRH : types doc / produits / societes / type photo."""
    return {
        "types_doc": svc.list_types_doc(),
        "types_produit": svc.list_types_produit(),
        "societes": svc.list_societes_actives(),
        "types_photo_dpae": svc.list_types_photo_dpae(),
    }


@router.post("/new")
def post_new(user: UserToken = Depends(get_current_user)):
    """Btn Nouveau : cree un doc vide."""
    return svc.create_doc_blank(user.id_salarie)


@router.get("/{id_doc_rh}")
def get_doc(
    id_doc_rh: int,
    _user: UserToken = Depends(get_current_user),
):
    """Metadonnees du doc + taille du contenu."""
    d = svc.get_doc_meta(id_doc_rh)
    if not d:
        raise HTTPException(404, "Document introuvable")
    return d


class DocRHMetaPayload(BaseModel):
    id_type_doc: int = 0
    titre: str = ""
    info_cpl: str = ""
    id_type_produit: int = 1
    id_ste: int = 0
    doc_actif: bool = True
    prioritaire: bool = False
    doc_dpae: bool = False
    doc_dpae_distrib: bool = False
    id_tk_type_photo_dpae: int = 0


@router.put("/{id_doc_rh}")
def put_meta(
    id_doc_rh: int,
    payload: DocRHMetaPayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn Enregistrer : update metadonnees (sans contenu)."""
    return svc.update_doc_meta(id_doc_rh, payload.model_dump(), user.id_salarie)


@router.post("/{id_doc_rh}/content")
async def post_content(
    id_doc_rh: int,
    file: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    """Upload du DOCX -> remplace le contenu bytea."""
    content = await file.read()
    res = svc.upload_doc_content(id_doc_rh, content, user.id_salarie)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec")
    return res


class HtmlContentPayload(BaseModel):
    html: str = ""


@router.post("/{id_doc_rh}/content-html")
def post_content_html(
    id_doc_rh: int,
    payload: HtmlContentPayload,
    user: UserToken = Depends(get_current_user),
):
    """Save du contenu en HTML (depuis l'editeur inline). Le bytea
    'contenu' devient le HTML encode en UTF-8."""
    res = svc.upload_doc_content(
        id_doc_rh, payload.html.encode("utf-8"), user.id_salarie
    )
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec")
    return res


@router.get("/{id_doc_rh}/content")
def get_content(
    id_doc_rh: int,
    _user: UserToken = Depends(get_current_user),
):
    """Telecharge le DOCX original."""
    content = svc.download_doc_content(id_doc_rh)
    if content is None:
        raise HTTPException(404, "Aucun contenu")
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'inline; filename="doc_{id_doc_rh}.docx"'},
    )


@router.post("/{id_doc_rh}/publipostage-test")
def post_publipostage_test(
    id_doc_rh: int,
    id_ste: int,
    _user: UserToken = Depends(get_current_user),
):
    """Btn 'Tester Mise en page' : substitue les variables et renvoie le
    document rempli. Si stockage DOCX -> retourne du .docx; si HTML ->
    retourne du HTML."""
    meta = svc.get_doc_meta(id_doc_rh)
    titre = meta.get("titre") if meta else ""
    result = svc.publipostage_test(id_doc_rh, id_ste, titre_doc=titre or "")
    if result is None:
        raise HTTPException(400, "Pas de contenu a publiposter")
    content, mime = result
    ext = "docx" if "wordprocessingml" in mime else "html"
    return Response(
        content,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="test_{id_doc_rh}.{ext}"',
        },
    )
