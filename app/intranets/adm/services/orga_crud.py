"""
CRUD organigramme (intranet ADM).

Cf. WinDev Fen_OrgaAjout / Fen_OrgaModif / menu contextuel bloc orga :
  - creer un sous-bloc
  - editer libelle / proprietes
  - deplacer un bloc vers un autre parent
  - supprimer un bloc
"""
from __future__ import annotations

import logging
from datetime import datetime

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection


logger = logging.getLogger(__name__)


# --------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------

class OrgaCombo(BaseModel):
    id: int
    lib: str


class OrgaCreatePayload(BaseModel):
    id_parent: str            # peut etre "" ou "0" pour racine
    lib_orga: str
    id_type_niveau_orga: int = 0    # 0 -> deduit du parent + 1
    id_type_orga: int = 0
    id_ste: int = 0
    id_distri: int = 0
    id_type_produit: int = 0
    ville: str = ""
    secteur: str = ""
    memo: str = ""
    invisible_podium: bool = False
    invisible_effectif: bool = False


class OrgaUpdatePayload(BaseModel):
    lib_orga: str
    id_type_niveau_orga: int = 0
    id_type_orga: int = 0
    id_ste: int = 0
    id_distri: int = 0
    id_type_produit: int = 0
    ville: str = ""
    secteur: str = ""
    memo: str = ""
    invisible_podium: bool = False
    invisible_effectif: bool = False


class OrgaMovePayload(BaseModel):
    id_parent_new: str


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _new_id() -> int:
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


def _to_int(v, default: int = 0) -> int:
    try:
        return int(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _deduce_id_type_niveau(id_parent: int) -> int:
    """Cf. WinDev : le niveau est celui du parent + 1 si non specifie."""
    if not id_parent:
        return 1
    rh = get_pg_connection("rh")
    r = rh.query_one(
        "SELECT id_type_niveau_orga FROM pgt_organigramme "
        "WHERE idorganigramme = ?",
        (id_parent,),
    )
    if not r:
        return 1
    return int(r.get("id_type_niveau_orga") or 0) + 1


# --------------------------------------------------------------------
# Combos
# --------------------------------------------------------------------

def list_types_niveau() -> list[OrgaCombo]:
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT id_type_niveau_orga, lib_niveau
                 FROM pgt_type_niveau_orga
                WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY id_type_niveau_orga ASC""",
        ) or []
    except Exception:
        logger.exception("list_types_niveau")
        return []
    return [
        OrgaCombo(
            id=int(r.get("id_type_niveau_orga") or 0),
            lib=(r.get("lib_niveau") or "").strip(),
        )
        for r in rows
    ]


def list_types_orga() -> list[OrgaCombo]:
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT id_type_orga, lib
                 FROM pgt_type_orga
                WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY id_type_orga ASC""",
        ) or []
    except Exception:
        logger.exception("list_types_orga")
        return []
    return [
        OrgaCombo(
            id=int(r.get("id_type_orga") or 0),
            lib=(r.get("lib") or "").strip(),
        )
        for r in rows
    ]


# --------------------------------------------------------------------
# CRUD
# --------------------------------------------------------------------

def create_orga(p: OrgaCreatePayload, op_id: int) -> str:
    """Cf. WinDev Fen_OrgaAjout."""
    if not p.lib_orga.strip():
        return ""
    id_parent = _to_int(p.id_parent)
    id_niveau = p.id_type_niveau_orga or _deduce_id_type_niveau(id_parent)
    new_id = _new_id()
    rh = get_pg_connection("rh")
    try:
        rh.execute(
            """INSERT INTO pgt_organigramme
                  (idorganigramme, id_parent, lib_orga,
                   id_type_niveau_orga, id_type_orga,
                   id_ste, id_distri, id_type_produit,
                   ville, secteur, memo,
                   invisible_podium, invisible_effectif,
                   modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       NOW(), ?, 'new')""",
            (
                new_id, id_parent, p.lib_orga.strip(),
                id_niveau, p.id_type_orga,
                p.id_ste, p.id_distri, p.id_type_produit,
                p.ville.strip(), p.secteur.strip(), p.memo.strip(),
                bool(p.invisible_podium), bool(p.invisible_effectif),
                op_id,
            ),
        )
    except Exception:
        logger.exception("create_orga")
        return ""
    return str(new_id)


