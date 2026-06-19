"""
Router Fen_DPAE_* (ADM, section Salaries -> Nouvelle DPAE).

Endpoints :
- POST /adm/dpae/recherche                : btn Loupe Fen_DPAE_Recherche
- GET  /adm/dpae/lookups                  : combos (societes/mutuelles/...)
- GET  /adm/dpae/preremplir               : pre-remplissage selon type_dpae
- POST /adm/dpae/enregistrer              : Btn Enregistrer Plan 1
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, BeforeValidator

from app.intranets.adm.services import fiche_documents as docs_svc

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import dpae_nouvelle as svc_n
from app.intranets.adm.services import dpae_recherche as svc


# Le frontend envoie les IDs 8 octets en string (preservation precision JS).
# String vide '' / None -> 0, sinon coerce en int.
def _coerce_int(v: Any) -> int:
    if v is None or v == "":
        return 0
    return int(v)


IdField = Annotated[int, BeforeValidator(_coerce_int)]


router = APIRouter(prefix="/dpae", tags=["adm-dpae"])


class DpaeRechercheRequest(BaseModel):
    nom: str = ""
    prenom: str = ""
    gsm: str = ""


@router.post("/recherche")
def post_recherche(
    req: DpaeRechercheRequest,
    _user: UserToken = Depends(get_current_user),
):
    """Btn Loupe Fen_DPAE_Recherche : combine cvtheque + registre RH."""
    return svc.search(req.nom, req.prenom, req.gsm)


# ---------------------------------------------------------------------------
# Fen_DPAE_Nouvelle
# ---------------------------------------------------------------------------


@router.get("/lookups")
def get_lookups(_user: UserToken = Depends(get_current_user)):
    """Combos statiques de Fen_DPAE_Nouvelle (societes, mutuelles,
    types poste/ctt/horaire)."""
    return {
        "societes": svc_n.list_societes(),
        "mutuelles": svc_n.list_mutuelles(),
        "postes": svc_n.list_postes(),
        "types_ctt": svc_n.list_types_ctt(),
        "types_horaire": svc_n.list_types_horaire(),
    }


@router.get("/preremplir")
def get_preremplir(
    type_dpae: int = 0,
    id_elem: int = 0,
    id_cv_suivi: int = 0,
    id_ticket: int = 0,
    _user: UserToken = Depends(get_current_user),
):
    """Pre-remplissage des champs selon le mode d'ouverture
    (cf. WinDev RecupInfoFicheCV / RecupInfoFicheSa / RecupInfoTkDpae)."""
    return svc_n.load_preremplissage(
        type_dpae, id_elem, id_cv_suivi, id_ticket,
    )


class DpaeSavePayload(BaseModel):
    # IDs 8 octets : envoyes en string par le frontend (precision JS).
    # IdField coerce '' / None -> 0.
    type_dpae: IdField = 0
    id_elem: IdField = 0
    id_cv_suivi: IdField = 0
    id_ticket: IdField = 0
    id_cvtheque: IdField = 0
    idorganigramme: IdField = 0
    id_ste: IdField = 0
    coopteur: IdField = 0
    jo_coopteur: IdField = 0

    civilite: IdField = 0
    sexe: str = ""
    nom: str = ""
    nom_marital: str = ""
    prenom: str = ""
    nationalite: str = "Française"
    date_naiss: str = ""
    lieu_naiss: str = ""
    dep_naiss: IdField = 0
    num_ss: str = ""
    cpam: str = ""
    num_cin: str = ""
    situation_fam: IdField = 0
    avec_enfant: bool = False
    nb_enfants: IdField = 0
    travailleur_handi: bool = False

    adresse1: str = ""
    adresse2: str = ""
    cp: str = ""
    ville: str = ""
    tel_mob: str = ""
    tel_fixe: str = ""
    mail: str = ""
    urg_nom: str = ""
    urg_lien: str = ""
    urg_tel: str = ""
    iban: str = ""
    bic: str = ""

    id_type_poste: IdField = 0
    id_type_ctt: IdField = 1
    id_type_horaire: IdField = 1
    date_debut: str = ""

    coopte: bool = False
    jodirecte: bool = False

    id_mutuelle: IdField = 0
    adhesion: bool = False
    adhesion_date: str = ""
    mutuelle_dossier: bool = False
    mutuelle_att_ss: bool = False
    mutuelle_rib: bool = False


@router.post("/enregistrer")
def post_enregistrer(
    payload: DpaeSavePayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn Enregistrer Plan 1 : cree salarie + coord + embauche + sortie
    vide + mutuelle + organigramme + droits."""
    try:
        return svc_n.save_dpae(payload.model_dump(), user.id_salarie)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Plan 2 - Codes partenaires
