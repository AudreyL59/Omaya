"""
Router Fen_GestionCarteCarb (ADM Ulease -> Gestion cartes carburant).

Endpoints :
  GET    /cartes                   -> liste cartes
  POST   /cartes                   -> create/update (id=0 = create)
  DELETE /cartes/{id}              -> soft delete

  GET    /cartes/{id}/attributions -> liste attributions
  GET    /attributions/{id}        -> detail
  POST   /attributions             -> create/update
  DELETE /attributions/{id}        -> soft delete

  GET    /fournisseurs             -> liste fournisseurs
  POST   /fournisseurs             -> create/update
  POST   /fournisseurs/{id}/logo   -> upload logo (multipart)
  DELETE /fournisseurs/{id}        -> soft delete

  GET    /types-releve             -> liste types
  POST   /types-releve             -> create/update
  DELETE /types-releve/{id}        -> soft delete
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import calcul_carte_carb as calcul_svc
from app.intranets.adm.services import gestion_carte_carb as svc
from app.intranets.adm.services import import_carte_carb as import_svc


router = APIRouter(prefix="/carte-carb", tags=["adm-carte-carb"])


# ---------------------------------------------------------------------------
# Cartes carburant
# ---------------------------------------------------------------------------


class CartePayload(BaseModel):
    id_carte_carburant: str = "0"
    code_carte: str = ""
    num_carte: str = ""
    id_carte_fournisseur: int = 0
    is_actif: bool = True


@router.get("/cartes")
def get_cartes(_user: UserToken = Depends(get_current_user)):
    return svc.list_cartes()


@router.post("/cartes")
def post_carte(
    payload: CartePayload,
    user: UserToken = Depends(get_current_user),
):
    return svc.save_carte(payload.model_dump(), user.id_salarie)


@router.delete("/cartes/{id_carte}")
def delete_carte(
    id_carte: int,
    user: UserToken = Depends(get_current_user),
):
    return svc.delete_carte(id_carte, user.id_salarie)


# ---------------------------------------------------------------------------
# Attributions de la carte
# ---------------------------------------------------------------------------


class AttributionPayload(BaseModel):
    id_carte_attribution: str = "0"
    id_carte_carburant: str
    id_conducteur: str
    du: str = ""
    au: str = ""


@router.get("/cartes/{id_carte}/attributions")
def get_attributions(
    id_carte: int,
    _user: UserToken = Depends(get_current_user),
):
    return svc.list_attributions(id_carte)


@router.get("/attributions/{id_att}")
def get_attribution(
    id_att: int,
    _user: UserToken = Depends(get_current_user),
):
    a = svc.get_attribution(id_att)
    if not a:
        raise HTTPException(404, "Attribution introuvable")
    return a


@router.post("/attributions")
def post_attribution(
    payload: AttributionPayload,
    user: UserToken = Depends(get_current_user),
):
    return svc.save_attribution(payload.model_dump(), user.id_salarie)


@router.delete("/attributions/{id_att}")
def delete_attribution(
    id_att: int,
    user: UserToken = Depends(get_current_user),
):
    return svc.delete_attribution(id_att, user.id_salarie)


# ---------------------------------------------------------------------------
# Fournisseurs
# ---------------------------------------------------------------------------


class FournisseurPayload(BaseModel):
    id_carte_fournisseur: str = "0"
    nom_fournisseur: str = ""


@router.get("/fournisseurs")
def get_fournisseurs(_user: UserToken = Depends(get_current_user)):
    return svc.list_fournisseurs()


@router.post("/fournisseurs")
def post_fournisseur(
    payload: FournisseurPayload,
    user: UserToken = Depends(get_current_user),
):
    return svc.save_fournisseur(payload.model_dump(), user.id_salarie)


@router.post("/fournisseurs/{id_four}/logo")
async def post_logo_fournisseur(
    id_four: int,
    file: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    content = await file.read()
    res = svc.upload_logo_fournisseur(id_four, content, user.id_salarie)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec")
    return res


@router.delete("/fournisseurs/{id_four}")
def delete_fournisseur(
    id_four: int,
    user: UserToken = Depends(get_current_user),
):
    return svc.delete_fournisseur(id_four, user.id_salarie)


# ---------------------------------------------------------------------------
# Types de releve fournisseur
# ---------------------------------------------------------------------------


class TypeReleve(BaseModel):
    id_type_releve_fournisseur: str = "0"
    lib_type: str = ""
    categorie: str = ""


@router.get("/types-releve")
def get_types(_user: UserToken = Depends(get_current_user)):
    return svc.list_types_releve()


@router.post("/types-releve")
def post_type(
    payload: TypeReleve,
    user: UserToken = Depends(get_current_user),
):
    return svc.save_type_releve(payload.model_dump(), user.id_salarie)


@router.delete("/types-releve/{id_type}")
def delete_type(
    id_type: int,
    user: UserToken = Depends(get_current_user),
):
    return svc.delete_type_releve(id_type, user.id_salarie)


# ---------------------------------------------------------------------------
# Import Excel fournisseur (Fen_ImportFournisseurCarte)
# ---------------------------------------------------------------------------


@router.post("/import-fournisseur")
async def post_import_fournisseur(
    file: UploadFile = File(...),
    type_import: str = Form(...),  # 'total_energies' ...
    id_carte_fournisseur: int = Form(...),
    ligne_depart: int = Form(2),
    simulation: bool = Form(False),
    cols: str = Form(""),  # JSON dict {id_facture:'A', compte_client:'B', ...}
    user: UserToken = Depends(get_current_user),
):
    """Import releves Excel. type_import = 'total_energies' pour l'instant."""
    content = await file.read()
    try:
        cols_dict = json.loads(cols) if cols else {}
    except Exception:
        raise HTTPException(400, "cols invalide (JSON attendu)")

    if type_import == "total_energies":
        res = import_svc.import_total_energies(
            content, id_carte_fournisseur, ligne_depart,
            cols_dict, simulation, user.id_salarie,
        )
    else:
        raise HTTPException(400, f"type_import non supporte : {type_import}")

    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec import")
    return res


