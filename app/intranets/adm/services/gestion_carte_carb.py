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


# ---------------------------------------------------------------------------
# Fen_RechercheRelev - Recherche releves
# ---------------------------------------------------------------------------


def list_categories() -> list[str]:
    """DISTINCT TypeReleveFournisseur.Categorie."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT DISTINCT categorie FROM ulease.pgt_typerelevefournisseur
            WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
              AND categorie IS NOT NULL AND categorie <> ''
         ORDER BY categorie ASC""",
    ) or []
    return [_str(r.get("categorie")) for r in rows]


def list_cartes_combo() -> list[dict]:
    """Combo 'Carte carburant' : NomFournisseur - NumCarte."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT cc.id_carte_carburant,
                  cf.nom_fournisseur || ' - ' || cc.num_carte AS nom_carte
             FROM ulease.pgt_cartecarburant cc
        LEFT JOIN ulease.pgt_cartefournisseur cf
               ON cf.id_carte_fournisseur = cc.id_carte_fournisseur
            WHERE (cc.modif_elem IS NULL OR cc.modif_elem <> 'suppr')
         ORDER BY nom_carte ASC""",
    ) or []
    return [{
        "id_carte_carburant": str(_int(r.get("id_carte_carburant"))),
        "nom_carte": _str(r.get("nom_carte")),
    } for r in rows]


def search_releves(
    du: str, au: str, id_carte_carburant: int, categorie: str,
) -> dict:
    """Btn Loupe : retourne {lignes:[...], total_ttc}.

    Filtres :
      - DATE BETWEEN du AND au
      - Si id_carte_carburant > 0 : filtre carte, sinon toutes
      - Si categorie non vide : filtre, sinon toutes
    """
    db = get_pg_connection("ulease")

    where_extra = []
    params: list = [du, au]
    if id_carte_carburant:
        where_extra.append("ccrf.id_carte_carburant = ?")
        params.append(int(id_carte_carburant))
    if categorie and categorie != "":
        where_extra.append("trf.categorie = ?")
        params.append(categorie)

    extra_sql = (" AND " + " AND ".join(where_extra)) if where_extra else ""

    rows = db.query(
        f"""SELECT ccrf.id_carte_carb_releve_fournisseur,
                   ccrf.date, ccrf.heure,
                   cf.nom_fournisseur, cc.num_carte,
                   trf.categorie, trf.lib_type,
                   ccrf.montant_ttc,
                   ccrf.id_carte_carburant
              FROM ulease.pgt_cartecarbrelevefournisseur ccrf
        INNER JOIN ulease.pgt_cartefournisseur cf
                ON cf.id_carte_fournisseur = ccrf.id_carte_fournisseur
        INNER JOIN ulease.pgt_typerelevefournisseur trf
                ON trf.id_type_releve_fournisseur = ccrf.id_type_releve_fournisseur
        INNER JOIN ulease.pgt_cartecarburant cc
                ON cc.id_carte_carburant = ccrf.id_carte_carburant
             WHERE (ccrf.modif_elem IS NULL OR ccrf.modif_elem NOT LIKE '%suppr%')
               AND ccrf.date BETWEEN ? AND ?{extra_sql}
          ORDER BY ccrf.date ASC, ccrf.heure ASC""",
        tuple(params),
    ) or []

    # Pour chaque ligne : conducteur attribue a la date (CarteAttribution
    # active du <= date <= au). Cache par (id_carte, date) pour eviter
    # N requetes si meme attribution.
    cache: dict[tuple[int, str], str] = {}
    out = []
    total = 0.0
    for r in rows:
        id_c = _int(r.get("id_carte_carburant"))
        d = r.get("date")
        d_str = _iso_date(d) if d else ""
        key = (id_c, d_str)
        if key in cache:
            attrib = cache[key]
        else:
            attrib = _find_attribue(id_c, d) if d else ""
            cache[key] = attrib
        montant = _float(r.get("montant_ttc"))
        total += montant
        # Heure : peut etre time ou string
        h = r.get("heure")
        h_str = ""
        if h is not None:
            if hasattr(h, "strftime"):
                h_str = h.strftime("%H:%M")
            else:
                s = str(h)
                h_str = s[:5] if len(s) >= 5 else s
        out.append({
            "id_carte_carb_releve_fournisseur": str(_int(r.get("id_carte_carb_releve_fournisseur"))),
            "date": d_str,
            "heure": h_str,
            "nom_fournisseur": _str(r.get("nom_fournisseur")),
            "num_carte": _str(r.get("num_carte")),
            "categorie": _str(r.get("categorie")),
            "lib_type": _str(r.get("lib_type")),
            "montant_ttc": montant,
            "attribue_a": attrib,
        })
    return {"lignes": out, "total_ttc": total}


