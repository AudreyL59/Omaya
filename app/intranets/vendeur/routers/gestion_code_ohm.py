"""Router Gestion Code OHM (Vendeur)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.vendeur.services import gestion_code_ohm as svc

# Prefixe /gestion-ohm reutilise l'ancien placeholder.
router = APIRouter(prefix="/gestion-ohm", tags=["vendeur-gestion-ohm"])


@router.get("/demandes")
def get_demandes(
    onglet: int = Query(1, description="1=en cours (type 38), 2=à désactiver (type 39)"),
    _user: UserToken = Depends(get_current_user),
):
    type_demande = svc.TYPE_DEMANDE_ENCOURS if onglet == 1 \
                    else svc.TYPE_DEMANDE_A_DESACTIVER
    return svc.liste_demandes(type_demande)


@router.get("/demandes/{id_tk_liste}/fichiers")
def get_fichiers(id_tk_liste: str,
                  _user: UserToken = Depends(get_current_user)):
    try:
        id_l = int(id_tk_liste)
    except (TypeError, ValueError):
        return []
    return svc.fichiers_demande(id_l)


@router.post("/demandes/{id_tk_liste}/enregistrer")
def post_enregistrer(id_tk_liste: str, payload: dict = Body(...),
                      user: UserToken = Depends(get_current_user)):
    try:
        id_l = int(id_tk_liste)
    except (TypeError, ValueError):
        raise HTTPException(400, "id_tk_liste invalide")
    ok = svc.enregistrer_modif(
        id_l, payload.get("code") or "", payload.get("login") or "",
        payload.get("mdp") or "", int(user.id_salarie),
    )
    if not ok:
        raise HTTPException(500, "echec enregistrement")
    return {"ok": True}


@router.post("/demandes/{id_tk_liste}/rejet")
def post_rejet(id_tk_liste: str,
                user: UserToken = Depends(get_current_user)):
    try:
        id_l = int(id_tk_liste)
    except (TypeError, ValueError):
        raise HTTPException(400, "id_tk_liste invalide")
    ok = svc.rejet_manque_document(id_l, int(user.id_salarie))
    if not ok:
        raise HTTPException(500, "echec rejet")
    return {"ok": True}


@router.post("/export-selection")
def post_export(payload: dict = Body(...),
                 user: UserToken = Depends(get_current_user)):
    """Export XLSX + ZIP FTP des demandes selectionnees + passage
    statut a 35. Payload : {'ids': [str, ...]}."""
    raw_ids = payload.get("ids") or []
    ids: list[int] = []
    for r in raw_ids:
        try:
            ids.append(int(r))
        except (TypeError, ValueError):
            continue
    if not ids:
        raise HTTPException(400, "Aucun ID valide")
    zip_bytes = svc.export_selection(ids, int(user.id_salarie))
    if not zip_bytes:
        raise HTTPException(500, "echec export")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        content=zip_bytes, media_type="application/zip",
        headers={"Content-Disposition":
                 f'attachment; filename="Demandes_Accreditations_{stamp}.zip"'},
    )


@router.post("/import-codes")
async def post_import(
    file: UploadFile = File(..., description="Fichier XLSX"),
    col_code: str = Form(..., description="Lettre colonne code (A/B/…)"),
    col_mdp: str = Form(..., description="Lettre colonne mdp"),
    col_nom: str = Form(..., description="Lettre colonne nom"),
    col_prenom: str = Form(..., description="Lettre colonne prénom"),
    user: UserToken = Depends(get_current_user),
):
    """Import XLSX : renseigne les codes en masse. Chaque ligne matche
    par code puis par nom+prenom, update la demande, envoie mail vendeur
    si TypeOri = DPAE."""
    content = await file.read()
    if not content:
        raise HTTPException(400, "Fichier vide")
    try:
        result = svc.import_codes(
            content, col_code, col_mdp, col_nom, col_prenom,
            int(user.id_salarie),
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception:
        raise HTTPException(500, "echec import")
    return result
