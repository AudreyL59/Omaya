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
from fastapi.responses import Response
from pydantic import BaseModel

from app.intranets.adm.schemas.fiche_salaires import (
    ChargerPdfResult, EnvoyerFdpParams, EnvoyerFdpResult,
    GenererPdfPrepaieParams, GenererPdfPrepaieResult,
    ParseXlsxResult, ReimportXlsxResult, SauvegardeXlsxResult,
    ValiderParams, ValiderResult, VendeurRow,
)
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


# --------------------------------------------------------------------
# Plan 1 : Valider + Sauvegarde / Reimport XLSX
# --------------------------------------------------------------------

@router.post("/valider", response_model=ValiderResult)
def post_valider(
    params: ValiderParams,
    user: UserToken = Depends(get_current_user),
):
    """Btn Valider - decoupe PDF + upload FTP + recuperation base."""
    _require_droit(user, "FichePaies")
    return svc.valider(params)


class SauvegardePayload(BaseModel):
    vendeurs: list[VendeurRow]
    pdf_b64: str = ""


@router.post("/sauvegarder-xlsx")
def post_sauvegarder_xlsx(
    payload: SauvegardePayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn Sauve EXCEL : exporte la table en XLSX (reprise ulterieure).
    Le PDF source (pdf_b64) est embarque dans une 2e feuille 'PDF' pour
    permettre la restauration complete au reimport.
    Retour : { xlsx_b64, fic_name } (base64 pour telechargement direct).
    """
    _require_droit(user, "FichePaies")
    r = svc.sauvegarder_xlsx(payload.vendeurs, payload.pdf_b64)
    return r


@router.post("/reimporter-xlsx", response_model=ReimportXlsxResult)
async def post_reimporter_xlsx(
    fichier: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    """Btn Reimporter Sauve XLS."""
    _require_droit(user, "FichePaies")
    content = await fichier.read()
    if not content:
        raise HTTPException(status_code=400, detail="XLSX vide")
    return svc.reimporter_xlsx(content)


# --------------------------------------------------------------------
# Plan 2 : Prepaie Excel
# --------------------------------------------------------------------

@router.post("/prepaie/parse-xlsx", response_model=ParseXlsxResult)
async def post_parse_xlsx_prepaie(
    fichier: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    """Btn Ouvrir un tableau prepaies : parse le XLSX en matrice."""
    _require_droit(user, "FichePaies")
    content = await fichier.read()
    if not content:
        raise HTTPException(status_code=400, detail="XLSX vide")
    return svc.parse_xlsx(content)


@router.post(
    "/prepaie/generer-pdf",
    response_model=GenererPdfPrepaieResult,
)
def post_generer_pdf_prepaie(
    params: GenererPdfPrepaieParams,
    user: UserToken = Depends(get_current_user),
):
    """Btn Enregistrer la selection en PDF.

    Genere un PDF de la plage selectionnee + upload FTP.
    """
    _require_droit(user, "FichePaies")
    return svc.generer_pdf_prepaie(params)


@router.post("/envoyer-fdp", response_model=EnvoyerFdpResult)
def post_envoyer_fdp(
    params: EnvoyerFdpParams,
    user: UserToken = Depends(get_current_user),
):
    """Btn Valider et envoyer les FDP.

    Pour chaque vendeur avec Choix=True et mail valide :
    - Recupere les PDF FTP (FS + base + prepaie)
    - Cree un ZIP AES-256 protege par le mot de passe du salarie
    - Envoie email via SMTP salaire@omaya.fr avec ZIP en PJ
    """
    _require_droit(user, "FichePaies")
    return svc.envoyer_fdp(params)