def _find_attribue(id_carte: int, d) -> str:
    """Cherche le conducteur attribue a la carte a la date d. Renvoie
    'NOM Prenom' depuis pgt_salarie (cf. WinDev DonneInfoSalarié, qui
    prend le nom courant du salarie - pas le snapshot conducteur)."""
    # 2 etapes : ulease.pgt_carteattribution -> pgt_conducteur, puis
    # rh.pgt_salarie. Cross-schema mais meme connexion PG, OK.
    db_ul = get_pg_connection("ulease")
    r = db_ul.query_one(
        """SELECT c.id_salarie
             FROM ulease.pgt_carteattribution ca
       INNER JOIN ulease.pgt_conducteur c
               ON c.id_conducteur = ca.id_conducteur
            WHERE (ca.modif_elem IS NULL OR ca.modif_elem <> 'suppr')
              AND ca.id_carte_carburant = ?
              AND ca.du <= ?
              AND (ca.au IS NULL OR ca.au >= ?)
         ORDER BY ca.du DESC LIMIT 1""",
        (int(id_carte), d, d),
    )
    id_sal = _int(r.get("id_salarie")) if r else 0
    if not id_sal:
        return ""
    db_rh = get_pg_connection("rh")
    s = db_rh.query_one(
        """SELECT nom, prenom, nom_marital FROM rh.pgt_salarie
            WHERE id_salarie = ? LIMIT 1""",
        (id_sal,),
    )
    if not s:
        return ""
    nom = _str(s.get("nom"))
    marital = _str(s.get("nom_marital"))
    prenom = _str(s.get("prenom")).strip()
    if prenom:
        prenom = prenom[:1].upper() + prenom[1:].lower()
    nom_complet = f"{nom} {marital}".strip() if marital else nom
    return f"{nom_complet} {prenom}".strip()


# ---------------------------------------------------------------------------
# Fen_AnalyseCarb - Detection alerte Carb (plein Vendredi + Lundi)
# ---------------------------------------------------------------------------


