"""
Service Fen_GestionCarteCarb (ADM Ulease -> Gestion cartes carburant).

4 entites :
  - CarteCarburant (table ulease.pgt_cartecarburant)
  - CarteFournisseur (table ulease.pgt_cartefournisseur) + logo bytea
  - TypeReleveFournisseur (table ulease.pgt_typerelevefournisseur)
  - CarteAttribution (table ulease.pgt_carteattribution) : qui a utilise
    quelle carte du DU au AU (JOIN conducteur + salarie pour le nom).
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


def _iso_date(v: Any) -> str:
    if v is None or v == "":
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    return s[:10] if len(s) >= 10 and s[4] == "-" else s


def _img_b64(v: Any) -> str:
    """bytea -> data:image/png;base64,..."""
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


def _new_id() -> int:
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


def _next_auto(db, schema: str, table: str, col: str) -> int:
    """Cf. calcul_carte_carb._next_auto. Tables HFSQL migrees sans
    sequence PG : on calcule MAX(_auto)+1 a la main."""
    r = db.query_one(
        f"SELECT COALESCE(MAX({col}),0)+1 AS n FROM {schema}.{table}",
    )
    return _int(r.get("n")) if r else 1


# ---------------------------------------------------------------------------
# Onglet 1 - Cartes carburant
# ---------------------------------------------------------------------------


def list_cartes() -> list[dict]:
    """ReqCarteCart : liste des cartes (Code, Num, Fournisseur, Actif)."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT cc.id_carte_carburant, cc.code_carte, cc.num_carte,
                  cc.id_carte_fournisseur, cc.is_actif,
                  cf.nom_fournisseur
             FROM ulease.pgt_cartecarburant cc
        LEFT JOIN ulease.pgt_cartefournisseur cf
               ON cf.id_carte_fournisseur = cc.id_carte_fournisseur
            WHERE (cc.modif_elem IS NULL OR cc.modif_elem <> 'suppr')
         ORDER BY cc.num_carte ASC""",
    ) or []
    return [{
        "id_carte_carburant": str(_int(r.get("id_carte_carburant"))),
        "code_carte": _str(r.get("code_carte")),
        "num_carte": _str(r.get("num_carte")),
        "id_carte_fournisseur": str(_int(r.get("id_carte_fournisseur"))),
        "nom_fournisseur": _str(r.get("nom_fournisseur")),
        "is_actif": bool(r.get("is_actif")),
    } for r in rows]


def save_carte(payload: dict, op_id: int) -> dict:
    db = get_pg_connection("ulease")
    id_c = _int(payload.get("id_carte_carburant"))
    code = _str(payload.get("code_carte"))
    num = _str(payload.get("num_carte"))
    id_four = _int(payload.get("id_carte_fournisseur"))
    actif = bool(payload.get("is_actif"))
    if id_c == 0:
        new_id = _new_id()
        next_auto = _next_auto(db, "ulease", "pgt_cartecarburant",
                               "id_carte_carburant_auto")
        db.query(
            """INSERT INTO ulease.pgt_cartecarburant
                 (id_carte_carburant_auto, id_carte_carburant,
                  code_carte, num_carte,
                  id_carte_fournisseur, is_actif,
                  modif_op, modif_date, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), 'new')""",
            (next_auto, new_id, code, num, id_four, actif, int(op_id)),
        )
        return {"ok": True, "id_carte_carburant": str(new_id)}
    db.query(
        """UPDATE ulease.pgt_cartecarburant
              SET code_carte = ?, num_carte = ?, id_carte_fournisseur = ?,
                  is_actif = ?, modif_op = ?, modif_date = NOW(),
                  modif_elem = 'modif'
            WHERE id_carte_carburant = ?""",
        (code, num, id_four, actif, int(op_id), id_c),
    )
    return {"ok": True, "id_carte_carburant": str(id_c)}


def delete_carte(id_carte: int, op_id: int) -> dict:
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_cartecarburant
              SET modif_op = ?, modif_date = NOW(), modif_elem = 'suppr'
            WHERE id_carte_carburant = ?""",
        (int(op_id), int(id_carte)),
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Onglet 1 (sous-liste) - Attributions de la carte
# ---------------------------------------------------------------------------


