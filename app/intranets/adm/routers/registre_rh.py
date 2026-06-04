"""Endpoints REST du Registre RH (ADM)."""

import sys
import traceback
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.registre_rh import (
    RegistreRefs,
    SalarieRegistre,
    SocieteOption,
)
from app.intranets.adm.services import registre_rh as svc

router = APIRouter(prefix="/registre-rh", tags=["adm-registre-rh"])


@router.get("/societes", response_model=list[SocieteOption])
def get_societes(user: UserToken = Depends(get_current_user)):
    try:
        return svc.list_societes()
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/refs", response_model=RegistreRefs)
def get_refs(user: UserToken = Depends(get_current_user)):
    try:
        return svc.list_refs()
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("", response_model=list[SalarieRegistre])
def get_salaries(
    id_ste: int = Query(..., description="IdSte selectionne dans la combo"),
    user: UserToken = Depends(get_current_user),
):
    try:
        return svc.list_salaries(id_ste)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/export.xlsx")
def export_xlsx(
    id_ste: int = Query(..., description="IdSte de la societe a exporter"),
    user: UserToken = Depends(get_current_user),
):
    """Genere et renvoie le Registre RH au format .xlsx."""
    try:
        data, filename = svc.export_xlsx(id_ste)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

    # RFC 5987 : filename* pour supporter les accents/espaces
    cd = f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": cd},
    )
