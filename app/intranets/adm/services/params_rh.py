"""
Service Fen_ParamRH (ADM Salaries -> Parametres RH).

CRUD generique sur les 9 tables de reference :
  1. type_poste          (id_type_poste, lib_poste, categorie)
  2. type_ctt            (id_type_ctt, intitule)
  3. type_horaire        (id_type_horaire, lib_horaire)
  4. type_sortie         (id_type_sortie, lib_sortie)
  5. mutuelle            (id_mutuelle, lib_mutuelle, is_actif)
  6. type_absence        (id_type_absence, lib_absence)
  7. type_ope_livret     (id_type_operation_livret, lib_opeation)
  8. type_produit        (id_type_produit, lib, type, logo) + partenaires lies
  9. portails_partenaires (PAS DE TABLE EN PG - a clarifier, V2)

Sans sequence PG sur les _auto : on calcule MAX+1 a la main pour les
INSERT.
"""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _new_id() -> int:
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


def _next_auto(db, schema: str, table: str, col: str) -> int:
    r = db.query_one(
        f"SELECT COALESCE(MAX({col}),0)+1 AS n FROM {schema}.{table}",
    )
    return _int(r.get("n")) if r else 1


def _img_b64(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, memoryview):
        v = bytes(v)
    if not isinstance(v, (bytes, bytearray)):
        return ""
    sig = bytes(v[:8])
    if sig.startswith(b"\x89PNG"):
        mime = "image/png"
    elif sig.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif sig[:6] in (b"GIF87a", b"GIF89a"):
        mime = "image/gif"
    else:
        mime = "image/png"
    return f"data:{mime};base64,{base64.b64encode(bytes(v)).decode('ascii')}"


# ---------------------------------------------------------------------------
# Schema generique : 1 dict par entite avec sa config
# ---------------------------------------------------------------------------

# Entites au schema simple : {id, lib} ou {id, lib, ...extra}
SIMPLE_ENTITIES = {
    "type_poste": {
        "schema": "rh", "table": "pgt_type_poste",
        "id_col": "id_type_poste", "auto_col": "id_type_poste_auto",
        "fields": ["lib_poste", "categorie"],
        "order_by": "lib_poste ASC",
    },
    "type_ctt": {
        "schema": "rh", "table": "pgt_type_ctt_travail",
        "id_col": "id_type_ctt", "auto_col": "id_type_ctt_travail",
        "fields": ["intitule"],
        "order_by": "intitule ASC",
    },
    "type_horaire": {
        "schema": "rh", "table": "pgt_type_horaire_travail",
        "id_col": "id_type_horaire", "auto_col": "id_type_horaire_travail",
        "fields": ["lib_horaire"],
        "order_by": "lib_horaire ASC",
    },
    "type_sortie": {
        "schema": "rh", "table": "pgt_type_sortie_salarie",
        "id_col": "id_type_sortie", "auto_col": "id_type_sortie_salarie",
        "fields": ["lib_sortie"],
        "order_by": "lib_sortie ASC",
    },
    "mutuelle": {
        "schema": "rh", "table": "pgt_mutuelle",
        "id_col": "id_mutuelle", "auto_col": "id_mutuelle_auto",
        "fields": ["lib_mutuelle", "is_actif"],
        "order_by": "lib_mutuelle ASC",
    },
    "type_absence": {
        "schema": "rh", "table": "pgt_type_absence",
        "id_col": "id_type_absence", "auto_col": "id_type_absence_auto",
        "fields": ["lib_absence"],
        "order_by": "lib_absence ASC",
    },
    "type_ope_livret": {
        "schema": "rh", "table": "pgt_type_operation_livret",
        "id_col": "id_type_operation_livret",
        "auto_col": "id_type_operation_livret_auto",
        "fields": ["lib_opeation"],  # sic. (typo en BDD)
        "order_by": "lib_opeation ASC",
    },
}


