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
    nom_resp: str = ""
    capacite: int = 0
    invisible_podium: bool = False
    invisible_effectif: bool = False


class OrgaDetail(BaseModel):
    """Detail complet d'un bloc orga pour prefill du modal edition."""
    id: str
    id_parent: str = ""
    lib_orga: str = ""
    id_type_niveau_orga: int = 0
    id_type_orga: int = 0
    id_ste: int = 0
    id_distri: int = 0
    id_distri_lib: str = ""
    id_type_produit: int = 0
    ville: str = ""
    secteur: str = ""
    memo: str = ""
    nom_resp: str = ""
    capacite: int = 0
    invisible_podium: bool = False
    invisible_effectif: bool = False


class OrgaMovePayload(BaseModel):
    id_parent_new: str


class OrgaCopierPayload(BaseModel):
    """Cf. WinDev Orga_Copier : duplique un bloc sous un nouveau parent.
    include_children_deep_1 : recopie aussi les fils directs.
    include_children_deep_2 : recopie aussi les petits-fils.
    """
    id_parent_new: str
    include_children_deep_1: bool = False
    include_children_deep_2: bool = False


class DeplacerSalariePayload(BaseModel):
    """Cf. WinDev DeplacerSalarie : change le rattachement orga d'un
    salarie a une date donnee."""
    id_salarie: str
    id_orga_cible: str
    date_changement: str      # YYYY-MM-DD


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


def list_types_produit() -> list[OrgaCombo]:
    """Combo Type Produit (pgt_type_produit)."""
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT id_type_produit, lib
                 FROM pgt_type_produit
                WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY lib ASC""",
        ) or []
    except Exception:
        logger.exception("list_types_produit")
        return []
    return [
        OrgaCombo(
            id=int(r.get("id_type_produit") or 0),
            lib=(r.get("lib") or "").strip(),
        )
        for r in rows
    ]


def list_societes_orga() -> list[OrgaCombo]:
    """Combo Societes (pgt_societe, non archivees)."""
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT id_ste, raison_sociale
                 FROM pgt_societe
                WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY raison_sociale ASC""",
        ) or []
    except Exception:
        logger.exception("list_societes_orga")
        return []
    return [
        OrgaCombo(
            id=int(r.get("id_ste") or 0),
            lib=(r.get("raison_sociale") or "").strip(),
        )
        for r in rows
    ]


