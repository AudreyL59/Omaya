"""Router ADM > Suivi SFR (Fen_SuiviSFR et ses sous-fenetres)."""

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import suivi_sfr as svc

router = APIRouter(prefix="/suivi-sfr", tags=["adm-suivi-sfr"])


# -- Fen_SFRCttaRacc : Ctts à raccorder ----------------------------


@router.get("/ctts-a-raccorder", response_model=list[svc.CttARaccorderItem])
def get_ctts_a_raccorder(
    du: date,
    au: date,
    _u: UserToken = Depends(get_current_user),
):
    return svc.list_ctts_a_raccorder(du, au)


class SendMailsPayload(BaseModel):
    ids_contrats: list[int]
    test_mode: bool = False


@router.post("/ctts-a-raccorder/send-mails",
             response_model=list[svc.SendMailsResult])
def post_send_mails(
    payload: SendMailsPayload,
    u: UserToken = Depends(get_current_user),
):
    return svc.send_mails_to_bos(
        payload.ids_contrats, u.id_salarie, payload.test_mode,
    )


# -- Fen_RemInterneSFR : Remunerations SFR (Fibre / Mobile) ----------


@router.get("/remunerations", response_model=list[svc.RemunItem])
def get_remunerations(
    categorie: str = "FIBRE",
    _u: UserToken = Depends(get_current_user),
):
    return svc.list_remunerations(categorie)


@router.get("/remunerations/produits", response_model=list[svc.ProduitSfrItem])
def get_produits_sfr(
    categorie: str = "FIBRE",
    _u: UserToken = Depends(get_current_user),
):
    return svc.list_sfr_produits(categorie)


@router.get("/remunerations/{id_sfr_remun}", response_model=svc.RemunItem)
def get_remun(
    id_sfr_remun: int,
    _u: UserToken = Depends(get_current_user),
):
    from fastapi import HTTPException
    r = svc.get_remun(id_sfr_remun)
    if not r:
        raise HTTPException(status_code=404, detail="Remun introuvable")
    return r


@router.post("/remunerations")
def post_remun(
    payload: svc.RemunPayload,
    u: UserToken = Depends(get_current_user),
):
    id_new = svc.create_remun(payload, u.id_salarie)
    return {"ok": True, "id_sfr_remun": str(id_new)}


@router.put("/remunerations/{id_sfr_remun}")
def put_remun(
    id_sfr_remun: int,
    payload: svc.RemunPayload,
    u: UserToken = Depends(get_current_user),
):
    svc.update_remun(id_sfr_remun, payload, u.id_salarie)
    return {"ok": True}


@router.post("/remunerations/{id_sfr_remun}/duplicate")
def post_duplicate_remun(
    id_sfr_remun: int,
    u: UserToken = Depends(get_current_user),
):
    id_new = svc.duplicate_remun(id_sfr_remun, u.id_salarie)
    return {"ok": True, "id_sfr_remun": str(id_new)}


@router.delete("/remunerations/{id_sfr_remun}")
def delete_remun(
    id_sfr_remun: int,
    u: UserToken = Depends(get_current_user),
):
    svc.delete_remun(id_sfr_remun, u.id_salarie)
    return {"ok": True}


# -- Fen_TicketCallSFR : tickets call SFR avec 4 onglets -------------


@router.get("/ticket-call", response_model=list[svc.TicketCallItem])
def get_ticket_call(
    du: date,
    au: date,
    etat: str = "tous",   # 'ouverts' | 'clotures' | 'tous'
    _u: UserToken = Depends(get_current_user),
):
    return svc.list_ticket_call_sfr(du, au, etat)


@router.get("/ticket-call/analyse", response_model=list[svc.AnalyseTrancheItem])
def get_ticket_call_analyse(
    du: date,
    au: date,
    etat: str = "tous",
    _u: UserToken = Depends(get_current_user),
):
    return svc.analyse_tk_call_sfr(du, au, etat)


@router.get("/ticket-call/analyse-ventes",
            response_model=svc.AnalyseVentesTotaux)
def get_ticket_call_analyse_ventes(
    du: date,
    au: date,
    etat: str = "tous",
    _u: UserToken = Depends(get_current_user),
):
    return svc.analyse_ventes_tk_call_sfr(du, au, etat)