def list_entity(entity: str) -> list[dict]:
    cfg = SIMPLE_ENTITIES.get(entity)
    if not cfg:
        return []
    db = get_pg_connection(cfg["schema"])
    cols = [cfg["id_col"]] + cfg["fields"]
    cols_sql = ", ".join(cols)
    rows = db.query(
        f"""SELECT {cols_sql}
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
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
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
# Type Produit (Orga - Groupe de Produits) + partenaires lies
# ---------------------------------------------------------------------------


def list_type_produit() -> list[dict]:
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_type_produit, lib, type, logo FROM rh.pgt_type_produit
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY lib ASC""",
    ) or []
    return [{
        "id": str(_int(r.get("id_type_produit"))),
        "lib": _str(r.get("lib")),
        "type": _str(r.get("type")),
        "logo": _img_b64(r.get("logo")),
    } for r in rows]


def save_type_produit(payload: dict, op_id: int) -> dict:
    db = get_pg_connection("rh")
    id_v = _int(payload.get("id"))
    lib = _str(payload.get("lib"))
    type_v = _str(payload.get("type"))
    if id_v == 0:
        new_id = _new_id()
        auto = _next_auto(db, "rh", "pgt_type_produit", "id_type_produit_auto")
        db.query(
            """INSERT INTO rh.pgt_type_produit
                 (id_type_produit_auto, id_type_produit, lib, type,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, NOW(), ?, 'new')""",
            (auto, new_id, lib, type_v, int(op_id)),
        )
        return {"ok": True, "id": str(new_id)}
    db.query(
        """UPDATE rh.pgt_type_produit
              SET lib = ?, type = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_type_produit = ?""",
        (lib, type_v, int(op_id), id_v),
    )
    return {"ok": True, "id": str(id_v)}


def delete_type_produit(id_v: int, op_id: int) -> dict:
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_type_produit
              SET modif_op = ?, modif_date = NOW(), modif_elem = 'suppr'
            WHERE id_type_produit = ?""",
        (int(op_id), int(id_v)),
    )
    return {"ok": True}


def upload_logo_type_produit(id_v: int, content: bytes, op_id: int) -> dict:
    if not content:
        return {"ok": False, "error": "Fichier vide"}
    import psycopg2
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_type_produit
              SET logo = ?, modif_date = NOW(), modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_type_produit = ?""",
        (psycopg2.Binary(content), int(op_id), int(id_v)),
    )
    return {"ok": True, "logo": _img_b64(content)}


def list_partenaires() -> list[dict]:
    """Combo Partenaire pour le sous-select Type Produit -> partenaires."""
    db = get_pg_connection("adv")
    rows = db.query(
        """SELECT id_partenaire, lib_partenaire FROM adv.pgt_partenaire
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY lib_partenaire ASC""",
    ) or []
    return [{
        "id_partenaire": str(_int(r.get("id_partenaire"))),
        "lib": _str(r.get("lib_partenaire")),
    } for r in rows]


def list_type_produit_partenaires(id_type_produit: int) -> list[dict]:
    """Partenaires lies a un type_produit."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_type_produit_partenaire, id_partenaire
             FROM rh.pgt_type_produit_partenaire
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
              AND id_type_produit = ?
         ORDER BY id_type_produit_partenaire""",
        (int(id_type_produit),),
    ) or []
    return [{
        "id_type_produit_partenaire": str(_int(r.get("id_type_produit_partenaire"))),
        "id_partenaire": str(_int(r.get("id_partenaire"))),
    } for r in rows]


def add_type_produit_partenaire(
    id_type_produit: int, id_partenaire: int, op_id: int,
) -> dict:
    db = get_pg_connection("rh")
    new_id = _new_id()
    db.query(
        """INSERT INTO rh.pgt_type_produit_partenaire
             (id_type_produit_partenaire, id_type_produit, id_partenaire,
              modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, NOW(), ?, 'new')""",
        (new_id, int(id_type_produit), int(id_partenaire), int(op_id)),
    )
    return {"ok": True, "id": str(new_id)}


