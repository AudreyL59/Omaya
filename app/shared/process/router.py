"""Router shared Process (bibliotheque de procedures/tutos).

Pattern factory : chaque intranet monte via get_process_router(intranet_key,
can_edit). ADM = can_edit=True (CRUD), Vendeur = can_edit=False (lecture
seule).

Cote frontend, `canEdit` est aussi passé pour masquer les boutons +/edit/
trash — mais le backend valide QUAND MEME (defense en profondeur).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.shared.process.schemas.process import (
    Process, ProcessDroitSavePayload, ProcessListItem, ProcessSavePayload,
    ProfilItem,
)
from app.shared.process.services import (
    crud as crud_svc,
    diagramme as diag_svc,
    droits as droits_svc,
    fichiers as fichiers_svc,
    list_service as list_svc,
    salaries as salaries_svc,
)

logger = logging.getLogger(__name__)


def get_process_router(intranet_key: str, can_edit: bool) -> APIRouter:
    """Construit le router /process pour un intranet donne.

    intranet_key : 'vendeur' | 'adm'
    can_edit     : True pour ADM (CRUD), False pour Vendeur (read only)
    """
    router = APIRouter(prefix="/process", tags=[f"process-{intranet_key}"])

    def _require_edit():
        if not can_edit:
            raise HTTPException(403, "Ce module est en lecture seule dans cet intranet")

    # -- Lecture (accessible aux 2 intranets) -----------------------------

    @router.get("", response_model=list[ProcessListItem])
    def get_list(search: str = Query("", description="Filtre titre + mots-clés"),
                  user: UserToken = Depends(get_current_user)):
        return list_svc.liste_process(int(user.id_salarie), search)

    @router.get("/services", response_model=list[str])
    def get_services(_user: UserToken = Depends(get_current_user)):
        return list_svc.liste_services_distincts()

    @router.get("/profils", response_model=list[ProfilItem])
    def get_profils(_user: UserToken = Depends(get_current_user)):
        return droits_svc.liste_profils()

    @router.get("/societes", response_model=list[dict])
    def get_societes(_user: UserToken = Depends(get_current_user)):
        return list_svc.liste_societes()

    @router.get("/salaries-search", response_model=list[dict])
    def get_salaries_search(q: str = Query("", min_length=0),
                             _user: UserToken = Depends(get_current_user)):
        return salaries_svc.search_salaries(q)

    @router.get("/{id_process}/diagramme")
    def get_diagramme(id_process: str,
                       _user: UserToken = Depends(get_current_user)):
        try:
            id_p = int(id_process)
        except (TypeError, ValueError):
            raise HTTPException(400, "id_process invalide")
        return {"json": diag_svc.get_diagramme(id_p) or ""}

    @router.put("/{id_process}/diagramme")
    def put_diagramme(id_process: str, payload: dict = Body(...),
                       user: UserToken = Depends(get_current_user)):
        _require_edit()
        try:
            id_p = int(id_process)
        except (TypeError, ValueError):
            raise HTTPException(400, "id_process invalide")
        js = payload.get("json") if isinstance(payload, dict) else None
        if not isinstance(js, str):
            js = ""
        ok = diag_svc.save_diagramme(id_p, js, int(user.id_salarie))
        if not ok:
            raise HTTPException(500, "echec sauvegarde diagramme")
        return {"ok": True}

    @router.get("/{id_process}", response_model=Process)
    def get_one(id_process: str,
                 _user: UserToken = Depends(get_current_user)):
        try:
            id_p = int(id_process)
        except (TypeError, ValueError):
            raise HTTPException(400, "id_process invalide")
        p = crud_svc.get_process(id_p)
        if not p:
            raise HTTPException(404, "process introuvable")
        return p

    @router.get("/fichier/{id_fichier}")
    def download_fichier(id_fichier: str,
                          _user: UserToken = Depends(get_current_user)):
        try:
            id_f = int(id_fichier)
        except (TypeError, ValueError):
            raise HTTPException(400, "id_fichier invalide")
        r = fichiers_svc.get_fichier(id_f)
        if not r:
            raise HTTPException(404, "fichier introuvable")
        contenu, filename, mime = r
        return Response(
            content=contenu, media_type=mime,
            headers={"Content-Disposition":
                     f'inline; filename="{filename}"'},
        )

    # -- Ecriture (ADM uniquement) ----------------------------------------

    @router.post("/save", response_model=dict)
    def post_save(payload: ProcessSavePayload = Body(...),
                   user: UserToken = Depends(get_current_user)):
        _require_edit()
        id_p = crud_svc.save_process(payload, int(user.id_salarie))
        if not id_p:
            raise HTTPException(500, "echec sauvegarde")
        return {"IDProcess": id_p}

    @router.delete("/{id_process}")
    def delete_one(id_process: str,
                    user: UserToken = Depends(get_current_user)):
        _require_edit()
        try:
            id_p = int(id_process)
        except (TypeError, ValueError):
            raise HTTPException(400, "id_process invalide")
        ok = crud_svc.delete_process(id_p, int(user.id_salarie))
        if not ok:
            raise HTTPException(500, "echec suppression")
        return {"ok": True}

    # -- Fichiers (ADM uniquement pour add/delete) -------------------------

    @router.post("/{id_process}/fichier")
    async def add_fichier(id_process: str,
                           file: UploadFile = File(...),
                           user: UserToken = Depends(get_current_user)):
        _require_edit()
        try:
            id_p = int(id_process)
        except (TypeError, ValueError):
            raise HTTPException(400, "id_process invalide")
        content = await file.read()
        id_f = fichiers_svc.add_fichier(
            id_p, file.filename or "fichier", content, int(user.id_salarie))
        if not id_f:
            raise HTTPException(500, "echec upload")
        return {"IDProcessFichier": id_f}

    @router.delete("/fichier/{id_fichier}")
    def delete_fichier(id_fichier: str,
                        user: UserToken = Depends(get_current_user)):
        _require_edit()
        try:
            id_f = int(id_fichier)
        except (TypeError, ValueError):
            raise HTTPException(400, "id_fichier invalide")
        ok = fichiers_svc.delete_fichier(id_f, int(user.id_salarie))
        if not ok:
            raise HTTPException(500, "echec suppression")
        return {"ok": True}

    # -- Droits (ADM uniquement) ------------------------------------------

    @router.post("/droit/save", response_model=dict)
    def post_save_droit(payload: ProcessDroitSavePayload = Body(...),
                         user: UserToken = Depends(get_current_user)):
        _require_edit()
        id_d = droits_svc.save_droit(payload, int(user.id_salarie))
        if not id_d:
            raise HTTPException(500, "echec sauvegarde droit")
        return {"IDProcessDroit": id_d}

    @router.delete("/droit/{id_droit}")
    def delete_droit(id_droit: str,
                      user: UserToken = Depends(get_current_user)):
        _require_edit()
        try:
            id_d = int(id_droit)
        except (TypeError, ValueError):
            raise HTTPException(400, "id_droit invalide")
        ok = droits_svc.delete_droit(id_d, int(user.id_salarie))
        if not ok:
            raise HTTPException(500, "echec suppression droit")
        return {"ok": True}

    return router
