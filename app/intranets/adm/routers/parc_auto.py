"""
Router Fen_TdbUlease + Fen_FicheVehicule (ADM Ulease -> Parc Auto).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import fiche_vehicule as fv_svc
from app.intranets.adm.services import parc_auto as svc
from app.intranets.adm.services import vehicule_conducteurs as cond_svc
from app.intranets.adm.services import vehicule_documents as doc_svc
from app.intranets.adm.services import vehicule_entretien as ent_svc


router = APIRouter(prefix="/parc-auto", tags=["adm-parc-auto"])


@router.get("/vehicules")
def get_vehicules(_user: UserToken = Depends(get_current_user)):
    """Tableau de bord : tous les vehicules en circulation + alertes."""
    return svc.list_vehicules_actifs()


# ---------------------------------------------------------------------------
# Fen_FicheVehicule
# ---------------------------------------------------------------------------


@router.get("/lookups")
def get_lookups(_user: UserToken = Depends(get_current_user)):
    """Combos marques / etats / types_capacite / societes / types_possession."""
    return fv_svc.get_lookups()


@router.get("/vehicules/{id_vehicule}")
def get_vehicule(
    id_vehicule: int,
    _user: UserToken = Depends(get_current_user),
):
    """Fiche complete vehicule pour Plan 1 + header."""
    v = fv_svc.get_vehicule(id_vehicule)
    if not v:
        raise HTTPException(404, "Véhicule introuvable")
    return v


class VehiculePayload(BaseModel):
    id_vehicule_marque: int = 0
    modele: str = ""
    immat: str = ""
    chevaux_fiscaux: int = 0
    date_mise_circulation: str = ""
    id_vehicule_type_capacite: int = 0
    date_deb: str = ""
    date_fin: str = ""
    id_ste_proprio: int = 0
    id_ste_reseau: int = 0
    achat_loc: str = ""
    id_vehicule_etat: int = 0
    forfait_km: int = 0
    k_mdepart: int = 0
    km_actuel: int = 0
    km_mensuel: int = 0
    date_releve: str = ""
    info_vehicule: str = ""


@router.put("/vehicules/{id_vehicule}")
def put_vehicule(
    id_vehicule: int,
    payload: VehiculePayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn Enregistrer Plan 1 (Info Vehicule)."""
    return fv_svc.update_vehicule(id_vehicule, payload.model_dump(), user.id_salarie)


