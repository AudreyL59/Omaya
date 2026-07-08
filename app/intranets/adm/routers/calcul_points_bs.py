"""
Router Fen_CalculPointsBS.

Endpoints :
  GET  /adm/paies/calcul-points/partenaires  - Combo partenaires actifs
  POST /adm/paies/calcul-points/recalcul     - Btn Calcul Point
  POST /adm/paies/calcul-points/export-xlsx  - Export XLSX
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.calcul_points_bs import (
    ExportXlsxParams, PartenaireCombo,
    RecalculParams, RecalculResult,
)
from app.intranets.adm.services import calcul_points_bs as svc

router = APIRouter(
    prefix="/paies/calcul-points",
    tags=["adm-paies-calcul-points"],
)


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


@router.get("/partenaires", response_model=list[PartenaireCombo])
def get_partenaires(user: UserToken = Depends(get_current_user)):
    _require_droit(user, "CalcPtsEni")
    return svc.list_partenaires()


@router.post("/recalcul", response_model=RecalculResult)
def post_recalcul(
    params: RecalculParams,
    user: UserToken = Depends(get_current_user),
):
    """Btn Calcul Point : lance Recalcul_Point(part) sur la periode."""
    _require_droit(user, "CalcPtsEni")
    return svc.recalcul_points(params)


@router.post("/export-xlsx")
def post_export_xlsx(
    params: ExportXlsxParams,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "CalcPtsEni")
    fic, content = svc.generer_xlsx(params)
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
