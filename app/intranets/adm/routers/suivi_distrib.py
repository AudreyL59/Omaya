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


# --------------------------------------------------------------------
# 5 boutons Doc (uniques + annuels)
# --------------------------------------------------------------------

class AssocierGerantPayload(BaseModel):
    nom_fichier: str


@router.post("/docs/{id_doc}/associer-pc")
async def post_associer_doc_pc(
    id_doc: int,
    fichier: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    """Btn Associer (vert) - cas 1 : upload depuis le PC."""
    _require_droit(user, "SuiviADMDistDoc")
    content = await fichier.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide")
    return svc.associer_doc_from_pc(
        id_doc, fichier.filename or "doc.pdf", content, user.id_salarie,
    )


@router.post("/docs/{id_doc}/associer-gerant")
def post_associer_doc_gerant(
    id_doc: int,
    payload: AssocierGerantPayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn Associer (vert) - cas 2 : choix depuis l'espace Doc du Gerant."""
    _require_droit(user, "SuiviADMDistDoc")
    return svc.associer_doc_from_gerant(
        id_doc, payload.nom_fichier, user.id_salarie,
    )


@router.post("/docs/{id_doc}/desassocier")
def post_desassocier_doc(
    id_doc: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Desassocier (rouge) : vide nom_fichier + date_depot."""
    _require_droit(user, "SuiviADMDistDoc")
    return svc.desassocier_doc(id_doc, user.id_salarie)


@router.delete("/docs/{id_doc}")
def delete_doc(
    id_doc: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Poubelle : soft-delete (modif_elem = 'suppr')."""
    _require_droit(user, "SuiviADMDistDoc")
    return svc.supprimer_doc(id_doc, user.id_salarie)


@router.post("/docs/{id_doc}/toggle-rappel")
def post_toggle_rappel_doc(
    id_doc: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Active/Deactive rappel : bascule 'PAS RAPPEL' <-> ''."""
    _require_droit(user, "SuiviADMDistDoc")
    return svc.toggle_rappel_doc(id_doc, user.id_salarie)


class AddMemoPayload(BaseModel):
    message: str


@router.get("/{id_ste}/suivi-adm")
def get_suivi_adm(
    id_ste: int,
    user: UserToken = Depends(get_current_user),
):
    """Liste des memos suivi ADM du gerant de la societe.

    Cf. WinDev Table_ReqSuiviADM (ordonne par datecrea DESC).
    """
    _require_droit(user, "SuiviADMDistri")
    return {"items": svc.list_suivi_adm(id_ste)}


@router.post("/{id_ste}/suivi-adm")
def post_add_memo_suivi_adm(
    id_ste: int,
    payload: AddMemoPayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Envoyer' : INSERT salarie_suiviADM + mail juristes/BO."""
    _require_droit(user, "SuiviADMDistri")
    return svc.add_memo_suivi_adm(
        id_ste, payload.message, user.id_salarie,
    )


@router.get("/docs/{id_doc}/telecharger")
def get_telecharger_doc(
    id_doc: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Telecharger : recupere le contenu du fichier depuis FTP.
    Retour : StreamingResponse (application/octet-stream + Content-Disposition).
    """
    from fastapi.responses import Response
    _require_droit(user, "SuiviADMDistDoc")
    d = svc.download_doc(id_doc)
    if not d:
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    # Determine MIME rapide
    fname = d["filename"]
    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
    mime = {
        "pdf": "application/pdf",
        "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    }.get(ext, "application/octet-stream")
    return Response(
        content=d["content"],
        media_type=mime,
        headers={"Content-Disposition": f'inline; filename="{fname}"'},
    )
