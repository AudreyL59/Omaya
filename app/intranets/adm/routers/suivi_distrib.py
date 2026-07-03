"""
Router Suivi Distributeurs (Fen_SuiviDistrib + FI_DetailDistributeur).

Endpoints :
  GET /distributeurs                            - liste (?actif=1|0)
  GET /distributeurs/{id_ste}                   - bootstrap detail
  GET /distributeurs/{id_ste}/docs-unique       - docs uniques + tickets
  GET /distributeurs/{id_ste}/docs-annuel       - docs annuels (?annee=YYYY)
  GET /distributeurs/{id_ste}/facturations      - liste tickets facturation

Droits : SuiviADMDistri (base) + SuiviADMDistDoc (docs).
"""

from datetime import date

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException, Query, UploadFile,
)
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import suivi_distrib as svc

router = APIRouter(
    prefix="/distributeurs",
    tags=["adm-suivi-distrib"],
)


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


# --------------------------------------------------------------------
# READ
# --------------------------------------------------------------------

@router.get("")
def get_list(
    actif: bool = Query(True),
    user: UserToken = Depends(get_current_user),
):
    """Liste des distributeurs (id_type_orga=3)."""
    _require_droit(user, "SuiviADMDistri")
    return {"items": svc.list_societes(actif=actif)}


@router.get("/{id_ste}")
def get_detail(
    id_ste: int,
    user: UserToken = Depends(get_current_user),
):
    """Bootstrap detail : dates + annees dispo + gerant."""
    _require_droit(user, "SuiviADMDistri")
    data = svc.get_detail_bootstrap(id_ste)
    if not data:
        raise HTTPException(status_code=404, detail="Societe introuvable")
    return data


@router.get("/{id_ste}/docs-unique")
def get_docs_unique(
    id_ste: int,
    user: UserToken = Depends(get_current_user),
):
    """Liste des docs uniques (rappel_annuel=0) pour la societe."""
    _require_droit(user, "SuiviADMDistDoc")
    return {"items": svc.list_docs_unique(id_ste)}


@router.get("/{id_ste}/docs-annuel")
def get_docs_annuel(
    id_ste: int,
    annee: int = Query(default_factory=lambda: date.today().year),
    user: UserToken = Depends(get_current_user),
):
    """Liste des docs annuels (rappel_annuel>0) pour l'annee donnee."""
    _require_droit(user, "SuiviADMDistDoc")
    return {"items": svc.list_docs_annuel(id_ste, annee), "annee": int(annee)}


@router.get("/{id_ste}/facturations")
def get_facturations(
    id_ste: int,
    user: UserToken = Depends(get_current_user),
):
    """Liste des tickets de facturation pour la societe."""
    _require_droit(user, "SuiviADMDistri")
    return {"items": svc.list_facturations(id_ste)}


@router.get("/refs/types-doc-unique")
def get_types_doc_unique(
    user: UserToken = Depends(get_current_user),
):
    """Combo reqDocUnique : types de docs avec rappel_annuel = 0."""
    _require_droit(user, "SuiviADMDistDoc")
    return {"items": svc.list_types_doc_unique()}


# --------------------------------------------------------------------
# WRITE
# --------------------------------------------------------------------

class AddDocPayload(BaseModel):
    id_type_doc_distributeur: int


class TicketReclamPayload(BaseModel):
    id_doc_distrib: int
    id_gerant: int


@router.post("/{id_ste}/docs-unique/verif")
def post_verif_docs_unique(
    id_ste: int,
    user: UserToken = Depends(get_current_user),
):
    """VerifDocUnique() : auto-cree les docs uniques manquants."""
    _require_droit(user, "SuiviADMDistDoc")
    return svc.verif_docs_unique(id_ste, user.id_salarie)


@router.post("/{id_ste}/docs-annuel/verif")
def post_verif_docs_annuel(
    id_ste: int,
    annee: int = Query(...),
    user: UserToken = Depends(get_current_user),
):
    """VerifDocAnnuel() : auto-cree les docs annuels manquants pour
    l'annee donnee (avec ventilation N occurrences)."""
    _require_droit(user, "SuiviADMDistDoc")
    return svc.verif_docs_annuel(id_ste, annee, user.id_salarie)


@router.post("/{id_ste}/docs-unique")
def post_add_doc_unique(
    id_ste: int,
    payload: AddDocPayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn '+' a cote de la combo : ajout manuel d'un doc unique."""
    _require_droit(user, "SuiviADMDistDoc")
    return svc.add_doc_unique(
        id_ste, payload.id_type_doc_distributeur, user.id_salarie,
    )


@router.post("/{id_ste}/tickets/reclam")
def post_ticket_reclam(
    id_ste: int,
    payload: TicketReclamPayload,
    user: UserToken = Depends(get_current_user),
):
    """Cree un ticket type 31 (reclamation doc). Retourne l'info gsm
    du gerant pour que le frontend puisse declencher le SMS.
    """
    _require_droit(user, "SuiviADMDistDoc")
    return svc.create_ticket_reclam(
        payload.id_doc_distrib, payload.id_gerant, user.id_salarie,
    )


@router.post("/{id_ste}/tickets/facturation")
async def post_ticket_facturation(
    id_ste: int,
    id_gerant: int = Form(...),
    montant: float = Form(...),
    facture: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    """Btn Ticket Facturation : upload PDF + creation ticket type 28
    + mail juristes.
    """
    _require_droit(user, "SuiviADMDistri")
    content = await facture.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide")
    return svc.create_ticket_facturation(
        id_ste, id_gerant, facture.filename or "facture.pdf",
        content, montant, user.id_salarie,
    )


@router.post("/facturation/{id_tk_liste}/recharger")
async def post_recharger_facture(
    id_tk_liste: int,
    facture: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    """Btn Recharger la facture : remplace le PDF + UPDATE fic_facture
    + mail juristes.
    """
    _require_droit(user, "SuiviADMDistri")
    content = await facture.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide")
    return svc.recharger_facture(
        id_tk_liste, facture.filename or "facture.pdf",
        content, user.id_salarie,
    )
