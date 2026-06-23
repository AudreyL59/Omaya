"""Service Fen_RechercheCV (shared : ADM + Vendeur + Call RH).

Couvre :
- Combos (sources, statuts, postes, annonceurs, societes)
- Recherche communes (autocompletion ville + rayon)
- Recherche CV (modes 1=CP, 3=Tel, 4=Nom — mode 2=Agence en V2)
- Filtres metier : age, source, profil, statut, periode
- LEFT JOIN dernier statut CvSuivi (statut_actuel + statut_periode a la date_fin)
- Detail source : nom coopteur ou lib annonceur
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Optional

from app.core.database.pg import get_pg_connection
from app.shared.recrutement.schemas.recherche_cv import (
    CommuneItem, ComboItem, CVRow, SearchCVFiltres,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEL_RE = re.compile(r"[^0-9]")


def _str(v) -> str:
    return "" if v is None else str(v)


def _int(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def _id(v) -> str:
    n = _int(v)
    return str(n) if n else ""


def _norm_date(v: Optional[str], end_of_day: bool = False) -> Optional[str]:
    """Normalise YYYY-MM-DD ou ISO en 'YYYY-MM-DD HH:MM:SS' PG-compatible."""
    if not v:
        return None
    s = str(v)[:19].replace("T", " ")
    if len(s) == 10:
        s += " 23:59:59" if end_of_day else " 00:00:00"
    return s


def _calc_age(date_naissance) -> int:
    if not date_naissance:
        return 0
    if isinstance(date_naissance, str):
        try:
            date_naissance = datetime.strptime(date_naissance[:10], "%Y-%m-%d").date()
        except ValueError:
            return 0
    today = datetime.now().date()
    return today.year - date_naissance.year - (
        (today.month, today.day) < (date_naissance.month, date_naissance.day)
    )


def _normalize_tel(s: str) -> str:
    return _TEL_RE.sub("", s or "")


# ---------------------------------------------------------------------------
# Combos
# ---------------------------------------------------------------------------


def list_sources() -> list[ComboItem]:
    db = get_pg_connection("recrutement")
    rows = db.query(
        "SELECT id_cvsource, lib_source FROM recrutement.pgt_cv_source "
        "WHERE is_actif = true ORDER BY lib_source ASC"
    ) or []
    return [ComboItem(id=str(r["id_cvsource"]), label=_str(r["lib_source"]))
            for r in rows]


def list_statuts() -> list[ComboItem]:
    db = get_pg_connection("recrutement")
    rows = db.query(
        "SELECT id_cv_statut, lib_statut FROM recrutement.pgt_cvstatut "
        "WHERE modif_elem NOT LIKE '%suppr%' ORDER BY id_cv_statut ASC"
    ) or []
    return [ComboItem(id=str(r["id_cv_statut"]), label=_str(r["lib_statut"]))
            for r in rows]


def list_postes() -> list[ComboItem]:
    db = get_pg_connection("recrutement")
    rows = db.query(
        "SELECT id_cvposte, lib_poste FROM recrutement.pgt_cvposte "
        "WHERE COALESCE(is_actif, true) = true ORDER BY lib_poste ASC"
    ) or []
    return [ComboItem(id=str(r["id_cvposte"]), label=_str(r["lib_poste"]))
            for r in rows if _str(r["lib_poste"]).strip()]


def list_annonceurs() -> list[ComboItem]:
    db = get_pg_connection("recrutement")
    rows = db.query(
        "SELECT id_cv_annonceur, lib_annonceur FROM recrutement.pgt_cv_annonceur "
        "WHERE modif_elem NOT LIKE '%suppr%' ORDER BY lib_annonceur ASC"
    ) or []
    return [ComboItem(id=str(r["id_cv_annonceur"]), label=_str(r["lib_annonceur"]))
            for r in rows]


def list_societes() -> list[ComboItem]:
    """Societes (RH) — id_type_orga = 1 (FDV Interne)."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT idorganigramme, lib_orga FROM rh.pgt_organigramme
            WHERE id_type_orga = 1
              AND modif_elem NOT LIKE '%suppr%'
         ORDER BY lib_orga ASC"""
    ) or []
    return [ComboItem(id=str(r["idorganigramme"]), label=_str(r["lib_orga"]))
            for r in rows]


# ---------------------------------------------------------------------------
# Communes (autocompletion + rayon)
# ---------------------------------------------------------------------------


def search_communes(query: str, limit: int = 50) -> list[CommuneItem]:
    """Recherche par CP ou nom de ville (LIKE prefix)."""
    if not query or len(query) < 2:
        return []
    q = query.strip().upper()
    q_like = q.replace(" ", "%").replace("-", "%")
    db = get_pg_connection("divers")
    rows = db.query(
        """SELECT id_communes_france, code_postal, nom_ville,
                  latitude_deg, longitude_deg
             FROM divers.pgt_communes_france
            WHERE modif_elem NOT LIKE '%suppr%'
              AND (UPPER(nom_ville) LIKE ? OR code_postal LIKE ?)
         ORDER BY code_postal ASC, nom_ville ASC
            LIMIT ?""",
        (q_like + "%", q + "%", int(limit)),
    ) or []
    return [
        CommuneItem(
            id_communes_france=str(r["id_communes_france"]),
            code_postal=_str(r["code_postal"]),
            nom_ville=_str(r["nom_ville"]),
            latitude_deg=r["latitude_deg"],
            longitude_deg=r["longitude_deg"],
        )
        for r in rows
    ]


def communes_by_rayon(
    centre_lat: float, centre_lon: float, rayon_km: int,
) -> list[str]:
    """Retourne les id_communes_france dans le rayon (haversine en SQL)."""
    if not centre_lat or not centre_lon or rayon_km <= 0:
        return []
    db = get_pg_connection("divers")
    # 6371 = rayon terre en km, formule haversine
    rows = db.query(
        """SELECT id_communes_france
             FROM divers.pgt_communes_france
            WHERE modif_elem NOT LIKE '%suppr%'
              AND latitude_deg IS NOT NULL
              AND longitude_deg IS NOT NULL
              AND (
                  6371 * acos(
                      LEAST(1.0, GREATEST(-1.0,
                          cos(radians(?)) * cos(radians(latitude_deg))
                          * cos(radians(longitude_deg) - radians(?))
                          + sin(radians(?)) * sin(radians(latitude_deg))
                      ))
                  )
              ) <= ?""",
        (centre_lat, centre_lon, centre_lat, rayon_km),
    ) or []
    return [str(r["id_communes_france"]) for r in rows]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance haversine en km (utilise si besoin cote Python)."""
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Recherche CV principale
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Organigramme (mode Agence)
# ---------------------------------------------------------------------------


