"""Endpoints mobile CallSFR (WebRest_Omayapp/CallSFR/*).

Portage iso-URL des 13 WS CallSFR mobile WinDev.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from app.mobile.deps import mobile_auth
from app.intranets.vendeur.services import ticket_call_procs as tc

router = APIRouter(tags=["mobile-call-sfr"],
                    dependencies=[Depends(mobile_auth)])


# ---------------------------------------------------------------------------
#  Referentiels
# ---------------------------------------------------------------------------

@router.get("/CallSFR/AnomalieListe")
def anomalie_liste():
    return tc.sfr_liste_anomalie()


# ---------------------------------------------------------------------------
#  Liste clients + gestion ticket
# ---------------------------------------------------------------------------

@router.post("/CallSFR/ClientsNonFinalises")
def sfr_clients_non_finalises(payload: dict = Body(default={}),
                                id_salarie: int = Depends(mobile_auth)):
    id_vend = tc._to_int(payload.get("IDSalarie") or id_salarie)
    return tc.sfr_liste_clients_non_finalises(id_vend)


@router.post("/CallSFR/NouveauTK")
def sfr_nouveau_tk(payload: dict = Body(...),
                    id_salarie: int = Depends(mobile_auth)):
    return tc.sfr_crea_modif_tk_call(payload, id_salarie)


@router.post("/CallSFR/ClientsNonFinalises/Suppr")
def sfr_suppr(payload: dict = Body(...),
               id_salarie: int = Depends(mobile_auth)):
    id_tk = tc._to_int(payload.get("IDTK_Liste"))
    return tc.sfr_supprimer_ticket(id_tk, id_salarie)


@router.post("/CallSFR/ClientsNonFinalises/Validation")
def sfr_validation(payload: dict = Body(...),
                    id_salarie: int = Depends(mobile_auth)):
    id_tk = tc._to_int(payload.get("IDTK_Liste"))
    return tc.sfr_validation_tk_call(id_tk, id_salarie)


@router.post("/CallSFR/ClientsNonFinalises/EnvoiLien")
def sfr_envoi_lien(payload: dict = Body(...)):
    id_tk = tc._to_int(payload.get("IDTK_Liste"))
    code = (payload.get("Code") or payload.get("code") or "").strip()
    return tc.sfr_envoi_lien_client(id_tk, code)


@router.post("/CallSFR/ClientsNonFinalises/VerifPhoto")
def sfr_verif_photo(payload: dict = Body(...)):
    id_tk = tc._to_int(payload.get("IDTK_Liste"))
    nom = payload.get("NomPhoto") or payload.get("nom_photo") or ""
    return tc.sfr_verif_photo(id_tk, nom)


@router.post("/CallSFR/ClientsNonFinalises/AnomalieMobile")
def sfr_anomalie_mobile(payload: dict = Body(...),
                          id_salarie: int = Depends(mobile_auth)):
    """Vente mobile differee : passe le ticket en anomalie mobile."""
    id_tk = tc._to_int(payload.get("IDTK_Liste"))
    id_anom = tc._to_int(payload.get("IDtk_CallSFR_Anomalie"))
    info_cplt = payload.get("InfoCpltAnomalie") or ""
    return tc.sfr_vente_mobile_diff(id_tk, id_anom, info_cplt, id_salarie)


# ---------------------------------------------------------------------------
#  Panier
# ---------------------------------------------------------------------------

@router.post("/CallSFR/ClientsNonFinalises/Panier")
def sfr_panier(payload: dict = Body(...)):
    id_tk = tc._to_int(payload.get("IDTK_Liste"))
    return tc.sfr_contenu_panier(id_tk)


@router.post("/CallSFR/ClientsNonFinalises/Panier/Produit/Ajout")
def sfr_panier_ajout(payload: dict = Body(...)):
    return tc.sfr_ajouter_produit_panier(payload)


@router.post("/CallSFR/ClientsNonFinalises/Panier/Produit/Suppr")
def sfr_panier_suppr(payload: dict = Body(...)):
    id_pan = tc._to_int(payload.get("IDtk_CallSFR_Panier"))
    return tc.sfr_supprimer_produit_panier(id_pan)


# ---------------------------------------------------------------------------
#  Non portes (TXT WinDev manquant)
# ---------------------------------------------------------------------------

@router.post("/CallSFR/DegroupagePanier")
def sfr_degroupage(_payload: dict = Body(default={})):
    """TODO : port a faire des que le TXT WinDev est fourni."""
    raise HTTPException(501, "CallSFR/DegroupagePanier non encore porte")


@router.post("/CallSFR/G")
def sfr_g(_payload: dict = Body(default={})):
    """TODO : port a faire des que le TXT WinDev est fourni.
    Nom d'endpoint ambigu ('G' seul) — probablement une tronque dans
    le xlsx. A verifier avec le TXT."""
    raise HTTPException(501, "CallSFR/G non encore porte")
