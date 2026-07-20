"""
Router Vendeur - Suivi Tickets Call (Fibre + Energie fusionnes).

Droit d'acces : TicketCall (deja cable dans le menu).
Filtrage orga :
  - Si le user a le droit 'ProdRezo' -> voit tout
  - Sinon -> voit uniquement les tickets dont le vendeur est rattache
    a son orga ou sous-orgas (cf. WinDev ListeOrgaComplet).
"""
from __future__ import annotations

import time
import anyio
from fastapi import APIRouter, Body, Depends, HTTPException, Query

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


@router.get("/live")
async def get_live(
    since: str = Query("", description="last_modif precedent, vide=initial"),
    timeout: int = Query(25, ge=1, le=55),
    user: UserToken = Depends(get_current_user),
):
    """Long polling : renvoie {changed, last_modif, page?} des qu'un
    ticket bouge ou apres `timeout` secondes.

    `page` est la liste unifiee des tickets en cours (comme /en-cours).
    Le tableau du bas + dashboards ne sont pas reconstruits ici (le
    client les rafraichit separement quand `changed=True`).
    """
    _require_droit(user, "TicketCall")
    id_user = int(user.id_salarie or 0)
    droits = user.droits or []

    if not since:
        page = await anyio.to_thread.run_sync(
            lambda: svc.list_en_cours_suivi(id_user, droits, 0),
        )
        latest = await anyio.to_thread.run_sync(svc.get_last_modif_cached)
        return {"changed": True, "last_modif": latest, "page": page}

    deadline = time.monotonic() + timeout
    while True:
        latest = await anyio.to_thread.run_sync(svc.get_last_modif_cached)
        if latest and latest != since:
            page = await anyio.to_thread.run_sync(
                lambda: svc.list_en_cours_suivi(id_user, droits, 0),
            )
            return {"changed": True, "last_modif": latest, "page": page}
        if time.monotonic() >= deadline:
            return {"changed": False, "last_modif": latest, "page": None}
        await anyio.sleep(0.75)


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


# =========================================================================
# Actions FIBRE (verrou, save, actions vente, docs)
# =========================================================================

def _lazy_actions_fibre():
    from app.intranets.vendeur.services import tickets_call_actions_fibre
    return tickets_call_actions_fibre


def _run_or_raise(fn, *args, err_404: bool = True, **kwargs) -> dict:
    try:
        data = fn(*args, **kwargs)
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")
    if isinstance(data, dict) and "error" in data:
        raise HTTPException(404 if err_404 else 400, data["error"])
    return data


