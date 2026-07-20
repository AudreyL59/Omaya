"""
Router Vendeur - Ticket Call ENERGIE (proxy Phase 2).

Reproduit exactement l'API WebRest_Omayapp/Call/... utilisee par
l'ecran Flutter Fen_Call. Chaque endpoint proxie l'appel via ws_client
vers le WS WinDev existant.

Phase 3 : chaque proxy sera remplace au fur et a mesure par un service
PG direct. Cf. docs/tickets_call_screens_analysis.md.

Droit d'acces : TkCALL (deja cable dans le menu Vendeur).
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.vendeur.services import ticket_call_procs as procs
from app.intranets.vendeur.services.ws_client import (
    WSError, get, post, encode_path_segment as _enc,
)


router = APIRouter(
    prefix="/ticket-call-energie",
    tags=["vendeur-ticket-call-energie"],
)


def _require(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(403, f"Droit manquant : {code}")


def _users_cial(user: UserToken) -> str:
    """usersCial pour les URLs WinDev = id_salarie du user connecte."""
    return _enc(user.id_salarie or 0)


def _proxy(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except WSError as e:
        raise HTTPException(status_code=502, detail=str(e))


# --- Init : tickets en cours + partenaires -------------------------------

@router.post("/clients-non-finalises")
def list_clients_non_finalises(
    user: UserToken = Depends(get_current_user),
):
    """POST /Call/ClientsNonFinalises/{usersCial}
    -> Liste des tickets non finalises du commercial.

    Phase 3 : porte en PG cf. procs.liste_clients_non_finalises().
    """
    _require(user, "TkCALL")
    return procs.liste_clients_non_finalises(int(user.id_salarie or 0))


@router.post("/partenaires")
def list_partenaires(user: UserToken = Depends(get_current_user)):
    """POST /PartCall -> Liste des partenaires (Nom, Bdd, Logo, Couleur).

    Phase 3 : porte en PG cf. procs.list_part_call().
    """
    _require(user, "TkCALL")
    return procs.list_part_call()


# --- Panier d'un ticket --------------------------------------------------

@router.post("/panier/{id_ticket}")
def get_panier(
    id_ticket: str,
    user: UserToken = Depends(get_current_user),
):
    """POST /Call/ClientsNonFinalises/Panier/{id_ticket}
    -> Liste des produits du panier.

    Phase 3 : porte en PG cf. procs.contenu_panier_call().
    """
    _require(user, "TkCALL")
    return procs.contenu_panier_call(int(id_ticket))


# --- Ticket : suppression / creation --------------------------------------

@router.post("/supprimer-ticket")
def supprimer_ticket(
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /Call/ClientsNonFinalises/Suppr/{usersCial}
    Body : {IDTK_Liste}.

    Phase 3 : porte en PG cf. procs.supprimer_ticket_call().
    NOTE : le .txt WinDev fourni est vide — implementation deduite
    (UPDATE modif_elem = 'suppr').
    """
    _require(user, "TkCALL")
    return procs.supprimer_ticket_call(int(payload.get("IDTK_Liste") or 0))


@router.post("/nouveau-ticket")
def nouveau_ticket(
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /Call/NouveauTK/{usersCial}
    Body : infos client (civilite, nom, prenom, ...)."""
    _require(user, "TkCALL")
    # Le WS peut mettre jusqu'a ~1 min a repondre pour la creation
    # (cf. kCreateReceiveTimeout cote Flutter).
    return _proxy(
        post,
        f"/Call/NouveauTK/{_users_cial(user)}",
        payload=payload,
        timeout=90.0,
    )


# --- Produits actifs d'un partenaire --------------------------------------

@router.post("/produits-actifs/{part}")
def produits_actifs(
    part: str,
    user: UserToken = Depends(get_current_user),
):
    """POST /Call/ProduitActifs/{part} (part = OEN/ENI/STR/VAL/PRO/OHM).
    -> Liste des produits actifs du partenaire.

    Phase 3 : porte en PG cf. procs.liste_produit_actif_by_part().
    """
    _require(user, "TkCALL")
    return procs.liste_produit_actif_by_part(part)


# --- OHM ------------------------------------------------------------------

@router.get("/ohm/liste-type-install")
def ohm_liste_type_install(
    user: UserToken = Depends(get_current_user),
):
    """GET /Call/OHM/ListeTypeInstall -> Liste des types d'installation OHM.

    Phase 3 : porte en PG (hardcode 4 types) cf. procs.ohm_liste_type_install().
    """
    _require(user, "TkCALL")
    return procs.ohm_liste_type_install()


# --- Panier : ajout / suppression de produit ------------------------------

@router.post("/panier/produit/ajouter")
def ajouter_produit(
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /Call/ClientsNonFinalises/Panier/Produit/Ajout
    Body : produit (~30 champs).

    Phase 3 : porte en PG cf. procs.ajouter_produit_panier_call().
    """
    _require(user, "TkCALL")
    return procs.ajouter_produit_panier_call(payload)


@router.post("/panier/produit/supprimer")
def supprimer_produit(
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /Call/ClientsNonFinalises/Panier/Produit/Suppr
    Body : {IDtk_Call_Panier}.

    Phase 3 : porte en PG cf. procs.supprimer_produit_panier_call().
    """
    _require(user, "TkCALL")
    return procs.supprimer_produit_panier_call(
        int(payload.get("IDtk_Call_Panier") or 0),
    )


# --- Validation panier par SMS -------------------------------------------

@router.post("/envoi-lien/{code}")
def envoi_lien(
    code: str,
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /Call/ClientsNonFinalises/EnvoiLien/{code}
    Body : {IDTK_Liste}. Envoie le SMS + lien + mail au client.

    Phase 3 : porte en PG cf. procs.envoi_lien_client_call().
    """
    _require(user, "TkCALL")
    return procs.envoi_lien_client_call(
        int(payload.get("IDTK_Liste") or 0),
        str(code),
    )


@router.post("/validation")
def validation(
    payload: dict = Body(default_factory=dict),
    user: UserToken = Depends(get_current_user),
):
    """POST /Call/ClientsNonFinalises/Validation/{usersCial}
    Body : {IDTK_Liste}. Cloture le ticket (statut a traiter = 1).

    Phase 3 : porte en PG cf. procs.validation_tk_call().
    """
    _require(user, "TkCALL")
    return procs.validation_tk_call(
        int(payload.get("IDTK_Liste") or 0),
        int(user.id_salarie or 0),
    )


# --- Verification photo (CIN / KBIS / Justif) ----------------------------

@router.get("/verif-photo/{id_ticket}/{type_doc}")
def verif_photo(
    id_ticket: str,
    type_doc: str,
    user: UserToken = Depends(get_current_user),
):
    """GET /Call/ClientsNonFinalises/VerifPhoto/{id_ticket}/{type}
    type = PieceIdentite | KBIS | Justif.

    Phase 3 : porte en PG cf. procs.verif_photo() (HEAD HTTP DocOmaya).
    """
    _require(user, "TkCALL")
    return procs.verif_photo(int(id_ticket), type_doc)