def list_orga_children(id_parent: int) -> list[dict]:
    """Enfants directs d'un noeud (id_parent=0 = racine 'Reseau')."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT o.idorganigramme, o.lib_orga,
                  EXISTS (
                    SELECT 1 FROM rh.pgt_organigramme c
                     WHERE c.id_parent = o.idorganigramme
                       AND c.modif_elem NOT LIKE '%suppr%'
                       AND c.idorganigramme <> 0
                  ) AS has_children
             FROM rh.pgt_organigramme o
            WHERE o.id_parent = ?
              AND o.idorganigramme <> 0
              AND o.modif_elem NOT LIKE '%suppr%'
         ORDER BY o.lib_orga ASC""",
        (int(id_parent),),
    ) or []
    return [{
        "idorganigramme": str(r["idorganigramme"]),
        "lib_orga": _str(r["lib_orga"]),
        "has_children": bool(r["has_children"]),
    } for r in rows]


def get_orga_descendants(ids_orga: list[int]) -> list[int]:
    """Recursive CTE : retourne tous les descendants inclus."""
    if not ids_orga:
        return []
    db = get_pg_connection("rh")
    ph = ",".join(["?"] * len(ids_orga))
    rows = db.query(
        f"""WITH RECURSIVE sub AS (
                SELECT idorganigramme FROM rh.pgt_organigramme
                 WHERE idorganigramme IN ({ph})
                   AND modif_elem NOT LIKE '%suppr%'
                UNION
                SELECT o.idorganigramme
                  FROM rh.pgt_organigramme o
                  JOIN sub s ON o.id_parent = s.idorganigramme
                 WHERE o.modif_elem NOT LIKE '%suppr%'
                   AND o.idorganigramme <> 0
            )
            SELECT idorganigramme FROM sub""",
        tuple(int(x) for x in ids_orga),
    ) or []
    return [_int(r["idorganigramme"]) for r in rows]