@router.get("/fiche-fibre/{id_ticket}/documents")
def get_fibre_documents(
    id_ticket: str,
    client_pro: bool = Query(False),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _lazy_actions_fibre().load_documents(int(id_ticket), client_pro=client_pro)


@router.get("/fiche-fibre/panier/{id_panier}/test-eligibilite")
def get_fibre_test_eligibilite(
    id_panier: str, user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return {"test_eligibilite": _lazy_actions_fibre().load_panier_ligne_image(int(id_panier))}


@router.get("/fiche-fibre/{id_ticket}/panier/{id_panier}/lettre-resil")
def get_fibre_lettre_resil(
    id_ticket: str, id_panier: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _lazy_actions_fibre().load_lettre_resil(int(id_ticket), int(id_panier))


@router.get("/fiche-fibre/{id_ticket}/verrou")
def get_fibre_verrou(
    id_ticket: str, user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(_lazy_actions_fibre().peek_verrou, int(id_ticket))


@router.post("/fiche-fibre/{id_ticket}/verrou/prendre")
def post_fibre_verrou_prendre(
    id_ticket: str,
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(
        _lazy_actions_fibre().prendre_appel,
        int(id_ticket), int(user.id_salarie or 0),
        force=bool(payload.get("force", False)),
    )


@router.post("/fiche-fibre/{id_ticket}/verrou/lacher")
def post_fibre_verrou_lacher(
    id_ticket: str, user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(_lazy_actions_fibre().lacher_appel, int(id_ticket))


@router.post("/fiche-fibre/panier/{id_panier}/annuler-ligne")
def post_fibre_annuler_ligne(
    id_panier: str,
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(
        _lazy_actions_fibre().annuler_ligne_panier,
        int(id_panier),
        payload.get("motifs") or [],
        payload.get("precisions") or "",
        err_404=False,
    )


@router.post("/fiche-fibre/{id_ticket}/save-vente")
def post_fibre_save_vente(
    id_ticket: str,
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(_lazy_actions_fibre().save_vente_infos, int(id_ticket), payload)


@router.post("/fiche-fibre/panier/{id_panier}/save-offre")
def post_fibre_save_offre(
    id_panier: str,
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(_lazy_actions_fibre().save_offre, int(id_panier), payload)


@router.post("/fiche-fibre/{id_ticket}/annuler-vente")
def post_fibre_annuler_vente(
    id_ticket: str,
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(_lazy_actions_fibre().annuler_vente, int(id_ticket), payload)


@router.post("/fiche-fibre/{id_ticket}/valider-vente")
def post_fibre_valider_vente(
    id_ticket: str,
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(_lazy_actions_fibre().valider_vente, int(id_ticket), payload)


@router.post("/fiche-fibre/{id_ticket}/renvoyer-complement")
def post_fibre_renvoyer_complement(
    id_ticket: str, user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(_lazy_actions_fibre().renvoyer_complement, int(id_ticket))


@router.post("/fiche-fibre/{id_ticket}/renvoyer-lettre-resil")
def post_fibre_renvoyer_lettre_resil(
    id_ticket: str, user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(
        _lazy_actions_fibre().renvoyer_lettre_resil,
        int(id_ticket),
        user.nom or "", user.prenom or "",
    )


# =========================================================================
# Actions ENERGIE (verrou, save, actions vente, docs, clarification)
# =========================================================================

def _lazy_actions_energie():
    from app.intranets.vendeur.services import tickets_call_actions_energie
    return tickets_call_actions_energie


@router.get("/fiche-energie/{id_ticket}/documents")
def get_energie_documents(
    id_ticket: str,
    client_pro: bool = Query(False),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _lazy_actions_energie().load_documents(int(id_ticket), client_pro=client_pro)


@router.get("/fiche-energie/panier/{id_panier}/clarification")
def get_energie_clarification(
    id_panier: str, user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _lazy_actions_energie().load_clarification(int(id_panier))


@router.get("/fiche-energie/{id_ticket}/verrou")
def get_energie_verrou(
    id_ticket: str, user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(_lazy_actions_energie().peek_verrou, int(id_ticket))


@router.post("/fiche-energie/{id_ticket}/verrou/prendre")
def post_energie_verrou_prendre(
    id_ticket: str,
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(
        _lazy_actions_energie().prendre_appel,
        int(id_ticket), int(user.id_salarie or 0),
        force=bool(payload.get("force", False)),
    )


@router.post("/fiche-energie/{id_ticket}/verrou/lacher")
def post_energie_verrou_lacher(
    id_ticket: str, user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(_lazy_actions_energie().lacher_appel, int(id_ticket))


@router.post("/fiche-energie/panier/{id_panier}/annuler-ligne")
def post_energie_annuler_ligne(
    id_panier: str,
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(
        _lazy_actions_energie().annuler_ligne_panier,
        int(id_panier),
        payload.get("motifs") or [],
        payload.get("precisions") or "",
        err_404=False,
    )


@router.post("/fiche-energie/{id_ticket}/save-vente")
def post_energie_save_vente(
    id_ticket: str,
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(_lazy_actions_energie().save_vente_infos, int(id_ticket), payload)


@router.post("/fiche-energie/panier/{id_panier}/save-offre")
def post_energie_save_offre(
    id_panier: str,
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(_lazy_actions_energie().save_offre, int(id_panier), payload)


@router.post("/fiche-energie/{id_ticket}/annuler-vente")
def post_energie_annuler_vente(
    id_ticket: str,
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(_lazy_actions_energie().annuler_vente, int(id_ticket), payload)


@router.post("/fiche-energie/{id_ticket}/valider-vente")
def post_energie_valider_vente(
    id_ticket: str,
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(_lazy_actions_energie().valider_vente, int(id_ticket), payload)


@router.post("/fiche-energie/{id_ticket}/renvoyer-complement")
def post_energie_renvoyer_complement(
    id_ticket: str, user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(_lazy_actions_energie().renvoyer_complement, int(id_ticket))


@router.post("/fiche-energie/{id_ticket}/renvoyer-clarification")
def post_energie_renvoyer_clarification(
    id_ticket: str, user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TicketCall")
    return _run_or_raise(
        _lazy_actions_energie().renvoyer_clarification,
        int(id_ticket),
        user.nom or "", user.prenom or "",
    )
