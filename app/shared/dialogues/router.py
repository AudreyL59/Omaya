"""Router shared Dialogues (chat + workflow ticket).

Pattern factory (identique a shared/recrutement) : chaque intranet
appelle `get_dialogues_router(intranet_key)` pour monter les endpoints
sous son propre prefixe (/api/vendeur/dialogues, /api/adm/dialogues).

Le param `usersCial` conserve dans les URLs vient du portage strict de
l'API mobile Flutter. Cote intranet Web, on injecte l'id du user
connecte au moment du fetch.
"""

from __future__ import annotations

import logging

import os
from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.shared.dialogues.schemas.dialogues import (
    Dialogue, DialogueMsgPayload, DialoguePJPayload, DialogueSavePayload,
    DialogueStatut, DialogueTheme, MsgModifPayload, MsgSupprPayload,
    ReponseTK, SalarieDest, DialogueMsg, DialoguePJ, TacheIT,
)
from app.shared.dialogues.services import (
    destinataires as dest_svc,
    enregistre as enr_svc,
    liste as liste_svc,
    marquer_lu as lu_svc,
    msg as msg_svc,
    pj as pj_svc,
    statuts as statuts_svc,
    taches_it as taches_it_svc,
    themes as themes_svc,
)

logger = logging.getLogger(__name__)


def get_dialogues_router(intranet_key: str) -> APIRouter:
    """Construit le router /dialogues pour un intranet donne.

    intranet_key : 'vendeur' | 'adm' (utilise pour tag/log)
    """
    router = APIRouter(prefix="/dialogues", tags=[f"dialogues-{intranet_key}"])

    # -- Referentiels -------------------------------------------------------

    @router.get("/statuts", response_model=list[DialogueStatut])
    def get_statuts(_user: UserToken = Depends(get_current_user)):
        return statuts_svc.liste_statuts()

    @router.get("/themes", response_model=list[DialogueTheme])
    def get_themes(_user: UserToken = Depends(get_current_user)):
        return themes_svc.liste_themes()

    @router.post("/liste-dest", response_model=list[SalarieDest])
    def post_liste_dest(_user: UserToken = Depends(get_current_user)):
        return dest_svc.liste_destinataires()

    # -- Liste dialogues (la grosse) ---------------------------------------

    @router.post("/liste-json/{type_msg}/{id_vend}", response_model=list[Dialogue])
    def post_liste_json(type_msg: int, id_vend: str,
                         _user: UserToken = Depends(get_current_user)):
        """type_msg : 0 = actifs, autre = clos. id_vend en str car IDs 8 octets."""
        try:
            id_v = int(id_vend)
        except (TypeError, ValueError):
            id_v = 0
        return liste_svc.liste_dialogues(int(type_msg), id_v)

    # -- Marquer lu --------------------------------------------------------

    @router.get("/marquer-lu/{id_dial}/{id_vend}", response_model=ReponseTK)
    def get_marquer_lu(id_dial: str, id_vend: str,
                        _user: UserToken = Depends(get_current_user)):
        try:
            id_d = int(id_dial); id_v = int(id_vend)
        except (TypeError, ValueError):
            return ReponseTK(nIdDemande="0", sInfoData="ids invalides")
        return lu_svc.marquer_lu(id_d, id_v)

    # -- Create / update dialogue ------------------------------------------

    @router.post("/enregistre/{id_vend}", response_model=Dialogue)
    def post_enregistre(id_vend: str, payload: DialogueSavePayload = Body(...),
                         _user: UserToken = Depends(get_current_user)):
        try:
            id_v = int(id_vend)
        except (TypeError, ValueError):
            id_v = 0
        return enr_svc.enregistrer_dialogue(payload, id_v)

    # -- Messages ----------------------------------------------------------

    @router.post("/enregistre-pjmsg", response_model=DialogueMsg)
    def post_enr_pjmsg(payload: DialogueMsgPayload = Body(...),
                        _user: UserToken = Depends(get_current_user)):
        return msg_svc.envoyer_msg(payload)

    @router.post("/modif-msg", response_model=DialogueMsg)
    def post_modif_msg(payload: MsgModifPayload = Body(...),
                        user: UserToken = Depends(get_current_user)):
        return msg_svc.modifier_msg(payload, int(user.id_salarie))

    @router.post("/suppr-msg", response_model=DialogueMsg)
    def post_suppr_msg(payload: MsgSupprPayload = Body(...),
                        user: UserToken = Depends(get_current_user)):
        return msg_svc.supprimer_msg(payload, int(user.id_salarie))

    # -- Pieces jointes ----------------------------------------------------

    @router.post("/enregistre-pj", response_model=DialoguePJ)
    def post_enr_pj(payload: DialoguePJPayload = Body(...),
                     _user: UserToken = Depends(get_current_user)):
        return pj_svc.enregistrer_pj(payload)

    # -- Suivi IT : taches liees a un dialogue -----------------------------

    @router.get("/{id_dialogue}/taches-it", response_model=list[TacheIT])
    def get_taches_it(id_dialogue: str,
                       _user: UserToken = Depends(get_current_user)):
        try:
            id_d = int(id_dialogue)
        except (TypeError, ValueError):
            return []
        return taches_it_svc.liste_taches_it(id_d)

    # -- Upload / download PJ ---------------------------------------------

    @router.post("/upload-fichier/{id_dialogue}")
    async def upload_fichier(id_dialogue: str,
                              file: UploadFile = File(...),
                              _user: UserToken = Depends(get_current_user)):
        """Ecrit le fichier dans {DOCS_BASE_PATH}/DocConv/{id_dialogue}/{filename}.
        Cree le dossier si besoin. Ne cree PAS l'entree pgt_dialoguepj :
        l'appel /enregistre-pj (ou /enregistre-pjmsg) suivra.
        """
        try:
            id_d = int(id_dialogue)
        except (TypeError, ValueError):
            raise HTTPException(400, "id_dialogue invalide")
        if not id_d:
            raise HTTPException(400, "id_dialogue = 0")
        filename = (file.filename or "").strip() or "upload.bin"
        # Interdit tout chemin relatif (path traversal)
        filename = os.path.basename(filename)
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

    @router.get("/fichier/{id_dialogue}/{nom_fic}")
    def download_fichier(id_dialogue: str, nom_fic: str,
                          _user: UserToken = Depends(get_current_user)):
        """Sert un fichier depuis DocConv/{id_dialogue}/{nom_fic}."""
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

    return router
