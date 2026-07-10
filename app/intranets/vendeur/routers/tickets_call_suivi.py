"""
Router Vendeur - Suivi Tickets Call (Fibre + Energie fusionnes).

Droit d'acces : TicketCall (deja cable dans le menu).
Filtrage orga :
  - Si le user a le droit 'ProdRezo' -> voit tout
  - Sinon -> voit uniquement les tickets dont le vendeur est rattache
    a son orga ou sous-orgas (cf. WinDev ListeOrgaComplet).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.vendeur.services import tickets_call_suivi as svc


router = APIRouter(
    prefix="/tickets-call/suivi",
    tags=["vendeur-tickets-call-suivi"],
)


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


@router.get("/en-cours")
def get_en_cours(user: UserToken = Depends(get_current_user)):
    """Liste unifiee des tickets Call en cours du jour (Fibre + Energie),
    filtree par orga si pas ProdRezo.
    """
    _require_droit(user, "TicketCall")
    id_user = int(user.id_salarie or 0)
    # Note : id_poste_user n'est pas expose dans UserToken. On passe 0
    # (donc pas de filtre TicketDiff pour poste 20). A affiner plus tard
    # si besoin.
    return {
        "tickets_en_cours": svc.list_en_cours_suivi(
            id_user=id_user,
            user_droits=user.droits or [],
            id_poste_user=0,
        ),
    }


@router.get("/traites")
def get_traites(
    jour: str | None = None,
    user: UserToken = Depends(get_current_user),
):
    """Liste unifiee des tickets Call traites (Fibre + Energie) pour un
    jour donne (default = today), filtree par orga si pas ProdRezo.

    jour : 'YYYY-MM-DD' ou 'YYYYMMDD'.
    """
    _require_droit(user, "TicketCall")
    id_user = int(user.id_salarie or 0)
    return {
        "tickets_traites": svc.list_traites_suivi(
            id_user=id_user,
            user_droits=user.droits or [],
            jour=jour,
        ),
    }


@router.get("/dashboard/fibre")
def get_dashboard_fibre(
    jour: str | None = None,
    user: UserToken = Depends(get_current_user),
):
    """Dashboard Fibre : 4 stats + agences internes + Power/Fox.
    Cf. compute_stats de call/fibre/tickets.py.
    """
    _require_droit(user, "TicketCall")
    return svc.dashboard_fibre(user.droits or [], jour=jour)


@router.get("/dashboard/energie")
def get_dashboard_energie(
    jour: str | None = None,
    user: UserToken = Depends(get_current_user),
):
    """Dashboard Energie : partenaires globaux + zones
    (agences internes / multicom / power) avec detail par_partenaire.
    Cf. compute_stats_energie de call/energie/tickets.py.
    """
    _require_droit(user, "TicketCall")
    return svc.dashboard_energie(user.droits or [], jour=jour)


# --- Fiches ticket (portage PG) ------------------------------------------

@router.get("/fiche-fibre/{id_ticket}")
def get_fiche_fibre(
    id_ticket: str,
    user: UserToken = Depends(get_current_user),
):
    """Charge la fiche d'un ticket Call Fibre (portage PG de
    /call/fibre/tickets/{id}/fiche)."""
    _require_droit(user, "TicketCall")
    from app.intranets.vendeur.services import (
        tickets_call_fiche_fibre as fiche_svc,
    )
    id_user = int(user.id_salarie or 0)
    try:
        data = fiche_svc.load_fiche(int(id_ticket), current_user_id=id_user)
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")
    if "error" in data:
        raise HTTPException(404, data["error"])
    return data


@router.get("/fiche-energie/{id_ticket}")
def get_fiche_energie(
    id_ticket: str,
    user: UserToken = Depends(get_current_user),
):
    """Charge la fiche d'un ticket Call Energie (portage PG de
    /call/energie/tickets/{id}/fiche)."""
    _require_droit(user, "TicketCall")
    from app.intranets.vendeur.services import (
        tickets_call_fiche_energie as fiche_svc,
    )
    id_user = int(user.id_salarie or 0)
    try:
        data = fiche_svc.load_fiche(int(id_ticket), current_user_id=id_user)
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")
    if "error" in data:
        raise HTTPException(404, data["error"])
    return data