def get_orga_detail(id_orga: str) -> OrgaDetail | None:
    """Detail d'un bloc pour prefill du modal edition."""
    if not id_orga or id_orga == "0":
        return None
    rh = get_pg_connection("rh")
    try:
        r = rh.query_one(
            """SELECT idorganigramme, id_parent, lib_orga,
                      id_type_niveau_orga, id_type_orga,
                      id_ste, id_distri, id_type_produit,
                      ville, secteur, memo,
                      nom_resp, capacite,
                      in_visible_podium, in_visible_effectif
                 FROM pgt_organigramme
                WHERE idorganigramme = ?""",
            (int(id_orga),),
        )
    except Exception:
        logger.exception("get_orga_detail")
        return None
    if not r:
        return None
    # Recupere raison sociale du distri (si idDistri != 0)
    lib_distri = ""
    id_distri = int(r.get("id_distri") or 0)
    if id_distri:
        try:
            sr = rh.query_one(
                """SELECT raison_sociale FROM pgt_societe
                    WHERE id_ste = ? LIMIT 1""",
                (id_distri,),
            )
            lib_distri = (sr.get("raison_sociale") or "").strip() if sr else ""
        except Exception:
            pass
    return OrgaDetail(
        id=str(int(r.get("idorganigramme"))),
        id_parent=str(int(r.get("id_parent") or 0)),
        lib_orga=(r.get("lib_orga") or "").strip(),
        id_type_niveau_orga=int(r.get("id_type_niveau_orga") or 0),
        id_type_orga=int(r.get("id_type_orga") or 0),
        id_ste=int(r.get("id_ste") or 0),
        id_distri=id_distri,
        id_distri_lib=lib_distri,
        id_type_produit=int(r.get("id_type_produit") or 0),
        ville=(r.get("ville") or "").strip(),
        secteur=(r.get("secteur") or "").strip(),
        memo=(r.get("memo") or "").strip(),
        nom_resp=(r.get("nom_resp") or "").strip(),
        capacite=int(r.get("capacite") or 0),
        invisible_podium=bool(r.get("in_visible_podium")),
        invisible_effectif=bool(r.get("in_visible_effectif")),
    )


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
        rh.query(
            """INSERT INTO pgt_organigramme
                  (idorganigramme, id_parent, lib_orga,
                   id_type_niveau_orga, id_type_orga,
                   id_ste, id_distri, id_type_produit,
                   ville, secteur, memo,
                   in_visible_podium, in_visible_effectif,
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
        rh.query(
            """UPDATE pgt_organigramme
                  SET lib_orga = ?,
                      id_type_niveau_orga = COALESCE(NULLIF(?, 0),
                                                    id_type_niveau_orga),
                      id_type_orga = ?, id_ste = ?, id_distri = ?,
                      id_type_produit = ?,
                      ville = ?, secteur = ?, memo = ?,
                      nom_resp = ?, capacite = ?,
                      in_visible_podium = ?, in_visible_effectif = ?,
                      modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
                WHERE idorganigramme = ?""",
            (
                p.lib_orga.strip(),
                p.id_type_niveau_orga,
                p.id_type_orga, p.id_ste, p.id_distri, p.id_type_produit,
                p.ville.strip(), p.secteur.strip(), p.memo.strip(),
                p.nom_resp.strip(), int(p.capacite),
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
        rh.query(
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


def _copy_one_orga(
    id_source: int, id_parent_new: int, op_id: int,
) -> int:
    """Copie une ligne orga sous un nouveau parent, retourne le new id."""
    rh = get_pg_connection("rh")
    src = rh.query_one(
        """SELECT lib_orga, id_type_niveau_orga, id_type_orga,
                  id_ste, id_distri, id_type_produit,
                  ville, secteur, memo,
                  in_visible_podium, in_visible_effectif
             FROM pgt_organigramme
            WHERE idorganigramme = ?""",
        (id_source,),
    )
    if not src:
        return 0
    new_id = _new_id()
    try:
        rh.query(
            """INSERT INTO pgt_organigramme
                  (idorganigramme, id_parent, lib_orga,
                   id_type_niveau_orga, id_type_orga,
                   id_ste, id_distri, id_type_produit,
                   ville, secteur, memo,
                   in_visible_podium, in_visible_effectif,
                   modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       NOW(), ?, 'new')""",
            (
                new_id, id_parent_new,
                (src.get("lib_orga") or "").strip(),
                int(src.get("id_type_niveau_orga") or 0),
                int(src.get("id_type_orga") or 0),
                int(src.get("id_ste") or 0),
                int(src.get("id_distri") or 0),
                int(src.get("id_type_produit") or 0),
                (src.get("ville") or "").strip(),
                (src.get("secteur") or "").strip(),
                (src.get("memo") or "").strip(),
                bool(src.get("in_visible_podium")),
                bool(src.get("in_visible_effectif")),
                op_id,
            ),
        )
    except Exception:
        logger.exception("_copy_one_orga")
        return 0
    return new_id


def copier_orga(
    id_orga: str, p: OrgaCopierPayload, op_id: int,
) -> dict:
    """Cf. WinDev Orga_Copier."""
    if not id_orga or id_orga == "0":
        return {"ok": False, "err": "ID bloc invalide"}
    id_src = int(id_orga)
    id_new_parent = _to_int(p.id_parent_new)
    # Copie le bloc racine
    new_root = _copy_one_orga(id_src, id_new_parent, op_id)
    if not new_root:
        return {"ok": False, "err": "Erreur copie du bloc"}
    if not p.include_children_deep_1:
        return {"ok": True, "id": str(new_root)}
    # Copie fils directs
    rh = get_pg_connection("rh")
    fils = rh.query(
        """SELECT idorganigramme FROM pgt_organigramme
            WHERE id_parent = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (id_src,),
    ) or []
    for f in fils:
        id_f = int(f.get("idorganigramme"))
        new_f = _copy_one_orga(id_f, new_root, op_id)
        if new_f and p.include_children_deep_2:
            petits_fils = rh.query(
                """SELECT idorganigramme FROM pgt_organigramme
                    WHERE id_parent = ?
                      AND (modif_elem IS NULL
                           OR modif_elem NOT LIKE '%suppr%')""",
                (id_f,),
            ) or []
            for pf in petits_fils:
                _copy_one_orga(int(pf.get("idorganigramme")), new_f, op_id)
    return {"ok": True, "id": str(new_root)}


