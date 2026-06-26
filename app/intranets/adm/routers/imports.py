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
from app.intranets.adm.services import import_iag as iag_svc
from app.intranets.adm.services import import_oen as oen_svc
from app.intranets.adm.services import import_pro as pro_svc
from app.intranets.adm.services import import_sfr as sfr_svc


router = APIRouter(prefix="/imports", tags=["adm-imports"])


@router.get("/partenaires", response_model=list[svc.PartenaireImport])
def get_partenaires(_user: UserToken = Depends(get_current_user)):
    return svc.list_partenaires()


@router.get("/auto-suivi", response_model=list[svc.ImportAutoSuivi])
def get_auto_suivi(_user: UserToken = Depends(get_current_user)):
    return svc.list_imports_auto_suivi()


# -- Fen_ImportENI : import partenaire PLENITUDE -----------------------------


# -- Fen_ImportIAG : 2 types (BJ + RUN), multi-fichier -----------------------


@router.post("/iag/run", response_model=iag_svc.ImportIagResult)
async def post_iag_run(
    type_import: int = Form(...),
    simulation: bool = Form(True),
    format_vendeur: str = Form("prenom_nom"),
    periode1_du: str = Form(""),
    periode1_au: str = Form(""),
    periode1_mois_paiement: str = Form(""),
    periode2_du: str = Form(""),
    periode2_au: str = Form(""),
    periode2_mois_paiement: str = Form(""),
    mois_paiement_distrib: str = Form(""),
    files: list[UploadFile] = File(...),
    user: UserToken = Depends(get_current_user),
):
    contents: list[tuple[str, bytes]] = []
    for f in files:
        contents.append((f.filename or "fichier.xlsx", await f.read()))
    return iag_svc.run_import_iag(
        iag_svc.ImportIagParams(
            type_import=type_import, simulation=simulation,
            format_vendeur=format_vendeur,
            periode1_du=periode1_du, periode1_au=periode1_au,
            periode1_mois_paiement=periode1_mois_paiement,
            periode2_du=periode2_du, periode2_au=periode2_au,
            periode2_mois_paiement=periode2_mois_paiement,
            mois_paiement_distrib=mois_paiement_distrib,
        ),
        contents, user.id_salarie,
    )


# -- Fen_ImportSFR : 10 types (BJ Fibre/Mobile/CALL, Hebdo, Options, RUN, CallRET x4) --


@router.post("/sfr/run", response_model=sfr_svc.ImportSfrResult)
async def post_sfr_run(
    type_import: int = Form(...),
    simulation: bool = Form(True),
    ligne_depart: int = Form(3),
    periode1_du: str = Form(""), periode1_au: str = Form(""),
    periode1_mois_paiement: str = Form(""),
    periode2_du: str = Form(""), periode2_au: str = Form(""),
    periode2_mois_paiement: str = Form(""),
    mois_paiement_distrib: str = Form(""),
    files: list[UploadFile] = File(...),
    user: UserToken = Depends(get_current_user),
):
    contents: list[tuple[str, bytes]] = []
    for f in files:
        contents.append((f.filename or "fichier.xlsx", await f.read()))
    return sfr_svc.run_import_sfr(
        sfr_svc.ImportSfrParams(
            type_import=type_import, simulation=simulation,
            ligne_depart=ligne_depart,
            periode1_du=periode1_du, periode1_au=periode1_au,
            periode1_mois_paiement=periode1_mois_paiement,
            periode2_du=periode2_du, periode2_au=periode2_au,
            periode2_mois_paiement=periode2_mois_paiement,
            mois_paiement_distrib=mois_paiement_distrib,
        ),
        contents, user.id_salarie,
    )


# -- Fen_ImportPRO : 2 types (BJ + RUN), multi-fichier -----------------------


@router.post("/pro/run", response_model=pro_svc.ImportProResult)
async def post_pro_run(
    type_import: int = Form(...),
    simulation: bool = Form(True),
    format_vendeur: str = Form("prenom_nom"),
    periode1_du: str = Form(""), periode1_au: str = Form(""),
    periode1_mois_paiement: str = Form(""),
    periode2_du: str = Form(""), periode2_au: str = Form(""),
    periode2_mois_paiement: str = Form(""),
    mois_paiement_distrib: str = Form(""),
    files: list[UploadFile] = File(...),
    user: UserToken = Depends(get_current_user),
):
    contents: list[tuple[str, bytes]] = []
    for f in files:
        contents.append((f.filename or "fichier.xlsx", await f.read()))
    return pro_svc.run_import_pro(
        pro_svc.ImportProParams(
            type_import=type_import, simulation=simulation,
            format_vendeur=format_vendeur,
            periode1_du=periode1_du, periode1_au=periode1_au,
            periode1_mois_paiement=periode1_mois_paiement,
            periode2_du=periode2_du, periode2_au=periode2_au,
            periode2_mois_paiement=periode2_mois_paiement,
            mois_paiement_distrib=mois_paiement_distrib,
        ),
        contents, user.id_salarie,
    )


# -- Fen_ImportOEN : 4 types OHM Energie -------------------------------------


@router.post("/oen/run", response_model=oen_svc.ImportOenResult)
async def post_oen_run(
    type_import: int = Form(...),
    simulation: bool = Form(True),
    periode1_du: str = Form(""), periode1_au: str = Form(""),
    periode1_mois_paiement: str = Form(""),
    periode2_du: str = Form(""), periode2_au: str = Form(""),
    periode2_mois_paiement: str = Form(""),
    mois_paiement_distrib: str = Form(""),
    file: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    content = await file.read()
    return oen_svc.run_import_oen(
        oen_svc.ImportOenParams(
            type_import=type_import, simulation=simulation,
            periode1_du=periode1_du, periode1_au=periode1_au,
            periode1_mois_paiement=periode1_mois_paiement,
            periode2_du=periode2_du, periode2_au=periode2_au,
            periode2_mois_paiement=periode2_mois_paiement,
            mois_paiement_distrib=mois_paiement_distrib,
        ),
        content, user.id_salarie,
    )


# -- Fen_ImportENI : 4 types ENI/PLENITUDE -----------------------------------


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
