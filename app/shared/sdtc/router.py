"""
Router shared SDTC (Solde De Tout Compte).

Endpoint principal :
  GET /api/shared/sdtc/{id_salarie}/load
    -> Charge les infos consolidees (salarie, societe, sortie, mutuelle,
       date dernier contrat) necessaires a l'affichage du resume SDTC.

Auth : utilisateur connecte (Bearer token, n'importe quel intranet).
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.shared.sdtc import service as svc

router = APIRouter(prefix="/api/shared/sdtc", tags=["shared-sdtc"])


@router.get("/{id_salarie}/load")
def sdtc_load(id_salarie: str, _user: UserToken = Depends(get_current_user)):
    try:
        sid = int(id_salarie)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"id_salarie invalide : {id_salarie}",
        )
    data = svc.load(sid)
    if not data.get("found"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salarie introuvable.",
        )
    return data
