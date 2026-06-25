"""Service Fen_SalonSalarie (shared) : CRUD des salons visio d'un recruteur.

Ouvert depuis Fen_EntretienAjout (bouton '+' a cote du combo Visio)
pour permettre au recruteur d'ajouter/modifier ses salons rapidement.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection
from app.shared.recrutement.services.recherche_cv import _int, _str


def _new_id() -> int:
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S")) * 1000 + n.microsecond // 1000


def _next_auto(db, schema: str, table: str, auto_col: str) -> int:
    r = db.query(f"SELECT COALESCE(MAX({auto_col}),0)+1 AS n FROM {schema}.{table}")
    return _int(r[0]["n"]) if r else 1


# ---------------------------------------------------------------------------
# Schemas inline
# ---------------------------------------------------------------------------


class SalonVisioRow(BaseModel):
    id_salon_visio: str
    id_type_salon_visio: str
    lib_salon: str          # ex : Teams, Zoom, Whereby
    lien_salon: str = ""
    id_salon: str = ""
    mpd_salon: str = ""


class TypeSalonItem(BaseModel):
    id_type_salon_visio: str
    lib_salon: str


class SalonVisioPayload(BaseModel):
    id_salon_visio: str = "0"     # 0 = create, sinon update
    id_salarie: str = ""          # obligatoire en create
    id_type_salon_visio: str = ""
    lien_salon: str = ""
    id_salon: str = ""
    mpd_salon: str = ""


# ---------------------------------------------------------------------------
# Liste / get
# ---------------------------------------------------------------------------


def list_salons_by_salarie(id_salarie: int) -> list[SalonVisioRow]:
    """Salons d'un recruteur (avec lib_salon resolu via type)."""
    if not id_salarie:
        return []
    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT sv.id_salon_visio, sv.id_type_salon_visio,
                  sv.lien_salon, sv.id_salon, sv.mpd_salon,
                  ts.lib_salon
             FROM recrutement.pgt_salon_visio sv
             LEFT JOIN recrutement.pgt_type_salon_visio ts
                    ON ts.id_type_salon_visio = sv.id_type_salon_visio
            WHERE sv.id_salarie = ?
              AND (sv.modif_elem IS NULL OR sv.modif_elem NOT LIKE '%suppr%')
         ORDER BY ts.lib_salon ASC""",
        (int(id_salarie),),
    ) or []
    return [SalonVisioRow(
        id_salon_visio=str(_int(r["id_salon_visio"])),
        id_type_salon_visio=str(_int(r.get("id_type_salon_visio"))),
        lib_salon=_str(r.get("lib_salon")) or "Salon",
        lien_salon=_str(r["lien_salon"]),
        id_salon=_str(r["id_salon"]),
        mpd_salon=_str(r["mpd_salon"]),
    ) for r in rows]


def list_types_salon() -> list[TypeSalonItem]:
    """Combo des types de salon visio (Teams, Zoom, etc.)."""
    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT id_type_salon_visio, lib_salon
             FROM recrutement.pgt_type_salon_visio
            WHERE is_actif = true
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY lib_salon ASC"""
    ) or []
    return [TypeSalonItem(
        id_type_salon_visio=str(_int(r["id_type_salon_visio"])),
        lib_salon=_str(r["lib_salon"]),
    ) for r in rows]


def get_salon(id_salon_visio: int) -> Optional[SalonVisioRow]:
    db = get_pg_connection("recrutement")
    r = db.query_one(
        """SELECT sv.id_salon_visio, sv.id_type_salon_visio,
                  sv.lien_salon, sv.id_salon, sv.mpd_salon,
                  ts.lib_salon
             FROM recrutement.pgt_salon_visio sv
             LEFT JOIN recrutement.pgt_type_salon_visio ts
                    ON ts.id_type_salon_visio = sv.id_type_salon_visio
            WHERE sv.id_salon_visio = ?""",
        (int(id_salon_visio),),
    )
    if not r:
        return None
    return SalonVisioRow(
        id_salon_visio=str(_int(r["id_salon_visio"])),
        id_type_salon_visio=str(_int(r.get("id_type_salon_visio"))),
        lib_salon=_str(r.get("lib_salon")) or "Salon",
        lien_salon=_str(r["lien_salon"]),
        id_salon=_str(r["id_salon"]),
        mpd_salon=_str(r["mpd_salon"]),
    )


# ---------------------------------------------------------------------------
# Save / delete
# ---------------------------------------------------------------------------


def save_salon(p: SalonVisioPayload, op_id: int) -> dict:
    """INSERT si id_salon_visio='0', UPDATE sinon."""
    db = get_pg_connection("recrutement")
    id_v = _int(p.id_salon_visio)
    id_sal = _int(p.id_salarie)
    id_type = _int(p.id_type_salon_visio)

    if id_v == 0:
        if not id_sal:
            return {"ok": False, "error": "id_salarie_requis"}
        id_v = _new_id()
        auto = _next_auto(db, "recrutement", "pgt_salon_visio", "id_salon_visio_auto")
        db.query(
            """INSERT INTO recrutement.pgt_salon_visio
                 (id_salon_visio_auto, id_salon_visio,
                  id_salarie, id_type_salon_visio,
                  lien_salon, id_salon, mpd_salon,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
            (auto, id_v, id_sal, id_type,
             p.lien_salon, p.id_salon, p.mpd_salon, int(op_id)),
        )
    else:
        db.query(
            """UPDATE recrutement.pgt_salon_visio
                  SET id_type_salon_visio = ?,
                      lien_salon = ?, id_salon = ?, mpd_salon = ?,
                      modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
                WHERE id_salon_visio = ?""",
            (id_type, p.lien_salon, p.id_salon, p.mpd_salon,
             int(op_id), id_v),
        )
    return {"ok": True, "id_salon_visio": str(id_v)}


def delete_salon(id_salon_visio: int, op_id: int) -> dict:
    db = get_pg_connection("recrutement")
    db.query(
        """UPDATE recrutement.pgt_salon_visio
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_salon_visio = ?""",
        (int(op_id), int(id_salon_visio)),
    )
    return {"ok": True}
