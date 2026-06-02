"""
Endpoints HTTP Call Energie - tickets.

Structure miroir de Call Fibre, mais sans la response stats globales
(dashboard du haut a definir separement).
"""

from datetime import date as _date

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.call.energie.services import tickets as svc
from app.intranets.call.energie.schemas.tickets import (
    TicketsPageResponse,
    TicketsLiveResponse,
    TicketsEnCoursResponse,
    TicketsTraitesResponse,
)

router = APIRouter()


@router.get("/tickets/en-cours", response_model=TicketsEnCoursResponse)
def get_tickets_en_cours(user: UserToken = Depends(get_current_user)):
    """Tableau du haut UNIQUEMENT : tickets a traiter + serveur_now + last_modif."""
    return svc.load_page_en_cours(user_id=user.id_salarie, user_id_poste=0)


@router.get("/tickets/traites", response_model=TicketsTraitesResponse)
def get_tickets_traites(
    user: UserToken = Depends(get_current_user),
    jour: str | None = Query(None, description="YYYY-MM-DD. Defaut = today."),
):
    """Tableau du bas (tickets traites du jour)."""
    return svc.load_page_traites(jour=jour)


@router.get("/tickets", response_model=TicketsPageResponse)
def get_tickets_page(
    user: UserToken = Depends(get_current_user),
    jour: str | None = Query(None, description="YYYY-MM-DD. Defaut = today."),
):
    """[COMPAT] Charge tout en 1 appel."""
    return svc.load_page(user_id=user.id_salarie, user_id_poste=0, jour=jour)


@router.post("/tickets/traites/export")
def export_tickets_traites(
    user: UserToken = Depends(get_current_user),
    jour: str | None = Query(None, description="YYYY-MM-DD. Defaut = today."),
    payload: dict = Body(default_factory=dict),
):
    """Export Excel du tableau des tickets traites du jour (couleurs preservees)."""
    rows = payload.get("tickets") if isinstance(payload, dict) else None
    xlsx_bytes = svc.export_traites_xlsx(jour=jour, traites=rows)
    j = (jour or _date.today().isoformat()).replace("-", "")
    filename = f"tickets_call_energie_{j}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/tickets/live", response_model=TicketsLiveResponse)
def get_tickets_live(
    user: UserToken = Depends(get_current_user),
    since: str = Query("", description="last_modif precedent. Vide = chargement initial."),
    timeout: int = Query(25, ge=1, le=55, description="Long polling timeout (s)."),
):
    """Long polling : renvoie les en-cours quand un changement est detecte."""
    changed, latest = svc.wait_for_change(since, timeout_seconds=timeout)
    if not changed:
        return {"changed": False, "page": None, "last_modif": latest}

    page = svc.load_page_en_cours(user_id=user.id_salarie, user_id_poste=0)
    return {"changed": True, "page": page, "last_modif": page["last_modif"]}
