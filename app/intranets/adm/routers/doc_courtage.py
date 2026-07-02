"""Router Fen_EditionDocCourtage (edition template doc courtage)."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import doc_courtage as svc

router = APIRouter(prefix="/doc-courtage", tags=["adm-doc-courtage"])


@router.get("/combos/societes-interne",
            response_model=list[svc.SocieteInterneItem])
def get_combo_societes_interne(_u: UserToken = Depends(get_current_user)):
    return svc.list_societes_interne()


@router.get("/combos/distribs-test",
            response_model=list[svc.DistribTestItem])
def get_combo_distribs_test(_u: UserToken = Depends(get_current_user)):
    return svc.list_distribs_test()


@router.get("", response_model=list[svc.DocCourtageListItem])
def get_list_docs(
    archives: bool = False,
    _u: UserToken = Depends(get_current_user),
):
    return svc.list_docs(archives)


@router.post("/{id_doc}/duplicate")
def post_duplicate(
    id_doc: int,
    u: UserToken = Depends(get_current_user),
):
    try:
        id_new = svc.duplicate_doc(id_doc, u.id_salarie)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"ok": True, "id_doc_courtage": str(id_new)}


@router.post("/{id_doc}/archive")
def post_archive(
    id_doc: int,
    u: UserToken = Depends(get_current_user),
):
    svc.archive_doc(id_doc, u.id_salarie)
    return {"ok": True}


@router.get("/{id_doc}", response_model=svc.DocCourtageDetail)
def get_doc(
    id_doc: int,
    _u: UserToken = Depends(get_current_user),
):
    d = svc.get_doc_courtage(id_doc)
    if not d:
        raise HTTPException(404, "Document introuvable")
    return d


@router.post("")
def post_doc(
    payload: svc.DocCourtagePayload,
    u: UserToken = Depends(get_current_user),
):
    id_new = svc.create_doc_courtage(payload, u.id_salarie)
    return {"ok": True, "id_doc_courtage": str(id_new)}


@router.put("/{id_doc}")
def put_doc(
    id_doc: int,
    payload: svc.DocCourtagePayload,
    u: UserToken = Depends(get_current_user),
):
    svc.update_doc_courtage(id_doc, payload, u.id_salarie)
    return {"ok": True}


@router.delete("/{id_doc}")
def delete_doc(
    id_doc: int,
    u: UserToken = Depends(get_current_user),
):
    svc.delete_doc_courtage(id_doc, u.id_salarie)
    return {"ok": True}


@router.get("/{id_doc}/contenu")
def download_contenu(
    id_doc: int,
    _u: UserToken = Depends(get_current_user),
):
    raw = svc.get_contenu(id_doc)
    if not raw:
        raise HTTPException(404, "Contenu absent")
    d = svc.get_doc_courtage(id_doc)
    filename = f"{(d.titre if d else 'doc').replace(' ', '_')}.docx"
    return Response(
        content=raw,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.post("/{id_doc}/contenu")
async def upload_contenu(
    id_doc: int,
    file: UploadFile = File(...),
    u: UserToken = Depends(get_current_user),
):
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Fichier vide")
    # Verif signature DOCX (ZIP)
    if not raw.startswith(b"PK\x03\x04"):
        raise HTTPException(400, "Fichier non-DOCX (signature ZIP absente)")
    svc.update_contenu(id_doc, raw, u.id_salarie)
    return {"ok": True, "size": len(raw)}
