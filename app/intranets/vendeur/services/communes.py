"""
Recherche des villes par code postal.

Transposition de l'endpoint REST WebRest_Omayapp/ListeVilleByCP.
Table communes_france dans Bdd_Omaya_Divers.
"""

from app.core.database import get_connection


def rechercher_par_cp(cp: str) -> list[dict]:
    """
    Retourne la liste des villes correspondant au code postal (France).

    Champs : id, nom_ville, cp
    """
    cp = (cp or "").strip()
    if not cp:
        return []

    db = get_connection("divers")
    rows = db.query(
        """SELECT IDCommunesFrance, NomVille, CodePostal
        FROM CommunesFrance
        WHERE ModifELEM NOT LIKE '%suppr%'
          AND CodePostal LIKE ?
        ORDER BY NomVille""",
        (f"{cp}%",),
    )

    return [
        {
            "id": int(r.get("IDCommunesFrance") or 0),
            "nom_ville": r.get("NomVille") or "",
            "cp": r.get("CodePostal") or "",
        }
        for r in rows
    ]
