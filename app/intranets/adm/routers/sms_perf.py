"""
Router Fen_SMSPerf.

Endpoints (droit 'GestPerfExo' partout) :

Toggle + Staff :
  GET  /adm/comm/sms-perf/actif       - etat courant du toggle
  PUT  /adm/comm/sms-perf/actif       - active/desactive
  GET  /adm/comm/sms-perf/staff       - liste jetons staff
  PUT  /adm/comm/sms-perf/staff       - remplace la liste

CRUD Regles d'envoi :
  GET  /adm/comm/sms-perf/regles                  - liste
  POST /adm/comm/sms-perf/regles                  - create
  PUT  /adm/comm/sms-perf/regles/{id}             - update
  DELETE /adm/comm/sms-perf/regles/{id}           - soft delete
  POST /adm/comm/sms-perf/regles/{id}/dupliquer   - clone

CRUD Destinataires (par code animation) :
  GET  /adm/comm/sms-perf/destinataires?code=X       - liste
  POST /adm/comm/sms-perf/destinataires              - create
  PUT  /adm/comm/sms-perf/destinataires/{id}         - update
  DELETE /adm/comm/sms-perf/destinataires/{id}       - soft delete
  POST /adm/comm/sms-perf/destinataires/{id}/duplicate

CRUD Equipes Scores :
  GET  /adm/comm/sms-perf/equipes-scores?code=X      - liste
  POST /adm/comm/sms-perf/equipes-scores             - create
  PUT  /adm/comm/sms-perf/equipes-scores/{id}        - update
  DELETE /adm/comm/sms-perf/equipes-scores/{id}      - soft delete
  POST /adm/comm/sms-perf/equipes-scores/{id}/duplicate
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.sms_perf import (
    DestinatairePayload, DestinataireRow, EquipeScorePayload, EquipeScoreRow,
    RegleEnvoi, RegleEnvoiPayload, StaffItem, StaffSaveParams, TogglePayload,
)
from app.intranets.adm.services import sms_perf as svc

router = APIRouter(prefix="/comm/sms-perf", tags=["adm-comm-sms-perf"])


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


# --------------------------------------------------------------------
# Toggle
# --------------------------------------------------------------------

class ToggleResult(BaseModel):
    is_actif: bool


@router.get("/actif", response_model=ToggleResult)
def get_actif(user: UserToken = Depends(get_current_user)):
    _require_droit(user, "GestPerfExo")
    return ToggleResult(is_actif=svc.get_perf_exo_actif())


@router.put("/actif")
def put_actif(
    payload: TogglePayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestPerfExo")
    svc.toggle_perf_exo(payload.is_actif)
    return {"ok": True, "is_actif": payload.is_actif}


# --------------------------------------------------------------------
# Staff Destinataire
# --------------------------------------------------------------------

@router.get("/staff", response_model=list[StaffItem])
def get_staff(user: UserToken = Depends(get_current_user)):
    _require_droit(user, "GestPerfExo")
    return svc.get_staff_destinataire()


@router.put("/staff")
def put_staff(
    payload: StaffSaveParams,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestPerfExo")
    svc.save_staff_destinataire(payload.id_salaries)
    return {"ok": True}


# --------------------------------------------------------------------
# CRUD RegleEnvoi
# --------------------------------------------------------------------

@router.get("/regles", response_model=list[RegleEnvoi])
def get_regles(user: UserToken = Depends(get_current_user)):
    _require_droit(user, "GestPerfExo")
    return svc.list_regles()


@router.post("/regles")
def post_regle(
    payload: RegleEnvoiPayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestPerfExo")
    if not payload.code_animation.strip():
        raise HTTPException(400, "Code Animation requis")
    op_id = int(user.id_salarie or 0)
    new_id = svc.create_regle(payload, op_id)
    return {"ok": True, "id_regle": new_id}


@router.put("/regles/{id_regle}")
def put_regle(
    id_regle: str,
    payload: RegleEnvoiPayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestPerfExo")
    op_id = int(user.id_salarie or 0)
    ok = svc.update_regle(id_regle, payload, op_id)
    return {"ok": ok}


@router.delete("/regles/{id_regle}")
def del_regle(
    id_regle: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestPerfExo")
    op_id = int(user.id_salarie or 0)
    ok = svc.delete_regle(id_regle, op_id)
    return {"ok": ok}


@router.post("/regles/{id_regle}/dupliquer")
def dup_regle(
    id_regle: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestPerfExo")
    op_id = int(user.id_salarie or 0)
    new_id = svc.duplicate_regle(id_regle, op_id)
    return {"ok": bool(new_id), "id_regle": new_id}


# --------------------------------------------------------------------
# CRUD Destinataires
# --------------------------------------------------------------------

@router.get("/destinataires", response_model=list[DestinataireRow])
def get_dests(
    code: str = Query(..., min_length=1),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestPerfExo")
    return svc.list_destinataires(code)


@router.post("/destinataires")
def post_dest(
    payload: DestinatairePayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestPerfExo")
    op_id = int(user.id_salarie or 0)
    new_id = svc.create_destinataire(payload, op_id)
    return {"ok": True, "id_dest": new_id}


@router.put("/destinataires/{id_dest}")
def put_dest(
    id_dest: str,
    payload: DestinatairePayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestPerfExo")
    op_id = int(user.id_salarie or 0)
    ok = svc.update_destinataire(id_dest, payload, op_id)
    return {"ok": ok}


@router.delete("/destinataires/{id_dest}")
def del_dest(
    id_dest: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestPerfExo")
    op_id = int(user.id_salarie or 0)
    ok = svc.delete_destinataire(id_dest, op_id)
    return {"ok": ok}


@router.post("/destinataires/{id_dest}/duplicate")
def dup_dest(
    id_dest: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestPerfExo")
    op_id = int(user.id_salarie or 0)
    new_id = svc.duplicate_destinataire(id_dest, op_id)
    return {"ok": bool(new_id), "id_dest": new_id}


# --------------------------------------------------------------------
# CRUD Equipes Scores
# --------------------------------------------------------------------

@router.get("/equipes-scores", response_model=list[EquipeScoreRow])
def get_eqs(
    code: str = Query(..., min_length=1),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestPerfExo")
    return svc.list_equipes_scores(code)


@router.post("/equipes-scores")
def post_eq(
    payload: EquipeScorePayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestPerfExo")
    op_id = int(user.id_salarie or 0)
    new_id = svc.create_equipe_score(payload, op_id)
    return {"ok": True, "id_orga_periode": new_id}


@router.put("/equipes-scores/{id_eq}")
def put_eq(
    id_eq: str,
    payload: EquipeScorePayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestPerfExo")
    op_id = int(user.id_salarie or 0)
    ok = svc.update_equipe_score(id_eq, payload, op_id)
    return {"ok": ok}


@router.delete("/equipes-scores/{id_eq}")
def del_eq(
    id_eq: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestPerfExo")
    op_id = int(user.id_salarie or 0)
    ok = svc.delete_equipe_score(id_eq, op_id)
    return {"ok": ok}


@router.post("/equipes-scores/{id_eq}/duplicate")
def dup_eq(
    id_eq: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestPerfExo")
    op_id = int(user.id_salarie or 0)
    new_id = svc.duplicate_equipe_score(id_eq, op_id)
    return {"ok": bool(new_id), "id_orga_periode": new_id}
