"""Router shared Recrutement / Recherche CV.

Pattern factory : chaque intranet (ADM, Vendeur, Call RH) inclut son
propre router via :
    router.include_router(get_recherche_cv_router("adm"))

`intranet_key` permet :
- de filtrer automatiquement la liste (ex: Vendeur ne voit que ses CV)
- de logger les actions cote audit
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.shared.recrutement.schemas.cv_fiche import (
    CheckDoublonPayload, CheckDoublonResponse, CreateCVPayload,
    CreateCVResponse, CVFicheDetail, CVFichePayload, CVObservationPayload,
    CVStatutQuickPayload, CVSuiviRow,
)
from app.shared.recrutement.schemas.recherche_cv import (
    CommuneItem, ComboItem, CVRow, SearchCVFiltres, SearchMotsClesFiltres,
)
from app.shared.recrutement.services import cv_fiche as fiche_svc
from app.shared.recrutement.services import entretien as ent_svc
from app.shared.recrutement.services import lieux_rdv as lieux_svc
from app.shared.recrutement.services import recherche_cv as svc
from app.shared.recrutement.services import prev_rec as prev_svc
from app.shared.recrutement.services import salons_visio as salons_svc


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

    @router.post("/search-mots-cles", response_model=list[CVRow])
    def post_search_mots_cles(
        filtres: SearchMotsClesFiltres,
        _user: UserToken = Depends(get_current_user),
    ):
        return svc.search_cv_mots_cles(filtres)

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

    @router.post("/presence")
    def post_presence(
        payload: dict[str, Any] = Body(...),
        _user: UserToken = Depends(get_current_user),
    ):
        """Polling : retourne l'etat de presence + statut courant pour
        les IDs fournis. Appele toutes les ~1.5s par le frontend."""
        ids = payload.get("ids") or []
        if not isinstance(ids, list):
            return {}
        ids_int = [int(x) for x in ids if str(x).isdigit()]
        return svc.get_presence(ids_int)

    # IMPORTANT : /orphans/release DOIT etre defini avant /{id_cv}/release
    # sinon FastAPI matche d'abord la route a path-param et lance un 422.
    @router.post("/orphans/release")
    def post_release_orphans(
        user: UserToken = Depends(get_current_user),
    ):
        """Nettoie mes claims abandonnes (date_traite < aujourd'hui).

        Appele par le frontend au mount de la page de recherche.
        """
        return svc.release_my_orphans(user.id_salarie)

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

    # -- Fen_CVSaisie : creation d'un nouveau CV ---------------------------

    @router.post("/check-doublon", response_model=CheckDoublonResponse)
    def post_check_doublon(
        payload: CheckDoublonPayload,
        _user: UserToken = Depends(get_current_user),
    ):
        return fiche_svc.check_doublon(payload)

    @router.post("", response_model=CreateCVResponse)
    def post_create_cv(
        payload: CreateCVPayload,
        user: UserToken = Depends(get_current_user),
    ):
        return fiche_svc.create_cv(payload, user.id_salarie)

    # IMPORTANT : les routes a path litteral (/salons-visio, /lieux-rdv,
    # /entretien) DOIVENT etre declarees AVANT /{id_cv} sinon FastAPI
    # matche d'abord la route a path-param et plante en 422 (id_cv='salons-visio').

    # -- Fen_SalonSalarie : gestion des salons visio d'un recruteur --------

    @router.get("/salons-visio/types", response_model=list[salons_svc.TypeSalonItem])
    def get_types_salon(
        _user: UserToken = Depends(get_current_user),
    ):
        return salons_svc.list_types_salon()

    @router.get("/salons-visio", response_model=list[salons_svc.SalonVisioRow])
    def get_salons_by_salarie(
        id_salarie: int = Query(...),
        _user: UserToken = Depends(get_current_user),
    ):
        return salons_svc.list_salons_by_salarie(id_salarie)

    @router.get("/salons-visio/{id_salon}", response_model=salons_svc.SalonVisioRow)
    def get_salon_route(
        id_salon: int,
        _user: UserToken = Depends(get_current_user),
    ):
        f = salons_svc.get_salon(id_salon)
        if not f:
            raise HTTPException(404, "Salon introuvable")
        return f

    @router.post("/salons-visio")
    def post_salon(
        payload: salons_svc.SalonVisioPayload,
        user: UserToken = Depends(get_current_user),
    ):
        res = salons_svc.save_salon(payload, user.id_salarie)
        if not res.get("ok"):
            raise HTTPException(400, res.get("error") or "fail")
        return res

    @router.delete("/salons-visio/{id_salon}")
    def del_salon(
        id_salon: int,
        user: UserToken = Depends(get_current_user),
    ):
        return salons_svc.delete_salon(id_salon, user.id_salarie)

    # -- Fen_LieuRDV : gestion des lieux de RDV ----------------------------
    # IMPORTANT : /lieux-rdv/geocode AVANT /lieux-rdv/{id_lieu}

    @router.get("/lieux-rdv", response_model=list[lieux_svc.LieuRDV])
    def get_lieux(
        is_actif: Optional[bool] = Query(None),
        _user: UserToken = Depends(get_current_user),
    ):
        return lieux_svc.list_lieux(is_actif)

    @router.post("/lieux-rdv/geocode", response_model=lieux_svc.GeocodeResponse)
    def post_geocode(
        payload: lieux_svc.GeocodePayload,
        _user: UserToken = Depends(get_current_user),
    ):
        return lieux_svc.geocode_adresse(payload)

    @router.post("/lieux-rdv")
    def post_lieu(
        payload: lieux_svc.LieuRdvPayload,
        user: UserToken = Depends(get_current_user),
    ):
        return lieux_svc.save_lieu(payload, user.id_salarie)

    @router.get("/lieux-rdv/{id_lieu}", response_model=lieux_svc.LieuRDV)
    def get_lieu_route(
        id_lieu: int,
        _user: UserToken = Depends(get_current_user),
    ):
        f = lieux_svc.get_lieu(id_lieu)
        if not f:
            raise HTTPException(404, "Lieu introuvable")
        return f

    @router.delete("/lieux-rdv/{id_lieu}")
    def del_lieu(
        id_lieu: int,
        user: UserToken = Depends(get_current_user),
    ):
        return lieux_svc.delete_lieu(id_lieu, user.id_salarie)

    @router.post("/lieux-rdv/{id_lieu}/duplicate")
    def post_dup_lieu(
        id_lieu: int,
        user: UserToken = Depends(get_current_user),
    ):
        res = lieux_svc.duplicate_lieu(id_lieu, user.id_salarie)
        if not res.get("ok"):
            raise HTTPException(400, res.get("error") or "fail")
        return res

    # -- Fen_PrevRec : prevision de recrutement (orga tree + sessions) -----

    @router.get("/prev-rec/orgas/racine",
                response_model=list[prev_svc.OrgaNode])
    def get_orgas_racine(
        _user: UserToken = Depends(get_current_user),
    ):
        return prev_svc.list_orgas_racine()

    @router.get("/prev-rec/orgas/{id_parent}/enfants",
                response_model=list[prev_svc.OrgaNode])
    def get_orgas_enfants(
        id_parent: int,
        _user: UserToken = Depends(get_current_user),
    ):
        return prev_svc.list_orgas_enfants(id_parent)

    @router.get("/prev-rec/etats", response_model=list[prev_svc.EtatItem])
    def get_etats(_user: UserToken = Depends(get_current_user)):
        return prev_svc.list_etats()

    @router.get("/prev-rec/orga-info/{id_orga}",
                response_model=prev_svc.OrgaInfo)
    def get_orga_info(
        id_orga: int,
        _user: UserToken = Depends(get_current_user),
    ):
        return prev_svc.get_orga_info(id_orga)

    @router.post("/prev-rec/cherche-coopt-sourcing",
                 response_model=prev_svc.CooptSourcingStats)
    def post_cherche_coopt(
        payload: dict[str, Any] = Body(...),
        _user: UserToken = Depends(get_current_user),
    ):
        return prev_svc.cherche_coopt_sourcing(
            id_communes_france=int(payload.get("id_communes_france", 0) or 0),
            rayon_km=int(payload.get("rayon_km", 30) or 30),
            type_recherche=int(payload.get("type_recherche", 1) or 1),
            date_crea_iso=str(payload.get("date_crea_iso", "")),
        )

    @router.post("/prev-rec")
    def post_session(
        payload: prev_svc.SessionPayload,
        user: UserToken = Depends(get_current_user),
    ):
        res = prev_svc.create_session(payload, user.id_salarie)
        if not res.get("ok"):
            raise HTTPException(400, "fail")
        return res

    @router.get("/prev-rec/session/{id_prev}",
                response_model=prev_svc.PrevRecRow)
    def get_session(
        id_prev: int,
        _user: UserToken = Depends(get_current_user),
    ):
        f = prev_svc.get_session(id_prev)
        if not f:
            raise HTTPException(404, "Prevision introuvable")
        return f

    @router.put("/prev-rec/session/{id_prev}")
    def put_session(
        id_prev: int,
        payload: prev_svc.SessionPayload,
        user: UserToken = Depends(get_current_user),
    ):
        res = prev_svc.update_session(id_prev, payload, user.id_salarie)
        if not res.get("ok"):
            raise HTTPException(400, res.get("error") or "fail")
        return res

    @router.get("/prev-rec/vendeurs-orga/{id_orga}",
                response_model=list[prev_svc.VendeurOrgaRow])
    def get_vendeurs_orga(
        id_orga: int,
        _user: UserToken = Depends(get_current_user),
    ):
        return prev_svc.list_vendeurs_orga(id_orga)

    @router.get("/prev-rec", response_model=list[prev_svc.PrevRecRow])
    def get_previsions(
        id_orga: int = Query(0, description="0 = toutes orgas"),
        date_ref: Optional[str] = Query(None, description="YYYY-MM-DD"),
        _user: UserToken = Depends(get_current_user),
    ):
        from datetime import date as _date
        ref: Optional[_date] = None
        if date_ref:
            try:
                ref = _date.fromisoformat(date_ref)
            except ValueError:
                pass
        return prev_svc.list_previsions(id_orga, ref)

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

    @router.get("/{id_cv}/mots-cles")
    def get_mots_cles(
        id_cv: int,
        _user: UserToken = Depends(get_current_user),
    ):
        return {"mots_cles": fiche_svc.get_mots_cles(id_cv)}

    @router.put("/{id_cv}/mots-cles")
    def put_mots_cles(
        id_cv: int,
        payload: dict[str, Any] = Body(...),
        user: UserToken = Depends(get_current_user),
    ):
        mots = str(payload.get("mots_cles") or "")
        return fiche_svc.save_mots_cles(id_cv, mots, user.id_salarie)

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

    # -- Fen_EntretienAjout (Planifier un RDV) -----------------------------

    @router.get("/entretien/recruteurs")
    def get_recruteurs(_user: UserToken = Depends(get_current_user)):
        return ent_svc.list_recruteurs()

    @router.get("/entretien/sessions")
    def get_sessions(_user: UserToken = Depends(get_current_user)):
        return ent_svc.list_sessions_recrut()

    @router.get("/entretien/lieux")
    def get_lieux(_user: UserToken = Depends(get_current_user)):
        return ent_svc.list_lieux_rdv()

    @router.get("/entretien/salons-visio/{id_recruteur}")
    def get_salons_visio(
        id_recruteur: int,
        _user: UserToken = Depends(get_current_user),
    ):
        return ent_svc.list_salons_visio(id_recruteur)

    @router.get("/entretien/agenda/{id_recruteur}")
    def get_agenda(
        id_recruteur: int,
        semaine_du: str = Query(...),
        _user: UserToken = Depends(get_current_user),
    ):
        return ent_svc.list_agenda_recruteur(id_recruteur, semaine_du)

    @router.put("/{id_cv}/coordonnees")
    def put_coords(
        id_cv: int,
        payload: ent_svc.UpdateCoordsPayload,
        user: UserToken = Depends(get_current_user),
    ):
        return ent_svc.update_coordonnees_candidat(
            id_cv, payload, user.id_salarie,
        )

    @router.post("/{id_cv}/rdv")
    def post_rdv(
        id_cv: int,
        payload: ent_svc.CreateRdvPayload,
        user: UserToken = Depends(get_current_user),
    ):
        res = ent_svc.create_rdv(id_cv, payload, user.id_salarie)
        if not res.get("ok"):
            raise HTTPException(400, res.get("error") or "rdv_failed")
        return res

    return router
