from fastapi import APIRouter, Depends, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.vendeur.schemas.cooptation import (
    CooptationItem,
    VendeurItem,
    VilleItem,
    CooptationCreate,
)
from app.intranets.vendeur.services.cooptation import (
    lister_cooptations_du_jour,
    rechercher_vendeurs,
    creer_cooptation,
)
from app.intranets.vendeur.services.communes import rechercher_par_cp

router = APIRouter(prefix="/cooptation", tags=["vendeur-cooptation"])


@router.get("", response_model=list[CooptationItem])
def get_cooptations(user: UserToken = Depends(get_current_user)):
    """Liste les cooptations saisies par l'utilisateur aujourd'hui."""
    return lister_cooptations_du_jour(user.id_salarie)


@router.get("/vendeurs", response_model=list[VendeurItem])
def get_vendeurs(q: str = "", user: UserToken = Depends(get_current_user)):
    """Recherche les vendeurs accessibles à l'utilisateur par début de nom."""
    acces_global = "ProdRezo" in user.droits
    is_resp = user.is_resp or "ProdGR" in user.droits
    return rechercher_vendeurs(
        user.id_salarie, q, acces_global=acces_global, is_resp=is_resp
    )


@router.get("/villes/{cp}", response_model=list[VilleItem])
def get_villes(cp: str):
    """Liste les villes correspondant à un code postal."""
    return rechercher_par_cp(cp)


@router.post("", response_model=dict)
def post_cooptation(
    data: CooptationCreate,
    user: UserToken = Depends(get_current_user),
):
    """Crée une nouvelle cooptation."""
    if not data.cp:
        raise HTTPException(status_code=400, detail="Code postal requis")
    if not data.id_vendeur or data.id_vendeur == "0":
        raise HTTPException(status_code=400, detail="Coopteur requis")
    if data.id_ville == 0:
        raise HTTPException(status_code=400, detail="Ville requise")
    if not data.gsm:
        raise HTTPException(status_code=400, detail="Numéro de téléphone requis")
    if not data.cooptation_directe and not data.lien_parente:
        raise HTTPException(status_code=400, detail="Lien de parenté du parrain requis")

    id_coopt = creer_cooptation(
        data=data.model_dump(),
        id_salarie_user=user.id_salarie,
        id_ste_user=user.id_ste,
    )
    return {"id": id_coopt}
