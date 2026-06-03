"""
Endpoints HTTP Call Fibre - tickets.

Stratégie de chargement de la page principale (transposition WinDev) :
1. Frontend appelle `/tickets/en-cours` -> rapide, affiche tableau du haut
2. En parallele, frontend appelle `/tickets/traites?jour=...` -> tableau du bas + stats
3. Long polling `/tickets/live?since=...` pour pousser les changements live
   sur le tableau du haut (en cours uniquement).
"""

from datetime import date as _date

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.call.fibre.services import tickets as svc
from app.intranets.call.fibre.services import fiche as fiche_svc
from app.intranets.call.fibre.schemas.tickets import (
    TicketsPageResponse,
    TicketsLiveResponse,
    TicketsEnCoursResponse,
    TicketsTraitesResponse,
)
from app.intranets.call.fibre.schemas.fiche import (
    FicheTicketFibreResponse,
    FicheTestEligibiliteResponse,
)

router = APIRouter()


@router.get("/tickets/en-cours", response_model=TicketsEnCoursResponse)
def get_tickets_en_cours(user: UserToken = Depends(get_current_user)):
    """Tableau du haut UNIQUEMENT : tickets a traiter + serveur_now + last_modif.

    Rapide (~5 queries) -> a appeler en premier pour afficher la page.
    """
    return svc.load_page_en_cours(user_id=user.id_salarie, user_id_poste=0)


@router.get("/tickets/traites", response_model=TicketsTraitesResponse)
def get_tickets_traites(
    user: UserToken = Depends(get_current_user),
    jour: str | None = Query(None, description="YYYY-MM-DD. Defaut = today."),
):
    """Tableau du bas + stats. A appeler en arriere-plan apres /en-cours.

    Plus lent (~10 queries : panier, offres, agences).
    """
    return svc.load_page_traites(jour=jour)


@router.get("/tickets", response_model=TicketsPageResponse)
def get_tickets_page(
    user: UserToken = Depends(get_current_user),
    jour: str | None = Query(None, description="YYYY-MM-DD. Defaut = today."),
):
    """[COMPAT] Charge tout en 1 appel. Prefer /tickets/en-cours + /traites."""
    return svc.load_page(user_id=user.id_salarie, user_id_poste=0, jour=jour)


@router.post("/tickets/traites/export")
def export_tickets_traites(
    user: UserToken = Depends(get_current_user),
    jour: str | None = Query(None, description="YYYY-MM-DD. Defaut = today."),
    payload: dict = Body(default_factory=dict),
):
    """Export Excel du tableau des tickets traites du jour.

    POST : le frontend envoie les rows deja chargees dans `payload.tickets`,
    on saute la requete HFSQL pour generer le xlsx en ~50ms.
    Si le payload est vide, on rappelle list_tickets_traites() (fallback lent).

    Couleurs de lignes preservees (rouge / gris / vert / blanc).
    """
    rows = payload.get("tickets") if isinstance(payload, dict) else None
    xlsx_bytes = svc.export_traites_xlsx(jour=jour, traites=rows)
    j = (jour or _date.today().isoformat()).replace("-", "")
    filename = f"tickets_call_fibre_{j}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/tickets/{id_ticket}/fiche", response_model=FicheTicketFibreResponse)
def get_fiche_ticket(
    id_ticket: str,
    user: UserToken = Depends(get_current_user),
):
    """Charge la fiche complete d'un ticket Call Fibre (popup).

    Phase 1 = lecture seule. Mobile masque si l'ope n'est pas celui qui a
    pris l'appel (= n'a pas pose le verrou).
    """
    return fiche_svc.load_fiche(
        id_tk_liste=int(id_ticket),
        current_user_id=user.id_salarie or 0,
    )


@router.get("/tickets/panier/{id_panier}/test-eligibilite", response_model=FicheTestEligibiliteResponse)
def get_panier_test_eligibilite(
    id_panier: str,
    user: UserToken = Depends(get_current_user),
):
    """Charge l'image TestEligibilite pour une ligne du panier (FIBRE only)."""
    url = fiche_svc.load_panier_ligne_image(int(id_panier))
    return {"test_eligibilite": url}


@router.get("/tickets/live", response_model=TicketsLiveResponse)
def get_tickets_live(
    user: UserToken = Depends(get_current_user),
    since: str = Query("", description="last_modif precedent. Vide = chargement initial."),
    timeout: int = Query(25, ge=1, le=55, description="Long polling timeout (s)."),
):
    """Long polling : ne renvoie QUE les en-cours quand un changement est detecte.

    Le tableau du bas n'est pas concerne (re-fetcher /tickets/traites
    apres changement si necessaire).
    """
    changed, latest = svc.wait_for_change(since, timeout_seconds=timeout)
    if not changed:
        return {"changed": False, "page": None, "last_modif": latest}

    page = svc.load_page_en_cours(user_id=user.id_salarie, user_id_poste=0)
    return {"changed": True, "page": page, "last_modif": page["last_modif"]}
