"""
Router Gestion Exo Cash (Fen_GestionExoCash + Fen_LotFiche).

Endpoints Onglet Lots :
  GET    /gestion-exo-cash/lots                     - liste
  GET    /gestion-exo-cash/lots/{id_lot}            - detail
  POST   /gestion-exo-cash/lots                     - create/update
  POST   /gestion-exo-cash/lots/{id_lot}/duplicate  - duplicate
  DELETE /gestion-exo-cash/lots/{id_lot}            - soft-delete
  POST   /gestion-exo-cash/lots/{id_lot}/photo/{num} - upload photo (1|2|3)
  DELETE /gestion-exo-cash/lots/{id_lot}/photo/{num} - delete photo
  GET    /gestion-exo-cash/lots/{id_lot}/photo/{num} - download photo

Endpoint Combo Famille :
  GET    /gestion-exo-cash/familles                 - liste
"""

from fastapi import (
    APIRouter, Depends, File, HTTPException, UploadFile,
)
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import gestion_exo_cash as svc

router = APIRouter(
    prefix="/gestion-exo-cash",
    tags=["adm-gestion-exo-cash"],
)


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


class LotPayload(BaseModel):
    id_exo_cash_lot: int = 0
    id_exo_cash_famille_lot: int = 0
    marque: str = ""
    lib_lot: str = ""
    description: str = ""
    montant: float = 0
    categorie: int = 0
    stock: int = 0
    sur_commande: bool = False
    en_solde: bool = False
    montant_solde: float = 0
    solde_deb: str = ""
    solde_fin: str = ""
    is_actif: bool = True


# --------------------------------------------------------------------
# Familles (combo)
# --------------------------------------------------------------------

@router.get("/familles")
def get_familles(user: UserToken = Depends(get_current_user)):
    """Combo Famille - liste des familles Exo Cash actives."""
    _require_droit(user, "GestExoCash")
    return {"items": svc.list_familles()}


class FamillePayload(BaseModel):
    id_exo_cash_famille_lot: int = 0
    lib_famille_lot: str = ""


@router.post("/familles")
def post_save_famille(
    payload: FamillePayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn Enregistrer Famille - INSERT si id=0, UPDATE sinon."""
    _require_droit(user, "GestExoCash")
    return svc.save_famille(
        payload.id_exo_cash_famille_lot,
        payload.lib_famille_lot,
        user.id_salarie,
    )


@router.delete("/familles/{id_famille}")
def delete_famille(
    id_famille: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Suppr Famille - soft-delete."""
    _require_droit(user, "GestExoCash")
    return svc.delete_famille(id_famille, user.id_salarie)


@router.post("/familles/{id_famille}/icone")
async def post_upload_icone(
    id_famille: int,
    fichier: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    """Btn Telecharger + Enregistrer icone Famille."""
    _require_droit(user, "GestExoCash")
    content = await fichier.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide")
    return svc.upload_icone(id_famille, content, user.id_salarie)


@router.get("/familles/{id_famille}/icone")
def get_icone(
    id_famille: int,
    user: UserToken = Depends(get_current_user),
):
    """Retourne le bytea de l icone."""
    _require_droit(user, "GestExoCash")
    content = svc.get_icone(id_famille)
    if not content:
        raise HTTPException(status_code=404, detail="Icone introuvable")
    mime = "image/jpeg"
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    elif content[:6] in (b"GIF87a", b"GIF89a"):
        mime = "image/gif"
    return Response(content=content, media_type=mime,
                    headers={"Cache-Control": "private, max-age=60"})


# --------------------------------------------------------------------
# Suivi des livrets (onglet 3)
# --------------------------------------------------------------------

@router.get("/suivi-livrets")
def get_suivi_livrets(user: UserToken = Depends(get_current_user)):
    """Table reqSuiviLivret - SUM debit/credit par salarie actif."""
    _require_droit(user, "GestExoCash")
    return {"items": svc.list_suivi_livrets()}


# --------------------------------------------------------------------
# Lots
# --------------------------------------------------------------------

@router.get("/lots")
def get_lots(user: UserToken = Depends(get_current_user)):
    """Table ReqLot - tous les lots avec famille."""
    _require_droit(user, "GestExoCash")
    return {"items": svc.list_lots()}


@router.get("/lots/{id_lot}")
def get_lot(id_lot: int, user: UserToken = Depends(get_current_user)):
    """Detail d'un lot (sans les photos)."""
    _require_droit(user, "GestExoCash")
    r = svc.get_lot(id_lot)
    if not r:
        raise HTTPException(status_code=404, detail="Lot introuvable")
    return r


@router.post("/lots")
def post_save_lot(
    payload: LotPayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn Enregistrer - INSERT si id=0, UPDATE sinon."""
    _require_droit(user, "GestExoCash")
    return svc.save_lot(payload.model_dump(), user.id_salarie)


@router.post("/lots/{id_lot}/duplicate")
def post_duplicate_lot(
    id_lot: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Duplique - copie du lot (avec photos)."""
    _require_droit(user, "GestExoCash")
    return svc.duplicate_lot(id_lot, user.id_salarie)


@router.delete("/lots/{id_lot}")
def delete_lot(
    id_lot: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Suppr - soft-delete."""
    _require_droit(user, "GestExoCash")
    return svc.delete_lot(id_lot, user.id_salarie)


# --------------------------------------------------------------------
# Photos (1, 2, 3)
# --------------------------------------------------------------------

@router.post("/lots/{id_lot}/photo/{num}")
async def post_upload_photo(
    id_lot: int,
    num: int,
    fichier: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    """Charger Photo N - upload d'une image (bytea)."""
    _require_droit(user, "GestExoCash")
    content = await fichier.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide")
    return svc.upload_photo(id_lot, num, content, user.id_salarie)


@router.delete("/lots/{id_lot}/photo/{num}")
def delete_photo(
    id_lot: int,
    num: int,
    user: UserToken = Depends(get_current_user),
):
    """Btn Suppr photo N - vide la colonne."""
    _require_droit(user, "GestExoCash")
    return svc.delete_photo(id_lot, num, user.id_salarie)


@router.get("/lots/{id_lot}/photo/{num}")
def get_photo(
    id_lot: int,
    num: int,
    user: UserToken = Depends(get_current_user),
):
    """Retourne le contenu binaire de la photo."""
    _require_droit(user, "GestExoCash")
    content = svc.get_photo(id_lot, num)
    if not content:
        raise HTTPException(status_code=404, detail="Photo introuvable")
    # Detection MIME rapide (signature JPEG/PNG/GIF)
    mime = "image/jpeg"
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    elif content[:6] in (b"GIF87a", b"GIF89a"):
        mime = "image/gif"
    elif content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        mime = "image/webp"
    return Response(
        content=content,
        media_type=mime,
        headers={
            "Cache-Control": "private, max-age=60",
        },
    )
