"""
Router shared SDTC (Solde De Tout Compte).

Endpoint principal :
  GET /api/shared/sdtc/{id_salarie}/load
    -> Charge les infos consolidees (salarie, societe, sortie, mutuelle,
       date dernier contrat) necessaires a l'affichage du resume SDTC.

Auth : utilisateur connecte (Bearer token, n'importe quel intranet).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.shared.sdtc import service as svc
from app.shared.sdtc.bareme import compute_bareme
from app.shared.sdtc.contrats import load_contrats

router = APIRouter(prefix="/api/shared/sdtc", tags=["shared-sdtc"])


class ComputeBaremePayload(BaseModel):
    contrat_ids: list[str]


def _parse_id(id_salarie: str) -> int:
    try:
        return int(id_salarie)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"id_salarie invalide : {id_salarie}",
        )


@router.get("/{id_salarie}/load")
def sdtc_load(id_salarie: str, _user: UserToken = Depends(get_current_user)):
    sid = _parse_id(id_salarie)
    data = svc.load(sid)
    if not data.get("found"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salarie introuvable.",
        )
    return data


@router.get("/{id_salarie}/contrats")
def sdtc_contrats(id_salarie: str, _user: UserToken = Depends(get_current_user)):
    """Charge les contrats du salarie tous partenaires confondus, repartis
    en 'traites' (deja affectes) et 'a_traiter' (eligibles SDTC)."""
    sid = _parse_id(id_salarie)
    return load_contrats(sid)


@router.post("/{id_salarie}/compute-bareme")
def sdtc_compute_bareme(
    id_salarie: str,
    payload: ComputeBaremePayload,
    _user: UserToken = Depends(get_current_user),
):
    """Calcule le bareme + commissions pour la selection de contrats donnee.

    Recharge la liste complete des contrats du salarie puis filtre selon les
    id_contrat fournis. Garde-fou anti-spoof : le calcul ne s'appuie que sur
    les donnees de la base, jamais sur des montants fournis par le client.
    """
    sid = _parse_id(id_salarie)
    selection_ids = {cid.strip() for cid in payload.contrat_ids if cid and cid.strip()}
    if not selection_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun contrat selectionne.",
        )

    data = load_contrats(sid)
    all_contrats: list[dict] = list(data.get("traites") or []) + list(
        data.get("a_traiter") or []
    )
    selected = [c for c in all_contrats if str(c.get("id_contrat")) in selection_ids]
    if not selected:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun contrat trouve pour les ids fournis.",
        )

    result = compute_bareme(selected)
    return {
        "nb_selectionnes": len(selected),
        "selection_ids": sorted(selection_ids),
        **result.to_dict(),
    }
