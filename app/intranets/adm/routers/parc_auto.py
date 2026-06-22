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
from app.intranets.adm.services import vehicule_accident as acc_svc
from app.intranets.adm.services import vehicule_pochette as poch_svc
from app.intranets.adm.services import vehicule_pv as pv_svc


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


@router.get("/vehicules/{id_vehicule}/pochette.pdf")
def get_pochette_pdf(
    id_vehicule: int,
    _user: UserToken = Depends(get_current_user),
):
    """Btn header 'Imprimer fiche' : PDF EtatPochette_Vehicule WinDev."""
    res = poch_svc.generate_pochette_pdf(id_vehicule)
    if res is None:
        raise HTTPException(404, "Véhicule introuvable ou échec PDF")
    pdf, filename = res
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


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


# ---------------------------------------------------------------------------
# Fen_Attribution (ajout/modif d'une attribution conducteur)
# ---------------------------------------------------------------------------


class AttributionFullPayload(BaseModel):
    id_vehicule_pc: str = "0"  # "0" = create, sinon update
    id_vehicule: str
    id_conducteur: str
    id_ste: int = 0
    perception_date: str = ""
    perception_heure: str = ""
    restitution_date: str = ""
    restitution_heure: str = ""
    k_mdepart: int = 0
    temporaire: bool = False
    conv_dispo: bool = False
    cg_originale_dossier: bool = False
    cg_conducteur: bool = False
    fiche_rest: bool = False
    c_vet_vignette: bool = False
    permis_cnd: bool = False


@router.post("/conducteurs/save")
def post_save_attribution(
    payload: AttributionFullPayload,
    user: UserToken = Depends(get_current_user),
):
    """Fen_Attribution btn Valider : create (id=0) ou update complet."""
    res = cond_svc.save_attribution(payload.model_dump(), user.id_salarie)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec")
    return res


@router.get("/salaries/search")
def get_salaries_search(
    q: str = "",
    limit: int = 50,
    _user: UserToken = Depends(get_current_user),
):
    """Btn 'Choisir le conducteur' (Fen_RechercheNomSalarie)."""
    return cond_svc.search_salaries(q, limit)


