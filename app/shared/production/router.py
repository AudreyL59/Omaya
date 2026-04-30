"""
Router Production — jobs d'extraction + lecture paginée des résultats.

Endpoints :
  POST   /production/jobs                 → créer un job
  GET    /production/jobs                 → mes jobs
  GET    /production/jobs/{id}            → détail + progression
  DELETE /production/jobs/{id}            → supprimer un job
  GET    /production/jobs/{id}/contrats   → résultat paginé (tableau)
  GET    /production/partenaires          → liste pour la case à cocher
  GET    /production/etats                → liste TypeEtatContrat
"""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.shared.production.schemas import (
    ContratPage,
    JobStats,
    PartenaireItem,
    ProductionJob,
    ProductionJobCreate,
    TypeEtatItem,
)
from app.shared.production.service import (
    QuotaExceeded,
    create_job,
    delete_job,
    get_job,
    list_jobs,
    list_partenaires,
    list_types_etat,
    search_organigrammes,
)
from app.shared.production.extraction import (
    EXPORT_COLUMNS,
    csv_value,
    read_contrats_page,
    read_job_stats,
)

router = APIRouter(prefix="/production", tags=["production"])


# ---------------------------------------------------------------
# Référentiels
# ---------------------------------------------------------------

@router.get("/partenaires", response_model=list[PartenaireItem])
def get_partenaires(user: UserToken = Depends(get_current_user)):
    """Liste des partenaires pour la page de sélection."""
    return list_partenaires()


@router.get("/etats", response_model=list[TypeEtatItem])
def get_etats(user: UserToken = Depends(get_current_user)):
    """Liste des TypeEtatContrat pour le dropdown."""
    return list_types_etat()


@router.get("/organigrammes")
def get_organigrammes(q: str = "", user: UserToken = Depends(get_current_user)):
    """Recherche d'orgas par libellé (picker Équipe)."""
    return search_organigrammes(q)


@router.get("/vendeurs")
def get_vendeurs(q: str = "", user: UserToken = Depends(get_current_user)):
    """Recherche de salariés vendeurs (picker Vendeur). Mêmes règles d'accès
    que la cooptation (acces_global via ProdRezo, scope équipe via is_resp)."""
    from app.intranets.vendeur.services.cooptation import rechercher_vendeurs
    acces_global = "ProdRezo" in user.droits
    is_resp = user.is_resp or "ProdGR" in user.droits
    return rechercher_vendeurs(
        user.id_salarie, q, acces_global=acces_global, is_resp=is_resp,
    )


# ---------------------------------------------------------------
# CRUD jobs
# ---------------------------------------------------------------

@router.post("/jobs")
def post_job(
    data: ProductionJobCreate,
    user: UserToken = Depends(get_current_user),
):
    """Crée un nouveau job d'extraction (en statut 'pending')."""
    if not data.partenaires:
        raise HTTPException(status_code=400, detail="Au moins un partenaire est requis")
    if not data.date_du or not data.date_au:
        raise HTTPException(status_code=400, detail="Période requise")
    if data.date_du > data.date_au:
        raise HTTPException(status_code=400, detail="Date Du > Date Au")

    try:
        id_job = create_job(
            id_salarie_user=user.id_salarie,
            params=data.model_dump(),
            user_nom=user.nom,
            user_prenom=user.prenom,
            droits=user.droits,
            is_resp=user.is_resp,
        )
    except QuotaExceeded as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Quota d'extractions dépassé : {exc.current} / {exc.quota} "
                "jobs actifs (en file ou en cours). "
                "Attends qu'un de tes jobs se termine ou supprime-en un."
            ),
        )
    return {"id_job": id_job}


@router.get("/jobs", response_model=list[ProductionJob])
def get_jobs(user: UserToken = Depends(get_current_user), limit: int = 50):
    """Liste des jobs du user (les 50 plus récents par défaut)."""
    return list_jobs(user.id_salarie, limit=limit)


@router.get("/jobs/{id_job}", response_model=ProductionJob)
def get_single_job(id_job: int, user: UserToken = Depends(get_current_user)):
    """Détail d'un job (progression incluse pour polling)."""
    job = get_job(id_job, user.id_salarie)
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    return job


@router.delete("/jobs/{id_job}")
def delete_single_job(id_job: int, user: UserToken = Depends(get_current_user)):
    """Soft-delete d'un job."""
    if not delete_job(id_job, user.id_salarie):
        raise HTTPException(status_code=404, detail="Job introuvable")
    return {"ok": True}


# ---------------------------------------------------------------
# Lecture résultats
# ---------------------------------------------------------------