def get_salaries_dans_orgas(
    ids_orga: list[int],
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
) -> list[int]:
    """Salaries rattaches a au moins un des orgas pendant la periode.

    Retourne la liste des id_salarie distincts.
    """
    if not ids_orga:
        return []
    db = get_pg_connection("rh")
    ph = ",".join(["?"] * len(ids_orga))
    params: list = list(int(x) for x in ids_orga)
    where_extra = ""
    if date_debut and date_fin:
        where_extra = (" AND so.date_debut <= ?"
                       " AND (so.date_fin IS NULL OR so.date_fin >= ?)")
        params.extend([date_fin[:10], date_debut[:10]])
    rows = db.query(
        f"""SELECT DISTINCT so.id_salarie
              FROM rh.pgt_salarie_organigramme so
             WHERE so.idorganigramme IN ({ph})
               AND so.modif_elem NOT LIKE '%suppr%'
               {where_extra}""",
        tuple(params),
    ) or []
    return [_int(r["id_salarie"]) for r in rows if _int(r["id_salarie"])]


# ---------------------------------------------------------------------------
# Presence : claim / release / poll
# ---------------------------------------------------------------------------


def claim_cv(id_cv: int, op_id: int) -> dict:
    """Marque le CV comme 'en cours de traitement' par cet operateur."""
    db = get_pg_connection("recrutement")
    # Verifie qu'il n'est pas deja claim par un autre aujourd'hui
    row = db.query(
        """SELECT op_traite, date_traite FROM recrutement.pgt_cvtheque
            WHERE id_cvtheque = ?""",
        (int(id_cv),),
    )
    if row:
        cur_op = _int(row[0].get("op_traite"))
        cur_dt = row[0].get("date_traite")
        if cur_op and cur_op != int(op_id) and cur_dt:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if cur_dt >= today:
                return {"ok": False, "error": "deja_claim", "op_traite": str(cur_op)}
    db.query(
        """UPDATE recrutement.pgt_cvtheque
              SET traite_en_cours = true, op_traite = ?, date_traite = NOW(),
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_cvtheque = ?""",
        (int(op_id), int(op_id), int(id_cv)),
    )
    return {"ok": True}


def release_cv(id_cv: int, op_id: int) -> dict:
    """Libere le CV (uniquement si c'est nous qui le possedons)."""
    db = get_pg_connection("recrutement")
    db.query(
        """UPDATE recrutement.pgt_cvtheque
              SET traite_en_cours = false, op_traite = 0,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_cvtheque = ? AND op_traite = ?""",
        (int(op_id), int(id_cv), int(op_id)),
    )
    return {"ok": True}


def release_my_orphans(op_id: int) -> dict:
    """Libere tous les claims de cet operateur datant d'avant aujourd'hui.

    Appele par le frontend au mount de la page (cleanup des sessions
    interrompues : crash navigateur, fermeture sans clean, etc.).
    """
    db = get_pg_connection("recrutement")
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    db.query(
        """UPDATE recrutement.pgt_cvtheque
              SET traite_en_cours = false, op_traite = 0,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE op_traite = ? AND date_traite < ?""",
        (int(op_id), int(op_id), today),
    )
    return {"ok": True}