@router.post("/conducteurs/from-salarie/{id_salarie}")
def post_ensure_conducteur(
    id_salarie: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Choisir le conducteur' apres selection : cree la fiche
    conducteur depuis le salarie si pas exist, sinon renvoie l'existant."""
    res = cond_svc.ensure_conducteur_from_salarie(id_salarie, user.id_salarie)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec")
    return res


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


class GenererPvPayload(BaseModel):
    type_pv: str  # 'livraison' | 'restitution'
    suivi_edition: bool = True


@router.post("/conducteurs/{id_vehicule_pc}/generer-pv")
def post_generer_pv(
    id_vehicule_pc: int,
    payload: GenererPvPayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Generer PV livraison/restitution' : cree salarie_doc_ulease +
    tk_demande_sign_pv_ulease + tk_liste + tk_demandesignpv_photo (1 par
    photo typecapacite). Retourne id_tk_liste."""
    res = cond_svc.generer_pv(
        id_vehicule_pc,
        payload.type_pv,
        payload.suivi_edition,
        user.id_salarie,
    )
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec")
    return res


# Documents lies a l'attribution = FTP /Vehicules/{id_vehicule}/{id_vehicule_pc}/
# (cf. WinDev listerFichierPC).


@router.get("/vehicules/{id_vehicule}/conducteurs/{id_vehicule_pc}/documents")
def get_documents_pc(
    id_vehicule: int,
    id_vehicule_pc: int,
    _user: UserToken = Depends(get_current_user),
):
    return doc_svc.list_files(id_vehicule, str(id_vehicule_pc))


@router.post("/vehicules/{id_vehicule}/conducteurs/{id_vehicule_pc}/documents")
async def post_document_pc(
    id_vehicule: int,
    id_vehicule_pc: int,
    file: UploadFile = File(...),
    _user: UserToken = Depends(get_current_user),
):
    content = await file.read()
    res = doc_svc.upload_file(
        id_vehicule, file.filename or "document", content, str(id_vehicule_pc),
    )
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec upload")
    return res


@router.get("/vehicules/{id_vehicule}/conducteurs/{id_vehicule_pc}/documents/download")
def get_document_pc_content(
    id_vehicule: int,
    id_vehicule_pc: int,
    name: str,
    _user: UserToken = Depends(get_current_user),
):
    content = doc_svc.download_file(id_vehicule, name, str(id_vehicule_pc))
    if content is None:
        raise HTTPException(404, "Fichier introuvable")
    return Response(
        content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.delete("/vehicules/{id_vehicule}/conducteurs/{id_vehicule_pc}/documents")
def delete_document_pc(
    id_vehicule: int,
    id_vehicule_pc: int,
    name: str,
    _user: UserToken = Depends(get_current_user),
):
    res = doc_svc.delete_file(id_vehicule, name, str(id_vehicule_pc))
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec")
    return res


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


# ---------------------------------------------------------------------------
# Plan 4 - PV / Amendes (vehicule_amende)
# ---------------------------------------------------------------------------


@router.get("/vehicules/{id_vehicule}/pv")
def get_pv_list(
    id_vehicule: int,
    _user: UserToken = Depends(get_current_user),
):
    return pv_svc.list_pv(id_vehicule)


@router.get("/pv/{id_vehicule_pv}")
def get_pv_detail(
    id_vehicule_pv: int,
    _user: UserToken = Depends(get_current_user),
):
    p = pv_svc.get_pv(id_vehicule_pv)
    if not p:
        raise HTTPException(404, "PV introuvable")
    return p


class PvPayload(BaseModel):
    id_vehicule_pv: int = 0
    id_vehicule: int
    id_vehicule_pc: int = 0
    vehicule_pv_date: str = ""
    montant: float = 0.0
    num_pv: str = ""
    frais: float = 15.0
    nb_pts: int = 0
    paye_employeur: bool = False
    paye_employeur_date: str = ""
    prel_salarie: bool = False
    prel_salarie_date: str = ""
    comment: str = ""


@router.post("/pv")
def post_pv(
    payload: PvPayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn Enregistrer le PV."""
    return pv_svc.save_pv(payload.model_dump(), user.id_salarie)


@router.delete("/pv/{id_vehicule_pv}")
def delete_pv(
    id_vehicule_pv: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Poubelle PV : soft delete."""
    return pv_svc.delete_pv(id_vehicule_pv, user.id_salarie)


# Documents PV : FTP /Vehicules/{id_vehicule}/PV_{id_vehicule_pv}/


@router.get("/vehicules/{id_vehicule}/pv/{id_vehicule_pv}/documents")
def get_documents_pv(
    id_vehicule: int,
    id_vehicule_pv: int,
    _user: UserToken = Depends(get_current_user),
):
    return doc_svc.list_files(id_vehicule, f"PV_{int(id_vehicule_pv)}")


@router.post("/vehicules/{id_vehicule}/pv/{id_vehicule_pv}/documents")
async def post_document_pv(
    id_vehicule: int,
    id_vehicule_pv: int,
    file: UploadFile = File(...),
    _user: UserToken = Depends(get_current_user),
):
    content = await file.read()
    res = doc_svc.upload_file(
        id_vehicule, file.filename or "document", content,
        f"PV_{int(id_vehicule_pv)}",
    )
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec upload")
    return res


@router.get("/vehicules/{id_vehicule}/pv/{id_vehicule_pv}/documents/download")
def get_document_pv_content(
    id_vehicule: int,
    id_vehicule_pv: int,
    name: str,
    _user: UserToken = Depends(get_current_user),
):
    content = doc_svc.download_file(
        id_vehicule, name, f"PV_{int(id_vehicule_pv)}",
    )
    if content is None:
        raise HTTPException(404, "Fichier introuvable")
    return Response(
        content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.delete("/vehicules/{id_vehicule}/pv/{id_vehicule_pv}/documents")
def delete_document_pv(
    id_vehicule: int,
    id_vehicule_pv: int,
    name: str,
    _user: UserToken = Depends(get_current_user),
):
    res = doc_svc.delete_file(
        id_vehicule, name, f"PV_{int(id_vehicule_pv)}",
    )
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec")
    return res


# ---------------------------------------------------------------------------
# Plan 5 - Accidents (vehicule_accident)
# ---------------------------------------------------------------------------


@router.get("/vehicules/{id_vehicule}/accidents")
def get_accidents(
    id_vehicule: int,
    _user: UserToken = Depends(get_current_user),
):
    return acc_svc.list_accidents(id_vehicule)


@router.get("/accidents/{id_vehicule_acc}")
def get_accident_detail(
    id_vehicule_acc: int,
    _user: UserToken = Depends(get_current_user),
):
    a = acc_svc.get_accident(id_vehicule_acc)
    if not a:
        raise HTTPException(404, "Accident introuvable")
    return a


class AccidentPayload(BaseModel):
    id_vehicule_acc: int = 0
    id_vehicule: int
    id_vehicule_pc: int = 0
    vehicule_acc_date: str = ""
    resp: int = 0
    prix_rep: float = 0.0
    prix_fran: float = 0.0
    reparable: bool = False
    deb_rep: str = ""
    fin_rep: str = ""
    repare: bool = False
    desc_: str = ""


@router.post("/accidents")
def post_accident(
    payload: AccidentPayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn Enregistrer accident + maj vehicule_fiche.etat."""
    return acc_svc.save_accident(payload.model_dump(), user.id_salarie)


@router.delete("/accidents/{id_vehicule_acc}")
def delete_accident(
    id_vehicule_acc: int,
    user: UserToken = Depends(get_current_user),
):
    return acc_svc.delete_accident(id_vehicule_acc, user.id_salarie)


# Documents Accident : FTP /Vehicules/{id_vehicule}/ACC_{id_vehicule_acc}/


@router.get("/vehicules/{id_vehicule}/accidents/{id_vehicule_acc}/documents")
def get_documents_acc(
    id_vehicule: int,
    id_vehicule_acc: int,
    _user: UserToken = Depends(get_current_user),
):
    return doc_svc.list_files(id_vehicule, f"ACC_{int(id_vehicule_acc)}")


@router.post("/vehicules/{id_vehicule}/accidents/{id_vehicule_acc}/documents")
async def post_document_acc(
    id_vehicule: int,
    id_vehicule_acc: int,
    file: UploadFile = File(...),
    _user: UserToken = Depends(get_current_user),
):
    content = await file.read()
    res = doc_svc.upload_file(
        id_vehicule, file.filename or "document", content,
        f"ACC_{int(id_vehicule_acc)}",
    )
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec upload")
    return res


@router.get(
    "/vehicules/{id_vehicule}/accidents/{id_vehicule_acc}/documents/download",
)
def get_document_acc_content(
    id_vehicule: int,
    id_vehicule_acc: int,
    name: str,
    _user: UserToken = Depends(get_current_user),
):
    content = doc_svc.download_file(
        id_vehicule, name, f"ACC_{int(id_vehicule_acc)}",
    )
    if content is None:
        raise HTTPException(404, "Fichier introuvable")
    return Response(
        content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.delete("/vehicules/{id_vehicule}/accidents/{id_vehicule_acc}/documents")
def delete_document_acc(
    id_vehicule: int,
    id_vehicule_acc: int,
    name: str,
    _user: UserToken = Depends(get_current_user),
):
    res = doc_svc.delete_file(
        id_vehicule, name, f"ACC_{int(id_vehicule_acc)}",
    )
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec")
    return res