def update_orga(id_orga: str, p: OrgaUpdatePayload, op_id: int) -> bool:
    """Cf. WinDev Fen_OrgaModif."""
    if not id_orga or id_orga == "0":
        return False
    if not p.lib_orga.strip():
        return False
    rh = get_pg_connection("rh")
    try:
        rh.execute(
            """UPDATE pgt_organigramme
                  SET lib_orga = ?,
                      id_type_niveau_orga = COALESCE(NULLIF(?, 0),
                                                    id_type_niveau_orga),
                      id_type_orga = ?, id_ste = ?, id_distri = ?,
                      id_type_produit = ?,
                      ville = ?, secteur = ?, memo = ?,
                      invisible_podium = ?, invisible_effectif = ?,
                      modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
                WHERE idorganigramme = ?""",
            (
                p.lib_orga.strip(),
                p.id_type_niveau_orga,
                p.id_type_orga, p.id_ste, p.id_distri, p.id_type_produit,
                p.ville.strip(), p.secteur.strip(), p.memo.strip(),
                bool(p.invisible_podium), bool(p.invisible_effectif),
                op_id, int(id_orga),
            ),
        )
    except Exception:
        logger.exception("update_orga")
        return False
    return True


def _is_descendant(id_candidate: int, id_reference: int) -> bool:
    """True si id_candidate est un descendant (direct ou indirect) de
    id_reference. Empeche les cycles lors du deplacement.
    """
    if id_candidate == id_reference:
        return True
    rh = get_pg_connection("rh")
    # Remonte l'arborescence de id_candidate
    cur = id_candidate
    seen: set[int] = set()
    while cur:
        if cur in seen:
            return False
        seen.add(cur)
        r = rh.query_one(
            "SELECT id_parent FROM pgt_organigramme "
            "WHERE idorganigramme = ?",
            (cur,),
        )
        if not r:
            return False
        parent = int(r.get("id_parent") or 0)
        if parent == id_reference:
            return True
        cur = parent
    return False


def move_orga(id_orga: str, id_parent_new: str, op_id: int) -> dict:
    """Deplace un bloc sous un autre parent (avec check anti-cycle)."""
    if not id_orga or id_orga == "0":
        return {"ok": False, "err": "ID bloc invalide"}
    id_o = int(id_orga)
    id_new = _to_int(id_parent_new)
    if id_new == id_o:
        return {"ok": False, "err": "Un bloc ne peut pas etre son propre parent"}
    if id_new and _is_descendant(id_new, id_o):
        return {
            "ok": False,
            "err": "Impossible : le parent choisi est un descendant du bloc",
        }
    rh = get_pg_connection("rh")
    try:
        rh.execute(
            """UPDATE pgt_organigramme
                  SET id_parent = ?, modif_date = NOW(),
                      modif_op = ?, modif_elem = 'modif'
                WHERE idorganigramme = ?""",
            (id_new, op_id, id_o),
        )
    except Exception:
        logger.exception("move_orga")
        return {"ok": False, "err": "Erreur base de donnees"}
    return {"ok": True}


def delete_orga(id_orga: str, op_id: int) -> dict:
    """Supprime (soft) un bloc si vide (pas d'enfants ni de salaries)."""
    if not id_orga or id_orga == "0":
        return {"ok": False, "err": "ID bloc invalide"}
    id_o = int(id_orga)
    rh = get_pg_connection("rh")
    # Verifie qu'il n'a pas d'enfants
    try:
        r = rh.query_one(
            """SELECT COUNT(*) AS n FROM pgt_organigramme
                WHERE id_parent = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
            (id_o,),
        )
        if r and int(r.get("n") or 0) > 0:
            return {"ok": False, "err": "Le bloc contient des sous-blocs"}
    except Exception:
        logger.exception("delete_orga check children")
        return {"ok": False, "err": "Erreur verification enfants"}
    # Verifie qu'il n'a pas de salaries lies
    try:
        r = rh.query_one(
            """SELECT COUNT(*) AS n FROM pgt_salarie_organigramme
                WHERE idorganigramme = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
            (id_o,),
        )
        if r and int(r.get("n") or 0) > 0:
            return {"ok": False, "err": "Le bloc contient des salaries"}
    except Exception:
        # Ce check est best-effort ; si la table n'existe pas on continue
        logger.exception("delete_orga check salaries (ignore)")
    try:
        rh.execute(
            """UPDATE pgt_organigramme
                  SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
                WHERE idorganigramme = ?""",
            (op_id, id_o),
        )
    except Exception:
        logger.exception("delete_orga")
        return {"ok": False, "err": "Erreur base de donnees"}
    return {"ok": True}
