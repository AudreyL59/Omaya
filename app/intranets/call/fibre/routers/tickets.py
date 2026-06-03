"""
Endpoints HTTP Call Fibre - tickets.

Stratégie de chargement de la page principale (transposition WinDev) :
1. Frontend appelle `/tickets/en-cours` -> rapide, affiche tableau du haut
2. En parallele, frontend appelle `/tickets/traites?jour=...` -> tableau du bas + stats
3. Long polling `/tickets/live?since=...` pour pousser les changements live
   sur le tableau du haut (en cours uniquement).
"""

from datetime import date as _date
import sys
import traceback

from fastapi import APIRouter, Body, Depends, HTTPException, Query
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
    FicheDocumentsResponse,
    LettreResilResponse,
    SaveVenteRequest,
    SaveOffreRequest,
    SaveResponse,
    VerrouPeek,
    VerrouResponse,
    PrendreAppelRequest,
    AnnulLignePanierRequest,
    ActionVenteRequest,
    ActionVenteResponse,
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
    try:
        data = fiche_svc.load_fiche(
            id_tk_liste=int(id_ticket),
            current_user_id=user.id_salarie or 0,
        )
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data


@router.get("/tickets/panier/{id_panier}/test-eligibilite", response_model=FicheTestEligibiliteResponse)
def get_panier_test_eligibilite(
    id_panier: str,
    user: UserToken = Depends(get_current_user),
):
    """Charge l'image TestEligibilite pour une ligne du panier (FIBRE only)."""
    url = fiche_svc.load_panier_ligne_image(int(id_panier))
    return {"test_eligibilite": url}


@router.get("/tickets/{id_ticket}/documents", response_model=FicheDocumentsResponse)
def get_fiche_documents(
    id_ticket: str,
    client_pro: bool = Query(False),
    user: UserToken = Depends(get_current_user),
):
    """Detecte les documents disponibles pour ce ticket (CIN, KBIS si Pro).

    Fait des HEAD HTTP vers rest.omaya.fr -> renvoie pour chaque doc l'URL
    et le type (pdf / image) si trouve, sinon vide.
    """
    return fiche_svc.load_documents(int(id_ticket), client_pro=client_pro)


# --- Phase 3 : verrou ope + actions panier --------------------------------

@router.get("/tickets/{id_ticket}/verrou", response_model=VerrouPeek)
def get_verrou(id_ticket: str, user: UserToken = Depends(get_current_user)):
    """Etat actuel du verrou ope (qui, depuis quand)."""
    try:
        data = fiche_svc.peek_verrou(int(id_ticket))
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data


@router.post("/tickets/{id_ticket}/verrou/prendre", response_model=VerrouResponse)
def post_verrou_prendre(
    id_ticket: str,
    payload: PrendreAppelRequest,
    user: UserToken = Depends(get_current_user),
):
    """Pose le verrou ope. Si pris par un autre, renvoie needs_confirm=True."""
    try:
        data = fiche_svc.prendre_appel(int(id_ticket), user.id_salarie or 0, force=payload.force)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data


@router.post("/tickets/{id_ticket}/verrou/lacher", response_model=SaveResponse)
def post_verrou_lacher(id_ticket: str, user: UserToken = Depends(get_current_user)):
    """Libere le verrou ope (raccroche)."""
    try:
        data = fiche_svc.lacher_appel(int(id_ticket))
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data


@router.post("/tickets/panier/{id_panier}/annuler-ligne", response_model=SaveResponse)
def post_annuler_ligne(
    id_panier: str,
    payload: AnnulLignePanierRequest,
    user: UserToken = Depends(get_current_user),
):
    """Annule une seule ligne du panier (StatutProd=2 + MotifAnnulation)."""
    try:
        data = fiche_svc.annuler_ligne_panier(int(id_panier), payload.motifs, payload.precisions)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    if "error" in data:
        raise HTTPException(status_code=400, detail=data["error"])
    return data


@router.post("/tickets/{id_ticket}/annuler-vente", response_model=ActionVenteResponse)
def post_annuler_vente(
    id_ticket: str,
    payload: ActionVenteRequest,
    user: UserToken = Depends(get_current_user),
):
    """Annule toute la vente (TK_Liste IDTK_Statut=14)."""
    try:
        data = fiche_svc.annuler_vente(int(id_ticket), payload.dict(exclude_none=True))
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    return data


@router.post("/tickets/{id_ticket}/valider-vente", response_model=ActionVenteResponse)
def post_valider_vente(
    id_ticket: str,
    payload: ActionVenteRequest,
    user: UserToken = Depends(get_current_user),
):
    """Valide le panier (TK_Liste IDTK_Statut=15). SMS si statut=34."""
    try:
        data = fiche_svc.valider_vente(int(id_ticket), payload.dict(exclude_none=True))
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    return data


@router.post("/tickets/{id_ticket}/renvoyer-complement", response_model=ActionVenteResponse)
def post_renvoyer_complement(id_ticket: str, user: UserToken = Depends(get_current_user)):
    """Renvoie le panier pour complement (TK_Liste IDTK_Statut=28). SMS toujours."""
    try:
        data = fiche_svc.renvoyer_complement(int(id_ticket))
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    return data


@router.post("/tickets/{id_ticket}/save-vente", response_model=SaveResponse)
def post_save_vente(
    id_ticket: str,
    payload: SaveVenteRequest,
    user: UserToken = Depends(get_current_user),
):
    """Save infos client + vente + anomalie (UPDATE TK_CallSFR).

    Transposition du bouton "Enregistrer les infos client et vente" WinDev.
    """
    try:
        return fiche_svc.save_vente_infos(int(id_ticket), payload.dict())
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/tickets/panier/{id_panier}/save-offre", response_model=SaveResponse)
def post_save_offre(
    id_panier: str,
    payload: SaveOffreRequest,
    user: UserToken = Depends(get_current_user),
):
    """Save les modifs d'une ligne d'offre (UPDATE TK_CallSFR_Panier).

    Transposition du bouton "Enregistrer les modifs Offre" WinDev.
    """
    try:
        return fiche_svc.save_offre(int(id_panier), payload.dict())
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/tickets/{id_ticket}/panier/{id_panier}/lettre-resil", response_model=LettreResilResponse)
def get_lettre_resil(
    id_ticket: str,
    id_panier: str,
    user: UserToken = Depends(get_current_user),
):
    """Detecte la Lettre de resiliation pour une ligne de panier (FIBRE only)."""
    return fiche_svc.load_lettre_resil(int(id_ticket), int(id_panier))


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
