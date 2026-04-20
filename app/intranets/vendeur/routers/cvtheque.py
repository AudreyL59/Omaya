import json
import queue
import threading

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.vendeur.schemas.cvtheque import (
    CvStatutItem,
    CvSourceItem,
    CvAnnonceurItem,
    CommuneCPItem,
    CvSearchRequest,
    CvResultItem,
    CvFicheResponse,
    TraitementRequest,
    CvSaveRequest,
    ObservationAddRequest,
)
from app.intranets.vendeur.services.cvtheque import (
    lister_statuts,
    lister_sources,
    lister_annonceurs,
    rechercher_communes,
    rechercher_cvtheque,
    get_fiche,
    modifier_traitement,
    enregistrer_fiche,
    ajouter_observation,
    get_traitement_bulk,
)
from app.intranets.vendeur.schemas.prise_rdv import (
    SessionItem,
    LieuRdvItem,
    LieuRdvInfo,
    SalonVisioItem,
    SalonVisioInfo,
    PriseRdvRequest,
)
from app.intranets.vendeur.services.prise_rdv import (
    lister_sessions,
    lister_lieux_rdv,
    info_lieu_rdv,
    lister_salons_visio,
    info_salon_visio,
    planifier_rdv,
)

router = APIRouter(prefix="/cvtheque", tags=["vendeur-cvtheque"])


@router.get("/statuts", response_model=list[CvStatutItem])
def get_statuts():
    """Liste des statuts CV."""
    return lister_statuts()


@router.get("/sources", response_model=list[CvSourceItem])
def get_sources():
    """Liste des sources CV actives."""
    return lister_sources()


@router.get("/annonceurs", response_model=list[CvAnnonceurItem])
def get_annonceurs():
    """Liste des annonceurs CV actifs."""
    return lister_annonceurs()


@router.get("/communes", response_model=list[CommuneCPItem])
def get_communes(ville: str = ""):
    """Retourne les CP/villes correspondant à un début de nom (avec coords GPS)."""
    return rechercher_communes(ville)


@router.post("/search", response_model=list[CvResultItem])
def post_search(
    data: CvSearchRequest,
    user: UserToken = Depends(get_current_user),
):
    """Recherche dans cvtheque (sans progression)."""
    acces_complet = "CV_VoirComplet" in user.droits
    return rechercher_cvtheque(
        mode=data.mode,
        latitude=data.latitude or 0,
        longitude=data.longitude or 0,
        rayon_km=data.rayon_km,
        date_debut=data.date_debut,
        date_fin=data.date_fin,
        age_min=data.age_min,
        age_max=data.age_max,
        id_cv_source=data.id_cv_source,
        id_coopteur=data.id_coopteur,
        id_annonceur=data.id_annonceur,
        profil=data.profil,
        id_cv_statut=data.id_cv_statut,
        tel=data.tel,
        nom=data.nom,
        prenom=data.prenom,
        acces_complet=acces_complet,
        id_salarie_user=user.id_salarie,
    )


@router.get("/{id_cvtheque}", response_model=CvFicheResponse)
def get_one(id_cvtheque: int, user: UserToken = Depends(get_current_user)):
    """Retourne la fiche CV + historique CvSuivi."""
    result = get_fiche(id_cvtheque)
    if not result:
        raise HTTPException(status_code=404, detail="CV introuvable")
    return result


@router.post("/{id_cvtheque}/traitement")
def post_traitement(
    id_cvtheque: int,
    data: TraitementRequest,
    user: UserToken = Depends(get_current_user),
):
    """Verrouille/libère le CV pour traitement."""
    modifier_traitement(
        id_cvtheque=id_cvtheque,
        id_op=user.id_salarie if data.is_traite else 0,
        is_traite=data.is_traite,
    )
    return {"ok": True}


@router.post("/{id_cvtheque}/observation")
def post_observation(
    id_cvtheque: int,
    data: ObservationAddRequest,
    user: UserToken = Depends(get_current_user),
):
    """Ajoute une observation datée au champ OBSERV."""
    try:
        new_observ = ajouter_observation(
            id_cvtheque=id_cvtheque,
            observation_add=data.observation,
            prenom_user=user.prenom,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "observation": new_observ}