def get_presence(ids: list[int]) -> dict[str, dict]:
    """Retourne pour chaque id_cvtheque : {op_traite, op_nom, statut_actuel}.

    Filtre presences expirees (date_traite < aujourd'hui).
    """
    if not ids:
        return {}
    db = get_pg_connection("recrutement")
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    ph = ",".join(["?"] * len(ids))
    rows = db.query(
        f"""SELECT id_cvtheque, op_traite, date_traite, traite_en_cours
              FROM recrutement.pgt_cvtheque
             WHERE id_cvtheque IN ({ph})""",
        tuple(int(x) for x in ids),
    ) or []

    # Dernier statut par CV
    sr = db.query(
        f"""SELECT DISTINCT ON (s.id_cvtheque)
                   s.id_cvtheque, s.id_cv_statut
              FROM recrutement.pgt_cvsuivi s
             WHERE s.id_cvtheque IN ({ph})
               AND (s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')
          ORDER BY s.id_cvtheque, s.datecrea DESC""",
        tuple(int(x) for x in ids),
    ) or []
    statut_by_cv = {_int(r["id_cvtheque"]): _int(r["id_cv_statut"]) for r in sr}

    # Resolveur op_traite -> nom prenom
    op_ids = {_int(r["op_traite"]) for r in rows if _int(r.get("op_traite"))
              and r.get("date_traite") and r["date_traite"] >= today}
    ops: dict[int, str] = {}
    if op_ids:
        db_rh = get_pg_connection("rh")
        ph2 = ",".join(["?"] * len(op_ids))
        opr = db_rh.query(
            f"SELECT id_salarie, nom, prenom FROM rh.pgt_salarie "
            f"WHERE id_salarie IN ({ph2})",
            tuple(op_ids),
        ) or []
        ops = {_int(r["id_salarie"]):
               f"{_str(r['nom']).upper()} {_str(r['prenom']).strip().title()}".strip()
               for r in opr}

    out: dict[str, dict] = {}
    for r in rows:
        id_cv = _int(r["id_cvtheque"])
        op = _int(r.get("op_traite"))
        dt = r.get("date_traite")
        if r.get("traite_en_cours") and op and dt and dt >= today:
            out[str(id_cv)] = {
                "op_traite": str(op),
                "op_nom": ops.get(op, ""),
                "statut_actuel": str(statut_by_cv.get(id_cv, "")),
            }
        else:
            out[str(id_cv)] = {
                "op_traite": "",
                "op_nom": "",
                "statut_actuel": str(statut_by_cv.get(id_cv, "")),
            }
    return out


