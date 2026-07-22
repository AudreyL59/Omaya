"""Endpoints mobile Dialogues (WebRest_Omayapp/Dialogues/*).

Portage iso-URL des 10 WS WinDev Dialogues. Reutilise les services
partages deja portes cote web (app.shared.dialogues.services).

Pas de duplication de logique metier — juste re-expose sous les URLs
WinDev pour permettre au mobile Flutter de basculer sans changer sa
convention de nommage.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.mobile.deps import mobile_auth
from app.shared.dialogues.schemas.dialogues import (
    DialogueMsgPayload, DialoguePJPayload, DialogueSavePayload,
    MsgModifPayload, MsgSupprPayload,
)
from app.shared.dialogues.services import (
    destinataires as dest_svc,
    enregistre as enr_svc,
    liste as liste_svc,
    marquer_lu as lu_svc,
    msg as msg_svc,
    pj as pj_svc,
    statuts as statuts_svc,
    themes as themes_svc,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mobile-dialogues"],
                    dependencies=[Depends(mobile_auth)])


# ---------------------------------------------------------------------------
#  Referentiels
# ---------------------------------------------------------------------------

@router.get("/Dialogues/Statuts")
def get_statuts():
    return statuts_svc.liste_statuts()


@router.get("/Dialogues/Themes")
def get_themes():
    return themes_svc.liste_themes()


@router.post("/Dialogues/ListeDest")
def post_liste_dest(_payload: dict = Body(default={})):
    return dest_svc.liste_destinataires()


# ---------------------------------------------------------------------------
#  Liste dialogues + marquage lu
# ---------------------------------------------------------------------------

@router.post("/Dialogues/ListeJSON/{type_msg}/{user_cial}")
def post_liste_json(type_msg: int, user_cial: str,
                     _payload: dict = Body(default={})):
    try:
        id_v = int(user_cial)
    except (TypeError, ValueError):
        id_v = 0
    return liste_svc.liste_dialogues(int(type_msg), id_v)


@router.get("/Dialogues/MarquerLu/{id_dial}/{user_cial}")
def get_marquer_lu(id_dial: str, user_cial: str):
    try:
        id_d = int(id_dial); id_v = int(user_cial)
    except (TypeError, ValueError):
        return {"nIdDemande": "0", "sInfoData": "ids invalides"}
    return lu_svc.marquer_lu(id_d, id_v)


# ---------------------------------------------------------------------------
#  Create / update / messages / PJ
# ---------------------------------------------------------------------------

@router.post("/Dialogues/Enregistre/{user_cial}")
def post_enregistre(user_cial: str, payload: DialogueSavePayload = Body(...)):
    try:
        id_v = int(user_cial)
    except (TypeError, ValueError):
        id_v = 0
    return enr_svc.enregistrer_dialogue(payload, id_v)


@router.post("/Dialogues/EnregistrePJMSG")
def post_enr_pjmsg(payload: DialogueMsgPayload = Body(...)):
    return msg_svc.envoyer_msg(payload)


@router.post("/Dialogues/EnregistrePJ")
def post_enr_pj(payload: DialoguePJPayload = Body(...)):
    return pj_svc.enregistrer_pj(payload)


@router.post("/Dialogues/ModifMSG")
def post_modif_msg(payload: MsgModifPayload = Body(...),
                    id_salarie: int = Depends(mobile_auth)):
    return msg_svc.modifier_msg(payload, id_salarie)


@router.post("/Dialogues/SupprMSG")
def post_suppr_msg(payload: MsgSupprPayload = Body(...),
                    id_salarie: int = Depends(mobile_auth)):
    return msg_svc.supprimer_msg(payload, id_salarie)


# ---------------------------------------------------------------------------
#  Upload / download PJ (RecepFichier + acces DocConv)
# ---------------------------------------------------------------------------

@router.post("/Dialogues/UploadFichier/{id_dialogue}")
async def upload_fichier(id_dialogue: str, file: UploadFile = File(...)):
    """Upload PJ d'un dialogue. Path miroir de l'API web
    /api/vendeur/dialogues/upload-fichier/{id} mais avec URL iso mobile.
    """
    try:
        id_d = int(id_dialogue)
    except (TypeError, ValueError):
        raise HTTPException(400, "id_dialogue invalide")
    if not id_d:
        raise HTTPException(400, "id_dialogue = 0")
    filename = (file.filename or "").strip() or "upload.bin"
    filename = os.path.basename(filename)  # anti path-traversal
    base = os.environ.get("DOCS_BASE_PATH", r"D:\OMAYA")
    target_dir = os.path.join(base, "DocConv", str(id_d))
    try:
        os.makedirs(target_dir, exist_ok=True)
    except Exception as e:
        raise HTTPException(500, f"mkdir failed: {e}")
    target_path = os.path.join(target_dir, filename)
    try:
        data = await file.read()
        with open(target_path, "wb") as f:
            f.write(data)
    except Exception as e:
        raise HTTPException(500, f"write failed: {e}")
    return {"fileName": filename, "fileSize": len(data), "ResEnvoi": True}


@router.get("/Dialogues/Fichier/{id_dialogue}/{nom_fic}")
def download_fichier(id_dialogue: str, nom_fic: str):
    try:
        id_d = int(id_dialogue)
    except (TypeError, ValueError):
        raise HTTPException(400, "id_dialogue invalide")
    nom_fic = os.path.basename(nom_fic or "")
    base = os.environ.get("DOCS_BASE_PATH", r"D:\OMAYA")
    path = os.path.join(base, "DocConv", str(id_d), nom_fic)
    if not os.path.exists(path):
        raise HTTPException(404, "fichier introuvable")
    return FileResponse(path, filename=nom_fic)