def deplacer_salarie(p: DeplacerSalariePayload, op_id: int) -> dict:
    """Cf. WinDev DeplacerSalarie :
    - Parcourt tous les rattachements du salarie (ORDER BY date_debut DESC)
    - Pour chaque ratt actif (date_fin invalide / vide) : ferme avec
      date_fin = date_changement - 1 et cale date_debut si besoin
    - Ajoute une nouvelle ligne salarie_organigramme
    """
    from app.core.utils.sentinel_dates import is_sentinel

    if not p.id_salarie or not p.id_orga_cible or not p.date_changement:
        return {"ok": False, "err": "Parametres invalides"}
    d = p.date_changement[:10]
    from datetime import date as _date, timedelta
    try:
        d_dt = _date.fromisoformat(d)
    except ValueError:
        return {"ok": False, "err": "Date invalide"}
    d_fin_prev = (d_dt - timedelta(days=1)).isoformat()

    rh = get_pg_connection("rh")
    id_sal = int(p.id_salarie)
    id_orga = int(p.id_orga_cible)

    # Recupere id_ste de l'orga cible (heritage cf. WinDev)
    orga = rh.query_one(
        "SELECT id_ste FROM pgt_organigramme WHERE idorganigramme = ?",
        (id_orga,),
    )
    id_ste = int((orga or {}).get("id_ste") or 0)

    # 1) Parcourt les rattachements existants (comme WinDev)
    try:
        ratts = rh.query(
            """SELECT id_salarie_organigramme,
                      date_debut, date_fin
                 FROM pgt_salarie_organigramme
                WHERE id_salarie = ?
                  AND (modif_elem IS NULL
                       OR modif_elem NOT LIKE '%suppr%')
                ORDER BY date_debut DESC""",
            (id_sal,),
        ) or []
    except Exception as e:
        logger.exception("deplacer_salarie select ratts")
        return {"ok": False, "err": f"SELECT ratts : {e}"}

    # 2) Ferme uniquement les ratt dont date_fin est invalide (=en cours)
    for r in ratts:
        df = r.get("date_fin")
        # Rattachement encore en cours = date_fin NULL ou sentinelle 1900
        if df is not None and not is_sentinel(df):
            continue
        rid = int(r.get("id_salarie_organigramme"))
        dd = r.get("date_debut")
        # Si date_debut > d_fin_prev, on la ramene a d_fin_prev
        new_dd = None
        if dd and not is_sentinel(dd):
            try:
                dd_iso = dd.isoformat() if hasattr(dd, "isoformat") else str(dd)[:10]
                new_dd = d_fin_prev if dd_iso > d_fin_prev else dd_iso
            except Exception:
                new_dd = None
        try:
            rh.query(
                """UPDATE pgt_salarie_organigramme
                      SET date_fin = ?,
                          date_debut = COALESCE(?, date_debut),
                          aff_actif = FALSE,
                          modif_date = NOW(), modif_op = ?,
                          modif_elem = 'modif'
                    WHERE id_salarie_organigramme = ?""",
                (d_fin_prev, new_dd, op_id, rid),
            )
        except Exception as e:
            logger.exception("deplacer_salarie close ratt %s", rid)
            return {
                "ok": False,
                "err": f"Fermeture ratt {rid} : {e}",
            }

    # 3) Insert le nouveau rattachement
    try:
        new_id = _new_id()
        rh.query(
            """INSERT INTO pgt_salarie_organigramme
                  (id_salarie_organigramme, id_salarie, idorganigramme,
                   date_debut, date_fin, aff_actif, id_ste,
                   modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, NULL, TRUE, ?, NOW(), ?, 'new')""",
            (new_id, id_sal, id_orga, d, id_ste, op_id),
        )
    except Exception as e:
        logger.exception("deplacer_salarie insert")
        return {"ok": False, "err": f"INSERT ratt : {e}"}
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
        rh.query(
            """UPDATE pgt_organigramme
                  SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
                WHERE idorganigramme = ?""",
            (op_id, id_o),
        )
    except Exception:
        logger.exception("delete_orga")
        return {"ok": False, "err": "Erreur base de donnees"}
    return {"ok": True}
