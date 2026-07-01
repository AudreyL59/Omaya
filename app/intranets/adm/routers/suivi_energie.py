"""Router ADM > Suivi Energie (Fen_SuiviEnergie et ses sous-fenetres)."""

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import suivi_energie as svc

router = APIRouter(prefix="/suivi-energie", tags=["adm-suivi-energie"])


# -- Fen_ExtractionEnergie ---------------------------------------------


@router.get("/extraction",
            response_model=list[svc.ExtractionEnergieRow])
def get_extraction_energie(
    du: date,
    au: date,
    statut: str = "valide",   # 'valide' | 'annule'
    _u: UserToken = Depends(get_current_user),
):
    return svc.search_extraction_energie(du, au, statut)


# -- Fen_TicketCall Energie -------------------------------------------


@router.get("/ticket-call", response_model=list[svc.TicketCallItem])
def get_ticket_call_energie(
    du: date,
    au: date,
    etat: str = "tous",   # 'ouverts' | 'clotures' | 'tous'
    _u: UserToken = Depends(get_current_user),
):
    return svc.list_ticket_call_energie(du, au, etat)


@router.get("/ticket-call/analyse-ventes",
            response_model=svc.AnalyseVentesTotaux)
def get_ticket_call_analyse_ventes(
    du: date,
    au: date,
    etat: str = "tous",
    _u: UserToken = Depends(get_current_user),
):
    return svc.analyse_ventes_tk_call_energie(du, au, etat)


@router.get("/ticket-call/planning",
            response_model=list[svc.PlanningRdvItem])
def get_ticket_call_planning(
    du: date,
    au: date,
    etat: str = "tous",
    _u: UserToken = Depends(get_current_user),
):
    return svc.planning_appels_energie(du, au, etat)


@router.get("/ticket-call/detail/{id_tk_liste}",
            response_model=svc.TicketCallDetail)
def get_ticket_call_detail(
    id_tk_liste: int,
    _u: UserToken = Depends(get_current_user),
):
    from fastapi import HTTPException
    d = svc.get_ticket_call_detail(id_tk_liste)
    if not d:
        raise HTTPException(404, "Ticket introuvable")
    return d


class UpdatePanierPayload(BaseModel):
    num: str = ""
    statut_prod: int = 0


@router.put("/ticket-call/panier/{id_panier}")
def put_ticket_call_panier(
    id_panier: int,
    payload: UpdatePanierPayload,
    u: UserToken = Depends(get_current_user),
):
    svc.update_panier_call_energie(
        id_panier, payload.num, payload.statut_prod, u.id_salarie,
    )
    return {"ok": True}


@router.get("/ticket-call/{id_tk_call}/justif-url")
def get_ticket_call_justif_url(
    id_tk_call: int,
    id_panier: int,
    partenaire: str,
    source: str = "normal",   # 'normal' | 'sos'
    _u: UserToken = Depends(get_current_user),
):
    return {"url": svc.resolve_call_justif_url(
        id_tk_call, id_panier, partenaire, source,
    )}


@router.get("/extraction/export.xlsx")
def get_extraction_energie_export(
    du: date,
    au: date,
    statut: str = "valide",
    _u: UserToken = Depends(get_current_user),
):
    from fastapi.responses import Response
    rows = svc.search_extraction_energie(du, au, statut)
    content = svc.export_extraction_energie_xlsx(rows)
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                f'attachment; filename="extraction-energie-{statut}-{du}-{au}.xlsx"',
        },
    )
