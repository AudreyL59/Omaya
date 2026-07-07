"""
Recherche de salaries - commune a l'intranet ADM.

Utilisee par les pickers de salarie dans les pages Stats RH, Factures,
Fen_FicheSalaires (attribution manuelle), etc.

Cf. WinDev Fen_RechercheNomSalarie : chaque resultat affiche
poste + societe + date embauche + statut (Toujours en activite /
plus dans les effectifs).
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.core.database.pg import get_pg_connection

router = APIRouter(prefix="/salaries", tags=["adm-salaries"])


class SalarieItem(BaseModel):
    id_salarie: str
    nom: str
    prenom: str
    # Contexte enrichi (cf. Fen_RechercheNomSalarie)
    poste: str = ""              # prof_poste (VRP multicartes, Manager...)
    raison_sociale: str = ""     # rs_interne de la societe (S'COOL, ILLYADE...)
    date_embauche: str = ""      # YYYY-MM-DD (date_debut du dernier segment)
    date_sortie: str = ""        # YYYY-MM-DD (vide si en_activite=TRUE)
    en_activite: bool = False


@router.get("/search", response_model=list[SalarieItem])
def search_salaries(
    q: str = Query(..., min_length=1),
    include_sortis: bool = Query(True),
    user: UserToken = Depends(get_current_user),
):
    """
    Recherche les salaries par nom OU prenom. Les noms sont stockes en
    majuscules en base : on uppercase la saisie pour matcher.

    Params :
      q : chaine (min 1 char), matche 'q%' sur nom OU prenom
      include_sortis : si True, inclut les salaries sortis (defaut True
        pour permettre l'attribution des fiches de salaire aux anciens).

    Chaque resultat inclut le contexte (poste, societe, date_embauche,
    en_activite) pour affichage riche cote frontend.
    """
    search = q.strip().upper()
    if not search:
        return []

    db = get_pg_connection("rh")
    like = f"{search}%"

    en_activite_clause = "" if include_sortis else "AND se.en_activite = TRUE"

    rows = db.query(
        f"""SELECT DISTINCT ON (s.id_salarie)
                s.id_salarie, s.nom, s.prenom,
                tp.lib_poste, se.date_debut,
                se.en_activite,
                ste.rs_interne,
                ss.date_sortie_reelle
              FROM pgt_salarie s
              INNER JOIN pgt_salarie_embauche se ON s.id_salarie = se.id_salarie
              LEFT JOIN pgt_societe ste ON ste.id_ste = se.id_ste
              LEFT JOIN pgt_type_poste tp
                     ON tp.id_type_poste = se.id_type_poste
              LEFT JOIN pgt_salarie_sortie ss
                     ON ss.id_salarie = s.id_salarie
                    AND (ss.modif_elem IS NULL
                         OR ss.modif_elem NOT LIKE '%suppr%')
             WHERE (s.nom LIKE ? OR UPPER(s.prenom) LIKE ?)
               AND (se.modif_elem IS NULL OR se.modif_elem NOT LIKE '%suppr%')
               {en_activite_clause}
             ORDER BY s.id_salarie, se.date_debut DESC NULLS LAST,
                      ss.date_sortie_reelle DESC NULLS LAST""",
        (like, like),
    )

    def _iso(v) -> str:
        if v is None:
            return ""
        s = str(v)[:10]
        if s.startswith("1900") or s.startswith("0000"):
            return ""
        return s

    items = []
    for r in rows:
        items.append({
            "id_salarie": str(r.get("id_salarie")),
            "nom": (r.get("nom") or "").strip(),
            "prenom": (r.get("prenom") or "").strip(),
            "poste": (r.get("lib_poste") or "").strip(),
            "raison_sociale": (r.get("rs_interne") or "").strip(),
            "date_embauche": _iso(r.get("date_debut")),
            "date_sortie": (
                "" if r.get("en_activite")
                else _iso(r.get("date_sortie_reelle"))
            ),
            "en_activite": bool(r.get("en_activite")),
        })
    # Tri final : actifs d'abord puis sortis, puis alpha
    items.sort(
        key=lambda x: (
            0 if x["en_activite"] else 1,
            x["nom"], x["prenom"],
        ),
    )
    return items