# ---------------------------------------------------------------------------


@router.get("/partenaires-portail")
def get_partenaires_portail(_user: UserToken = Depends(get_current_user)):
    """Combo Partenaire du Plan 2."""
    return svc_n.list_partenaires_portail()


@router.get("/partenaire-portail/{id_partenaire}")
def get_portail(
    id_partenaire: int,
    _user: UserToken = Depends(get_current_user),
):
    """Credentials du portail pour ce partenaire."""
    return svc_n.get_portail_credentials(id_partenaire)


@router.get("/societe-salarie/{id_salarie}")
def get_societe_salarie(
    id_salarie: int,
    _user: UserToken = Depends(get_current_user),
):
    """Societe d'embauche du salarie (raison sociale + SIRET pour URSSAF)."""
    return svc_n.get_societe_salarie(id_salarie)


@router.get("/codes/{id_salarie}")
def get_codes_salarie(
    id_salarie: int,
    _user: UserToken = Depends(get_current_user),
):
    """ZR_ElemsFaits : partenaires deja codes pour ce salarie."""
    return svc_n.list_codes_salarie(id_salarie)


@router.get("/dpae-state/{id_salarie}")
def get_dpae_state(
    id_salarie: int,
    _user: UserToken = Depends(get_current_user),
):
    """Etat URSSAF du salarie (dpae_num + dpae_date)."""
    return svc_n.get_dpae_state(id_salarie)


class UrssafPayload(BaseModel):
    dpae_num: str


@router.post("/urssaf/{id_salarie}")
def post_urssaf(
    id_salarie: int,
    payload: UrssafPayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Valider les infos URSSAF'."""
    return svc_n.update_dpae_urssaf(id_salarie, payload.dpae_num, user.id_salarie)


@router.post("/urssaf/{id_salarie}/pdf")
async def post_urssaf_pdf(
    id_salarie: int,
    file: UploadFile = File(...),
    target_filename: str = Form(""),
    _user: UserToken = Depends(get_current_user),
):
    """Upload du PDF DPAE dans le dossier salarie (FTP gestionRH/{id}/).
    Cf. WinDev btn 'Valider URSSAF' qui propose d'ajouter la DPAE en PDF
    apres validation.

    target_filename : nom voulu (ex: 'DPAE_12345.pdf'). Si absent, garde
    le nom original."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide")
    name = target_filename.strip() or file.filename or "DPAE.pdf"
    res = docs_svc.upload_file(id_salarie, "internes", name, content)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("error") or "Echec upload")
    return res


class CodesPayload(BaseModel):
    id_partenaire: int
    code: str = ""
    login: str = ""
    mdp: str = ""


@router.post("/codes/{id_salarie}")
def post_codes(
    id_salarie: int,
    payload: CodesPayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Valider les codes Partenaires'."""
    return svc_n.save_codes_partenaire(
        id_salarie, payload.id_partenaire,
        payload.code, payload.login, payload.mdp,
        user.id_salarie,
    )


class CharteEthiquePayload(BaseModel):
    id_partenaire: int


@router.post("/charte-ethique/{id_salarie}")
def post_charte_ethique(
    id_salarie: int,
    payload: CharteEthiquePayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Envoyer la charte Ethique' : cree TK_DemandeCodeVendeur + TK_Liste."""
    return svc_n.envoyer_charte_ethique(id_salarie, payload.id_partenaire, user.id_salarie)


class TerminerPayload(BaseModel):
    id_ticket: int = 0


@router.post("/terminer/{id_salarie}")
def post_terminer(
    id_salarie: int,
    payload: TerminerPayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Terminer ma DPAE' : (re)applique droits + cloture ticket."""
    return svc_n.terminer_dpae(id_salarie, payload.id_ticket, user.id_salarie)


class InfosPartenairePayload(BaseModel):
    id_partenaire: IdField = 0
    lib_partenaire: str
    code: str = ""
    login: str = ""
    mdp: str = ""
    dpae_num: str = ""
    pdf_filename: str = ""


@router.post("/envoyer-infos/{id_salarie}")
def post_envoyer_infos(
    id_salarie: int,
    payload: InfosPartenairePayload,
    user: UserToken = Depends(get_current_user),
):
    """envoieInfoPartenaire WinDev : SMS au candidat + mail HTML
    (avec PDF DPAE en PJ si pdf_filename fourni pour URSSAF)."""
    return svc_n.envoyer_infos_partenaire(
        id_salarie, payload.id_partenaire, payload.lib_partenaire,
        payload.code, payload.login, payload.mdp, payload.dpae_num,
        op_id=user.id_salarie, pdf_filename=payload.pdf_filename,
    )
