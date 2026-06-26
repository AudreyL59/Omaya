"""Router Fen_ChoixImports (ADM Imports Bases -> Import contrats).

Endpoints :
  GET /imports/partenaires      -> combo partenaires (Fen_ChoixImports)
  GET /imports/auto-suivi       -> tableau de progression (polling)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import imports as svc


router = APIRouter(prefix="/imports", tags=["adm-imports"])


@router.get("/partenaires", response_model=list[svc.PartenaireImport])
def get_partenaires(_user: UserToken = Depends(get_current_user)):
    return svc.list_partenaires()


@router.get("/auto-suivi", response_model=list[svc.ImportAutoSuivi])
def get_auto_suivi(_user: UserToken = Depends(get_current_user)):
    return svc.list_imports_auto_suivi()
