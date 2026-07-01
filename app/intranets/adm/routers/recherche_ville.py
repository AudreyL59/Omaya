"""Router ADM > Fen_RechercheVille (picker commune + ajout commune)."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import recherche_ville as svc

router = APIRouter(prefix="/rech-ville", tags=["adm-rech-ville"])


@router.get("/search", response_model=list[svc.CommuneItem])
def get_rech_ville_search(
    cp: str = "",
    nom: str = "",
    limit: int = 500,
    _u: UserToken = Depends(get_current_user),
):
    return svc.search_communes(cp, nom, limit)


@router.post("", response_model=svc.CommuneItem)
def post_rech_ville_create(
    payload: svc.CommunePayload,
    u: UserToken = Depends(get_current_user),
):
    """Ajoute une commune (droit AjoutCommune requis cf WinDev)."""
    if "AjoutCommune" not in (u.droits or []):
        raise HTTPException(403, "Droit AjoutCommune requis pour ajouter une ville")
    try:
        id_new = svc.create_commune(payload, u.id_salarie)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return svc.CommuneItem(
        id_communes_france=str(id_new),
        code_postal=payload.code_postal,
        nom_ville=payload.nom_ville.upper(),
        departement=payload.departement,
        code_commune=payload.code_commune,
        code_pays=payload.code_pays,
        latitude_deg=payload.latitude_deg,
        longitude_deg=payload.longitude_deg,
        favorite=False,
    )
