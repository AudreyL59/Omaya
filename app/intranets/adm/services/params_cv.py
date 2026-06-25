"""Service Fen_ParamCV (Parametres CVtheque).

Pattern identique a params_rh.SIMPLE_ENTITIES : config dictionnaire
des entites + list/save/delete generiques.

Entites :
 - cv_source   : pgt_cv_source        (id_cvsource, lib_source, is_actif)
 - cv_annonceur: pgt_cv_annonceur     (lib_annonceur, is_actif, logo upload)
 - cv_poste    : pgt_cvposte          (lib_poste, is_actif)
 - salon_visio : pgt_type_salon_visio (lib_salon, is_actif)
 - cv_statut   : pgt_cvstatut         (lib_statut, icone)  -- pas de is_actif
"""

from __future__ import annotations

import base64
from datetime import datetime

from app.core.database.pg import get_pg_connection
from app.shared.recrutement.services.recherche_cv import _int, _str


def _new_id() -> int:
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S")) * 1000 + n.microsecond // 1000


def _next_auto(db, schema: str, table: str, auto_col: str) -> int:
    r = db.query(f"SELECT COALESCE(MAX({auto_col}), 0) + 1 AS n FROM {schema}.{table}")
    return _int(r[0]["n"]) if r else 1


SIMPLE_ENTITIES: dict[str, dict] = {
    "cv_source": {
        "schema": "recrutement", "table": "pgt_cv_source",
        "id_col": "id_cvsource", "auto_col": "id_cv_source_auto",
        "fields": ["lib_source", "is_actif"],
        "order_by": "lib_source ASC",
    },
    "cv_annonceur": {
        "schema": "recrutement", "table": "pgt_cv_annonceur",
        "id_col": "id_cv_annonceur", "auto_col": "id_cv_annonceur_auto",
        "fields": ["lib_annonceur", "is_actif"],
        "order_by": "lib_annonceur ASC",
        "has_logo": True,
    },
    "cv_poste": {
        "schema": "recrutement", "table": "pgt_cvposte",
        "id_col": "id_cvposte", "auto_col": "id_cv_poste_auto",
        "fields": ["lib_poste", "is_actif"],
        "order_by": "lib_poste ASC",
    },
    "salon_visio": {
        "schema": "recrutement", "table": "pgt_type_salon_visio",
        "id_col": "id_type_salon_visio", "auto_col": "id_type_salon_visio_auto",
        "fields": ["lib_salon", "is_actif"],
        "order_by": "lib_salon ASC",
    },
    "cv_statut": {
        "schema": "recrutement", "table": "pgt_cvstatut",
        "id_col": "id_cv_statut", "auto_col": "id_cv_statut_auto",
        "fields": ["lib_statut", "icone"],
        "order_by": "id_cv_statut ASC",
    },
}


def list_entity(entity: str) -> list[dict]:
    cfg = SIMPLE_ENTITIES.get(entity)
    if not cfg:
        return []
    db = get_pg_connection(cfg["schema"])
    cols = [cfg["id_col"]] + cfg["fields"]
    # Logo en base64 si applicable (extra column)
    extra = ", logo" if cfg.get("has_logo") else ""
    cols_sql = ", ".join(cols)
    rows = db.query(
        f"""SELECT {cols_sql}{extra}
              FROM {cfg["schema"]}.{cfg["table"]}
             WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
          ORDER BY {cfg["order_by"]}""",
    ) or []
    out = []
    for r in rows:
        d: dict = {"id": str(_int(r.get(cfg["id_col"])))}
        for f in cfg["fields"]:
            v = r.get(f)
            if isinstance(v, bool):
                d[f] = v
            else:
                d[f] = _str(v)
        if cfg.get("has_logo"):
            logo = r.get("logo")
            d["has_logo"] = bool(logo)
        out.append(d)
    return out


def save_entity(entity: str, payload: dict, op_id: int) -> dict:
    cfg = SIMPLE_ENTITIES.get(entity)
    if not cfg:
        return {"ok": False, "error": "Entité inconnue"}
    db = get_pg_connection(cfg["schema"])
    id_v = _int(payload.get("id"))
    field_values = []
    for f in cfg["fields"]:
        v = payload.get(f)
        if f == "is_actif":
            v = bool(v) if v is not None else True
        else:
            v = _str(v)
        field_values.append(v)

    if id_v == 0:
        new_id = _new_id()
        auto = _next_auto(db, cfg["schema"], cfg["table"], cfg["auto_col"])
        fields_sql = ", ".join(cfg["fields"])
        placeholders = ", ".join(["?"] * len(cfg["fields"]))
        db.query(
            f"""INSERT INTO {cfg["schema"]}.{cfg["table"]}
                  ({cfg["auto_col"]}, {cfg["id_col"]}, {fields_sql},
                   modif_date, modif_op, modif_elem)
               VALUES (?, ?, {placeholders}, NOW(), ?, 'new')""",
            (auto, new_id, *field_values, int(op_id)),
        )
        return {"ok": True, "id": str(new_id)}

    set_sql = ", ".join([f"{f} = ?" for f in cfg["fields"]])
    db.query(
        f"""UPDATE {cfg["schema"]}.{cfg["table"]}
              SET {set_sql},
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE {cfg["id_col"]} = ?""",
        (*field_values, int(op_id), id_v),
    )
    return {"ok": True, "id": str(id_v)}


def delete_entity(entity: str, id_v: int, op_id: int) -> dict:
    cfg = SIMPLE_ENTITIES.get(entity)
    if not cfg:
        return {"ok": False, "error": "Entité inconnue"}
    db = get_pg_connection(cfg["schema"])
    db.query(
        f"""UPDATE {cfg["schema"]}.{cfg["table"]}
              SET modif_op = ?, modif_date = NOW(), modif_elem = 'suppr'
            WHERE {cfg["id_col"]} = ?""",
        (int(op_id), int(id_v)),
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Upload logo annonceur
# ---------------------------------------------------------------------------


def upload_logo_annonceur(id_v: int, content: bytes, op_id: int) -> dict:
    if not id_v or not content:
        return {"ok": False, "error": "id ou contenu manquant"}
    db = get_pg_connection("recrutement")
    db.query(
        """UPDATE recrutement.pgt_cv_annonceur
              SET logo = ?, modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_cv_annonceur = ?""",
        (content, int(op_id), int(id_v)),
    )
    return {"ok": True}


def get_logo_annonceur(id_v: int) -> bytes | None:
    db = get_pg_connection("recrutement")
    r = db.query_one(
        """SELECT logo FROM recrutement.pgt_cv_annonceur
            WHERE id_cv_annonceur = ?""",
        (int(id_v),),
    )
    return r.get("logo") if r else None
