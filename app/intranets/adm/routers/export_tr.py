"""
Router Fen_ExportFicTR - Export CSV pour Commande de TR.

Endpoints :
  POST /adm/paies/export-tr/recherche-entite   - Btn Lancer par entite
  POST /adm/paies/export-tr/recherche-salarie  - Btn Lancer par salarie
  POST /adm/paies/export-tr/export-csv         - Btn Export CSV
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.export_tr import (
    ExportCsvParams, RechercheParEntiteParams, RechercheParSalarieParams,
    RechercheResult,
)
from app.intranets.adm.services import export_tr as svc

router = APIRouter(prefix="/paies/export-tr", tags=["adm-paies-export-tr"])


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


@router.post("/recherche-entite", response_model=RechercheResult)
def post_recherche_entite(
    params: RechercheParEntiteParams,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "ExportTR")
    return svc.rechercher_par_entite(params)


@router.post("/recherche-salarie", response_model=RechercheResult)
def post_recherche_salarie(
    params: RechercheParSalarieParams,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "ExportTR")
    return svc.rechercher_par_salarie(params)


@router.post("/export-csv")
def post_export_csv(
    params: ExportCsvParams,
    user: UserToken = Depends(get_current_user),
):
    """Genere le CSV et le retourne en download direct."""
    _require_droit(user, "ExportTR")
    if not params.lignes:
        raise HTTPException(status_code=400, detail="Aucune ligne a exporter")
    fic_name, content = svc.generer_csv(params)
    return Response(
        content=content,
        media_type="text/csv; charset=windows-1252",
        headers={
            "Content-Disposition": f'attachment; filename="{fic_name}"',
        },
    )
