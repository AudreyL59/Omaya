"""
Liste des annonceurs actifs — pour la combo Stats RH Annonceurs.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.core.database import get_connection

router = APIRouter(prefix="/annonceurs", tags=["adm-annonceurs"])


class AnnonceurItem(BaseModel):
    id_annonceur: str
    lib_annonceur: str


@router.get("/list", response_model=list[AnnonceurItem])
def list_annonceurs(user: UserToken = Depends(get_current_user)):
    """
    Retourne tous les annonceurs (actifs ET inactifs), tries par libelle.
    Inclut les inactifs car ils peuvent avoir des CV historiques a analyser.
    """
    db = get_connection("recrutement")
    rows = db.query(
        """SELECT IDCvAnnonceur, Lib_Annonceur, IsActif
        FROM CvAnnonceur
        WHERE ModifElem NOT LIKE '%suppr%'
        ORDER BY Lib_Annonceur"""
    )
    result = []
    for r in rows:
        id_ann = int(r.get("IDCvAnnonceur") or 0)
        # Sanity check : ignorer les ids bogus (NULL HFSQL renvoye comme 2^64-1)
        if id_ann <= 0 or id_ann > 9_000_000_000_000_000_000:
            continue
        lib = r.get("Lib_Annonceur") or ""
        if not bool(r.get("IsActif")):
            lib = f"{lib} (inactif)"
        result.append({
            "id_annonceur": str(id_ann),
            "lib_annonceur": lib,
        })
    return result
