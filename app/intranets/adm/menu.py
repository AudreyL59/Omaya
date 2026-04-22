"""
Configuration du menu Intranet ADM.

Retourne la liste des éléments de menu visibles selon les droits de l'utilisateur.
À compléter au fur et à mesure de l'ajout des pages.
"""

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter()


def _verif_droit(user: UserToken, code: str) -> bool:
    return code in user.droits


@router.get("/menu")
def get_menu(user: UserToken = Depends(get_current_user)):
    """
    Retourne la configuration du menu pour l'utilisateur connecté.

    Chaque élément contient :
    - key : identifiant technique
    - label : libellé affiché
    - route : route frontend (relative au basename /adm)
    - visible : si le bouton est visible
    """
    # TODO : brancher les codes de droit WinDev corrects pour chaque page
    items: list[dict] = [
        {
            "key": "agenda_recrutement",
            "label": "Agenda Recrutement",
            "route": "/agenda-recrutement",
            "visible": True,  # TODO : _verif_droit(user, "?")
        },
        {
            "key": "envois_sms",
            "label": "Envois de SMS",
            "route": "/envois-sms",
            "visible": True,  # TODO : _verif_droit(user, "?")
        },
        {
            "key": "factures",
            "label": "Factures",
            "route": "/factures",
            "visible": True,  # TODO : _verif_droit(user, "?")
        },
        {
            "key": "recherche_rh",
            "label": "Recherche RH",
            "route": "/recherche-rh",
            "visible": True,  # TODO : _verif_droit(user, "?")
        },
        {
            "key": "stat_rh",
            "label": "Stat RH",
            "route": "/stat-rh",
            "visible": _verif_droit(user, "AdmStatRH"),
        },
        {
            "key": "stat_adv",
            "label": "Stat ADV",
            "route": "/stat-adv",
            "visible": True,  # TODO : _verif_droit(user, "?")
        },
    ]

    return {
        "menu_visible": True,
        "items": items,
    }
