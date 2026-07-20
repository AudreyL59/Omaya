"""
Router Vendeur - Ticket Call FIBRE SFR (proxy Phase 2).

Reproduit exactement l'API WebRest_Omayapp/CallSFR/... et /SFR/...
utilisee par l'ecran Flutter Fen_CallSFR.

Cf. docs/tickets_call_screens_analysis.md.

Droit d'acces : BS_SFR (deja cable dans le menu Vendeur).
"""
from __future__ import annotations

import urllib.error
import urllib.request

from fastapi import APIRouter, Body, Depends, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.core.config import WEBREST_BASE_URL
from app.intranets.vendeur.services.ws_client import (
    WSError, get, post, encode_path_segment as _enc,
)


router = APIRouter(
    prefix="/ticket-call-fibre",
    tags=["vendeur-ticket-call-fibre"],
)


def _require(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(403, f"Droit manquant : {code}")


def _users_cial(user: UserToken) -> str:
    return _enc(user.id_salarie or 0)


def _proxy(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except WSError as e:
        raise HTTPException(status_code=502, detail=str(e))


# --- Init : tickets + anomalies -----------------------------------------

@router.post("/clients-non-finalises")
def list_clients_non_finalises(
    user: UserToken = Depends(get_current_user),
):
    """POST /CallSFR/ClientsNonFinalises/{usersCial}."""
    _require(user, "BS_SFR")
    return _proxy(post, f"/CallSFR/ClientsNonFinalises/{_users_cial(user)}")


@router.get("/anomalies")
def anomalie_liste(user: UserToken = Depends(get_current_user)):
    """GET /CallSFR/AnomalieListe -> Liste des motifs d'anomalie mobile."""
    _require(user, "BS_SFR")
    return _proxy(get, "/CallSFR/AnomalieListe")


# --- Panier d'un ticket --------------------------------------------------

@router.post("/panier/{id_ticket}")
def get_panier(
    id_ticket: str,
    user: UserToken = Depends(get_current_user),
):
    """POST /CallSFR/ClientsNonFinalises/Panier/{id_ticket}."""
    _require(user, "BS_SFR")
    return _proxy(post, f"/CallSFR/ClientsNonFinalises/Panier/{_enc(id_ticket)}")


# --- Ticket : suppression / creation -------------------------------------

@router.post("/supprimer-ticket")
def supprimer_ticket(
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /CallSFR/ClientsNonFinalises/Suppr/{usersCial}
    Body : {IDTK_Liste}."""
    _require(user, "BS_SFR")
    return _proxy(
        post,
        f"/CallSFR/ClientsNonFinalises/Suppr/{_users_cial(user)}",
        payload=payload,
    )


@router.post("/nouveau-ticket")
def nouveau_ticket(
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /CallSFR/NouveauTK/{usersCial}
    Body : infos client (avec Mobile2)."""
    _require(user, "BS_SFR")
    return _proxy(
        post,
        f"/CallSFR/NouveauTK/{_users_cial(user)}",
        payload=payload,
        timeout=90.0,
    )


# --- Offres SFR ----------------------------------------------------------

@router.get("/offres/{type_offre}/{avec_tv}")
def lister_offres(
    type_offre: str,
    avec_tv: str,
    user: UserToken = Depends(get_current_user),
):
    """GET /SFR/ListerOffres/{type}/{avecTV}
    type = FIBRE | MOBILE | FIB PRO | MOB PRO, avecTV = 0|1."""
    _require(user, "BS_SFR")
    return _proxy(get, f"/SFR/ListerOffres/{_enc(type_offre)}/{_enc(avec_tv)}")


# --- Panier : ajout / suppression / anomalie -----------------------------

@router.post("/panier/produit/ajouter")
def ajouter_produit(
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /CallSFR/ClientsNonFinalises/Panier/Produit/Ajout."""
    _require(user, "BS_SFR")
    return _proxy(
        post,
        "/CallSFR/ClientsNonFinalises/Panier/Produit/Ajout",
        payload=payload,
    )


@router.post("/panier/produit/supprimer")
def supprimer_produit(
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /CallSFR/ClientsNonFinalises/Panier/Produit/Suppr
    Body : {IDtk_CallSFR_Panier}."""
    _require(user, "BS_SFR")
    return _proxy(
        post,
        "/CallSFR/ClientsNonFinalises/Panier/Produit/Suppr",
        payload=payload,
    )


@router.post("/panier/anomalie-mobile/{id_ind}")
def anomalie_mobile(
    id_ind: str,
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /CallSFR/ClientsNonFinalises/AnomalieMobile/{usersCial}/{idInd}
    idInd = 0 (init bascule differee) | 1 (changement motif)
    Body : {IDTK_Liste, IDtk_CallSFR_Anomalie, InfoCplAnomalie}."""
    _require(user, "BS_SFR")
    return _proxy(
        post,
        f"/CallSFR/ClientsNonFinalises/AnomalieMobile/{_users_cial(user)}/{_enc(id_ind)}",
        payload=payload,
    )


# --- Validation panier par SMS ------------------------------------------

@router.post("/envoi-lien/{code}")
def envoi_lien(
    code: str,
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /CallSFR/ClientsNonFinalises/EnvoiLien/{code}
    Body : {IDTK_Liste}."""
    _require(user, "BS_SFR")
    return _proxy(
        post,
        f"/CallSFR/ClientsNonFinalises/EnvoiLien/{_enc(code)}",
        payload=payload,
    )


@router.post("/validation")
def validation(
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /CallSFR/ClientsNonFinalises/Validation/{usersCial}
    Body : {IDTK_Liste}."""
    _require(user, "BS_SFR")
    return _proxy(
        post,
        f"/CallSFR/ClientsNonFinalises/Validation/{_users_cial(user)}",
        payload=payload,
    )


# --- Verification photo (CIN / KBIS) -------------------------------------

@router.get("/verif-photo/{id_ticket}/{type_doc}")
def verif_photo(
    id_ticket: str,
    type_doc: str,
    user: UserToken = Depends(get_current_user),
):
    """GET /CallSFR/ClientsNonFinalises/VerifPhoto/{id_ticket}/{type}
    type = PieceIdentite | KBIS."""
    _require(user, "BS_SFR")
    return _proxy(
        get,
        f"/CallSFR/ClientsNonFinalises/VerifPhoto/{_enc(id_ticket)}/{_enc(type_doc)}",
    )


# --- Verif presence lettre de resiliation sur DocOmaya -------------------

@router.get("/lettre-resil-existe/{id_ticket}")
def lettre_resil_existe(
    id_ticket: str,
    user: UserToken = Depends(get_current_user),
):
    """HEAD (partial GET) sur {lienSiteRest}/DocOmaya/{id_ticket}_LettreResil.pdf
    -> {"exists": true|false}."""
    _require(user, "BS_SFR")
    url = f"{WEBREST_BASE_URL.rstrip('/')}/DocOmaya/{_enc(id_ticket)}_LettreResil.pdf"
    try:
        req = urllib.request.Request(
            url, method="GET", headers={"Range": "bytes=0-0"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return {"exists": 200 <= resp.status < 300}
    except urllib.error.HTTPError as e:
        return {"exists": e.code in (200, 206)}
    except Exception:
        return {"exists": False}
