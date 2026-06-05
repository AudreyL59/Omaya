"""
Endpoints HTTP Call Energie - tickets.

Structure miroir de Call Fibre, mais sans la response stats globales
(dashboard du haut a definir separement).
"""

import sys
import time
import traceback
from datetime import date as _date

import anyio
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.call.energie.services import tickets as svc
from app.intranets.call.energie.services import fiche as fiche_svc
from app.intranets.call.energie.schemas.tickets import (
    TicketsPageResponse,
    TicketsLiveResponse,
    TicketsEnCoursResponse,
    TicketsTraitesResponse,
)
from app.intranets.call.energie.schemas.fiche import (
    FicheTicketEnergieResponse,
    FicheDocumentsResponse,
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


@router.get("/tickets/{id_ticket}/fiche", response_model=FicheTicketEnergieResponse)
def get_fiche_ticket(
    id_ticket: str,
    user: UserToken = Depends(get_current_user),
):
    """Charge la fiche complete d'un ticket Call Energie (popup, Phase 1)."""
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


# --- Phase 3 : verrou ope + actions panier --------------------------------

@router.get("/tickets/{id_ticket}/verrou", response_model=VerrouPeek)
def get_verrou(id_ticket: str, user: UserToken = Depends(get_current_user)):
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
    try:
        return fiche_svc.annuler_vente(int(id_ticket), payload.dict(exclude_none=True))
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/tickets/{id_ticket}/valider-vente", response_model=ActionVenteResponse)
def post_valider_vente(
    id_ticket: str,
    payload: ActionVenteRequest,
    user: UserToken = Depends(get_current_user),
):
    try:
        return fiche_svc.valider_vente(int(id_ticket), payload.dict(exclude_none=True))
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/tickets/{id_ticket}/renvoyer-complement", response_model=ActionVenteResponse)
def post_renvoyer_complement(id_ticket: str, user: UserToken = Depends(get_current_user)):
    try:
        return fiche_svc.renvoyer_complement(int(id_ticket))
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/tickets/{id_ticket}/renvoyer-clarification", response_model=ActionVenteResponse)
def post_renvoyer_clarification(id_ticket: str, user: UserToken = Depends(get_current_user)):
    """Bouton specifique : 'Renvoyer pour fiche clarification' (Energie).

    UPDATE InfoVente avec note 'Renvoye pour fiche clarification le {now} par
    {user}' + statut 28 + SMS specifique.
    """
    try:
        return fiche_svc.renvoyer_clarification(
            int(id_ticket),
            user_nom=user.nom or "",
            user_prenom=user.prenom or "",
        )
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/tickets/{id_ticket}/save-vente", response_model=SaveResponse)
def post_save_vente(
    id_ticket: str,
    payload: SaveVenteRequest,
    user: UserToken = Depends(get_current_user),
):
    """Save infos client + vente (UPDATE TK_Call)."""
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
    """Save les modifs d'une ligne d'offre (UPDATE TK_Call_Panier).

    Champs optionnels : on n'update que ceux fournis dans le payload.
    """
    try:
        return fiche_svc.save_offre(int(id_panier), payload.dict(exclude_none=True))
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/tickets/{id_ticket}/documents", response_model=FicheDocumentsResponse)
def get_fiche_documents(
    id_ticket: str,
    client_pro: bool = Query(False),
    user: UserToken = Depends(get_current_user),
):
    """Detecte les documents : CIN + KBIS (si Pro) + Justif (specifique Energie)."""
    return fiche_svc.load_documents(int(id_ticket), client_pro=client_pro)


@router.get("/tickets/panier/{id_panier}/clarification")
def get_clarification(
    id_panier: str,
    user: UserToken = Depends(get_current_user),
):
    """Detecte la fiche de clarification PDF d'une ligne de panier (OEN)."""
    return fiche_svc.load_clarification(int(id_panier))


@router.get("/tickets/en-cours", response_model=TicketsEnCoursResponse)
def get_tickets_en_cours(user: UserToken = Depends(get_current_user)):
    """Tableau du haut UNIQUEMENT : tickets a traiter + serveur_now + last_modif."""
    try:
        return svc.load_page_en_cours(user_id=user.id_salarie, user_id_poste=0)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/tickets/traites", response_model=TicketsTraitesResponse)
def get_tickets_traites(
    user: UserToken = Depends(get_current_user),
    jour: str | None = Query(None, description="YYYY-MM-DD. Defaut = today."),
):
    """Tableau du bas (tickets traites du jour)."""
    try:
        return svc.load_page_traites(jour=jour)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


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
async def get_tickets_live(
    user: UserToken = Depends(get_current_user),
    since: str = Query("", description="last_modif precedent. Vide = chargement initial."),
    timeout: int = Query(25, ge=1, le=55, description="Long polling timeout (s)."),
):
    """Long polling ASYNC : l'attente (`await anyio.sleep`) ne monopolise aucun
    thread du pool ; seul le check du token (cache ~1s) emprunte un thread
    quelques ms. Sous N operateurs, le pool reste libre pour les fiches."""
    try:
        if not since:
            page = await anyio.to_thread.run_sync(
                lambda: svc.load_page_en_cours(user.id_salarie or 0, 0)
            )
            return {"changed": True, "page": page, "last_modif": page["last_modif"]}

        deadline = time.monotonic() + timeout
        while True:
            latest = await anyio.to_thread.run_sync(svc.get_last_modif_call_energie_cached)
            if latest and latest != since:
                page = await anyio.to_thread.run_sync(
                    lambda: svc.load_page_en_cours(user.id_salarie or 0, 0)
                )
                return {"changed": True, "page": page, "last_modif": page["last_modif"]}
            if time.monotonic() >= deadline:
                return {"changed": False, "page": None, "last_modif": latest}
            await anyio.sleep(0.75)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
