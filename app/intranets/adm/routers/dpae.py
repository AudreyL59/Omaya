"""
Router Fen_DPAE_* (ADM, section Salaries -> Nouvelle DPAE).

Endpoints :
- POST /adm/dpae/recherche                : btn Loupe Fen_DPAE_Recherche
- GET  /adm/dpae/lookups                  : combos (societes/mutuelles/...)
- GET  /adm/dpae/preremplir               : pre-remplissage selon type_dpae
- POST /adm/dpae/enregistrer              : Btn Enregistrer Plan 1
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import dpae_nouvelle as svc_n
from app.intranets.adm.services import dpae_recherche as svc


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
    type_dpae: int = 0
    id_elem: int = 0
    id_cv_suivi: int = 0
    id_ticket: int = 0
    id_cvtheque: int = 0

    civilite: int = 0
    sexe: str = ""
    nom: str = ""
    nom_marital: str = ""
    prenom: str = ""
    nationalite: str = "Française"
    date_naiss: str = ""
    lieu_naiss: str = ""
    dep_naiss: int = 0
    num_ss: str = ""
    cpam: str = ""
    num_cin: str = ""
    situation_fam: int = 0
    avec_enfant: bool = False
    nb_enfants: int = 0
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

    idorganigramme: int = 0
    id_ste: int = 0
    id_type_poste: int = 0
    id_type_ctt: int = 1
    id_type_horaire: int = 1
    date_debut: str = ""

    coopte: bool = False
    coopteur: int = 0
    jodirecte: bool = False
    jo_coopteur: int = 0

    id_mutuelle: int = 0
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