def search_cv(f: SearchCVFiltres) -> list[CVRow]:
    """Construit la query dynamique selon le mode et execute."""
    where: list[str] = ["(cv.modif_elem IS NULL OR cv.modif_elem NOT LIKE '%suppr%')"]
    params: list = []

    date_deb = _norm_date(f.date_debut, end_of_day=False)
    date_fin = _norm_date(f.date_fin, end_of_day=True)

    # === Mode-specific filtres ===
    if f.mode == 1:
        # Mode CP
        if f.sous_mode_cp == 1:
            # avec ville (id_communes_france liste) + rayon optionnel
            ids = list(f.id_communes_france or [])
            if f.rayon_km and f.centre_lat and f.centre_lon:
                ids += communes_by_rayon(
                    f.centre_lat, f.centre_lon, f.rayon_km,
                )
            ids = list({_id(x) for x in ids if _id(x)})
            if ids:
                ph = ",".join(["?"] * len(ids))
                where.append(f"cv.id_communes_france IN ({ph})")
                params.extend([int(x) for x in ids])
            else:
                # aucune commune -> aucun resultat
                return []
        elif f.sous_mode_cp == 2:
            # CV sans commune
            where.append("(cv.id_communes_france IS NULL "
                         "OR cv.id_communes_france < 900000 "
                         "AND cv.id_communes_france = 0)")
        # sous_mode 3 = ne pas geolocaliser : pas de filtre commune

        # date filtre
        if date_deb and date_fin:
            if f.select_type_date == 1:
                where.append(
                    "(cv.date_saisie BETWEEN ? AND ? "
                    "OR cv.date_reac BETWEEN ? AND ? "
                    "OR cv.date_rappel BETWEEN ?::date AND ?::date)"
                )
                params.extend([date_deb, date_fin, date_deb, date_fin,
                               date_deb[:10], date_fin[:10]])
            else:
                where.append(
                    "EXISTS (SELECT 1 FROM recrutement.pgt_cvsuivi s "
                    "WHERE s.id_cvtheque = cv.id_cvtheque "
                    "AND s.datecrea BETWEEN ? AND ?)"
                )
                params.extend([date_deb, date_fin])

    elif f.mode == 2:
        # Mode agence : resoudre orgas -> descendants -> salaries -> CV cooptes
        ids_orga = [_int(x) for x in (f.id_organigrammes or []) if _int(x)]
        if not ids_orga:
            return []
        all_orgas = get_orga_descendants(ids_orga)
        if not all_orgas:
            return []
        ids_sal = get_salaries_dans_orgas(
            all_orgas,
            date_debut=date_deb, date_fin=date_fin,
        )
        if not ids_sal:
            return []
        ph_sal = ",".join(["?"] * len(ids_sal))
        where.append(f"cv.id_cvsource = 1 AND cv.id_elem_source IN ({ph_sal})")
        params.extend(ids_sal)
        # date filtre
        if date_deb and date_fin:
            if f.select_type_date == 1:
                where.append(
                    "(cv.date_saisie BETWEEN ? AND ? "
                    "OR cv.date_reac BETWEEN ? AND ?)"
                )
                params.extend([date_deb, date_fin, date_deb, date_fin])
            else:
                where.append(
                    "EXISTS (SELECT 1 FROM recrutement.pgt_cvsuivi s "
                    "WHERE s.id_cvtheque = cv.id_cvtheque "
                    "AND s.datecrea BETWEEN ? AND ?)"
                )
                params.extend([date_deb, date_fin])

    elif f.mode == 3:
        # Mode tel
        tel = _normalize_tel(f.tel or "")
        if not tel:
            return []
        where.append("cv.gsm LIKE ?")
        params.append("%" + tel + "%")

    elif f.mode == 4:
        # Mode nom
        nom = (f.nom or "").strip().upper()
        prenom = (f.prenom or "").strip().upper()
        if not nom:
            return []
        nom_like = nom.replace(" ", "%").replace("-", "%")
        where.append("UPPER(cv.nom) LIKE ?")
        params.append("%" + nom_like + "%")
        if prenom:
            prenom_like = prenom.replace(" ", "%").replace("-", "%")
            where.append("UPPER(cv.prenom) LIKE ?")
            params.append("%" + prenom_like + "%")

    # === Filtres communs (mode 1+2) ===
    if f.mode in (1, 2):
        if f.id_cvsource and f.id_cvsource != "%":
            where.append("cv.id_cvsource = ?")
            params.append(_int(f.id_cvsource))
            if f.id_elem_source:
                where.append("cv.id_elem_source = ?")
                params.append(_int(f.id_elem_source))

        if f.id_ste and f.id_ste != "%":
            where.append("cv.id_ste = ?")
            params.append(_int(f.id_ste))

        # Profil
        if f.select_profil == 1:
            where.append("cv.id_cvposte IN (0, 1)")
        elif f.select_profil == 2:
            where.append("cv.id_cvposte IN (10, 13)")
        elif f.select_profil == 3:
            where.append("cv.id_cvposte IN (0, 1, 10, 13)")
        elif f.select_profil == 4 and f.id_cvposte and f.id_cvposte != "%":
            where.append("cv.id_cvposte = ?")
            params.append(_int(f.id_cvposte))

        # Age (date_naissance)
        if f.age_max < 100:
            today = datetime.now().date()
            age_max_date = today.replace(year=today.year - f.age_min)
            age_min_date = today.replace(year=today.year - f.age_max - 1)
            if f.age_min == 0:
                where.append("(cv.date_naissance IS NULL "
                             "OR cv.date_naissance BETWEEN ? AND ?)")
                params.extend([age_min_date, age_max_date])
            else:
                where.append("cv.date_naissance BETWEEN ? AND ?")
                params.extend([age_min_date, age_max_date])

    where_sql = " AND ".join(where)
    sql = f"""
        SELECT
          cv.id_cvtheque,
          cv.nom, cv.prenom,
          cv.date_naissance, cv.date_saisie, cv.date_reac,
          cv.date_rappel, cv.observ,
          cv.gsm, cv.id_cvsource, cv.id_elem_source, cv.id_cvposte,
          cv.id_communes_france, cv.traite_en_cours, cv.op_traite,
          cv.date_traite,
          c.code_postal, c.nom_ville
        FROM recrutement.pgt_cvtheque cv
        LEFT JOIN divers.pgt_communes_france c
               ON c.id_communes_france = cv.id_communes_france
        WHERE {where_sql}
        ORDER BY cv.date_saisie DESC
        LIMIT {int(f.limit)}
    """
    db = get_pg_connection("recrutement")
    rows = db.query(sql, tuple(params)) or []
    return _enrich_cv_rows(rows, f)


