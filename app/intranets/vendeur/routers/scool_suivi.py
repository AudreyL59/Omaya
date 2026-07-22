"""Router Suivi Scool (Vendeur)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.vendeur.services import scool_suivi as svc

router = APIRouter(prefix="/scool", tags=["vendeur-scool"])


@router.get("/formations")
def get_formations(
    date_min: str = Query("", description="Date min ISO YYYY-MM-DD, defaut = aujourd'hui"),
    actives: bool = Query(True, description="Uniquement formations actives"),
    search: str = Query("", description="Filtre intitule + ville"),
    user: UserToken = Depends(get_current_user),
):
    return svc.liste_formations(
        int(user.id_salarie), user.droits or [], date_min, actives, search,
    )


@router.get("/formations/{id_formation}/stagiaires")
def get_stagiaires(id_formation: str,
                    _user: UserToken = Depends(get_current_user)):
    try:
        id_f = int(id_formation)
    except (TypeError, ValueError):
        return []
    return svc.stagiaires_formation(id_f)
