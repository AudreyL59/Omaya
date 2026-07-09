import sys
import traceback
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.organigramme import OrgaTreeNode
from app.intranets.adm.services.organigramme import get_organigramme_adm
from app.intranets.adm.services import orga_crud as crud
from app.intranets.adm.services.orga_crud import (
    DeplacerSalariePayload,
    OrgaCombo, OrgaCopierPayload, OrgaCreatePayload, OrgaDetail,
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
def get_types_niveau(
    type: str = Query("", description="'STAFF' | 'FDV' | ''"),
    user: UserToken = Depends(get_current_user),
):
    _ = user
    return crud.list_types_niveau(type)


@router.get("/types-orga", response_model=list[OrgaCombo])
def get_types_orga(user: UserToken = Depends(get_current_user)):
    _ = user
    return crud.list_types_orga()


@router.get("/types-produit", response_model=list[OrgaCombo])
def get_types_produit(
    type: str = Query("", description="'STAFF' | 'FDV' | ''"),
    user: UserToken = Depends(get_current_user),
):
    _ = user
    return crud.list_types_produit(type)


@router.get("/societes-combo", response_model=list[OrgaCombo])
def get_societes_combo(user: UserToken = Depends(get_current_user)):
    _ = user
    return crud.list_societes_orga()


@router.get("/detail/{id_orga}", response_model=OrgaDetail)
def get_orga_detail(
    id_orga: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "Menu_Salariés")
    d = crud.get_orga_detail(id_orga)
    if not d:
        raise HTTPException(404, "Bloc introuvable")
    return d


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


@router.get("/{id_orga}/export-xlsx")
def get_export_xlsx(
    id_orga: str,
    user: UserToken = Depends(get_current_user),
):
    """Cf. WinDev Btn 'Exporter la selection'."""
    _require_droit(user, "Menu_Salariés")
    from app.intranets.adm.services.orga_export import (
        export_orga_selection_xlsx,
    )
    try:
        xlsx = export_orga_selection_xlsx(id_orga)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(500, f"{type(e).__name__}: {e}")
    fname = f"{datetime.now():%Y%m%d_%H%M%S}_ExportOrganigramme.xlsx"
    return Response(
        content=xlsx,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


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
