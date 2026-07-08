"""
Router Fen_ScoolFormation.

Endpoints (droit 'FormScool') :
  GET  /adm/scool/formations                    - Liste
  GET  /adm/scool/formations/{id}               - Detail
  POST /adm/scool/formations                    - Create
  PUT  /adm/scool/formations/{id}               - Update
  DELETE /adm/scool/formations/{id}             - Soft delete
  POST /adm/scool/formations/{id}/dupliquer     - Duplique
  GET  /adm/scool/modeles                       - Liste modeles
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.scool_formation import (
    FormateurCombo, FormationDetail, FormationPayload, FormationRow,
    ListeFormationsParams, ModeleFormationCombo, ModeleFormationRow,
)
from app.intranets.adm.services import scool_formation as svc

router = APIRouter(prefix="/scool", tags=["adm-scool"])


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


@router.get("/formations", response_model=list[FormationRow])
def get_formations(
    afficher_depuis_le: str = Query("", description="YYYY-MM-DD"),
    uniquement_actives: bool = Query(True),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    return svc.list_formations(ListeFormationsParams(
        afficher_depuis_le=afficher_depuis_le,
        uniquement_actives=uniquement_actives,
    ))


@router.get("/formations/{id_formation}", response_model=FormationDetail)
def get_formation(
    id_formation: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    detail = svc.get_formation(id_formation)
    if not detail:
        raise HTTPException(404, "Formation introuvable")
    return detail


@router.post("/formations")
def post_formation(
    payload: FormationPayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    if not payload.intitule.strip():
        raise HTTPException(400, "Intitulé requis")
    op_id = int(user.id_salarie or 0)
    new_id = svc.create_formation(payload, op_id)
    return {"ok": bool(new_id), "id_formation": new_id}


@router.put("/formations/{id_formation}")
def put_formation(
    id_formation: str,
    payload: FormationPayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.update_formation(id_formation, payload, op_id)
    return {"ok": ok}


@router.delete("/formations/{id_formation}")
def del_formation(
    id_formation: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.delete_formation(id_formation, op_id)
    return {"ok": ok}


@router.post("/formations/{id_formation}/dupliquer")
def dup_formation(
    id_formation: str,
    dupliquer_programme: bool = Query(False),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    new_id = svc.duplicate_formation(
        id_formation, op_id, dupliquer_programme,
    )
    return {"ok": bool(new_id), "id_formation": new_id}


@router.get("/modeles", response_model=list[ModeleFormationRow])
def get_modeles(user: UserToken = Depends(get_current_user)):
    _require_droit(user, "FormScool")
    return svc.list_modeles()


@router.get("/modeles-combo", response_model=list[ModeleFormationCombo])
def get_modeles_combo(user: UserToken = Depends(get_current_user)):
    """Combo 'Utiliser ce modele' de Fen_ScoolFormation_Ajout.
    Premier item = 'Ne pas utiliser de modele' (id=0).
    """
    _require_droit(user, "FormScool")
    return svc.list_modeles_combo()


@router.get("/formateurs", response_model=list[FormateurCombo])
def get_formateurs(user: UserToken = Depends(get_current_user)):
    """Combos Formateur1..5 de Fen_ScoolFormation_Ajout : formateurs
    actifs (JOIN pgt_formateur + pgt_salarie + pgt_salarie_embauche).
    """
    _require_droit(user, "FormScool")
    return svc.list_formateurs()
