"""
Router Fen_PaiesBS - Module paies.

Endpoints Etape 1 :
  POST /adm/paies/lister-contrats - Btn Lister les contrats
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.paies_bs import (
    ListerContratsParams, ListerContratsResult,
    ValiderPaiesParams, ValiderPaiesResult,
)
from app.intranets.adm.services import paies_bs as svc

router = APIRouter(
    prefix="/paies",
    tags=["adm-paies"],
)


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


@router.post("/lister-contrats", response_model=ListerContratsResult)
def post_lister_contrats(
    params: ListerContratsParams,
    user: UserToken = Depends(get_current_user),
):
    """Cf. WinDev Btn Lister les contrats.

    Retourne la liste des contrats du salarie sur le mois de paiement,
    par partenaire actif, avec enrichissement options ENI/SFR + calcul
    jours non-prod + separation contrats decommission.
    """
    _require_droit(user, "ModPaie")
    return svc.lister_contrats(params)


@router.post("/valider-paies", response_model=ValiderPaiesResult)
def post_valider_paies(
    params: ValiderPaiesParams,
    user: UserToken = Depends(get_current_user),
):
    """Cf. WinDev Btn Valider les paies.

    Valide la paie du salarie :
    - Pour SFR + type_etat=8 + date_racc_valid <= date_racc_limite :
      passe l'etat a 6 (Paye par employeur - Raccordement) + UPDATE
      mois_p_ra + nb_pts_payes_ra + histo etat (si non-simu).
    - Reset mois_paiement pour rejet/resil (autres partenaires).
    - Calcule le nombre de titres restaurant (TR) :
      * 3 ctts ENI/IAG/STR par jour = 1 TR
      * 1 ctt SFR-Fibre par jour    = 1 TR
    """
    _require_droit(user, "ModPaie")
    return svc.valider_paies(params, user.id_salarie)
