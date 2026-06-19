"""
Router Fen_TdbUlease + Fen_FicheVehicule (ADM Ulease -> Parc Auto).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import fiche_vehicule as fv_svc
from app.intranets.adm.services import parc_auto as svc


router = APIRouter(prefix="/parc-auto", tags=["adm-parc-auto"])


@router.get("/vehicules")
def get_vehicules(_user: UserToken = Depends(get_current_user)):
    """Tableau de bord : tous les vehicules en circulation + alertes."""
    return svc.list_vehicules_actifs()


# ---------------------------------------------------------------------------
# Fen_FicheVehicule
# ---------------------------------------------------------------------------


@router.get("/lookups")
def get_lookups(_user: UserToken = Depends(get_current_user)):
    """Combos marques / etats / types_capacite / societes / types_possession."""
    return fv_svc.get_lookups()


@router.get("/vehicules/{id_vehicule}")
def get_vehicule(
    id_vehicule: int,
    _user: UserToken = Depends(get_current_user),
):
    """Fiche complete vehicule pour Plan 1 + header."""
    v = fv_svc.get_vehicule(id_vehicule)
    if not v:
        raise HTTPException(404, "Véhicule introuvable")
    return v


class VehiculePayload(BaseModel):
    id_vehicule_marque: int = 0
    modele: str = ""
    immat: str = ""
    chevaux_fiscaux: int = 0
    date_mise_circulation: str = ""
    id_vehicule_type_capacite: int = 0
    date_deb: str = ""
    date_fin: str = ""
    id_ste_proprio: int = 0
    id_ste_reseau: int = 0
    achat_loc: str = ""
    id_vehicule_etat: int = 0
    forfait_km: int = 0
    k_mdepart: int = 0
    km_actuel: int = 0
    km_mensuel: int = 0
    date_releve: str = ""
    info_vehicule: str = ""


@router.put("/vehicules/{id_vehicule}")
def put_vehicule(
    id_vehicule: int,
    payload: VehiculePayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn Enregistrer Plan 1 (Info Vehicule)."""
    return fv_svc.update_vehicule(id_vehicule, payload.model_dump(), user.id_salarie)


@router.delete("/vehicules/{id_vehicule}")
def delete_vehicule(
    id_vehicule: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Supprimer la fiche : soft delete."""
    return fv_svc.delete_vehicule(id_vehicule, user.id_salarie)