def list_attributions(id_carte: int) -> list[dict]:
    """ReqAttCart : conducteurs ayant utilise la carte du DU au AU."""
    if not id_carte:
        return []
    db_ul = get_pg_connection("ulease")
    rows = db_ul.query(
        """SELECT ca.id_carte_attribution, ca.id_conducteur,
                  ca.du, ca.au,
                  c.nom_conducteur, c.prenom_conducteur, c.nom_marital
             FROM ulease.pgt_carteattribution ca
        INNER JOIN ulease.pgt_conducteur c
                ON c.id_conducteur = ca.id_conducteur
            WHERE (ca.modif_elem IS NULL OR ca.modif_elem <> 'suppr')
              AND ca.id_carte_carburant = ?
         ORDER BY ca.du DESC""",
        (int(id_carte),),
    ) or []
    out = []
    for r in rows:
        nom = _str(r.get("nom_conducteur"))
        marital = _str(r.get("nom_marital"))
        prenom = _str(r.get("prenom_conducteur")).strip().capitalize()
        nom_complet = f"{nom} {marital}".strip() if marital else nom
        out.append({
            "id_carte_attribution": str(_int(r.get("id_carte_attribution"))),
            "id_conducteur": str(_int(r.get("id_conducteur"))),
            "conducteur": f"{nom_complet} {prenom}".strip(),
            "du": _iso_date(r.get("du")),
            "au": _iso_date(r.get("au")),
        })
    return out


def get_attribution(id_carte_attribution: int) -> dict | None:
    db = get_pg_connection("ulease")
    r = db.query_one(
        """SELECT id_carte_attribution, id_carte_carburant, id_conducteur,
                  du, au
             FROM ulease.pgt_carteattribution
            WHERE id_carte_attribution = ? LIMIT 1""",
        (int(id_carte_attribution),),
    )
    if not r:
        return None
    return {
        "id_carte_attribution": str(_int(r.get("id_carte_attribution"))),
        "id_carte_carburant": str(_int(r.get("id_carte_carburant"))),
        "id_conducteur": str(_int(r.get("id_conducteur"))),
        "du": _iso_date(r.get("du")),
        "au": _iso_date(r.get("au")),
    }


def save_attribution(payload: dict, op_id: int) -> dict:
    """Fen_AttCarteCarb btn Valider : create (id=0) ou update."""
    db = get_pg_connection("ulease")
    id_att = _int(payload.get("id_carte_attribution"))
    id_carte = _int(payload.get("id_carte_carburant"))
    id_cond = _int(payload.get("id_conducteur"))
    du = payload.get("du") or None
    au = payload.get("au") or None
    if du == "":
        du = None
    if au == "":
        au = None
    if id_att == 0:
        new_id = _new_id()
        next_auto = _next_auto(db, "ulease", "pgt_carteattribution",
                               "id_carte_attribution_auto")
        db.query(
            """INSERT INTO ulease.pgt_carteattribution
                 (id_carte_attribution_auto, id_carte_attribution,
                  id_carte_carburant, id_conducteur,
                  du, au, modif_op, modif_date, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), 'new')""",
            (next_auto, new_id, id_carte, id_cond, du, au, int(op_id)),
        )
        return {"ok": True, "id_carte_attribution": str(new_id)}
    db.query(
        """UPDATE ulease.pgt_carteattribution
              SET id_conducteur = ?, du = ?, au = ?,
                  modif_op = ?, modif_date = NOW(), modif_elem = 'modif'
            WHERE id_carte_attribution = ?""",
        (id_cond, du, au, int(op_id), id_att),
    )
    return {"ok": True, "id_carte_attribution": str(id_att)}


