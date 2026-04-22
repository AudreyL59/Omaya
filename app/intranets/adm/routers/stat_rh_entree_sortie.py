from fastapi import APIRouter, Depends, Query

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.stat_rh_entree_sortie import StatEntreeSortieResponse
from app.intranets.adm.services.stat_rh_entree_sortie import calculer_stats_entree_sortie

router = APIRouter(prefix="/stat-rh", tags=["adm-stat-rh"])


@router.get("/entree-sortie", response_model=StatEntreeSortieResponse)
def get_stats_entree_sortie(
    date_du: str = Query(..., description="YYYYMMDD"),
    date_au: str = Query(..., description="YYYYMMDD"),
    type_recherche: str = Query("reseau", description="reseau ou orga"),
    id_orga: list[str] = Query(
        default=[],
        description="IDs des orgas a scoper (mode orga). Plusieurs possibles via id_orga=1&id_orga=2. String pour preserver la precision > 2^53.",
    ),
    user: UserToken = Depends(get_current_user),
):
    """
    Stats DPAE et Sortie sur une periode.

    - type_recherche = 'reseau' : tout le reseau (requiert droit StatsRHGr)
    - type_recherche = 'orga'   : salaries rattaches a l'une des id_orga ou leurs descendants
    """
    # Protection : reseau complet requiert StatsRHGr
    if type_recherche == "reseau" and "StatsRHGr" not in user.droits:
        if not id_orga:
            return {"dpae": [], "sorties": [], "resume": []}
        type_recherche = "orga"

    # Convertir les strings en int (cote backend uniquement ; Python gere nativement les ints arbitraires)
    orgas_scope: list[int] = []
    for raw in id_orga or []:
        try:
            v = int(raw)
            if v > 0:
                orgas_scope.append(v)
        except (ValueError, TypeError):
            continue

    return calculer_stats_entree_sortie(
        date_debut=date_du,
        date_fin=date_au,
        type_recherche=type_recherche,
        id_orgas=orgas_scope,
    )
