"""
Configuration du menu Intranet Vendeur.

Transposition de initMenu() WinDev.
Retourne la liste des éléments de menu visibles selon les droits de l'utilisateur.
"""

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter()


def _verif_droit(user: UserToken, code: str) -> bool:
    return code in user.droits


def _has_any_ticket_droit(user: UserToken, is_vendeur_distrib: bool) -> bool:
    """Vérifie si l'utilisateur a accès à au moins un type de ticket."""
    if _verif_droit(user, "TkDPAE"):
        return True
    if _verif_droit(user, "TkDpaeDist"):
        return True
    if _verif_droit(user, "TkAVANCE"):
        return True
    if _verif_droit(user, "TkDemEC"):
        return True
    if _verif_droit(user, "TkRESA"):
        return True
    if _verif_droit(user, "BS_SFR"):
        return True
    return False


@router.get("/menu")
def get_menu(user: UserToken = Depends(get_current_user)):
    """
    Retourne la configuration du menu pour l'utilisateur connecté.

    Chaque élément contient :
    - key : identifiant technique
    - label : libellé affiché
    - route : route frontend
    - visible : si le bouton est visible
    """
    if not user.is_actif:
        # Utilisateur inactif : uniquement Mon Compte, pas de menu
        return {
            "menu_visible": False,
            "items": [
                {"key": "mon_compte", "label": "Mon Compte", "route": "/vendeur/mon-compte", "visible": True},
            ],
        }

    is_callrh = user.prof_poste == "CALLRH"
    # TODO: récupérer VendeurDistrib et formateurScool depuis InfoUser
    # Pour l'instant on les met à False, à brancher quand on aura la procédure
    is_vendeur_distrib = False
    is_formateur_scool = False

    items = [
        {
            "key": "mon_compte",
            "label": "Mon Compte",
            "route": "/vendeur/mon-compte",
            "visible": True,
        },
        {
            "key": "cooptation",
            "label": "Cooptation",
            "route": "/vendeur/cooptation",
            "visible": not is_callrh,
        },
        {
            "key": "agenda_recrutement",
            "label": "Agenda Recrutement",
            "route": "/vendeur/agenda-recrutement",
            "visible": user.agenda_actif,
        },
        {
            "key": "agenda_cial",
            "label": "Agenda Commercial",
            "route": "/vendeur/agenda-cial",
            "visible": _verif_droit(user, "AgendaCial"),
        },
        {
            "key": "cvtheque",
            "label": "CVthèque",
            "route": "/vendeur/cvtheque",
            "visible": _verif_droit(user, "CVTHEQUE"),
        },
        {
            "key": "organigramme",
            "label": "Organigramme",
            "route": "/vendeur/organigramme",
            "visible": _verif_droit(user, "ORGA"),
        },
        {
            "key": "gestion_ohm",
            "label": "Gestion Code OHM",
            "route": "/vendeur/gestion-ohm",
            "visible": _verif_droit(user, "GestCodeOhm"),
        },
        {
            "key": "scool",
            "label": "Suivi Scool",
            "route": "/vendeur/scool",
            "visible": is_formateur_scool or _verif_droit(user, "SuiviScool"),
        },
        {
            "key": "production",
            "label": "Production",
            "route": "/vendeur/production",
            "visible": is_vendeur_distrib and not user.is_pause and not is_callrh,
        },
        {
            "key": "clusters",
            "label": "Clusters",
            "route": "/vendeur/clusters",
            "visible": _verif_droit(user, "ClustSFR_Liste"),
        },
        {
            "key": "tickets",
            "label": "Tickets",
            "route": "/vendeur/tickets",
            "visible": _has_any_ticket_droit(user, is_vendeur_distrib),
        },
        {
            "key": "process",
            "label": "Process",
            "route": "/vendeur/process",
            "visible": _verif_droit(user, "Process"),
        },
        {
            "key": "tickets_call_suivi",
            "label": "Tickets Call Suivi",
            "route": "/vendeur/tickets-call",
            "visible": _verif_droit(user, "TicketCall"),
        },
        {
            "key": "tickets_call_energie",
            "label": "Ticket Énergie",
            "route": "/vendeur/tickets-call/energie",
            "visible": _verif_droit(user, "TkCALL"),
        },
        {
            "key": "tickets_call_fibre",
            "label": "Ticket Fibre",
            "route": "/vendeur/tickets-call/fibre",
            "visible": _verif_droit(user, "BS_SFR"),
        },
        {
            "key": "dialogues",
            "label": "Dialogues",
            "route": "/vendeur/dialogues",
            "visible": _verif_droit(user, "IntraConvDR"),
        },
    ]

    return {
        "menu_visible": True,
        "items": items,
    }
