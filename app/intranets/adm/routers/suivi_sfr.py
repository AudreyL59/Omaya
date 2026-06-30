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
