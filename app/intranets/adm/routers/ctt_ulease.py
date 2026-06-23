"""
Router Fen_ListeDocUlease (ADM Ulease -> Liste des documents Ulease).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import ctt_travail as ctt_svc
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
    """Combos pour Fen_EditionDocUlease : types doc + societes +
    salaries (test publipostage)."""
    return {
        "types_doc": svc.list_types_doc(),
        "societes": ctt_svc.list_societes_actives(),
        "salaries": svc.list_salaries_test(),
    }


@router.get("/salaries/{id_salarie}/attributions")
def get_attributions(
    id_salarie: int,
    _user: UserToken = Depends(get_current_user),
):
    """Combo 'Avec vehicule' apres selection d'un salarie test."""
    return svc.list_attributions_salarie(id_salarie)


# ---------------------------------------------------------------------------
# Edition du doc (modal Fen_EditionDocUlease)
# ---------------------------------------------------------------------------


@router.post("/new")
def post_new(user: UserToken = Depends(get_current_user)):
    """Btn Nouveau : cree un doc vide."""
    return svc.create_doc_blank(user.id_salarie)


@router.get("/{id_doc_ulease}")
def get_doc(
    id_doc_ulease: int,
    _user: UserToken = Depends(get_current_user),
):
    """Meta du doc (sans contenu)."""
    r = svc.get_doc_meta(id_doc_ulease)
    if not r:
        raise HTTPException(404, "Document introuvable")
    return r


class DocUleaseMeta(BaseModel):
    id_type_doc: int = 0
    titre: str = ""
    info_cpl: str = ""
    id_ste: int = 0
    doc_actif: bool = True
    prioritaire: bool = False


@router.put("/{id_doc_ulease}")
def put_doc(
    id_doc_ulease: int,
    payload: DocUleaseMeta,
    user: UserToken = Depends(get_current_user),
):
    """PUT metadonnees."""
    return svc.update_doc_meta(
        id_doc_ulease, payload.model_dump(), user.id_salarie,
    )


@router.get("/{id_doc_ulease}/content")
def get_doc_content(
    id_doc_ulease: int,
    _user: UserToken = Depends(get_current_user),
):
    """Telecharge le contenu brut (DOCX ou HTML)."""
    content = svc.download_doc_content(id_doc_ulease)
    if content is None:
        raise HTTPException(404, "Pas de contenu")
    media = (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document" if ctt_svc.is_docx(content)
        else "text/html; charset=utf-8"
    )
    return Response(content, media_type=media)


@router.post("/{id_doc_ulease}/content")
async def post_doc_content(
    id_doc_ulease: int,
    file: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    """Upload nouveau contenu (DOCX ou HTML)."""
    content = await file.read()
    res = svc.upload_doc_content(id_doc_ulease, content, user.id_salarie)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec upload")
    return res


class PreviewPdfPayload(BaseModel):
    id_ste: int = 0
    id_salarie: int = 0
    id_vehicule_pc: int = 0
    titre_doc: str = ""


@router.post("/{id_doc_ulease}/preview-pdf")
def post_preview_pdf(
    id_doc_ulease: int,
    payload: PreviewPdfPayload,
    _user: UserToken = Depends(get_current_user),
):
    """Btn 'Tester Mise en page' : PDF publiposte."""
    pdf = svc.publipostage_test_pdf(
        id_doc_ulease,
        payload.id_ste,
        id_salarie=payload.id_salarie,
        id_vehicule_pc=payload.id_vehicule_pc,
        titre_doc=payload.titre_doc,
    )
    if pdf is None:
        raise HTTPException(400, "Genération PDF impossible")
    return Response(pdf, media_type="application/pdf")