# ---------------------------------------------------------------------------
# Calcul montant carte carburant (Fen_CalculCart)
# ---------------------------------------------------------------------------


class CalculPayload(BaseModel):
    mois: int
    annee: int


@router.post("/calcul")
def post_calcul(
    payload: CalculPayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Démarrer Calcul' : recalcule et persiste."""
    res = calcul_svc.calcul_montant_cartes(
        payload.mois, payload.annee, user.id_salarie,
    )
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "Echec calcul")
    return res


@router.get("/calcul")
def get_calcul(
    mois: int,
    annee: int,
    _user: UserToken = Depends(get_current_user),
):
    """Relit le tableau de calcul deja persiste (pas de recalcul)."""
    return calcul_svc.list_calcul(mois, annee)


class CalculAttribuePayload(BaseModel):
    montant_attribue: float


@router.put("/calcul/{id_calc}/attribue")
def put_calcul_attribue(
    id_calc: int,
    payload: CalculAttribuePayload,
    user: UserToken = Depends(get_current_user),
):
    """Ajustement manuel du MontantAttribue."""
    return calcul_svc.update_montant_attribue(
        id_calc, payload.montant_attribue, user.id_salarie,
    )


# ---------------------------------------------------------------------------
# Recherche releves (Fen_RechercheRelev)
# ---------------------------------------------------------------------------


@router.get("/categories")
def get_categories(_user: UserToken = Depends(get_current_user)):
    """DISTINCT TypeReleveFournisseur.Categorie pour le combo de filtre."""
    return svc.list_categories()


@router.get("/cartes-combo")
def get_cartes_combo(_user: UserToken = Depends(get_current_user)):
    """Combo 'Carte carburant' (NomFournisseur - NumCarte)."""
    return svc.list_cartes_combo()


@router.get("/releves/search")
def get_releves_search(
    du: str,
    au: str,
    id_carte_carburant: int = 0,
    categorie: str = "",
    _user: UserToken = Depends(get_current_user),
):
    """Btn Loupe : retourne {lignes, total_ttc}."""
    return svc.search_releves(du, au, id_carte_carburant, categorie)


@router.get("/alertes/detect")
def get_alertes(
    du: str,
    au: str,
    _user: UserToken = Depends(get_current_user),
):
    """Fen_AnalyseCarb btn 'Detecter alerte'. Detecte les pleins
    Vendredi + Lundi sur la meme carte (= soupcon d'usage perso)."""
    return svc.detect_alertes(du, au)