def delete_type_produit_partenaire(id_v: int, op_id: int) -> dict:
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_type_produit_partenaire
              SET modif_op = ?, modif_date = NOW(), modif_elem = 'suppr'
            WHERE id_type_produit_partenaire = ?""",
        (int(op_id), int(id_v)),
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Portails Partenaires (BDD recrutement)
# ---------------------------------------------------------------------------


def list_portails() -> list[dict]:
    """Liste des portails + lib partenaire (cross-schema adv)."""
    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT id_portail_partenaire, id_partenaire, lien_portail,
                  login, mdp, id_entite, mail_contact, is_actif
             FROM recrutement.pgt_portail_partenaire
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY id_partenaire ASC""",
    ) or []
    # Resolve lib_partenaire en 1 query
    ids_part = sorted({_int(r.get("id_partenaire"))
                       for r in rows if _int(r.get("id_partenaire"))})
    lib_by_id: dict[int, str] = {}
    if ids_part:
        db_adv = get_pg_connection("adv")
        ph = ",".join(["?"] * len(ids_part))
        prows = db_adv.query(
            f"""SELECT id_partenaire, lib_partenaire FROM adv.pgt_partenaire
                 WHERE id_partenaire IN ({ph})""",
            tuple(ids_part),
        ) or []
        lib_by_id = {
            _int(p.get("id_partenaire")): _str(p.get("lib_partenaire"))
            for p in prows
        }
    return [{
        "id": str(_int(r.get("id_portail_partenaire"))),
        "id_partenaire": str(_int(r.get("id_partenaire"))),
        "partenaire_lib": lib_by_id.get(_int(r.get("id_partenaire")), ""),
        "lien_portail": _str(r.get("lien_portail")),
        "login": _str(r.get("login")),
        "mdp": _str(r.get("mdp")),
        "id_entite": _str(r.get("id_entite")),
        "mail_contact": _str(r.get("mail_contact")),
        "is_actif": bool(r.get("is_actif")),
    } for r in rows]


def save_portail(payload: dict, op_id: int) -> dict:
    db = get_pg_connection("recrutement")
    id_v = _int(payload.get("id"))
    fields = (
        _int(payload.get("id_partenaire")),
        _str(payload.get("lien_portail")),
        _str(payload.get("login")),
        _str(payload.get("mdp")),
        _str(payload.get("id_entite")),
        _str(payload.get("mail_contact")),
        bool(payload.get("is_actif", True)),
    )
    if id_v == 0:
        new_id = _new_id()
        auto = _next_auto(
            db, "recrutement", "pgt_portail_partenaire",
            "id_portail_partenaire_auto",
        )
        db.query(
            """INSERT INTO recrutement.pgt_portail_partenaire
                 (id_portail_partenaire_auto, id_portail_partenaire,
                  id_partenaire, lien_portail, login, mdp, id_entite,
                  mail_contact, is_actif,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
            (auto, new_id, *fields, int(op_id)),
        )
        return {"ok": True, "id": str(new_id)}
    db.query(
        """UPDATE recrutement.pgt_portail_partenaire
              SET id_partenaire = ?, lien_portail = ?, login = ?,
                  mdp = ?, id_entite = ?, mail_contact = ?, is_actif = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_portail_partenaire = ?""",
        (*fields, int(op_id), id_v),
    )
    return {"ok": True, "id": str(id_v)}


def delete_portail(id_v: int, op_id: int) -> dict:
    db = get_pg_connection("recrutement")
    db.query(
        """UPDATE recrutement.pgt_portail_partenaire
              SET modif_op = ?, modif_date = NOW(), modif_elem = 'suppr'
            WHERE id_portail_partenaire = ?""",
        (int(op_id), int(id_v)),
    )
    return {"ok": True}
