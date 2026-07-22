"""Endpoints mobile 'petits WS unitaires' (WebRest_Omayapp/*).

Porte tout ce qui peut l'etre sans TXT WinDev supplementaire (services
deja en place cote web). Les autres sont en 501 en attente des TXT.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from app.mobile.deps import mobile_auth
from app.intranets.vendeur.services import ticket_call_procs as tc

router = APIRouter(tags=["mobile-misc"],
                    dependencies=[Depends(mobile_auth)])


# ---------------------------------------------------------------------------
#  Portage direct depuis les services existants
# ---------------------------------------------------------------------------

@router.post("/PartCall")
def part_call(_payload: dict = Body(default={})):
    """Liste des partenaires actifs cote Call.
    Portage ListePartCall WinDev -> tc.list_part_call().
    Reponse : [{Nom, Bdd, Logo(base64), Couleur(RVB int)}]
    """
    return tc.list_part_call()


# ---------------------------------------------------------------------------
#  En attente des TXT WinDev
# ---------------------------------------------------------------------------

@router.post("/AjoutLog")
def ajout_log(_payload: dict = Body(default={})):
    raise HTTPException(501, "AjoutLog non encore porte (TXT manquant)")


@router.post("/ExoNews")
def exo_news(_payload: dict = Body(default={})):
    raise HTTPException(501, "ExoNews non encore porte (TXT manquant)")


@router.post("/ListePoste")
def liste_poste(_payload: dict = Body(default={})):
    raise HTTPException(501, "ListePoste non encore porte (TXT manquant)")


@router.post("/ListeSteActive")
def liste_ste_active(_payload: dict = Body(default={})):
    raise HTTPException(501, "ListeSteActive non encore porte (TXT manquant)")


@router.post("/ListeTypeProd")
def liste_type_prod(_payload: dict = Body(default={})):
    raise HTTPException(501, "ListeTypeProd non encore porte (TXT manquant)")


@router.post("/ListeVilleByCP")
def liste_ville_by_cp(_payload: dict = Body(default={})):
    raise HTTPException(501, "ListeVilleByCP non encore porte (TXT manquant)")


@router.post("/News/Liste")
def news_liste(_payload: dict = Body(default={})):
    raise HTTPException(501, "News/Liste non encore porte (TXT manquant)")


@router.post("/Org/Liste")
def org_liste(_payload: dict = Body(default={})):
    raise HTTPException(501, "Org/Liste non encore porte (TXT manquant)")


@router.post("/Podium")
def podium(_payload: dict = Body(default={})):
    raise HTTPException(501, "Podium non encore porte (TXT manquant)")


@router.post("/TKDPAE/ListeBySalarie")
def tkdpae_liste(_payload: dict = Body(default={})):
    raise HTTPException(501, "TKDPAE/ListeBySalarie non encore porte (TXT manquant)")


# NotifPush
@router.post("/NotifPush/EnrNotif")
def notifpush_enr(_payload: dict = Body(default={})):
    raise HTTPException(501, "NotifPush/EnrNotif non encore porte (TXT manquant)")


@router.post("/NotifPush/Liste")
def notifpush_liste(_payload: dict = Body(default={})):
    raise HTTPException(501, "NotifPush/Liste non encore porte (TXT manquant)")


# Signature
@router.post("/Signature/MiseADispo/Liste")
def signature_liste(_payload: dict = Body(default={})):
    raise HTTPException(501, "Signature/MiseADispo/Liste non encore porte (TXT manquant)")


@router.post("/Signature/MiseADispo/Signer")
def signature_signer(_payload: dict = Body(default={})):
    raise HTTPException(501, "Signature/MiseADispo/Signer non encore porte (TXT manquant)")


# TK* (4 groupes symetriques : TKAttEC, TKAvance, TKCong, TKFourniture)
@router.post("/TKAttEC/Ajouter")
def tkattec_ajouter(_payload: dict = Body(default={})):
    raise HTTPException(501, "TKAttEC/Ajouter non encore porte (TXT manquant)")


@router.post("/TKAttEC/ListeBySalarie")
def tkattec_liste(_payload: dict = Body(default={})):
    raise HTTPException(501, "TKAttEC/ListeBySalarie non encore porte (TXT manquant)")


@router.post("/TKAvance/Ajouter")
def tkavance_ajouter(_payload: dict = Body(default={})):
    raise HTTPException(501, "TKAvance/Ajouter non encore porte (TXT manquant)")


@router.post("/TKAvance/ListeBySalarie")
def tkavance_liste(_payload: dict = Body(default={})):
    raise HTTPException(501, "TKAvance/ListeBySalarie non encore porte (TXT manquant)")


@router.post("/TKCong/Ajouter")
def tkcong_ajouter(_payload: dict = Body(default={})):
    raise HTTPException(501, "TKCong/Ajouter non encore porte (TXT manquant)")


@router.post("/TKCong/ListeBySalarie")
def tkcong_liste(_payload: dict = Body(default={})):
    raise HTTPException(501, "TKCong/ListeBySalarie non encore porte (TXT manquant)")


@router.post("/TKFourniture/Ajouter")
def tkfourn_ajouter(_payload: dict = Body(default={})):
    raise HTTPException(501, "TKFourniture/Ajouter non encore porte (TXT manquant)")


@router.post("/TKFourniture/ListeBySalarie")
def tkfourn_liste(_payload: dict = Body(default={})):
    raise HTTPException(501, "TKFourniture/ListeBySalarie non encore porte (TXT manquant)")


# Notifications
@router.post("/Notifications/ListeBySalarie")
def notifications_liste(_payload: dict = Body(default={})):
    raise HTTPException(501, "Notifications/ListeBySalarie non encore porte (TXT manquant)")


@router.post("/Notifications/MarquerLue")
def notifications_marquer_lue(_payload: dict = Body(default={})):
    raise HTTPException(501, "Notifications/MarquerLue non encore porte (TXT manquant)")


@router.post("/Notifications/MarquerToutLu")
def notifications_marquer_tout(_payload: dict = Body(default={})):
    raise HTTPException(501, "Notifications/MarquerToutLu non encore porte (TXT manquant)")


# SignPDF
@router.post("/SignPDF/Fichier")
def signpdf_fichier(_payload: dict = Body(default={})):
    raise HTTPException(501, "SignPDF/Fichier non encore porte (TXT manquant)")


@router.post("/SignPDF/ListeBySalarie")
def signpdf_liste(_payload: dict = Body(default={})):
    raise HTTPException(501, "SignPDF/ListeBySalarie non encore porte (TXT manquant)")


@router.post("/SignPDF/Signer")
def signpdf_signer(_payload: dict = Body(default={})):
    raise HTTPException(501, "SignPDF/Signer non encore porte (TXT manquant)")
