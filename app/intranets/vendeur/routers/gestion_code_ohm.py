"""Router Gestion Code OHM (Vendeur)."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query

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
