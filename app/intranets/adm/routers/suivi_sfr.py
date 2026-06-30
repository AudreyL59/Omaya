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


@router.get("/ticket-call/detail/{id_tk_liste}",
            response_model=svc.TicketCallDetail)
def get_ticket_call_detail(
    id_tk_liste: int,
    _u: UserToken = Depends(get_current_user),
):
    from fastapi import HTTPException
    d = svc.get_ticket_call_detail(id_tk_liste)
    if not d:
        raise HTTPException(status_code=404, detail="Ticket introuvable")
    return d


class UpdatePanierNumPayload(BaseModel):
    num: str
    id_tk_liste: int


@router.get("/ticket-call/{id_call_sfr}/cin-url")
def get_cin_url(
    id_call_sfr: int,
    source: str = "normal",   # 'normal' | 'sos'
    _u: UserToken = Depends(get_current_user),
):
    """Renvoie l'URL a ouvrir : essaie .jpg, fallback _PieceIdentite.pdf."""
    return {"url": svc.resolve_cin_url(id_call_sfr, source)}


class SelectionTicketsPayload(BaseModel):
    ids_tk_liste: list[int]


# -- Fen_ExtractionSFR --------------------------------------------------


@router.get("/extraction-sfr/etats", response_model=list[svc.EtatSfrItem])
def get_extraction_sfr_etats(_u: UserToken = Depends(get_current_user)):
    return svc.list_etats_sfr()


@router.get("/extraction-sfr/search", response_model=list[svc.ExtractionSfrRow])
def get_extraction_sfr_search(
    du: date,
    au: date,
    mode: str = "date_racc",   # 'date_racc' | 'rdv_tech' | 'churn'
    id_etat_sfr: int = 0,
    _u: UserToken = Depends(get_current_user),
):
    return svc.search_extraction_sfr(du, au, mode, id_etat_sfr)


@router.get("/extraction-sfr/export.xlsx")
def get_extraction_sfr_export(
    du: date,
    au: date,
    mode: str = "date_racc",
    id_etat_sfr: int = 0,
    _u: UserToken = Depends(get_current_user),
):
    from fastapi.responses import Response
    rows = svc.search_extraction_sfr(du, au, mode, id_etat_sfr)
    content = svc.export_extraction_sfr_xlsx(rows)
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                f'attachment; filename="extraction-sfr-{mode}-{du}-{au}.xlsx"',
        },
    )


class ConvertContratsPayload(BaseModel):
    id_contrats: list[int]


@router.post("/extraction-sfr/convert-rdv-tech")
def post_convert_rdv_tech(
    payload: ConvertContratsPayload,
    u: UserToken = Depends(get_current_user),
):
    return svc.convert_to_ret_rdv_tech(payload.id_contrats, u.id_salarie)


@router.post("/extraction-sfr/convert-racc")
def post_convert_racc(
    payload: ConvertContratsPayload,
    u: UserToken = Depends(get_current_user),
):
    return svc.convert_to_ret_racc(payload.id_contrats, u.id_salarie)


# -- Fen_ParcoursChaine ------------------------------------------------


@router.get("/parcours-chaines", response_model=list[svc.ParcoursChaineRow])
def get_parcours_chaines(
    du: date,
    au: date,
    _u: UserToken = Depends(get_current_user),
):
    return svc.search_parcours_chaines(du, au)


class SetDroitDiffPayload(BaseModel):
    ids_salarie: list[int]
    actif: bool


@router.post("/parcours-chaines/droit-diff")
def post_parcours_droit_diff(
    payload: SetDroitDiffPayload,
    u: UserToken = Depends(get_current_user),
):
    n = svc.set_droit_diff_sfr(payload.ids_salarie, payload.actif, u.id_salarie)
    return {"ok": True, "nb_updated": n}


@router.get("/parcours-chaines/export.xlsx")
def get_parcours_chaines_export(
    du: date,
    au: date,
    _u: UserToken = Depends(get_current_user),
):
    from fastapi.responses import Response
    rows = svc.search_parcours_chaines(du, au)
    content = svc.export_parcours_chaines_xlsx(rows)
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                f'attachment; filename="parcours-chaines-{du}-{au}.xlsx"',
        },
    )


@router.post("/ticket-call/convert-selection",
             response_model=list[svc.ConversionResultItem])
def post_convert_selection(
    payload: SelectionTicketsPayload,
    u: UserToken = Depends(get_current_user),
):
    return svc.convert_selection_to_contracts(payload.ids_tk_liste,
                                               u.id_salarie)


@router.post("/ticket-call/cloture-selection",
             response_model=list[svc.ConversionResultItem])
def post_cloture_selection(
    payload: SelectionTicketsPayload,
    u: UserToken = Depends(get_current_user),
):
    return svc.cloture_selection_sans_convertir(payload.ids_tk_liste,
                                                  u.id_salarie)


@router.put("/ticket-call/panier/{id_panier}/num")
def put_panier_num(
    id_panier: int,
    payload: UpdatePanierNumPayload,
    u: UserToken = Depends(get_current_user),
):
    svc.update_panier_num(id_panier, payload.num, payload.id_tk_liste,
                          u.id_salarie)
    return {"ok": True}


@router.get("/ticket-call/planning",
            response_model=list[svc.PlanningRdvItem])
def get_ticket_call_planning(
    du: date,
    au: date,
    etat: str = "tous",
    _u: UserToken = Depends(get_current_user),
):
    return svc.planning_appels(du, au, etat)
