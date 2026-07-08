"""
Router Fen_TableauSalarie.

Endpoints :
  GET  /adm/paies/tableau-salarie/orgas         - Combo/picker equipes
  POST /adm/paies/tableau-salarie/rechercher    - Btn Lancer la recherche
  POST /adm/paies/tableau-salarie/export-xlsx   - Btn Export XLS
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.tableau_salarie import (
    ExportXlsxParams, OrgaCombo, RechercherParams, RechercherResult,
)
from app.intranets.adm.services import tableau_salarie as svc

router = APIRouter(
    prefix="/paies/tableau-salarie",
    tags=["adm-paies-tableau-salarie"],
)


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


@router.get("/orgas", response_model=list[OrgaCombo])
def get_orgas(user: UserToken = Depends(get_current_user)):
    _require_droit(user, "TabSalarie")
    return svc.list_orgas()


@router.post("/rechercher", response_model=RechercherResult)
def post_rechercher(
    params: RechercherParams,
    user: UserToken = Depends(get_current_user),
):
    """Btn Lancer la recherche : creaListeVendeur."""
    _require_droit(user, "TabSalarie")
    return svc.rechercher(params)


@router.post("/export-xlsx")
def post_export_xlsx(
    params: ExportXlsxParams,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "TabSalarie")
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
