import sys
import traceback

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.organigramme import OrgaTreeNode
from app.intranets.adm.services.organigramme import get_organigramme_adm
from app.intranets.adm.services import orga_crud as crud
from app.intranets.adm.services.orga_crud import (
    DeplacerSalariePayload,
    OrgaCombo, OrgaCopierPayload, OrgaCreatePayload,
    OrgaMovePayload, OrgaUpdatePayload,
)


router = APIRouter(prefix="/organigramme", tags=["adm-organigramme"])


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


@router.get("", response_model=list[OrgaTreeNode])
def get_tree(user: UserToken = Depends(get_current_user)):
    """Arborescence complète (accès global pour l'intranet ADM)."""
    try:
        return get_organigramme_adm()
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


# --------------------------------------------------------------------
# Combos
# --------------------------------------------------------------------

@router.get("/types-niveau", response_model=list[OrgaCombo])
def get_types_niveau(user: UserToken = Depends(get_current_user)):
    _ = user
    return crud.list_types_niveau()


@router.get("/types-orga", response_model=list[OrgaCombo])
def get_types_orga(user: UserToken = Depends(get_current_user)):
    _ = user
    return crud.list_types_orga()


# --------------------------------------------------------------------
# CRUD orga (droit GestionOrga)
# --------------------------------------------------------------------

@router.post("")
def post_orga(
    payload: OrgaCreatePayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "Menu_Salariés")
    op_id = int(user.id_salarie or 0)
    new_id = crud.create_orga(payload, op_id)
    return {"ok": bool(new_id), "id": new_id}


@router.put("/{id_orga}")
def put_orga(
    id_orga: str,
    payload: OrgaUpdatePayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "Menu_Salariés")
    op_id = int(user.id_salarie or 0)
    ok = crud.update_orga(id_orga, payload, op_id)
    return {"ok": ok}


@router.post("/{id_orga}/move")
def post_orga_move(
    id_orga: str,
    payload: OrgaMovePayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "Menu_Salariés")
    op_id = int(user.id_salarie or 0)
    return crud.move_orga(id_orga, payload.id_parent_new, op_id)


@router.delete("/{id_orga}")
def del_orga(
    id_orga: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "Menu_Salariés")
    op_id = int(user.id_salarie or 0)
    return crud.delete_orga(id_orga, op_id)


@router.post("/{id_orga}/copier")
def post_orga_copier(
    id_orga: str,
    payload: OrgaCopierPayload,
    user: UserToken = Depends(get_current_user),
):
    """Cf. WinDev Orga_Copier."""
    _require_droit(user, "Menu_Salariés")
    op_id = int(user.id_salarie or 0)
    return crud.copier_orga(id_orga, payload, op_id)


@router.post("/deplacer-salarie")
def post_deplacer_salarie(
    payload: DeplacerSalariePayload,
    user: UserToken = Depends(get_current_user),
):
    """Cf. WinDev DeplacerSalarie / Orga_AjoutSa."""
    _require_droit(user, "Menu_Salariés")
    op_id = int(user.id_salarie or 0)
    return crud.deplacer_salarie(payload, op_id)
