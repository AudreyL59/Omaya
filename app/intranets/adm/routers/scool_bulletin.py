"""
Router Fen_ScoolBulletin.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.scool_bulletin import (
    BulletinDetail, BulletinPayload, CalculerNotesParams,
    CalculerNotesResult, MentionCombo, RecupererProdParams,
    RecupererProdResult, StagiaireBulletinCombo,
)
from app.intranets.adm.services import scool_bulletin as svc

router = APIRouter(prefix="/scool/bulletins", tags=["adm-scool-bulletins"])


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


@router.get("/mentions", response_model=list[MentionCombo])
def get_mentions(user: UserToken = Depends(get_current_user)):
    _require_droit(user, "FormScool")
    return svc.list_mentions()


@router.get("/stagiaires/{id_formation}",
            response_model=list[StagiaireBulletinCombo])
def get_stagiaires(
    id_formation: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    return svc.list_stagiaires_formation(id_formation)


@router.get("/{id_bulletin}", response_model=BulletinDetail)
def get_detail(
    id_bulletin: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    d = svc.get_bulletin(id_bulletin)
    if not d:
        raise HTTPException(404, "Bulletin introuvable")
    return d


@router.get("", response_model=BulletinDetail)
def get_initial(
    id_formation: str = Query(...),
    id_salarie: str = Query(...),
    user: UserToken = Depends(get_current_user),
):
    """Cf. WinDev Code Init branche IdBulletin=0 : initialise Du/Au."""
    _require_droit(user, "FormScool")
    return svc.initial_bulletin(id_formation, id_salarie)


@router.post("")
def post_create(
    payload: BulletinPayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    new_id = svc.create_bulletin(payload, op_id)
    return {"ok": bool(new_id), "id_bulletin": new_id}


@router.put("/{id_bulletin}")
def put_update(
    id_bulletin: str,
    payload: BulletinPayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.update_bulletin(id_bulletin, payload, op_id)
    return {"ok": ok}


@router.post("/recuperer-prod", response_model=RecupererProdResult)
def post_recuperer_prod(
    payload: RecupererProdParams,
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Recuperer la prod et les absences'."""
    _require_droit(user, "FormScool")
    return svc.recuperer_prod(payload)


@router.post("/calculer-notes", response_model=CalculerNotesResult)
def post_calculer_notes(
    payload: CalculerNotesParams,
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Calculer les notes'."""
    _require_droit(user, "FormScool")
    return svc.calculer_notes(payload)


@router.get("/debug/signature-cachet")
def get_debug_signature_cachet(
    user: UserToken = Depends(get_current_user),
):
    """Diagnostic : verifie Pillow + PyMuPDF + composition."""
    _require_droit(user, "FormScool")
    from app.intranets.adm.services import scool_bulletin_pdf as pdfsvc

    diag: dict = {}
    # Test PyMuPDF
    try:
        import fitz
        diag["pymupdf"] = f"OK v{fitz.__version__}"
    except ImportError as e:
        diag["pymupdf"] = f"KO : {e}"
    # Test Pillow
    try:
        from PIL import Image, __version__ as pil_ver
        diag["pillow"] = f"OK v{pil_ver}"
    except ImportError as e:
        diag["pillow"] = f"KO : {e}"

    so = pdfsvc._load_infos_societe()
    diag["raison_sociale"] = so.get("raison_sociale")

    def _to_bytes(v):
        if v is None:
            return b""
        if hasattr(v, "tobytes"):
            v = v.tobytes()
        return bytes(v)

    cachet_raw = _to_bytes(so.get("cachet_cial"))
    signature_raw = _to_bytes(so.get("gerant_signature"))
    diag["cachet_raw_bytes"] = len(cachet_raw)
    diag["signature_raw_bytes"] = len(signature_raw)
    diag["cachet_mime"] = pdfsvc._detect_image_mime(cachet_raw)
    diag["signature_mime"] = pdfsvc._detect_image_mime(signature_raw)

    # Conversion PDF -> PNG si necessaire
    if diag["cachet_mime"] == "application/pdf":
        cachet_png = pdfsvc._pdf_first_page_to_png(cachet_raw)
        diag["cachet_pdf_to_png_bytes"] = len(cachet_png)
    else:
        cachet_png = cachet_raw

    signature_png = signature_raw

    # Composition
    combined = pdfsvc._compose_signature_cachet(cachet_png, signature_png)
    diag["combined_bytes"] = len(combined)

    return diag


@router.get("/{id_bulletin}/pdf")
def get_pdf(
    id_bulletin: str,
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Generer le bulletin PDF' - Etat_ScoolBulletin (WeasyPrint)."""
    _require_droit(user, "FormScool")
    from app.intranets.adm.services import scool_bulletin_pdf
    detail = svc.get_bulletin(id_bulletin)
    if not detail:
        raise HTTPException(404, "Bulletin introuvable")
    try:
        pdf_bytes = scool_bulletin_pdf.build_bulletin_pdf(detail)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                f'attachment; filename="Bulletin_{id_bulletin}.pdf"',
        },
    )