def delete_attribution(id_carte_attribution: int, op_id: int) -> dict:
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_carteattribution
              SET modif_op = ?, modif_date = NOW(), modif_elem = 'suppr'
            WHERE id_carte_attribution = ?""",
        (int(op_id), int(id_carte_attribution)),
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Onglet 2 - Fournisseurs
# ---------------------------------------------------------------------------


def list_fournisseurs() -> list[dict]:
    """ReqFournisseur : logo + nom."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT id_carte_fournisseur, nom_fournisseur, logo
             FROM ulease.pgt_cartefournisseur
            WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
         ORDER BY nom_fournisseur ASC""",
    ) or []
    return [{
        "id_carte_fournisseur": str(_int(r.get("id_carte_fournisseur"))),
        "nom_fournisseur": _str(r.get("nom_fournisseur")),
        "logo": _img_b64(r.get("logo")),
    } for r in rows]


def save_fournisseur(payload: dict, op_id: int) -> dict:
    db = get_pg_connection("ulease")
    id_f = _int(payload.get("id_carte_fournisseur"))
    nom = _str(payload.get("nom_fournisseur"))
    if id_f == 0:
        new_id = _new_id()
        next_auto = _next_auto(db, "ulease", "pgt_cartefournisseur",
                               "id_carte_fournisseur_auto")
        db.query(
            """INSERT INTO ulease.pgt_cartefournisseur
                 (id_carte_fournisseur_auto, id_carte_fournisseur,
                  nom_fournisseur,
                  modif_op, modif_date, modif_elem)
               VALUES (?, ?, ?, ?, NOW(), 'new')""",
            (next_auto, new_id, nom, int(op_id)),
        )
        return {"ok": True, "id_carte_fournisseur": str(new_id)}
    db.query(
        """UPDATE ulease.pgt_cartefournisseur
              SET nom_fournisseur = ?, modif_op = ?, modif_date = NOW(),
                  modif_elem = 'modif'
            WHERE id_carte_fournisseur = ?""",
        (nom, int(op_id), id_f),
    )
    return {"ok": True, "id_carte_fournisseur": str(id_f)}


def delete_fournisseur(id_carte_fournisseur: int, op_id: int) -> dict:
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_cartefournisseur
              SET modif_op = ?, modif_date = NOW(), modif_elem = 'suppr'
            WHERE id_carte_fournisseur = ?""",
        (int(op_id), int(id_carte_fournisseur)),
    )
    return {"ok": True}


def upload_logo_fournisseur(id_carte_fournisseur: int, content: bytes,
                            op_id: int) -> dict:
    """HAttacheMemo CarteFournisseur.Logo (HMemoImg)."""
    if not content:
        return {"ok": False, "error": "Fichier vide"}
    db = get_pg_connection("ulease")
    from psycopg2 import Binary
    db.query(
        """UPDATE ulease.pgt_cartefournisseur
              SET logo = ?, modif_op = ?, modif_date = NOW(),
                  modif_elem = 'modif'
            WHERE id_carte_fournisseur = ?""",
        (Binary(content), int(op_id), int(id_carte_fournisseur)),
    )
    return {"ok": True, "logo": _img_b64(content)}


# ---------------------------------------------------------------------------
# Onglet 2 (sous-liste) - Types de releve fournisseur
# ---------------------------------------------------------------------------


def list_types_releve() -> list[dict]:
    """ReqTypeReleveFournisseur (Categorie, Lib_Type)."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT id_type_releve_fournisseur, lib_type, categorie
             FROM ulease.pgt_typerelevefournisseur
            WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
         ORDER BY categorie ASC, lib_type ASC""",
    ) or []
    return [{
        "id_type_releve_fournisseur": str(_int(r.get("id_type_releve_fournisseur"))),
        "lib_type": _str(r.get("lib_type")),
        "categorie": _str(r.get("categorie")),
    } for r in rows]


def save_type_releve(payload: dict, op_id: int) -> dict:
    db = get_pg_connection("ulease")
    id_t = _int(payload.get("id_type_releve_fournisseur"))
    lib = _str(payload.get("lib_type"))
    cat = _str(payload.get("categorie"))
    if id_t == 0:
        new_id = _new_id()
        next_auto = _next_auto(db, "ulease", "pgt_typerelevefournisseur",
                               "id_type_releve_fournisseur_auto")
        db.query(
            """INSERT INTO ulease.pgt_typerelevefournisseur
                 (id_type_releve_fournisseur_auto, id_type_releve_fournisseur,
                  lib_type, categorie,
                  modif_op, modif_date, modif_elem)
               VALUES (?, ?, ?, ?, ?, NOW(), 'new')""",
            (next_auto, new_id, lib, cat, int(op_id)),
        )
        return {"ok": True, "id_type_releve_fournisseur": str(new_id)}
    db.query(
        """UPDATE ulease.pgt_typerelevefournisseur
              SET lib_type = ?, categorie = ?, modif_op = ?,
                  modif_date = NOW(), modif_elem = 'modif'
            WHERE id_type_releve_fournisseur = ?""",
        (lib, cat, int(op_id), id_t),
    )
    return {"ok": True, "id_type_releve_fournisseur": str(id_t)}


def delete_type_releve(id_type_releve_fournisseur: int, op_id: int) -> dict:
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_typerelevefournisseur
              SET modif_op = ?, modif_date = NOW(), modif_elem = 'suppr'
            WHERE id_type_releve_fournisseur = ?""",
        (int(op_id), int(id_type_releve_fournisseur)),
    )
    return {"ok": True}
