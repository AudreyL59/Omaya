"""
Router Fen_ScoolStagiaire_Fiche.

Endpoints (droit 'FormScool') :
  GET  /adm/scool/stagiaire-fiche/motifs-absence
  GET  /adm/scool/stagiaire-fiche/{id_form}/{id_sal}?type_prod=ENI|SFR
  POST /adm/scool/stagiaire-fiche/save
  POST /adm/scool/stagiaire-fiche/ajout-ligne-prod
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.scool_stagiaire_fiche import (
    AjoutLigneProdPayload, MotifAbsenceCombo,
    ScoolStagiaireFiche, StagiaireHeaderPayload,
)
from app.intranets.adm.services import scool_stagiaire_fiche as svc

router = APIRouter(
    prefix="/scool/stagiaire-fiche", tags=["adm-scool-stagiaire-fiche"],
)


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


@router.get("/motifs-absence", response_model=list[MotifAbsenceCombo])
def get_motifs_absence(user: UserToken = Depends(get_current_user)):
    _require_droit(user, "FormScool")
    return svc.list_motifs_absence()


@router.get(
    "/{id_formation}/{id_salarie}",
    response_model=ScoolStagiaireFiche,
)
def get_fiche(
    id_formation: str,
    id_salarie: str,
    type_prod: str = Query("", description="ENI | SFR | (vide)"),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    f = svc.get_fiche_stagiaire(id_formation, id_salarie, type_prod)
    if not f:
        raise HTTPException(404, "Stagiaire introuvable dans cette formation")
    return f


@router.post("/save")
def post_save(
    payload: StagiaireHeaderPayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.save_header(payload, op_id)
    return {"ok": ok}


@router.post("/ajout-ligne-prod")
def post_ajout_ligne_prod(
    payload: AjoutLigneProdPayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.ajout_ligne_prod(payload, op_id)
    return {"ok": ok}


# --------------------------------------------------------------------
# PDFs (3 etats WinDev)
# --------------------------------------------------------------------

def _load_fiche_or_404(
    id_formation: str, id_salarie: str, type_prod: str,
):
    f = svc.get_fiche_stagiaire(id_formation, id_salarie, type_prod)
    if not f:
        raise HTTPException(404, "Stagiaire introuvable dans cette formation")
    return f


@router.get("/{id_formation}/{id_salarie}/pdf-declpres")
def get_pdf_declpres(
    id_formation: str, id_salarie: str,
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Imprimer PDF' onglet Declaratif de presence
    (cf. WinDev EtatScool_DeclPres).
    """
    _require_droit(user, "FormScool")
    from app.intranets.adm.services import scool_stagiaire_pdf
    fiche = _load_fiche_or_404(id_formation, id_salarie, "")
    try:
        pdf = scool_stagiaire_pdf.build_declpres_pdf(fiche)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return Response(
        content=pdf, media_type="application/pdf",
        headers={
            "Content-Disposition":
                f'attachment; filename="EmargementScool_{id_salarie}.pdf"',
        },
    )


@router.get("/{id_formation}/{id_salarie}/pdf-prodeni")
def get_pdf_prodeni(
    id_formation: str, id_salarie: str,
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Imprimer' onglet Prod ENI
    (cf. WinDev EtatProdStagiareScool)."""
    _require_droit(user, "FormScool")
    from app.intranets.adm.services import scool_stagiaire_pdf
    fiche = _load_fiche_or_404(id_formation, id_salarie, "ENI")
    try:
        pdf = scool_stagiaire_pdf.build_prodeni_pdf(fiche)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return Response(
        content=pdf, media_type="application/pdf",
        headers={
            "Content-Disposition":
                f'attachment; filename="SuiviScool_ENI_{id_salarie}.pdf"',
        },
    )


@router.get("/{id_formation}/{id_salarie}/pdf-prodsfr")
def get_pdf_prodsfr(
    id_formation: str, id_salarie: str,
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Imprimer' onglet Prod SFR
    (cf. WinDev EtatProdStagiareScoolFibre)."""
    _require_droit(user, "FormScool")
    from app.intranets.adm.services import scool_stagiaire_pdf
    fiche = _load_fiche_or_404(id_formation, id_salarie, "SFR")
    try:
        pdf = scool_stagiaire_pdf.build_prodsfr_pdf(fiche)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return Response(
        content=pdf, media_type="application/pdf",
        headers={
            "Content-Disposition":
                f'attachment; filename="SuiviScool_SFR_{id_salarie}.pdf"',
        },
    )
