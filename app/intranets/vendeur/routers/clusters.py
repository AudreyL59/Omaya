from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.core.database import get_connection
from app.intranets.vendeur.schemas.clusters import ClusterCard, GroupementItem
from app.intranets.vendeur.services.clusters import (
    list_clusters,
    list_groupements,
)

router = APIRouter(prefix="/clusters", tags=["vendeur-clusters"])


def _get_user_scope(user: UserToken) -> dict:
    """
    Récupère les infos nécessaires pour scoper/afficher les cartes :
      - id_affectation : premier salarie_organigramme actif du user
      - lib_affectation : Lib_ORGA correspondant
      - lib_societe : RaisonSociale du user (via id_ste)
      - logo_ste : logo société (GUIMMICK) en base64
    """
    db_rh = get_connection("rh")
    today = datetime.now().strftime("%Y%m%d")

    # Affectation principale
    aff_row = db_rh.query_one(
        """SELECT TOP 1 so.idorganigramme, o.Lib_ORGA
        FROM salarie_organigramme so
        LEFT JOIN organigramme o ON o.idorganigramme = so.idorganigramme
        WHERE so.IDSalarie = ?
          AND so.ModifELEM <> 'suppr'
          AND LEFT(so.DateDébut, 8) <= ?
          AND (so.DateFin = '' OR LEFT(so.DateFin, 8) >= ?)
        ORDER BY so.DateDébut DESC""",
        (user.id_salarie, today, today),
    )
    id_affectation = 0
    lib_affectation = ""
    if aff_row:
        raw_id = aff_row.get("idorganigramme")
        try:
            id_affectation = int(raw_id) if raw_id not in (None, "") else 0
        except (TypeError, ValueError):
            id_affectation = 0
        lib_affectation = aff_row.get("Lib_ORGA") or ""

    # Société du user
    lib_societe = ""
    logo_ste = ""
    if user.id_ste:
        ste_row = db_rh.query_one(
            "SELECT RaisonSociale, GUIMMICK FROM societe WHERE IdSte = ?",
            (user.id_ste,),
        )
        if ste_row:
            lib_societe = ste_row.get("RaisonSociale") or ""
            logo_ste = ste_row.get("GUIMMICK") or ""

    return {
        "id_affectation": id_affectation,
        "lib_affectation": lib_affectation,
        "lib_societe": lib_societe,
        "logo_ste": logo_ste,
    }


@router.get("", response_model=list[ClusterCard])
def get_clusters(
    mois_du: int = Query(..., ge=1, le=12),
    annee_du: int = Query(..., ge=2000, le=2100),
    mois_au: int = Query(..., ge=1, le=12),
    annee_au: int = Query(..., ge=2000, le=2100),
    code_vad: str = Query("", description="Si fourni, retourne les sous-clusters du département"),
    jetons: list[str] = Query(default_factory=list, description="Filtres texte (chips)"),
    user: UserToken = Depends(get_current_user),
):
    """
    Liste des clusters SFR.

    - Sans code_vad : cartes agrégées par département (ex: "14 - Calvados")
    - Avec code_vad : sous-clusters du département (ex: "14-01", "14-02")

    Filtrage :
      - droit ProdRezo : voit tous les responsables
      - sinon : restreint à son affectation + lignes Réseau (IDResp=0)
    """
    acces_global = "ProdRezo" in user.droits
    scope = _get_user_scope(user) if not acces_global else {
        "id_affectation": 0,
        "lib_affectation": "",
        "lib_societe": "",
        "logo_ste": "",
    }

    return list_clusters(
        mois_du=mois_du,
        annee_du=annee_du,
        mois_au=mois_au,
        annee_au=annee_au,
        acces_global=acces_global,
        id_affectation_user=scope["id_affectation"],
        id_ste_user=user.id_ste,
        lib_societe_user=scope["lib_societe"],
        lib_affectation_user=scope["lib_affectation"],
        logo_ste_user=scope["logo_ste"],
        code_vad_parent=code_vad,
        jetons=jetons,
    )


@router.get("/groupements", response_model=list[GroupementItem])
def get_groupements(user: UserToken = Depends(get_current_user)):
    """
    Retourne la liste des orgas internes servant de chips de filtre.
    Actuellement hardcodée ; à rendre dynamique plus tard.
    """
    return list_groupements()
