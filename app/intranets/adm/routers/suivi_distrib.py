"""
Router Suivi Distributeurs (Fen_SuiviDistrib + FI_DetailDistributeur).

Endpoints :
  GET /distributeurs                            - liste (?actif=1|0)
  GET /distributeurs/{id_ste}                   - bootstrap detail
  GET /distributeurs/{id_ste}/docs-unique       - docs uniques + tickets
  GET /distributeurs/{id_ste}/docs-annuel       - docs annuels (?annee=YYYY)
  GET /distributeurs/{id_ste}/facturations      - liste tickets facturation

Droits : SuiviADMDistri (base) + SuiviADMDistDoc (docs).
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import suivi_distrib as svc

router = APIRouter(
    prefix="/distributeurs",
    tags=["adm-suivi-distrib"],
)


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


# --------------------------------------------------------------------
# READ
# --------------------------------------------------------------------

@router.get("")
def get_list(
    actif: bool = Query(True),
    user: UserToken = Depends(get_current_user),
):
    """Liste des distributeurs (id_type_orga=3)."""
    _require_droit(user, "SuiviADMDistri")
    return {"items": svc.list_societes(actif=actif)}


@router.get("/{id_ste}")
def get_detail(
    id_ste: int,
    user: UserToken = Depends(get_current_user),
):
    """Bootstrap detail : dates + annees dispo + gerant."""
    _require_droit(user, "SuiviADMDistri")
    data = svc.get_detail_bootstrap(id_ste)
    if not data:
        raise HTTPException(status_code=404, detail="Societe introuvable")
    return data


@router.get("/{id_ste}/docs-unique")
def get_docs_unique(
    id_ste: int,
    user: UserToken = Depends(get_current_user),
):
    """Liste des docs uniques (rappel_annuel=0) pour la societe."""
    _require_droit(user, "SuiviADMDistDoc")
    return {"items": svc.list_docs_unique(id_ste)}


@router.get("/{id_ste}/docs-annuel")
def get_docs_annuel(
    id_ste: int,
    annee: int = Query(default_factory=lambda: date.today().year),
    user: UserToken = Depends(get_current_user),
):
    """Liste des docs annuels (rappel_annuel>0) pour l'annee donnee."""
    _require_droit(user, "SuiviADMDistDoc")
    return {"items": svc.list_docs_annuel(id_ste, annee), "annee": int(annee)}


@router.get("/{id_ste}/facturations")
def get_facturations(
    id_ste: int,
    user: UserToken = Depends(get_current_user),
):
    """Liste des tickets de facturation pour la societe."""
    _require_droit(user, "SuiviADMDistri")
    return {"items": svc.list_facturations(id_ste)}
