"""
Router Fen_TableauDivers.

Endpoints :
  POST /adm/paies/tableaux-divers/lister               - Btn Lister les vendeurs
  POST /adm/paies/tableaux-divers/generer-valandre     - Btn Generer fichier Valandre EXO
  POST /adm/paies/tableaux-divers/generer-comptable    - Btn Generer fichier Comptable
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.tableau_divers import (
    GenererComptableParams, GenererValandreParams,
    ListerDemandesParams, ListerDemandesResult,
)
from app.intranets.adm.services import tableau_divers as svc

router = APIRouter(
    prefix="/paies/tableaux-divers",
    tags=["adm-paies-tableau-divers"],
)


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


_XLSX_MIME = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


@router.post("/lister", response_model=ListerDemandesResult)
def post_lister(
    params: ListerDemandesParams,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GenTabDivers")
    return svc.lister_demandes(params)


@router.post("/generer-valandre")
def post_generer_valandre(
    params: GenererValandreParams,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GenTabDivers")
    if not params.lignes:
        raise HTTPException(status_code=400, detail="Aucun vendeur")
    fic_name, content = svc.generer_valandre_xlsx(params)
    if not content:
        raise HTTPException(status_code=500, detail="openpyxl indisponible")
    return Response(
        content=content, media_type=_XLSX_MIME,
        headers={
            "Content-Disposition": f'attachment; filename="{fic_name}"',
        },
    )


@router.post("/generer-comptable")
def post_generer_comptable(
    params: GenererComptableParams,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "GenTabDivers")
    try:
        fic_name, content = svc.generer_comptable_xlsx(params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not content:
        raise HTTPException(status_code=500, detail="openpyxl indisponible")
    return Response(
        content=content, media_type=_XLSX_MIME,
        headers={
            "Content-Disposition": f'attachment; filename="{fic_name}"',
        },
    )