@router.delete("/vehicules/{id_vehicule}")
def delete_vehicule(
    id_vehicule: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Supprimer la fiche : soft delete."""
    return fv_svc.delete_vehicule(id_vehicule, user.id_salarie)


# ---------------------------------------------------------------------------
# Documents FTP du vehicule (Plan 1 section 'Documents du vehicule')
# ---------------------------------------------------------------------------


@router.get("/vehicules/{id_vehicule}/documents")
def get_documents(
    id_vehicule: int,
    _user: UserToken = Depends(get_current_user),
):
    """FTPListeFichier sur /OMAYA/Vehicules/{id}/."""
    return doc_svc.list_files(id_vehicule)


@router.post("/vehicules/{id_vehicule}/documents")
async def post_document(
    id_vehicule: int,
    file: UploadFile = File(...),
    _user: UserToken = Depends(get_current_user),
):
    """Upload d'un fichier vers /OMAYA/Vehicules/{id}/."""
    content = await file.read()
    res = doc_svc.upload_file(id_vehicule, file.filename or "document", content)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec upload")
    return res


@router.get("/vehicules/{id_vehicule}/documents/download")
def get_document_content(
    id_vehicule: int,
    name: str,
    _user: UserToken = Depends(get_current_user),
):
    """Download du fichier."""
    content = doc_svc.download_file(id_vehicule, name)
    if content is None:
        raise HTTPException(404, "Fichier introuvable")
    return Response(
        content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.delete("/vehicules/{id_vehicule}/documents")
def delete_document(
    id_vehicule: int,
    name: str,
    _user: UserToken = Depends(get_current_user),
):
    """DELE du fichier sur le FTP."""
    res = doc_svc.delete_file(id_vehicule, name)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec")
    return res


@router.post("/vehicules/{id_vehicule}/documents/carte-grise")
def post_carte_grise(
    id_vehicule: int,
    name: str,
    user: UserToken = Depends(get_current_user),
):
    """Marque le fichier comme carte grise du vehicule."""
    return doc_svc.set_as_carte_grise(id_vehicule, name, user.id_salarie)


# ---------------------------------------------------------------------------
# Plan 2 - Conducteurs (attributions)
# ---------------------------------------------------------------------------


@router.get("/vehicules/{id_vehicule}/conducteurs")
def get_conducteurs(
    id_vehicule: int,
    _user: UserToken = Depends(get_current_user),
):
    """Liste des attributions du vehicule (ReqListeCondByVehicule)."""
    return cond_svc.list_conducteurs(id_vehicule)


@router.get("/conducteurs/{id_vehicule_pc}")
def get_attribution(
    id_vehicule_pc: int,
    _user: UserToken = Depends(get_current_user),
):
    """Details d'une attribution (FichierVersEcran)."""
    a = cond_svc.get_attribution(id_vehicule_pc)
    if not a:
        raise HTTPException(404, "Attribution introuvable")
    return a


class AttributionPayload(BaseModel):
    id_ste: int = 0
    temporaire: bool = False
    conv_dispo: bool = False
    cg_originale_dossier: bool = False
    cg_conducteur: bool = False
    fiche_rest: bool = False
    c_vet_vignette: bool = False
    permis_cnd: bool = False
    fiche_enlev: bool = False
    info_vehicule: str = ""


@router.put("/conducteurs/{id_vehicule_pc}")
def put_attribution(
    id_vehicule_pc: int,
    payload: AttributionPayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn Enregistrer Plan 2."""
    return cond_svc.update_attribution(
        id_vehicule_pc, payload.model_dump(), user.id_salarie,
    )


@router.delete("/conducteurs/{id_vehicule_pc}")
def delete_attribution(
    id_vehicule_pc: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Poubelle Plan 2 : soft delete vehicule_conducteur."""
    return cond_svc.delete_attribution(id_vehicule_pc, user.id_salarie)


@router.get("/conducteurs/{id_vehicule_pc}/doc-ulease")
def get_doc_ulease(
    id_vehicule_pc: int,
    _user: UserToken = Depends(get_current_user),
):
    """DocUleaseEdite : liste docs (mise a dispo / PV) lies a l'attribution."""
    return cond_svc.list_doc_ulease_for_pc(id_vehicule_pc)


class InfoComplementaire(BaseModel):
    commentaire: str


@router.post("/conducteurs/{id_vehicule_pc}/info-complementaire")
def post_info_complementaire(
    id_vehicule_pc: int,
    payload: InfoComplementaire,
    user: UserToken = Depends(get_current_user),
):
    """Append daté au champ info_vehicule (avec prenom user)."""
    return cond_svc.add_info_complementaire(
        id_vehicule_pc, payload.commentaire,
        user.prenom or user.email.split("@")[0], user.id_salarie,
    )


# ---------------------------------------------------------------------------
# Plan 3 - Carnet d'entretien (types 1/2/3) + Releves kilometriques (type 4)
# ---------------------------------------------------------------------------


@router.get("/vehicules/{id_vehicule}/entretiens")
def get_entretiens(
    id_vehicule: int,
    type_entretien: int,
    _user: UserToken = Depends(get_current_user),
):
    """List entretiens d'un type (1=revision, 2=CT, 3=pneus)."""
    return ent_svc.list_entretiens(id_vehicule, type_entretien)


class EntretienPayload(BaseModel):
    id_vehicule_entretien: int = 0
    id_vehicule: int
    type_entretien: int
    realise_le: str = ""
    montant_ht: float = 0.0
    montant_ttc: float = 0.0
    c_rentretien: str = ""


@router.post("/entretiens")
def post_entretien(
    payload: EntretienPayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn Enregistrer entretien (create ou update)."""
    return ent_svc.save_entretien(payload.model_dump(), user.id_salarie)


@router.delete("/entretiens/{id_vehicule_entretien}")
def delete_entretien(
    id_vehicule_entretien: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Poubelle entretien."""
    return ent_svc.delete_entretien(id_vehicule_entretien, user.id_salarie)


@router.get("/vehicules/{id_vehicule}/releves")
def get_releves(
    id_vehicule: int,
    _user: UserToken = Depends(get_current_user),
):
    """Liste des releves kilometriques du vehicule."""
    return ent_svc.list_releves(id_vehicule)


@router.get("/vehicules/{id_vehicule}/conducteurs-all")
def get_conducteurs_all(
    id_vehicule: int,
    _user: UserToken = Depends(get_current_user),
):
    """Combo conducteur Plan 4 (tous, meme historiques)."""
    return ent_svc.list_conducteurs_all(id_vehicule)


class RelevePayload(BaseModel):
    id_vehicule: int
    id_vehicule_pc: int = 0
    date_releve: str
    km: int
    km_parcouru: int = 0
    km_restant: int = 0
    alerte: bool = False
    commentaire: str = ""


@router.post("/releves")
def post_releve(
    payload: RelevePayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn Enregistrer la releve."""
    return ent_svc.save_releve(payload.model_dump(), user.id_salarie)


@router.delete("/releves/{id_vehicule_releve}")
def delete_releve(
    id_vehicule_releve: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Poubelle releve."""
    return ent_svc.delete_releve(id_vehicule_releve, user.id_salarie)
