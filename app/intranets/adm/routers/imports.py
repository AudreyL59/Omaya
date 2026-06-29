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
from app.intranets.adm.services import import_str as str_svc
from app.intranets.adm.services import import_val as val_svc
from app.intranets.adm.services import import_masse as masse_svc


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


# -- Fen_ImportMasse : 5 onglets (Etat, Produit, Options SFR, Infos, Vendeur) ---


@router.get("/masse/partenaires", response_model=list[dict])
def get_masse_partenaires(_user: UserToken = Depends(get_current_user)):
    return masse_svc.list_partenaires()


@router.get("/masse/etats/{partenaire}", response_model=list[dict])
def get_masse_etats(partenaire: str, _user: UserToken = Depends(get_current_user)):
    return masse_svc.list_etats(partenaire)


@router.get("/masse/produits/{partenaire}", response_model=list[dict])
def get_masse_produits(partenaire: str, _user: UserToken = Depends(get_current_user)):
    return masse_svc.list_produits(partenaire)


@router.post("/masse/etat", response_model=masse_svc.MasseResult)
async def post_masse_etat(
    partenaire: str = Form(...),
    id_etat_new: int = Form(...),
    mois_paiement: str = Form(""),
    col_num: str = Form("A"),
    simulation: bool = Form(True),
    modif_deja_statues: bool = Form(False),
    modif_uniquement_attente: bool = Form(True),
    recoche_energies: bool = Form(False),
    mode: str = Form("vendeur"),
    file: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    return masse_svc.run_modif_etat(
        masse_svc.MasseEtatParams(
            partenaire=partenaire, id_etat_new=id_etat_new,
            mois_paiement=mois_paiement, col_num=col_num,
            simulation=simulation, modif_deja_statues=modif_deja_statues,
            modif_uniquement_attente=modif_uniquement_attente,
            recoche_energies=recoche_energies, mode=mode,
        ),
        await file.read(), user.id_salarie,
    )


@router.post("/masse/produit", response_model=masse_svc.MasseResult)
async def post_masse_produit(
    partenaire: str = Form(...), id_produit_new: int = Form(...),
    col_num: str = Form("A"), simulation: bool = Form(True),
    file: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    return masse_svc.run_modif_produit(
        masse_svc.MasseProduitParams(
            partenaire=partenaire, id_produit_new=id_produit_new,
            col_num=col_num, simulation=simulation,
        ),
        await file.read(), user.id_salarie,
    )


@router.post("/masse/option-sfr", response_model=masse_svc.MasseResult)
async def post_masse_option_sfr(
    hors_cluster: bool = Form(...),
    col_num: str = Form("A"), simulation: bool = Form(True),
    file: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    return masse_svc.run_modif_option_sfr(
        masse_svc.MasseOptionSfrParams(
            hors_cluster=hors_cluster, col_num=col_num, simulation=simulation,
        ),
        await file.read(), user.id_salarie,
    )


@router.post("/masse/info-interne", response_model=masse_svc.MasseResult)
async def post_masse_info_interne(
    partenaire: str = Form(...),
    col_num: str = Form("A"), col_comment: str = Form("B"),
    simulation: bool = Form(True),
    file: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    return masse_svc.run_ajout_info_interne(
        masse_svc.MasseInfoParams(
            partenaire=partenaire, col_num=col_num, col_comment=col_comment,
            simulation=simulation,
        ),
        await file.read(), user.id_salarie,
    )


@router.post("/masse/vendeur", response_model=masse_svc.MasseResult)
async def post_masse_vendeur(
    partenaire: str = Form(...), id_salarie_new: int = Form(...),
    col_num: str = Form("A"), simulation: bool = Form(True),
    file: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    return masse_svc.run_modif_vendeur(
        masse_svc.MasseVendeurParams(
            partenaire=partenaire, id_salarie_new=id_salarie_new,
            col_num=col_num, simulation=simulation,
        ),
        await file.read(), user.id_salarie,
    )


# -- Fen_ImportVAL : 3 types (BJ + RUN + Resil Hebdo), multi-fichier --------


@router.post("/val/run", response_model=val_svc.ImportValResult)
async def post_val_run(
    type_import: int = Form(...),
    simulation: bool = Form(True),
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
    return val_svc.run_import_val(
        val_svc.ImportValParams(
            type_import=type_import, simulation=simulation,
            periode1_du=periode1_du, periode1_au=periode1_au,
            periode1_mois_paiement=periode1_mois_paiement,
            periode2_du=periode2_du, periode2_au=periode2_au,
            periode2_mois_paiement=periode2_mois_paiement,
            mois_paiement_distrib=mois_paiement_distrib,
        ),
        contents, user.id_salarie,
    )


# -- Fen_ImportSTR : 3 types (BJ + RUN + Resil Hebdo), multi-fichier --------


@router.post("/str/run", response_model=str_svc.ImportStrResult)
async def post_str_run(
    type_import: int = Form(...),
    simulation: bool = Form(True),
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
    return str_svc.run_import_str(
        str_svc.ImportStrParams(
            type_import=type_import, simulation=simulation,
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
