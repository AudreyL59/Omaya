"""
Router Fen_RechUlease (ADM Ulease -> Recherche Vehicule / Conducteur).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import recherche_ulease as svc


router = APIRouter(prefix="/recherche-ulease", tags=["adm-rech-ulease"])


@router.get("/lookups")
def get_lookups(_user: UserToken = Depends(get_current_user)):
    """Combos : etats vehicule + marques + societes (FDV Interne)."""
    return svc.list_lookups()


@router.get("/vehicules")
def get_vehicules(
    modele: str = "",
    chevaux: str = "",
    immat: str = "",
    id_etat: int = 0,
    id_marque: int = 0,
    _user: UserToken = Depends(get_current_user),
):
    """ReqChercheVehicule."""
    return svc.search_vehicules(
        modele=modele, chevaux=chevaux, immat=immat,
        id_etat=id_etat, id_marque=id_marque,
    )


@router.get("/conducteurs")
def get_conducteurs(
    nom: str = "",
    prenom: str = "",
    num_permis: str = "",
    id_ste: int = 0,
    tel: str = "",
    mobile: str = "",
    _user: UserToken = Depends(get_current_user),
):
    """ReqChercheConducteur."""
    return svc.search_conducteurs(
        nom=nom, prenom=prenom, num_permis=num_permis,
        id_ste=id_ste, tel=tel, mobile=mobile,
    )
