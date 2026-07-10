"""
Router Vendeur - Suivi Tickets Call (Fibre + Energie fusionnes).

Droit d'acces : TicketCall (deja cable dans le menu).
Filtrage orga :
  - Si le user a le droit 'ProdRezo' -> voit tout
  - Sinon -> voit uniquement les tickets dont le vendeur est rattache
    a son orga ou sous-orgas (cf. WinDev ListeOrgaComplet).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.vendeur.services import tickets_call_suivi as svc


router = APIRouter(
    prefix="/tickets-call/suivi",
    tags=["vendeur-tickets-call-suivi"],
)


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


@router.get("/en-cours")
def get_en_cours(user: UserToken = Depends(get_current_user)):
    """Liste unifiee des tickets Call en cours du jour (Fibre + Energie),
    filtree par orga si pas ProdRezo.
    """
    _require_droit(user, "TicketCall")
    id_user = int(user.id_salarie or 0)
    # Note : id_poste_user n'est pas expose dans UserToken. On passe 0
    # (donc pas de filtre TicketDiff pour poste 20). A affiner plus tard
    # si besoin.
    return {
        "tickets_en_cours": svc.list_en_cours_suivi(
            id_user=id_user,
            user_droits=user.droits or [],
            id_poste_user=0,
        ),
    }
