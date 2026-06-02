"""
Endpoints HTTP Call Fibre - tickets.

Phase 1 (ce commit) : GET de chargement de la page (tableaux haut/bas + stats).
Phases suivantes :
- POST /tickets/{id}/prendre, /liberer (verrou opé)
- GET  /tickets/live (long polling pour push)
"""

from fastapi import APIRouter, Depends, Query

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.call.fibre.services import tickets as svc
from app.intranets.call.fibre.schemas.tickets import TicketsPageResponse, TicketsLiveResponse

router = APIRouter()


@router.get("/tickets", response_model=TicketsPageResponse)
def get_tickets_page(
    user: UserToken = Depends(get_current_user),
    jour: str | None = Query(
        None,
        description="Date du jour pour le tableau du bas (YYYY-MM-DD). Defaut = today.",
    ),
):
    """Charge tout ce qu'il faut pour la page principale Call Fibre.

    Inclut :
    - tickets_en_cours (tableau du haut, a traiter)
    - tickets_traites (tableau du bas, jour donne ou today)
    - stats (4 compteurs + stats par agence interne/externe)
    - last_modif : token a renvoyer dans /tickets/live?since=...
    """
    return svc.load_page(
        user_id=user.id_salarie,
        user_id_poste=user.id_type_poste or 0,
        jour=jour,
    )


@router.get("/tickets/live", response_model=TicketsLiveResponse)
def get_tickets_live(
    user: UserToken = Depends(get_current_user),
    since: str = Query(
        "",
        description="last_modif obtenu precedemment. Vide = chargement initial.",
    ),
    jour: str | None = Query(
        None,
        description="Date du tableau du bas (YYYY-MM-DD). Defaut = today.",
    ),
    timeout: int = Query(
        25,
        ge=1, le=55,
        description="Timeout du long polling en secondes (max 55).",
    ),
):
    """Long polling : attend qu'un ticket bouge puis renvoie la page complete.

    Cote client :
    1. Premier appel sans `since` -> renvoie immediatement la page + last_modif
    2. Appels suivants avec `since=<last_modif precedent>` -> attend max `timeout`s
       qu'un changement survienne :
       - Si oui : changed=True, page rempli, last_modif mis a jour
       - Si non (timeout) : changed=False, last_modif inchange. Le client peut
         relancer immediatement.

    Note IIS : le timeout par defaut est 25s pour rester confortablement sous
    la limite ARR (2 min). Si tu changes le timeout, verifie aussi la config
    ARR (proxy timeout).
    """
    changed, latest = svc.wait_for_change(since, timeout_seconds=timeout)
    if not changed:
        return {"changed": False, "page": None, "last_modif": latest}

    page = svc.load_page(
        user_id=user.id_salarie,
        user_id_poste=user.id_type_poste or 0,
        jour=jour,
    )
    return {"changed": True, "page": page, "last_modif": page["last_modif"]}