def detect_alertes(du: str, au: str) -> list[dict]:
    """Detecte les cas suspects : plein de Carburant le Vendredi suivi
    d'un plein le Lundi suivant (= +3 jours) sur la meme carte.

    PG : EXTRACT(DOW FROM date) -> 0=dim, 1=lun, ... 5=ven, 6=sam.
    WinDev/MySQL DAYOFWEEK : 1=dim, 2=lun, ... 6=ven (decalage +1).
    Ici on filtre DOW=5 pour vendredi et DOW=1 pour lundi.

    Retourne une ligne par alerte avec :
      - num_carte
      - date_vendredi (ISO)
      - nom_conducteur (a la date du vendredi)
      - detail_alerte (texte multi-ligne : 'Carb <date> a <h> de <m>€'
        + idem pour le lundi).
    """
    db = get_pg_connection("ulease")

    # 1. Tous les pleins Carburant Vendredi entre Du et Au
    ven_rows = db.query(
        """SELECT ccrf.id_carte_carburant, ccrf.date, ccrf.heure,
                  ccrf.montant_ttc, cc.num_carte
             FROM ulease.pgt_cartecarbrelevefournisseur ccrf
       INNER JOIN ulease.pgt_typerelevefournisseur trf
               ON trf.id_type_releve_fournisseur = ccrf.id_type_releve_fournisseur
       INNER JOIN ulease.pgt_cartecarburant cc
               ON cc.id_carte_carburant = ccrf.id_carte_carburant
            WHERE EXTRACT(DOW FROM ccrf.date) = 5
              AND trf.categorie = 'Carburant'
              AND (ccrf.modif_elem IS NULL OR ccrf.modif_elem <> 'suppr')
              AND ccrf.date BETWEEN ? AND ?
         ORDER BY ccrf.id_carte_carburant ASC, ccrf.date ASC, ccrf.heure ASC""",
        (du, au),
    ) or []
    # Regroupement par (id_carte, date) -> liste de pleins
    groups_ven: dict[tuple[int, str], list] = {}
    num_by_id: dict[int, str] = {}
    for r in ven_rows:
        id_c = _int(r.get("id_carte_carburant"))
        d_iso = _iso_date(r.get("date"))
        num_by_id[id_c] = _str(r.get("num_carte"))
        groups_ven.setdefault((id_c, d_iso), []).append(r)

    out: list[dict] = []
    from datetime import timedelta as _td

    for (id_c, d_iso), pleins_ven in groups_ven.items():
        d_ven = _try_parse_date(d_iso)
        if not d_ven:
            continue
        d_lun = d_ven + _td(days=3)
        # 2. Pleins Carburant lundi suivant pour la meme carte
        lun_rows = db.query(
            """SELECT date, heure, montant_ttc, lieu
                 FROM ulease.pgt_cartecarbrelevefournisseur ccrf
           INNER JOIN ulease.pgt_typerelevefournisseur trf
                   ON trf.id_type_releve_fournisseur = ccrf.id_type_releve_fournisseur
                WHERE EXTRACT(DOW FROM ccrf.date) = 1
                  AND trf.categorie = 'Carburant'
                  AND (ccrf.modif_elem IS NULL OR ccrf.modif_elem <> 'suppr')
                  AND ccrf.date = ?
                  AND ccrf.id_carte_carburant = ?
             ORDER BY ccrf.date ASC, ccrf.heure ASC""",
            (d_lun, id_c),
        ) or []
        if not lun_rows:
            continue

        # 3. Construction du detail_alerte
        detail = _format_pleins(pleins_ven) + "\n" + _format_pleins(lun_rows)

        out.append({
            "num_carte": num_by_id.get(id_c, ""),
            "date_vendredi": d_iso,
            "nom_conducteur": _find_attribue(id_c, d_ven),
            "detail_alerte": detail,
        })

    out.sort(key=lambda x: (x["date_vendredi"], x["num_carte"]))
    return out


_JOURS_FR = {0: "Dim", 1: "Lun", 2: "Mar", 3: "Mer", 4: "Jeu", 5: "Ven", 6: "Sam"}


def _format_pleins(rows: list) -> str:
    """Concatene les pleins d'un meme jour en un seul texte :
    'Carb Ven 15/05/26 a 18:32 de 65.20€ et a 19:01 de 12.30€'."""
    if not rows:
        return ""
    # On suppose que tous les rows ont la meme date (regroupement amont)
    first = rows[0]
    d_str = _iso_date(first.get("date"))
    d_parsed = _try_parse_date(d_str)
    jour = _JOURS_FR.get(d_parsed.weekday() if d_parsed else 0, "")
    jj = f"{d_str[8:10]}/{d_str[5:7]}/{d_str[2:4]}" if d_str else ""
    parts = []
    for r in rows:
        h = r.get("heure")
        m = _float(r.get("montant_ttc"))
        h_str = ""
        if h is not None:
            if hasattr(h, "strftime"):
                h_str = h.strftime("%H:%M")
            else:
                s = str(h)
                h_str = s[:5] if len(s) >= 5 else s
        parts.append(f"à {h_str} de {m:.2f}€")
    body = " et ".join(parts)
    return f"Carb {jour} {jj} {body}"


def _try_parse_date(s: str):
    if not s or len(s) < 10:
        return None
    try:
        from datetime import date as _d
        return _d(int(s[:4]), int(s[5:7]), int(s[8:10]))
    except Exception:
        return None
