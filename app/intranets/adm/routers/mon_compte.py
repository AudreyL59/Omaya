"""
Endpoint fiche salarié pour l'intranet ADM.

Accès global ADM : pas de contrôle 'FicheVend' — le droit d'accès à l'intranet
ADM suffit pour consulter la fiche de n'importe quel salarié.
"""

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.vendeur.routers.mon_compte import _charger_fiche
from app.intranets.vendeur.schemas.mon_compte import DocumentItem, MonCompteResponse
from app.intranets.vendeur.services.ftp_documents import lister_fiches_salaire

router = APIRouter(prefix="/mon-compte", tags=["adm-mon-compte"])


@router.get("/fiche/{id_salarie}", response_model=MonCompteResponse)
def get_fiche_salarie(id_salarie: int, user: UserToken = Depends(get_current_user)):
    return _charger_fiche(id_salarie)


@router.get("/fiche/{id_salarie}/documents", response_model=list[DocumentItem])
def get_fiche_documents(id_salarie: int, user: UserToken = Depends(get_current_user)):
    return lister_fiches_salaire(id_salarie)
