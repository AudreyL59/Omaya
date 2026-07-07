"""
Router Fen_FicheSalaires - Envoi fiches de salaire.

Endpoints commit 1 :
  GET  /paies/fiches/societes-fdv    - Combo societes FDV interne
  POST /paies/fiches/charger-pdf     - Btn Charger le fichier PDF (upload + extraction)
  GET  /paies/fiches/recherche-salarie?q=  - Recherche libre (ligne rouge)
"""

from fastapi import (
    APIRouter, Depends, File, HTTPException, Query, UploadFile,
)

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.fiche_salaires import ChargerPdfResult
from app.intranets.adm.services import fiche_salaires as svc

router = APIRouter(
    prefix="/paies/fiches",
    tags=["adm-paies-fiches"],
)


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


@router.get("/societes-fdv")
def get_societes_fdv(user: UserToken = Depends(get_current_user)):
    """Combo Societes FDV Interne (id_type_orga=1 + is_actif)."""
    _require_droit(user, "FichePaies")
    return {"items": svc.list_societes_fdv()}


@router.post("/charger-pdf", response_model=ChargerPdfResult)
async def post_charger_pdf(
    fichier: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    """Btn Charger le fichier PDF.

    Extraction pattern natif ##BULLETIN## dans chaque page + matching
    salaries via pgt_salarie.
    """
    _require_droit(user, "FichePaies")
    content = await fichier.read()
    if not content:
        raise HTTPException(status_code=400, detail="PDF vide")
    return svc.charger_pdf(content)


@router.get("/recherche-salarie")
def get_recherche_salarie(
    q: str = Query(..., min_length=2),
    user: UserToken = Depends(get_current_user),
):
    """Recherche libre nom/prenom (attribution manuelle des lignes rouges).
    Cf. WinDev Fen_RechercheNomSalarie.
    """
    _require_droit(user, "FichePaies")
    return {"items": svc.rechercher_salaries(q)}
