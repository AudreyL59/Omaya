"""Endpoints REST de la Fiche Salarie ADM."""

import sys
import traceback

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.fiche_salarie import (
    FicheCoordonnees,
    FicheHeader,
    FicheIdentite,
    SaveCoordonneesPayload,
    SaveIdentitePayload,
    SaveResponse,
    ToggleStatusPayload,
)
from app.intranets.adm.services import fiche_salarie as svc

router = APIRouter(prefix="/fiche-salarie", tags=["adm-fiche-salarie"])


@router.get("/{id_salarie}/photo")
def get_photo(id_salarie: int = Path(...), user: UserToken = Depends(get_current_user)):
    """Photo du salarie (bytea decode + content-type auto). 404 si pas de photo."""
    try:
        result = svc.load_photo(id_salarie)
        if not result:
            raise HTTPException(status_code=404, detail="Pas de photo")
        data, content_type = result
        return Response(
            content=data,
            media_type=content_type,
            headers={"Cache-Control": "private, max-age=300"},
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/{id_salarie}/header", response_model=FicheHeader)
def get_header(id_salarie: int = Path(...), user: UserToken = Depends(get_current_user)):
    try:
        data = svc.load_header(id_salarie)
        if not data:
            raise HTTPException(status_code=404, detail="Salarie introuvable")
        return data
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/{id_salarie}/identite", response_model=FicheIdentite)
def get_identite(id_salarie: int = Path(...), user: UserToken = Depends(get_current_user)):
    try:
        data = svc.load_identite(id_salarie)
        if not data:
            raise HTTPException(status_code=404, detail="Salarie introuvable")
        return data
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/{id_salarie}/identite", response_model=SaveResponse)
def save_identite(
    payload: SaveIdentitePayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    try:
        # On filtre les champs non fournis pour ne PAS ecraser avec None
        body = payload.model_dump(exclude_unset=True)
        return svc.save_identite(id_salarie, body)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/{id_salarie}/actif", response_model=SaveResponse)
def toggle_actif(
    payload: ToggleStatusPayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    try:
        return svc.set_en_activite(id_salarie, payload.value)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/{id_salarie}/en-pause", response_model=SaveResponse)
def toggle_en_pause(
    payload: ToggleStatusPayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    try:
        return svc.set_en_pause(id_salarie, payload.value)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


# --- Onglet 2 : Coordonnees ---------------------------------------------

@router.get("/{id_salarie}/coordonnees", response_model=FicheCoordonnees)
def get_coordonnees(id_salarie: int = Path(...), user: UserToken = Depends(get_current_user)):
    try:
        return svc.load_coordonnees(id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/{id_salarie}/coordonnees", response_model=SaveResponse)
def save_coordonnees(
    payload: SaveCoordonneesPayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    try:
        body = payload.model_dump(exclude_unset=True)
        return svc.save_coordonnees(id_salarie, body)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
