"""Router shared Recrutement / Recherche CV.

Pattern factory : chaque intranet (ADM, Vendeur, Call RH) inclut son
propre router via :
    router.include_router(get_recherche_cv_router("adm"))

`intranet_key` permet :
- de filtrer automatiquement la liste (ex: Vendeur ne voit que ses CV)
- de logger les actions cote audit
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.shared.recrutement.schemas.cv_fiche import (
    CVFicheDetail, CVFichePayload, CVObservationPayload,
    CVStatutQuickPayload, CVSuiviRow,
)
from app.shared.recrutement.schemas.recherche_cv import (
    CommuneItem, ComboItem, CVRow, SearchCVFiltres,
)
from app.shared.recrutement.services import cv_fiche as fiche_svc
from app.shared.recrutement.services import recherche_cv as svc


def get_recherche_cv_router(intranet_key: str) -> APIRouter:
    """Construit le router /recrutement/cv pour un intranet donne.

    intranet_key : "adm", "vendeur", "call_rh"
    """
    router = APIRouter(prefix="/recrutement/cv", tags=["recrutement-cv"])

    @router.get("/sources", response_model=list[ComboItem])
    def get_sources(_user: UserToken = Depends(get_current_user)):
        return svc.list_sources()

    @router.get("/statuts", response_model=list[ComboItem])
    def get_statuts(_user: UserToken = Depends(get_current_user)):
        return svc.list_statuts()

    @router.get("/postes", response_model=list[ComboItem])
    def get_postes(_user: UserToken = Depends(get_current_user)):
        return svc.list_postes()

    @router.get("/annonceurs", response_model=list[ComboItem])
    def get_annonceurs(_user: UserToken = Depends(get_current_user)):
        return svc.list_annonceurs()

    @router.get("/societes", response_model=list[ComboItem])
    def get_societes(_user: UserToken = Depends(get_current_user)):
        return svc.list_societes()

    @router.get("/communes", response_model=list[CommuneItem])
    def get_communes(
        q: str = Query(..., min_length=2),
        limit: int = Query(50, ge=1, le=200),
        _user: UserToken = Depends(get_current_user),
    ):
        return svc.search_communes(q, limit)

    @router.post("/search", response_model=list[CVRow])
    def post_search(
        filtres: SearchCVFiltres,
        user: UserToken = Depends(get_current_user),
    ):
        # Filtre auto Vendeur : force id_cvsource=1 + id_elem_source=user
        if intranet_key == "vendeur":
            filtres.id_cvsource = "1"
            filtres.id_elem_source = str(user.id_salarie)
        return svc.search_cv(filtres)

    @router.post("/export.xlsx")
    def post_export_xlsx(
        payload: dict[str, Any] = Body(...),
        _user: UserToken = Depends(get_current_user),
    ):
        """Rendu XLSX des lignes deja filtrees/triees cote frontend."""
        rows = payload.get("rows") or []
        if not isinstance(rows, list):
            raise HTTPException(400, "payload.rows must be a list")
        data = svc.export_to_xlsx(rows)
        from datetime import datetime
        fname = f"RechercheCV_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        return Response(
            content=data,
            media_type=("application/vnd.openxmlformats-officedocument"
                        ".spreadsheetml.sheet"),
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )

    # -- Organigramme (mode Agence) -----------------------------------------

    @router.get("/organigramme/children")
    def get_orga_children(
        id_parent: int = Query(0),
        _user: UserToken = Depends(get_current_user),
    ):
        """Enfants directs d'un noeud (id_parent=0 = racine 'Reseau')."""
        return svc.list_orga_children(id_parent)

    # -- Presence -----------------------------------------------------------

    class IdsPayload(BaseModel):
        ids: list[str] = []

    @router.post("/presence")
    def post_presence(
        payload: IdsPayload,
        _user: UserToken = Depends(get_current_user),
    ):
        """Polling : retourne l'etat de presence + statut courant pour
        les IDs fournis. Appele toutes les ~1.5s par le frontend."""
        ids_int = [int(x) for x in payload.ids if str(x).isdigit()]
        return svc.get_presence(ids_int)

    @router.post("/{id_cv}/claim")
    def post_claim(
        id_cv: int,
        user: UserToken = Depends(get_current_user),
    ):
        """Pose une presence (ouverture de fiche CV)."""
        res = svc.claim_cv(id_cv, user.id_salarie)
        if not res.get("ok"):
            raise HTTPException(409, res.get("error") or "claim_failed")
        return res

    @router.post("/{id_cv}/release")
    def post_release(
        id_cv: int,
        user: UserToken = Depends(get_current_user),
    ):
        """Retire ma presence (fermeture de fiche CV)."""
        return svc.release_cv(id_cv, user.id_salarie)

    @router.post("/orphans/release")
    def post_release_orphans(
        user: UserToken = Depends(get_current_user),
    ):
        """Nettoie mes claims abandonnes (date_traite < aujourd'hui).

        Appele par le frontend au mount de la page de recherche.
        """
        return svc.release_my_orphans(user.id_salarie)

    # -- Fiche CV (Fen_CVFiche) --------------------------------------------

    @router.get("/{id_cv}", response_model=CVFicheDetail)
    def get_fiche(
        id_cv: int,
        _user: UserToken = Depends(get_current_user),
    ):
        f = fiche_svc.get_fiche(id_cv)
        if not f:
            raise HTTPException(404, "CV introuvable")
        return f

    @router.get("/{id_cv}/cvsuivi", response_model=list[CVSuiviRow])
    def get_cvsuivi(
        id_cv: int,
        _user: UserToken = Depends(get_current_user),
    ):
        return fiche_svc.list_cvsuivi(id_cv)

    @router.put("/{id_cv}")
    def put_fiche(
        id_cv: int,
        payload: CVFichePayload,
        user: UserToken = Depends(get_current_user),
    ):
        return fiche_svc.save_fiche(id_cv, payload, user.id_salarie)

    @router.post("/{id_cv}/restatuer")
    def post_restatuer(
        id_cv: int,
        user: UserToken = Depends(get_current_user),
    ):
        return fiche_svc.restatuer(id_cv, user.id_salarie)

    @router.post("/{id_cv}/statut-quick")
    def post_statut_quick(
        id_cv: int,
        payload: CVStatutQuickPayload,
        user: UserToken = Depends(get_current_user),
    ):
        return fiche_svc.statut_quick(id_cv, payload, user.id_salarie)

    @router.post("/{id_cv}/reactualiser")
    def post_reactualiser(
        id_cv: int,
        user: UserToken = Depends(get_current_user),
    ):
        return fiche_svc.reactualiser(id_cv, user.id_salarie)

    @router.post("/{id_cv}/observation")
    def post_observation(
        id_cv: int,
        payload: CVObservationPayload,
        user: UserToken = Depends(get_current_user),
    ):
        return fiche_svc.add_observation(id_cv, payload, user.id_salarie)

    @router.delete("/{id_cv}")
    def delete_fiche(
        id_cv: int,
        user: UserToken = Depends(get_current_user),
    ):
        # Droit WinDev : CVSuppr
        if "CVSuppr" not in (user.droits or []):
            raise HTTPException(403, "Droit CVSuppr requis")
        return fiche_svc.delete_fiche(id_cv, user.id_salarie)

    @router.post("/{id_cv}/upload-cv")
    async def post_upload_cv(
        id_cv: int,
        nom: str = Form(""),
        file: UploadFile = File(...),
        user: UserToken = Depends(get_current_user),
    ):
        content = await file.read()
        return fiche_svc.upload_cv_file(
            id_cv, nom, content, file.filename or "", user.id_salarie,
        )

    return router