@router.post("/traitement/bulk")
def post_traitement_bulk(
    ids: list[str],
    user: UserToken = Depends(get_current_user),
):
    """Retourne l'état de traitement en cours pour une liste de CV IDs."""
    cv_ids = [int(i) for i in ids if i]
    return get_traitement_bulk(cv_ids)


@router.get("/rdv/sessions", response_model=list[SessionItem])
def get_sessions():
    """Sessions de recrutement actives (à partir d'aujourd'hui)."""
    return lister_sessions()


@router.get("/rdv/lieux", response_model=list[LieuRdvItem])
def get_lieux():
    """Lieux de RDV actifs."""
    return lister_lieux_rdv()


@router.get("/rdv/lieux/{id_lieu}", response_model=LieuRdvInfo)
def get_lieu_info(id_lieu: int):
    """Détail d'un lieu de RDV."""
    info = info_lieu_rdv(id_lieu)
    if not info:
        raise HTTPException(status_code=404, detail="Lieu introuvable")
    return info


@router.get("/rdv/salons-visio", response_model=list[SalonVisioItem])
def get_salons_visio(id_salarie: int):
    """Salons visio d'un recruteur."""
    return lister_salons_visio(id_salarie)


@router.get("/rdv/salons-visio/{id_salon}", response_model=SalonVisioInfo)
def get_salon_info(id_salon: int):
    """Détail d'un salon visio."""
    info = info_salon_visio(id_salon)
    if not info:
        raise HTTPException(status_code=404, detail="Salon introuvable")
    return info


@router.post("/rdv")
def post_rdv(
    data: PriseRdvRequest,
    user: UserToken = Depends(get_current_user),
):
    """Planifie un RDV candidat avec un recruteur."""
    try:
        return planifier_rdv(
            id_cvtheque=int(data.id_cvtheque),
            id_recruteur=int(data.id_recruteur),
            id_session=int(data.id_session or 0),
            date_rdv=data.date_rdv,
            heure_rdv=data.heure_rdv,
            type_entretien=data.type_entretien,
            id_lieu_rdv=data.id_lieu_rdv,
            id_salon_visio=int(data.id_salon_visio or 0),
            envoyer_sms=data.envoyer_sms,
            id_salarie_user=user.id_salarie,
            prenom_user=user.prenom,
            nom_user=user.nom,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{id_cvtheque}/save")
def post_save(
    id_cvtheque: int,
    data: CvSaveRequest,
    ancien_statut: int = 0,
    user: UserToken = Depends(get_current_user),
):
    """Enregistre la fiche + ajoute un CvSuivi si changement de statut."""
    try:
        result = enregistrer_fiche(
            id_cvtheque=id_cvtheque,
            data=data.model_dump(),
            id_salarie_user=user.id_salarie,
            prenom_user=user.prenom,
            ancien_statut=ancien_statut,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.post("/search/stream")
def post_search_stream(
    data: CvSearchRequest,
    user: UserToken = Depends(get_current_user),
):
    """
    Recherche streamée : émet NDJSON {"progress": int, "msg": str} pendant la
    recherche puis {"done": true, "results": [...]} en fin.
    """
    acces_complet = "CV_VoirComplet" in user.droits
    q: queue.Queue = queue.Queue()

    def progress_cb(pct: int, msg: str):
        q.put({"progress": pct, "msg": msg})

    def worker():
        try:
            results = rechercher_cvtheque(
                mode=data.mode,
                latitude=data.latitude or 0,
                longitude=data.longitude or 0,
                rayon_km=data.rayon_km,
                date_debut=data.date_debut,
                date_fin=data.date_fin,
                age_min=data.age_min,
                age_max=data.age_max,
                id_cv_source=data.id_cv_source,
                id_coopteur=data.id_coopteur,
                id_annonceur=data.id_annonceur,
                profil=data.profil,
                id_cv_statut=data.id_cv_statut,
                tel=data.tel,
                nom=data.nom,
                prenom=data.prenom,
                acces_complet=acces_complet,
                id_salarie_user=user.id_salarie,
                progress_cb=progress_cb,
            )
            q.put({"done": True, "results": results})
        except Exception as e:
            q.put({"error": str(e)})
        finally:
            q.put(None)  # sentinel

    threading.Thread(target=worker, daemon=True).start()

    def stream():
        while True:
            item = q.get()
            if item is None:
                break
            yield json.dumps(item, default=str) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")
