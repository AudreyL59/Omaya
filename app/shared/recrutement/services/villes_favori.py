"""Service Fen_VillesFavorites (shared) : CRUD des villes en favori
(pgt_communes_france.favorite = true)."""

from __future__ import annotations

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection
from app.shared.recrutement.services.recherche_cv import _int, _str


class VilleFavoriteRow(BaseModel):
    id_communes_france: str
    nom_ville: str
    code_postal: str
    departement: str = ""
    latitude_deg: float = 0.0
    longitude_deg: float = 0.0


def list_favorites() -> list[VilleFavoriteRow]:
    db = get_pg_connection("divers")
    rows = db.query(
        """SELECT id_communes_france, nom_ville, code_postal, departement,
                  latitude_deg, longitude_deg
             FROM divers.pgt_communes_france
            WHERE favorite = TRUE
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY nom_ville ASC"""
    ) or []
    return [VilleFavoriteRow(
        id_communes_france=str(_int(r["id_communes_france"])),
        nom_ville=_str(r["nom_ville"]),
        code_postal=_str(r["code_postal"]),
        departement=_str(r.get("departement")),
        latitude_deg=float(r.get("latitude_deg") or 0),
        longitude_deg=float(r.get("longitude_deg") or 0),
    ) for r in rows]


def add_favorite(id_commune: int, op_id: int) -> dict:
    if not id_commune:
        return {"ok": False, "error": "id_required"}
    db = get_pg_connection("divers")
    db.query(
        """UPDATE divers.pgt_communes_france
              SET favorite = TRUE, modif_date = NOW(), modif_op = ?
            WHERE id_communes_france = ?""",
        (int(op_id), int(id_commune)),
    )
    return {"ok": True}


def remove_favorite(id_commune: int, op_id: int) -> dict:
    if not id_commune:
        return {"ok": False, "error": "id_required"}
    db = get_pg_connection("divers")
    db.query(
        """UPDATE divers.pgt_communes_france
              SET favorite = FALSE, modif_date = NOW(), modif_op = ?
            WHERE id_communes_france = ?""",
        (int(op_id), int(id_commune)),
    )
    return {"ok": True}