def _enrich_cv_rows(rows: list[dict], f: SearchCVFiltres) -> list[CVRow]:
    """Resolveur des statuts (actuel + periode) + details source en batch."""
    if not rows:
        return []
    db = get_pg_connection("recrutement")

    ids_cv = [_int(r["id_cvtheque"]) for r in rows if _int(r["id_cvtheque"])]

    # Dernier statut par CV (LATERAL JOIN)
    statut_by_cv: dict[int, dict] = {}
    if ids_cv:
        ph = ",".join(["?"] * len(ids_cv))
        sr = db.query(
            f"""SELECT DISTINCT ON (s.id_cvtheque)
                       s.id_cvtheque, s.id_cv_statut, s.datecrea
                  FROM recrutement.pgt_cvsuivi s
                 WHERE s.id_cvtheque IN ({ph})
                   AND (s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')
              ORDER BY s.id_cvtheque, s.datecrea DESC""",
            tuple(ids_cv),
        ) or []
        statut_by_cv = {_int(r["id_cvtheque"]): r for r in sr}

    # Statut a une date donnee (mode 1 par date saisie -> on cherche le statut
    # qui etait le sien a date_fin)
    date_fin = _norm_date(f.date_fin, end_of_day=True)
    statut_periode_by_cv: dict[int, int] = {}
    if ids_cv and date_fin:
        ph = ",".join(["?"] * len(ids_cv))
        sr = db.query(
            f"""SELECT DISTINCT ON (s.id_cvtheque)
                       s.id_cvtheque, s.id_cv_statut
                  FROM recrutement.pgt_cvsuivi s
                 WHERE s.id_cvtheque IN ({ph})
                   AND s.modif_date <= ?
                   AND (s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')
              ORDER BY s.id_cvtheque, s.datecrea DESC""",
            (*ids_cv, date_fin),
        ) or []
        statut_periode_by_cv = {
            _int(r["id_cvtheque"]): _int(r["id_cv_statut"]) for r in sr
        }

    # Resolveur coopteurs (id_elem_source -> nom prenom) pour source = 1
    coopteur_ids = {_int(r["id_elem_source"])
                    for r in rows if _int(r["id_cvsource"]) == 1
                    and _int(r["id_elem_source"])}
    coopteurs: dict[int, dict] = {}
    if coopteur_ids:
        db_rh = get_pg_connection("rh")
        ph = ",".join(["?"] * len(coopteur_ids))
        cr = db_rh.query(
            f"""SELECT id_salarie, nom, prenom FROM rh.pgt_salarie
                 WHERE id_salarie IN ({ph})""",
            tuple(coopteur_ids),
        ) or []
        coopteurs = {_int(r["id_salarie"]): r for r in cr}

    # Resolveur annonceurs (id_elem_source -> lib) pour source = 2
    annonceur_ids = {_int(r["id_elem_source"])
                     for r in rows if _int(r["id_cvsource"]) == 2
                     and _int(r["id_elem_source"])}
    annonceurs: dict[int, str] = {}
    if annonceur_ids:
        ph = ",".join(["?"] * len(annonceur_ids))
        ar = db.query(
            f"""SELECT id_cv_annonceur, lib_annonceur
                  FROM recrutement.pgt_cv_annonceur
                 WHERE id_cv_annonceur IN ({ph})""",
            tuple(annonceur_ids),
        ) or []
        annonceurs = {_int(r["id_cv_annonceur"]): _str(r["lib_annonceur"])
                      for r in ar}

    # Resolveur op_traite -> nom salarie pour presence
    op_ids = {_int(r["op_traite"]) for r in rows if _int(r["op_traite"])}
    ops: dict[int, str] = {}
    if op_ids:
        db_rh = get_pg_connection("rh")
        ph = ",".join(["?"] * len(op_ids))
        opr = db_rh.query(
            f"""SELECT id_salarie, nom, prenom FROM rh.pgt_salarie
                 WHERE id_salarie IN ({ph})""",
            tuple(op_ids),
        ) or []
        ops = {_int(r["id_salarie"]): f"{_str(r['nom'])} {_str(r['prenom'])}".strip()
               for r in opr}

    out: list[CVRow] = []
    now = datetime.now()
    cv_statut_appel = _int(f.cv_statut_appel) if (
        f.cv_statut_appel and f.cv_statut_appel != "%"
    ) else None

    for r in rows:
        id_cv = _int(r["id_cvtheque"])
        nom = _str(r["nom"]).upper()
        prenom = _str(r["prenom"]).strip().title()

        statut_row = statut_by_cv.get(id_cv) or {}
        statut_actuel = _int(statut_row.get("id_cv_statut"))
        statut_periode = statut_periode_by_cv.get(id_cv, statut_actuel)

        # Filtre statut (post-query car necessite jointure)
        if cv_statut_appel is not None and statut_actuel != cv_statut_appel:
            continue

        # Presence : op_traite + date_traite valide
        op_traitement = ""
        op_traitement_id = ""
        if r.get("traite_en_cours") and _int(r.get("op_traite")):
            date_traite = r.get("date_traite")
            if date_traite and date_traite >= now.replace(hour=0, minute=0, second=0, microsecond=0):
                op_traitement = ops.get(_int(r["op_traite"]), "")
                op_traitement_id = str(_int(r["op_traite"]))

        # Localisation
        loc = ""
        if r.get("code_postal") or r.get("nom_ville"):
            loc = f"{_str(r['code_postal'])} {_str(r['nom_ville'])}".strip()

        # Detail source
        detail = ""
        id_src = _int(r["id_cvsource"])
        id_elem = _int(r["id_elem_source"])
        if id_src == 1 and id_elem and id_elem in coopteurs:
            c = coopteurs[id_elem]
            detail = f"{_str(c['nom']).upper()} {_str(c['prenom']).strip().title()}"
        elif id_src == 2 and id_elem in annonceurs:
            detail = annonceurs[id_elem]

        # Commentaire (premiere ligne datee)
        obs = _str(r.get("observ"))
        commentaire = ""
        if obs:
            for ligne in obs.split("\n"):
                if re.match(r"\d{2}/\d{2}/\d{4}", ligne.strip()):
                    commentaire = ligne.strip()
                    break
            if not commentaire:
                commentaire = obs.split("\n")[0].strip()

        out.append(CVRow(
            id_cvtheque=str(id_cv),
            identite=f"{nom} {prenom}".strip(),
            nom=nom,
            prenom=prenom,
            op_traitement=op_traitement,
            op_traitement_id=op_traitement_id,
            statut_actuel=str(statut_actuel) if statut_actuel else "",
            statut_periode=str(statut_periode) if statut_periode else "",
            source=str(id_src) if id_src else "",
            detail_source=detail,
            age=_calc_age(r.get("date_naissance")),
            tel=_str(r.get("gsm")),
            localisation=loc,
            date_saisie=str(r.get("date_saisie") or "")[:10],
            date_rappel=str(r.get("date_rappel") or "")[:10] if statut_actuel == 2 else "",
            commentaire=commentaire,
        ))
    return out
