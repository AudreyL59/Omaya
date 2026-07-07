"""
Router Fen_GestionPodium.

Endpoints :
  GET  /comm/podium/combos/types              - Combo Type Podium (actifs)
  GET  /comm/podium/combos/distributeurs      - Combo Distrib
  # Onglet 2 - Parametres
  GET  /comm/podium/types                     - Liste PodiumType
  POST /comm/podium/types                     - Create PodiumType
  PUT  /comm/podium/types/{id}                - Update PodiumType
  DELETE /comm/podium/types/{id}              - Soft delete PodiumType
  GET  /comm/podium/types/{id}/parts          - Liste PodiumTypePart
  POST /comm/podium/parts                     - Create PodiumTypePart
  PUT  /comm/podium/parts/{id}                - Update PodiumTypePart
  DELETE /comm/podium/parts/{id}              - Soft delete PodiumTypePart
  # Onglet 3 - Annee Podium
  POST /comm/podium/valider-annee             - Valider annee
  # Onglet 1 - Podiums Vendeurs
  POST /comm/podium/rechercher                - Btn Rechercher
  POST /comm/podium/score-visible             - Btn disquette (save score visible)
  POST /comm/podium/calcul                    - Btn Calcul Podium
  POST /comm/podium/telecharger-xlsx          - Btn Telecharger
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.podium import (
    PodiumType, PodiumTypePart, PodiumTypePartPayload,
    PodiumTypePayload,
    RechercherPodiumParams, RechercherPodiumResult,
    SauveScoreVisibleParams, TelechargerParams,
    ValiderAnneeParams, ValiderAnneeResult,
)
from app.intranets.adm.services import podium as svc
from app.intranets.adm.services import podium_calcul as svc_calc
from app.intranets.adm.schemas.podium import (
    CalculPodiumParams, CalculPodiumResult,
)

router = APIRouter(prefix="/comm/podium", tags=["adm-comm-podium"])


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


# --------------------------------------------------------------------
# Combos
# --------------------------------------------------------------------

@router.get("/combos/types")
def get_combo_types(user: UserToken = Depends(get_current_user)):
    _require_droit(user, "GestionPodium")
    return {"items": svc.list_types_podium_actifs()}


@router.get("/combos/distributeurs")
def get_combo_distributeurs(user: UserToken = Depends(get_current_user)):
    _require_droit(user, "GestionPodium")
    return {"items": svc.list_distributeurs()}


# --------------------------------------------------------------------
# Onglet 2 - PodiumType
# --------------------------------------------------------------------

@router.get("/types", response_model=list[PodiumType])
def get_types(user: UserToken = Depends(get_current_user)):
    _require_droit(user, "GestionPodium")
    return svc.list_podium_types()


@router.post("/types")
def post_type(
    payload: PodiumTypePayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestionPodium")
    if not payload.lib_podium_type.strip():
        raise HTTPException(status_code=400, detail="Libelle requis")
    op_id = int(user.id_salarie or 0)
    new_id = svc.create_podium_type(payload, op_id)
    return {"ok": True, "id_podium_type": new_id}


@router.put("/types/{id_pt}")
def put_type(
    id_pt: str,
    payload: PodiumTypePayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestionPodium")
    op_id = int(user.id_salarie or 0)
    ok = svc.update_podium_type(id_pt, payload, op_id)
    return {"ok": ok}


@router.delete("/types/{id_pt}")
def delete_type(
    id_pt: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestionPodium")
    op_id = int(user.id_salarie or 0)
    ok = svc.delete_podium_type(id_pt, op_id)
    return {"ok": ok}


# --------------------------------------------------------------------
# Onglet 2 - PodiumTypePart
# --------------------------------------------------------------------

@router.get(
    "/types/{id_pt}/parts",
    response_model=list[PodiumTypePart],
)
def get_type_parts(
    id_pt: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestionPodium")
    return svc.list_podium_type_parts(id_pt)


@router.post("/parts")
def post_part(
    payload: PodiumTypePartPayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestionPodium")
    if not payload.id_podium_type or payload.id_podium_type == "0":
        raise HTTPException(status_code=400, detail="PodiumType requis")
    op_id = int(user.id_salarie or 0)
    new_id = svc.create_podium_type_part(payload, op_id)
    return {"ok": True, "id_podium_type_part": new_id}


@router.put("/parts/{id_ptp}")
def put_part(
    id_ptp: str,
    payload: PodiumTypePartPayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestionPodium")
    op_id = int(user.id_salarie or 0)
    ok = svc.update_podium_type_part(id_ptp, payload, op_id)
    return {"ok": ok}


@router.delete("/parts/{id_ptp}")
def delete_part(
    id_ptp: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestionPodium")
    op_id = int(user.id_salarie or 0)
    ok = svc.delete_podium_type_part(id_ptp, op_id)
    return {"ok": ok}


# --------------------------------------------------------------------
# Onglet 3 - Valider annee
# --------------------------------------------------------------------

@router.post("/valider-annee", response_model=ValiderAnneeResult)
def post_valider_annee(
    params: ValiderAnneeParams,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GestionPodium")
    op_id = int(user.id_salarie or 0)
    return svc.valider_annee(params, op_id)


# --------------------------------------------------------------------
# Onglet 1 - Podiums Vendeurs
# --------------------------------------------------------------------

@router.post("/rechercher", response_model=RechercherPodiumResult)
def post_rechercher(
    params: RechercherPodiumParams,
    user: UserToken = Depends(get_current_user),
):
    """Btn Rechercher : lance la requete + agrege par salarie / equipe."""
    _require_droit(user, "GestionPodium")
    return svc.rechercher_podium(params)


@router.post("/score-visible")
def post_score_visible(
    params: SauveScoreVisibleParams,
    user: UserToken = Depends(get_current_user),
):
    """Btn Disquette : sauve score_visible sur PodiumMois."""
    _require_droit(user, "GestionPodium")
    op_id = int(user.id_salarie or 0)
    ok = svc.sauver_score_visible(params, op_id)
    return {"ok": ok}


@router.post("/calcul", response_model=CalculPodiumResult)
def post_calcul_podium(
    params: CalculPodiumParams,
    user: UserToken = Depends(get_current_user),
):
    """Btn Calcul Podium : recalcule les podiums entre du et au+7j
    (boucle par pas de 1 mois). Cf. WinDev Podium_Calcul.
    """
    _require_droit(user, "GestionPodium")
    op_id = int(user.id_salarie or 0)
    return svc_calc.calcul_podium(params, op_id)


@router.post("/telecharger-xlsx")
def post_telecharger_xlsx(
    params: TelechargerParams,
    user: UserToken = Depends(get_current_user),
):
    """Btn Telecharger : XLSX du podium tel qu'affiche."""
    _require_droit(user, "GestionPodium")
    fic, content = svc.generer_xlsx_podium(params)
    if not content:
        raise HTTPException(status_code=500, detail="openpyxl indisponible")
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{fic}"',
        },
    )
