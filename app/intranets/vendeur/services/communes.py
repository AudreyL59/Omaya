"""
Recherche des villes par code postal.

Transposition de l'endpoint REST WebRest_Omayapp/ListeVilleByCP.
Table pgt_communes_france dans le schema divers de erp_db.
"""

from app.core.database.pg import get_pg_connection


def rechercher_par_cp(cp: str) -> list[dict]:
    """
    Retourne la liste des villes correspondant au code postal (France).

    Champs : id, nom_ville, cp
    """
    cp = (cp or "").strip()
    if not cp:
        return []

    db = get_pg_connection("divers")
    rows = db.query(
        """SELECT id_communes_france, nom_ville, code_postal
        FROM pgt_communes_france
        WHERE modif_elem NOT LIKE '%suppr%'
          AND code_postal LIKE ?
        ORDER BY nom_ville""",
        (f"{cp}%",),
    )

    return [
        {
            "id": int(r.get("id_communes_france") or 0),
            "nom_ville": r.get("nom_ville") or "",
            "cp": r.get("code_postal") or "",
        }
        for r in rows
    ]
