"""Router Fen_ChoixImports (ADM Imports Bases -> Import contrats).

Endpoints :
  GET /imports/partenaires      -> combo partenaires (Fen_ChoixImports)
  GET /imports/auto-suivi       -> tableau de progression (polling)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import imports as svc
from app.intranets.adm.services import import_eni as eni_svc


router = APIRouter(prefix="/imports", tags=["adm-imports"])


@router.get("/partenaires", response_model=list[svc.PartenaireImport])
def get_partenaires(_user: UserToken = Depends(get_current_user)):
    return svc.list_partenaires()


@router.get("/auto-suivi", response_model=list[svc.ImportAutoSuivi])
def get_auto_suivi(_user: UserToken = Depends(get_current_user)):
    return svc.list_imports_auto_suivi()


# -- Fen_ImportENI : import partenaire PLENITUDE -----------------------------


@router.post("/eni/run", response_model=eni_svc.ImportEniResult)
async def post_eni_run(
    type_import: int = Form(...),
    simulation: bool = Form(True),
    periode1_du: str = Form(""),
    periode1_au: str = Form(""),
    periode1_mois_paiement: str = Form(""),
    periode2_du: str = Form(""),
    periode2_au: str = Form(""),
    periode2_mois_paiement: str = Form(""),
    mois_paiement_distrib: str = Form(""),
    maj_produit_contrat_stand: bool = Form(True),
    maj_etats_contrats_existants: bool = Form(False),
    file: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    content = await file.read()
    return eni_svc.run_import(
        eni_svc.ImportEniParams(
            type_import=type_import, simulation=simulation,
            periode1_du=periode1_du, periode1_au=periode1_au,
            periode1_mois_paiement=periode1_mois_paiement,
            periode2_du=periode2_du, periode2_au=periode2_au,
            periode2_mois_paiement=periode2_mois_paiement,
            mois_paiement_distrib=mois_paiement_distrib,
            maj_produit_contrat_stand=maj_produit_contrat_stand,
            maj_etats_contrats_existants=maj_etats_contrats_existants,
        ),
        content, user.id_salarie,
    )
