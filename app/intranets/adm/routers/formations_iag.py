"""
Router Fen_importFormIAG (ADM Salaries -> Suivi des formations IAG).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import formations_iag as svc


router = APIRouter(prefix="/formations-iag", tags=["adm-formations-iag"])


@router.get("/a-former")
def get_a_former(_user: UserToken = Depends(get_current_user)):
    """Liste des salaries actifs concernes par la formation IAG."""
    return svc.list_a_former()


@router.post("/import")
async def post_import(
    file: UploadFile = File(...),
    cols: str = Form(""),
    limit_jours: int = Form(30),
    simulation: bool = Form(True),
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Importer le fichier' : Excel formations IAG."""
    content = await file.read()
    try:
        cols_dict = json.loads(cols) if cols else {}
    except Exception:
        raise HTTPException(400, "cols invalide (JSON attendu)")
    res = svc.import_formations(
        content, cols_dict, limit_jours, simulation, user.id_salarie,
    )
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec import")
    return res