@router.get("/jobs/{id_job}/contrats", response_model=ContratPage)
def get_contrats(
    id_job: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1_000_000),
    sort: str = Query("", description="Nom de colonne, préfixer par '-' pour desc"),
    partenaire: str = Query(""),
    vendeur: str = Query(""),
    client: str = Query(""),
    num_bs: str = Query(""),
    type_prod: str = Query(""),
    f: str = Query("", description="Filtres par colonne, JSON: {\"col\": \"val\"}"),
    user: UserToken = Depends(get_current_user),
):
    """Lecture paginée du tableau contrats (depuis le Parquet).

    Filtres :
      - les params nommés (partenaire, vendeur, client, num_bs, type_prod)
        couvrent les recherches "globales" rapides ;
      - `f` permet de filtrer sur n'importe quelle colonne via JSON
        (les filtres de colonnes du tableau).
    Les deux sources sont fusionnées (les filtres de `f` priment).
    """
    job = get_job(id_job, user.id_salarie)
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    if job["statut"] != "done":
        raise HTTPException(
            status_code=409,
            detail=f"Job en statut '{job['statut']}' — résultat non disponible",
        )
    path = job["path_resultat"]
    if not path:
        raise HTTPException(status_code=404, detail="Fichier résultat introuvable")

    filters: dict = {
        "partenaire": partenaire,
        # Pour vendeur/client on filtre sur le nom uniquement (recherche "contient")
        "vendeur_nom": vendeur,
        "client_nom": client,
        "num_bs": num_bs,
        "type_prod": type_prod,
    }
    if f:
        try:
            import json as _json
            extra = _json.loads(f)
            if isinstance(extra, dict):
                for k, v in extra.items():
                    if v not in (None, ""):
                        filters[str(k)] = v
        except Exception:
            # Si JSON invalide on ignore plutôt que renvoyer une 500
            pass

    # Nettoyer les filtres vides
    filters = {k: v for k, v in filters.items() if v not in (None, "")}
    return read_contrats_page(
        path, page=page, page_size=page_size, sort=sort, filters=filters,
        droits=user.droits,
    )


@router.get("/jobs/{id_job}/stats", response_model=JobStats)
def get_job_stats(
    id_job: int,
    user: UserToken = Depends(get_current_user),
):
    """Stats précalculées du job (onglets dashboard)."""
    job = get_job(id_job, user.id_salarie)
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    if job["statut"] != "done":
        raise HTTPException(
            status_code=409,
            detail=f"Job en statut '{job['statut']}' — stats non disponibles",
        )
    return read_job_stats(user.id_salarie, id_job)


@router.get("/jobs/{id_job}/export.csv")
def get_export_csv(
    id_job: int,
    user: UserToken = Depends(get_current_user),
):
    """Export CSV complet (UTF-8 BOM pour Excel FR)."""
    job = get_job(id_job, user.id_salarie)
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    if job["statut"] != "done":
        raise HTTPException(status_code=409, detail="Job non terminé")
    path = job["path_resultat"]
    if not path:
        raise HTTPException(status_code=404, detail="Fichier résultat introuvable")

    # On lit tout le Parquet (sans pagination) avec censure selon droits user
    data = read_contrats_page(
        path, page=1, page_size=1_000_000, droits=user.droits,
    )
    rows = data["rows"]

    def gen():
        buf = io.StringIO()
        buf.write("﻿")  # BOM UTF-8 pour Excel FR
        writer = csv.writer(buf, delimiter=";")
        writer.writerow([lbl for _, lbl in EXPORT_COLUMNS])
        for r in rows:
            writer.writerow([csv_value(r, k) for k, _ in EXPORT_COLUMNS])
        yield buf.getvalue().encode("utf-8")

    filename = f"production-job-{id_job}.csv"
    return StreamingResponse(
        gen(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class SelectionExportItem(BaseModel):
    partenaire: str
    id_contrat: str


class SelectionExportRequest(BaseModel):
    items: list[SelectionExportItem]


@router.post("/jobs/{id_job}/export-selection.csv")
def post_export_selection_csv(
    id_job: int,
    body: SelectionExportRequest,
    user: UserToken = Depends(get_current_user),
):
    """Export CSV des contrats explicitement sélectionnés (multi-lignes)."""
    job = get_job(id_job, user.id_salarie)
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    if job["statut"] != "done":
        raise HTTPException(status_code=409, detail="Job non terminé")
    path = job["path_resultat"]
    if not path:
        raise HTTPException(status_code=404, detail="Fichier résultat introuvable")
    if not body.items:
        raise HTTPException(status_code=400, detail="Aucune ligne sélectionnée")

    # Set des clés à conserver : (partenaire, id_contrat)
    wanted: set[tuple[str, str]] = {
        (it.partenaire, str(it.id_contrat)) for it in body.items
    }

    data = read_contrats_page(
        path, page=1, page_size=1_000_000, droits=user.droits,
    )
    rows = [
        r for r in data["rows"]
        if (r.get("partenaire", ""), str(r.get("id_contrat", ""))) in wanted
    ]

    def gen():
        buf = io.StringIO()
        buf.write("﻿")  # BOM UTF-8 pour Excel FR
        writer = csv.writer(buf, delimiter=";")
        writer.writerow([lbl for _, lbl in EXPORT_COLUMNS])
        for r in rows:
            writer.writerow([csv_value(r, k) for k, _ in EXPORT_COLUMNS])
        yield buf.getvalue().encode("utf-8")

    filename = f"production-job-{id_job}-selection.csv"
    return StreamingResponse(
        gen(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
