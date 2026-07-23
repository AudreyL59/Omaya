"""Endpoints mobile Call (WebRest_Omayapp/Call/*).

Portage iso-URL des 14 WS Call mobile WinDev. Reutilise les procs
partagees deja portees cote web (app.intranets.vendeur.services.ticket_call_procs).
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from app.mobile.deps import mobile_auth
from app.intranets.vendeur.services import ticket_call_procs as tc

router = APIRouter(tags=["mobile-call"],
                    dependencies=[Depends(mobile_auth)])


# ---------------------------------------------------------------------------
#  Liste clients + gestion ticket
# ---------------------------------------------------------------------------

@router.post("/Call/ClientsNonFinalises")
def clients_non_finalises(payload: dict = Body(default={}),
                           id_salarie: int = Depends(mobile_auth)):
    """Liste des clients non finalises du vendeur.
    Payload WinDev accepte : { IDSalarie: int }. Fallback : user
    authentifie via Bearer.
    """
    id_vend = tc._to_int(payload.get("IDSalarie") or id_salarie)
    return tc.liste_clients_non_finalises(id_vend)


@router.post("/Call/ContenuCall")
def contenu_call(payload: dict = Body(...)):
    """Detail d'un ticket Call + son panier. Portage DonneInfoTkCall.

    Payload : {IDTK_Liste: int}
    """
    id_tk = tc._to_int(payload.get("IDTK_Liste"))
    return tc.call_contenu_call(id_tk)


@router.post("/Call/NouveauTK")
def nouveau_tk(payload: dict = Body(...),
                id_salarie: int = Depends(mobile_auth)):
    """Creation/modification d'un ticket Call. Portage crea_modif_tk_call."""
    return tc.crea_modif_tk_call(payload, id_salarie)


@router.post("/Call/ClientsNonFinalises/Suppr")
def suppr_ticket(payload: dict = Body(...),
                  id_salarie: int = Depends(mobile_auth)):
    id_tk = tc._to_int(payload.get("IDTK_Liste"))
    return tc.supprimer_ticket_call(id_tk, id_salarie)


@router.post("/Call/ClientsNonFinalises/Validation")
def validation(payload: dict = Body(...),
                id_salarie: int = Depends(mobile_auth)):
    id_tk = tc._to_int(payload.get("IDTK_Liste"))
    return tc.validation_tk_call(id_tk, id_salarie)


@router.post("/Call/ClientsNonFinalises/EnvoiLien")
def envoi_lien(payload: dict = Body(...)):
    id_tk = tc._to_int(payload.get("IDTK_Liste"))
    code = (payload.get("Code") or payload.get("code") or "").strip()
    return tc.envoi_lien_client_call(id_tk, code)


@router.post("/Call/ClientsNonFinalises/VerifPhoto")
def verif_photo(payload: dict = Body(...)):
    id_tk = tc._to_int(payload.get("IDTK_Liste"))
    nom = payload.get("NomPhoto") or payload.get("nom_photo") or ""
    return tc.verif_photo(id_tk, nom)


# ---------------------------------------------------------------------------
#  Panier
# ---------------------------------------------------------------------------

@router.post("/Call/ClientsNonFinalises/Panier")
def panier(payload: dict = Body(...)):
    id_tk = tc._to_int(payload.get("IDTK_Liste"))
    return tc.contenu_panier_call(id_tk)


@router.post("/Call/ClientsNonFinalises/Panier/Produit/Ajout")
def panier_ajout(payload: dict = Body(...)):
    return tc.ajouter_produit_panier_call(payload)


@router.post("/Call/ClientsNonFinalises/Panier/Produit/Suppr")
def panier_suppr(payload: dict = Body(...)):
    id_pan = tc._to_int(payload.get("IDtk_Call_Panier"))
    return tc.supprimer_produit_panier_call(id_pan)


# ---------------------------------------------------------------------------
#  Referentiels
# ---------------------------------------------------------------------------

@router.post("/Call/ProduitActifs")
def produits_actifs(payload: dict = Body(...)):
    part = (payload.get("Part") or payload.get("part") or "").upper().strip()
    return tc.liste_produit_actif_by_part(part)


@router.post("/Call/ProduitActifs/VAL")
def produits_actifs_val(_payload: dict = Body(default={})):
    """Variante WinDev : shortcut sur partenaire VAL."""
    return tc.liste_produit_actif_by_part("VAL")


@router.get("/Call/OHM/ListeTypeInstall")
def ohm_types_install():
    return tc.ohm_liste_type_install()


@router.post("/Call/AjoutNumBS")
def ajout_num_bs(payload: dict = Body(...),
                  id_salarie: int = Depends(mobile_auth)):
    """Update NumBS d'une ligne panier. Portage AjouterNumBS."""
    return tc.call_ajout_num_bs(payload, id_salarie)
