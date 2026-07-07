"""
Router Fen_PaiesBS - Module paies.

Endpoints Etape 1 :
  POST /adm/paies/lister-contrats - Btn Lister les contrats
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.paies_bs import (
    GenerationBaseParams, GenerationBaseResult,
    ListerContratsParams, ListerContratsResult,
    ValiderPaiesParams, ValiderPaiesResult,
)
from app.intranets.adm.services import paies_bs as svc
from app.intranets.adm.services import paies_bs_pdf as pdf_svc

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


@router.post("/generation-base-pdf", response_model=GenerationBaseResult)
def post_generation_base_pdf(
    params: GenerationBaseParams,
    user: UserToken = Depends(get_current_user),
):
    """Cf. WinDev GenerationBase() : genere le PDF EtatBaseSalaire
    (Base Contrat) + upload FTP gestionRH/{id_sal}/Fiches_Salaires/.

    Retour : { pdf_b64, ftp_uploaded, url, fic_name }.
    """
    _require_droit(user, "ModPaie")
    return pdf_svc.generer_base_pdf(params, user.id_salarie)
