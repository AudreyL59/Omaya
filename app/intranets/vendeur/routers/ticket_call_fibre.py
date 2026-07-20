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
from app.intranets.vendeur.services import ticket_call_procs as procs
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
    """POST /CallSFR/ClientsNonFinalises/{usersCial}.

    Phase 3 : PG cf. procs.sfr_liste_clients_non_finalises().
    """
    _require(user, "BS_SFR")
    return procs.sfr_liste_clients_non_finalises(int(user.id_salarie or 0))


@router.get("/anomalies")
def anomalie_liste(user: UserToken = Depends(get_current_user)):
    """GET /CallSFR/AnomalieListe -> Liste des motifs d'anomalie mobile.

    Phase 3 : PG cf. procs.sfr_liste_anomalie().
    """
    _require(user, "BS_SFR")
    return procs.sfr_liste_anomalie()


# --- Panier d'un ticket --------------------------------------------------

@router.post("/panier/{id_ticket}")
def get_panier(
    id_ticket: str,
    user: UserToken = Depends(get_current_user),
):
    """POST /CallSFR/ClientsNonFinalises/Panier/{id_ticket}.

    Phase 3 : PG cf. procs.sfr_contenu_panier().
    """
    _require(user, "BS_SFR")
    return procs.sfr_contenu_panier(int(id_ticket))


# --- Ticket : suppression / creation -------------------------------------

@router.post("/supprimer-ticket")
def supprimer_ticket(
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /CallSFR/ClientsNonFinalises/Suppr/{usersCial}
    Body : {IDTK_Liste}.

    Phase 3 : PG cf. procs.sfr_supprimer_ticket() (identique Energie).
    """
    _require(user, "BS_SFR")
    return procs.sfr_supprimer_ticket(
        int(payload.get("IDTK_Liste") or 0),
        int(user.id_salarie or 0),
    )


@router.post("/nouveau-ticket")
def nouveau_ticket(
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /CallSFR/NouveauTK/{usersCial}
    Body : infos client (avec Mobile2).

    Phase 3 : PG cf. procs.sfr_crea_modif_tk_call().
    Anti-doublon tel client/salarie + blocage >75 ans + mail ALERT
    CALL SFR (cf. WinDev AjoutTicketCallSFR).
    """
    _require(user, "BS_SFR")
    return procs.sfr_crea_modif_tk_call(payload, int(user.id_salarie or 0))


# --- Offres SFR ----------------------------------------------------------

@router.get("/offres/{type_offre}/{avec_tv}")
def lister_offres(
    type_offre: str,
    avec_tv: str,
    user: UserToken = Depends(get_current_user),
):
    """GET /SFR/ListerOffres/{type}/{avecTV}
    type = FIBRE | MOBILE | FIB PRO | MOB PRO, avecTV = 0|1.

    Phase 3 : PG cf. procs.sfr_lister_offres().
    """
    _require(user, "BS_SFR")
    return procs.sfr_lister_offres(type_offre, avec_tv in ("1", "true", "True"))


# --- Panier : ajout / suppression / anomalie -----------------------------

@router.post("/panier/produit/ajouter")
def ajouter_produit(
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /CallSFR/ClientsNonFinalises/Panier/Produit/Ajout.

    Phase 3 : PG cf. procs.sfr_ajouter_produit_panier().
    """
    _require(user, "BS_SFR")
    return procs.sfr_ajouter_produit_panier(payload)


@router.post("/panier/produit/supprimer")
def supprimer_produit(
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /CallSFR/ClientsNonFinalises/Panier/Produit/Suppr
    Body : {IDtk_CallSFR_Panier}.

    Phase 3 : PG cf. procs.sfr_supprimer_produit_panier().
    Suppression LOGIQUE (modif_elem='suppr'), diverge du panier Energie
    qui fait un DELETE physique.
    """
    _require(user, "BS_SFR")
    return procs.sfr_supprimer_produit_panier(
        int(payload.get("IDtk_CallSFR_Panier") or 0),
    )


@router.post("/panier/anomalie-mobile/{id_ind}")
def anomalie_mobile(
    id_ind: str,
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /CallSFR/ClientsNonFinalises/AnomalieMobile/{usersCial}/{idInd}
    idInd = 0 (init bascule differee) | 1 (changement motif)
    Body : {IDTK_Liste, IDtk_CallSFR_Anomalie, InfoCplAnomalie}.

    Phase 3 : PG cf. procs.sfr_vente_mobile_diff().
    NOTE : les colonnes anomalie_mobile + id_tk_call_sfr_type_anomalie
    + info_cplt_anomalie ne sont pas encore dans le schema PG interne.
    L'UPDATE retournera sInfoData explicatif en cas d'echec — la
    fonctionnalite sera pleinement operationnelle des replication
    SymmetricDS de ces colonnes.
    """
    _require(user, "BS_SFR")
    return procs.sfr_vente_mobile_diff(
        int(payload.get("IDTK_Liste") or 0),
        int(payload.get("IDtk_CallSFR_Anomalie") or 0),
        payload.get("InfoCplAnomalie") or "",
        int(user.id_salarie or 0),
        int(id_ind or 0),
    )


# --- Validation panier par SMS ------------------------------------------

@router.post("/envoi-lien/{code}")
def envoi_lien(
    code: str,
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /CallSFR/ClientsNonFinalises/EnvoiLien/{code}
    Body : {IDTK_Liste}.

    Phase 3 : PG cf. procs.sfr_envoi_lien_client() (SMS + mail).
    """
    _require(user, "BS_SFR")
    return procs.sfr_envoi_lien_client(
        int(payload.get("IDTK_Liste") or 0),
        str(code),
    )


@router.post("/validation")
def validation(
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /CallSFR/ClientsNonFinalises/Validation/{usersCial}
    Body : {IDTK_Liste}.

    Phase 3 : PG cf. procs.sfr_validation_tk_call() (statut=1 +
    date_crea + modif). Conversion PieceIdentite.png -> CIN.jpg
    (WinDev) skip cote Python (acces FS distant).
    """
    _require(user, "BS_SFR")
    return procs.sfr_validation_tk_call(
        int(payload.get("IDTK_Liste") or 0),
        int(user.id_salarie or 0),
    )


# --- Verification photo (CIN / KBIS) -------------------------------------

@router.get("/verif-photo/{id_ticket}/{type_doc}")
def verif_photo(
    id_ticket: str,
    type_doc: str,
    user: UserToken = Depends(get_current_user),
):
    """GET /CallSFR/ClientsNonFinalises/VerifPhoto/{id_ticket}/{type}
    type = PieceIdentite | KBIS.

    Phase 3 : PG cf. procs.sfr_verif_photo() (HEAD HTTP DocOmaya).
    """
    _require(user, "BS_SFR")
    return procs.sfr_verif_photo(int(id_ticket), type_doc)


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
