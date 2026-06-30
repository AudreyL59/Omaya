"""Router Fen_FacturesSuivi + Fen_FactureFiche (ADM > Suivi des factures)."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import factures as svc

router = APIRouter(prefix="/factures", tags=["adm-factures"])


@router.get("/operateurs", response_model=list[svc.OperateurItem])
def get_operateurs(_u: UserToken = Depends(get_current_user)):
    return svc.list_operateurs_staff()


@router.get("/enseignes", response_model=list[svc.EnseigneItem])
def get_enseignes(_u: UserToken = Depends(get_current_user)):
    return svc.list_enseignes()


@router.get("/societes", response_model=list[svc.SocieteItem])
def get_societes(_u: UserToken = Depends(get_current_user)):
    return svc.list_societes()


@router.post("/search", response_model=list[svc.FactureLigne])
def post_search(
    filters: svc.FactureSearchFilters,
    _u: UserToken = Depends(get_current_user),
):
    return svc.search_factures(filters)


@router.get("/beneficiaires", response_model=list[svc.BeneficiaireItem])
def get_beneficiaires(
    mode: str = "salarie",   # 'salarie' ou 'service'
    q: str = "",
    _u: UserToken = Depends(get_current_user),
):
    return svc.search_beneficiaires(mode, q)


@router.post("/commandes")
def post_commande(
    payload: svc.CommandeCreatePayload,
    u: UserToken = Depends(get_current_user),
):
    id_new = svc.create_commande(payload, u.id_salarie)
    return {"ok": True, "id_commande": str(id_new)}


@router.delete("/commandes/{id_commande}")
def delete_commande(
    id_commande: int,
    u: UserToken = Depends(get_current_user),
):
    svc.delete_commande(id_commande, u.id_salarie)
    return {"ok": True}


# -- Fen_FactureFiche : detail + update + factures associees ----------


@router.get("/commandes/{id_commande}", response_model=svc.CommandeDetail)
def get_commande(
    id_commande: int,
    _u: UserToken = Depends(get_current_user),
):
    detail = svc.get_commande_detail(id_commande)
    if not detail:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    return detail


@router.put("/commandes/{id_commande}")
def put_commande(
    id_commande: int,
    payload: svc.CommandeCreatePayload,
    u: UserToken = Depends(get_current_user),
):
    svc.update_commande(id_commande, payload, u.id_salarie)
    return {"ok": True}


@router.get("/commandes/{id_commande}/factures",
            response_model=list[svc.FactureItem])
def get_factures(
    id_commande: int,
    _u: UserToken = Depends(get_current_user),
):
    return svc.list_factures_for_commande(id_commande)


@router.post("/commandes/{id_commande}/factures")
async def post_facture(
    id_commande: int,
    montant_ttc: float = Form(...),
    file: UploadFile = File(...),
    u: UserToken = Depends(get_current_user),
):
    content = await file.read()
    id_new = svc.add_facture(
        id_commande, content, file.filename or "facture.pdf",
        montant_ttc, u.id_salarie,
    )
    return {"ok": True, "id_commande_facture": str(id_new)}


@router.delete("/factures/{id_facture}")
def delete_facture(
    id_facture: int,
    u: UserToken = Depends(get_current_user),
):
    svc.delete_facture(id_facture, u.id_salarie)
    return {"ok": True}


@router.get("/factures/{id_facture}/download")
def download_facture(
    id_facture: int,
    _u: UserToken = Depends(get_current_user),
):
    path, name = svc.get_facture_file_path(id_facture)
    if not path:
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(str(path), filename=name)
