"""Service Tickets — accès aux tables TK_Liste / TK_TypeDemande / TK_Statut."""

from __future__ import annotations

import base64
import re
import struct
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from app.core.database.pg import get_pg_connection


# ---------------------------------------------------------------
# Cache mémoire (TTL) — évite les bursts d'appels au bridge HFSQL
# pour des données qui changent rarement (TK_TypeDemande / TK_Statut).
# ---------------------------------------------------------------

_CACHE_TTL_S = 60.0  # 60 secondes — invalidation auto

# (frozen_droits, droit_field) -> (timestamp, list[dict])
_types_cache: dict[tuple, tuple[float, list[dict]]] = {}
# (frozen_droits, droit_field) -> (timestamp, set[int])
_type_ids_cache: dict[tuple, tuple[float, set[int]]] = {}
# Statuts (statique) -> (timestamp, list[dict])
_statuts_cache: tuple[float, list[dict]] | None = None


def _cache_get(store: dict, key, ttl: float = _CACHE_TTL_S):
    item = store.get(key)
    if not item:
        return None
    ts, val = item
    if time.time() - ts > ttl:
        store.pop(key, None)
        return None
    return val


# ---------------------------------------------------------------
# Helpers (copiés du pattern production/service.py)
# ---------------------------------------------------------------

def _to_int(v) -> int:
    if v is None or v == "":
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            pass
        try:
            raw = base64.b64decode(v)
            if len(raw) == 8:
                return struct.unpack("<q", raw)[0]
            if len(raw) == 4:
                return struct.unpack("<i", raw)[0]
        except Exception:
            pass
    return 0


def _clean_id(n: int) -> int:
    if 0 < n < 9_000_000_000_000_000_000:
        return n
    return 0


def _str_id(v) -> str:
    """ID 8 octets en string (cf. règle projet)."""
    n = _clean_id(_to_int(v))
    return str(n) if n else ""


def _now_windev() -> str:
    now = datetime.now()
    return now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"


def _windev_to_iso(v) -> str:
    """Convertit en ISO 'YYYY-MM-DD HH:MM:SS' :
    - datetime/date natifs PG
    - chaine WinDev compact (YYYYMMDDHHMMSS[mmm])
    - chaine ISO deja
    Retourne "" si vide.
    """
    if v is None or v == "":
        return ""
    # PG renvoie des objets natifs apres bascule
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if hasattr(v, "year") and hasattr(v, "month") and hasattr(v, "day"):
        return v.strftime("%Y-%m-%d")
    s = str(v).strip()
    if not s:
        return ""
    # WinDev compact (14 ou 17 chiffres)
    if len(s) >= 14 and s[:8].isdigit() and s[8:14].isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}:{s[12:14]}"
    # ISO déjà ?
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:19]
    return s


# ---------------------------------------------------------------
# TK_TypeDemande
# ---------------------------------------------------------------

def list_type_ids_par_droit(droits: list[str], droit_field: str) -> set[int]:
    """Variante "light" de list_types_par_droit pour les contrôles d'accès :
    une seule requête (pas de fetch des mémos Lib_TypeDemande).

    Cache TTL 60s.
    """
    cache_key = (frozenset(droits or []), droit_field)
    cached = _cache_get(_type_ids_cache, cache_key)
    if cached is not None:
        return cached
    db = get_pg_connection("ticket")
    pg_droit_field = "droit_acces_vend" if droit_field == "DroitAccèsVend" else "droit_acces"
    rows = db.query(
        f"""SELECT id_tk_type_demande, {pg_droit_field}
        FROM pgt_tk_type_demande
        WHERE modif_elem <> 'suppr'"""
    )
    droits_set = set(droits or [])
    out: set[int] = set()
    for r in rows:
        droit = (r.get(pg_droit_field) or "").strip()
        if droit and droit not in droits_set:
            continue
        idt = _clean_id(_to_int(r.get("id_tk_type_demande")))
        if idt:
            out.add(idt)
    _type_ids_cache[cache_key] = (time.time(), out)
    return out


def list_types_par_droit(droits: list[str], droit_field: str) -> list[dict]:
    """Liste les types de demande accessibles selon les droits du user.

    droit_field : "DroitAccès" pour ADM, "DroitAccèsVend" pour Vendeur.
                  Si vide → un type sans droit configuré est visible
                  (sinon il faut que le code droit soit dans `droits`).

    Lib_TypeDemande (mémo texte) et icone (mémo binaire image) → fetch
    séparé 1 SELECT par mémo et par type, pour éviter la troncature du
    bridge HFSQL sur les SELECT multi-colonnes. Les fetchs sont
    parallélisés (ThreadPoolExecutor) car chaque query bridge ≈ 400 ms.

    Cache TTL 60s — la table TK_TypeDemande change rarement.

    Retour trié par Service puis Lib_TypeDemande.
    """
    cache_key = (frozenset(droits or []), droit_field)
    cached = _cache_get(_types_cache, cache_key)
    if cached is not None:
        return cached
    db = get_pg_connection("ticket")

    pg_droit_field = "droit_acces_vend" if droit_field == "DroitAccèsVend" else "droit_acces"

    # 1. SELECT des champs simples (pas de mémo).
    rows = db.query(
        f"""SELECT id_tk_type_demande, service, {pg_droit_field}
        FROM pgt_tk_type_demande
        WHERE modif_elem <> 'suppr'
        ORDER BY service"""
    )
    droits_set = set(droits or [])
    visible: list[tuple[int, str, str]] = []  # (id, service, droit)
    for r in rows:
        droit = (r.get(pg_droit_field) or "").strip()
        if droit and droit not in droits_set:
            continue
        idt = _clean_id(_to_int(r.get("id_tk_type_demande")))
        if not idt:
            continue
        visible.append((idt, (r.get("service") or "").strip(), droit))

    if not visible:
        return []

    # 2. Fetch séparé des mémos lib_type_demande (texte) et icone (bytea) :
    #    le pool PG gère plusieurs connexions, parallélisable comme avant.
    def _fetch_lib(idt: int) -> tuple[int, str]:
        try:
            db_t = get_pg_connection("ticket")
            r = db_t.query_one(
                "SELECT lib_type_demande FROM pgt_tk_type_demande WHERE id_tk_type_demande = ?",
                (idt,),
            )
            return idt, ((r.get("lib_type_demande") if r else "") or "").strip()
        except Exception:
            return idt, ""

    def _fetch_icone(idt: int) -> tuple[int, str]:
        try:
            db_t = get_pg_connection("ticket")
            r = db_t.query_one(
                "SELECT icone FROM pgt_tk_type_demande WHERE id_tk_type_demande = ?",
                (idt,),
            )
            return idt, _icone_to_data_url(r.get("icone") if r else None)
        except Exception:
            return idt, ""

    ids = [idt for idt, _svc, _dr in visible]
    libs: dict[int, str] = {}
    icones: dict[int, str] = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        lib_futs = [pool.submit(_fetch_lib, i) for i in ids]
        ico_futs = [pool.submit(_fetch_icone, i) for i in ids]
        for f in lib_futs:
            i, v = f.result()
            libs[i] = v
        for f in ico_futs:
            i, v = f.result()
            icones[i] = v

    out: list[dict] = []
    for idt, svc, _dr in visible:
        out.append({
            "id_type_demande": str(idt),
            "service": svc,
            "lib_type_demande": libs.get(idt, ""),
            "icone_data_url": icones.get(idt, ""),
        })
    out.sort(key=lambda x: (x["service"], x["lib_type_demande"].lower()))
    _types_cache[cache_key] = (time.time(), out)
    return out


def _icone_to_data_url(blob) -> str:
    """Convertit le mémo binaire en data: URL si possible (PNG/JPEG/GIF)."""
    if not blob:
        return ""
    # PG bytea peut revenir en memoryview ou bytes ; HFSQL le renvoie en
    # base64 dans une str. On supporte les deux.
    if isinstance(blob, memoryview):
        raw = bytes(blob)
    elif isinstance(blob, bytes):
        raw = blob
    else:
        raw = None
    if raw is None and isinstance(blob, str) and blob:
        try:
            raw = base64.b64decode(blob)
        except Exception:
            return ""
    if not raw or len(raw) < 8:
        return ""
    head = raw[:8]
    if head.startswith(b"\x89PNG"):
        mime = "image/png"
    elif head.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif head.startswith(b"GIF8"):
        mime = "image/gif"
    elif head[:5] == b"<?xml" or raw.lstrip().startswith(b"<svg"):
        mime = "image/svg+xml"
    else:
        return ""
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


# ---------------------------------------------------------------
# TK_Statut
# ---------------------------------------------------------------

def list_statuts() -> list[dict]:
    """Liste complète des statuts de tickets, ordonnés par IDTK_Statut.

    Cache TTL 60s — la table TK_Statut change quasi-jamais.
    """
    global _statuts_cache
    if _statuts_cache is not None:
        ts, val = _statuts_cache
        if time.time() - ts <= _CACHE_TTL_S:
            return val
    db = get_pg_connection("ticket")
    rows = db.query(
        """SELECT id_tk_statut, lib_statut FROM pgt_tk_statut
        WHERE modif_elem <> 'suppr'
        ORDER BY id_tk_statut ASC"""
    )
    out = [
        {
            "id_statut": _to_int(r.get("id_tk_statut")),
            "lib_statut": (r.get("lib_statut") or "").strip(),
        }
        for r in rows
    ]
    _statuts_cache = (time.time(), out)
    return out


# ---------------------------------------------------------------
# TK_Liste
# ---------------------------------------------------------------

def list_tickets_par_type(
    id_type_demande: int,
    cloturee: bool = False,
    date_du: str = "",
    date_au: str = "",
    limit: int = 500,
) -> list[dict]:
    """Liste les tickets pour un type de demande donné — équivalent
    REQ_ListeTicketByType (WinDev).

    cloturee : False = uniquement les non clôturés ; True = uniquement les
               clôturés (cf. Interrupteur1 dans le WinDev).
    date_du / date_au : période sur DATECREA. Vide = bornes max
               (2001-01-01 → 3061-01-01) — équivalent au cas Interrupteur1=0
               du WinDev.

    Filtre aussi IDTK_Statut <> 28 (statut "à archiver" exclu côté UI).
    Tri : IDTK_Statut ASC, DATECREA DESC.

    Retour : list de dicts bruts. Les libellés (lib_statut, op_dest_nom...)
    et l'Info (DonneInfoTicket) sont enrichis par l'appelant.
    """
    # Bornes : si pas de date fournie, on prend 2001-01-01 → 3061-01-01.
    # PG strict refuse le format compact HFSQL (YYYYMMDDHHMMSSmmm 17 chars),
    # donc on convertit en ISO. Si l'appelant fournit du compact, on convertit
    # aussi (via _windev_to_iso qui detecte les 2 formats).
    if not date_du:
        date_du = "2001-01-01 00:00:00"
    else:
        date_du = _windev_to_iso(date_du)
    if not date_au:
        date_au = "3061-01-01 00:00:00"
    else:
        date_au = _windev_to_iso(date_au)

    db = get_pg_connection("ticket")
    rows = db.query(
        f"""SELECT
            id_tk_liste, date_crea, op_crea, op_dest, service,
            id_tk_type_demande, id_tk_statut, date_report,
            cloturee, date_cloture,
            modif_date, modification,
            op_traitement_staff
        FROM pgt_tk_liste
        WHERE id_tk_type_demande = ?
          AND modif_elem NOT LIKE '%suppr%'
          AND cloturee = ?
          AND date_crea BETWEEN ?::timestamp AND ?::timestamp
          AND id_tk_statut <> 28
        ORDER BY id_tk_statut ASC, date_crea DESC
        LIMIT {int(limit)}""",
        (int(id_type_demande), bool(cloturee), date_du, date_au),
    )
    out: list[dict] = []
    for r in rows:
        out.append({
            "id_ticket": _str_id(r.get("id_tk_liste")),
            "id_type_demande": _str_id(r.get("id_tk_type_demande")),
            "service": (r.get("service") or "").strip(),
            "id_statut": _to_int(r.get("id_tk_statut")),
            "date_crea": _windev_to_iso(r.get("date_crea")),
            "op_crea": _str_id(r.get("op_crea")),
            "op_dest": _str_id(r.get("op_dest")),
            "op_traitement_staff": _str_id(r.get("op_traitement_staff")),
            "cloturee": bool(r.get("cloturee")),
            "date_cloture": _windev_to_iso(r.get("date_cloture")),
            "date_report": _windev_to_iso(r.get("date_report")),
            "modif_date": _windev_to_iso(r.get("modif_date")),
            "modification": bool(r.get("modification")),
        })
    return out


def list_tickets_modified_since(
    id_type_demande: int,
    cursor_compact: str,
    cloturee: bool = False,
    date_du: str = "",
    date_au: str = "",
    limit: int = 100,
) -> list[dict]:
    """Tickets dont ModifDate > cursor_compact — pour le polling SSE.

    cursor_compact : chaîne WinDev compacte (≥ 14 chiffres). Vide = pas de
                     filtre (ramène tout).
    date_du / date_au : bornes optionnelles sur DATECREA (WinDev compact).
                        Sert à conserver la cohérence avec le filtre côté UI.

    Retourne les mêmes champs que `list_tickets_par_type`, plus :
      - `_modif_compact`     : ModifDate brut (str compact WinDev)
      - `_date_crea_compact` : DATECREA brut (str compact WinDev)
    Ces 2 champs servent au générateur SSE pour faire avancer son curseur
    et discriminer added vs modified.
    """
    # Conversion cursor / dates compact WinDev -> ISO PG.
    def _to_pg_ts(s: str, default_iso: str) -> str:
        s = (s or "").strip()
        if not s:
            return default_iso
        # WinDev compact (14 chiffres min)
        if len(s) >= 14 and s[:8].isdigit() and s[8:14].isdigit():
            return f"{s[0:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}:{s[12:14]}"
        # ISO deja
        if len(s) >= 10 and s[4] == "-":
            return s[:19]
        return default_iso

    cursor_pg = _to_pg_ts(cursor_compact, "2001-01-01 00:00:00")
    date_du_pg = _to_pg_ts(date_du, "2001-01-01 00:00:00")
    date_au_pg = _to_pg_ts(date_au, "3061-01-01 00:00:00")

    db = get_pg_connection("ticket")
    rows = db.query(
        f"""SELECT id_tk_liste, date_crea, op_crea, op_dest, service,
            id_tk_type_demande, id_tk_statut, date_report,
            cloturee, date_cloture, modif_date, modification,
            op_traitement_staff
        FROM pgt_tk_liste
        WHERE id_tk_type_demande = ?
          AND modif_elem NOT LIKE '%suppr%'
          AND cloturee = ?
          AND modif_date > ?
          AND date_crea BETWEEN ? AND ?
          AND id_tk_statut <> 28
        ORDER BY modif_date DESC
        LIMIT {int(limit)}""",
        (int(id_type_demande), bool(cloturee), cursor_pg, date_du_pg, date_au_pg),
    )
    out: list[dict] = []
    for r in rows:
        md = r.get("modif_date")
        dc = r.get("date_crea")
        md_iso = _windev_to_iso(md)
        dc_iso = _windev_to_iso(dc)
        # Cursor compact reconstruit a partir de l'ISO pour rester compatible
        # avec le long-polling client qui repasse cette valeur en cursor.
        md_compact = md_iso.replace("-", "").replace(":", "").replace(" ", "") + "000" if md_iso else ""
        dc_compact = dc_iso.replace("-", "").replace(":", "").replace(" ", "") + "000" if dc_iso else ""
        out.append({
            "id_ticket": _str_id(r.get("id_tk_liste")),
            "id_type_demande": _str_id(r.get("id_tk_type_demande")),
            "service": (r.get("service") or "").strip(),
            "id_statut": _to_int(r.get("id_tk_statut")),
            "date_crea": dc_iso,
            "op_crea": _str_id(r.get("op_crea")),
            "op_dest": _str_id(r.get("op_dest")),
            "op_traitement_staff": _str_id(r.get("op_traitement_staff")),
            "cloturee": bool(r.get("cloturee")),
            "date_cloture": _windev_to_iso(r.get("date_cloture")),
            "date_report": _windev_to_iso(r.get("date_report")),
            "modif_date": md_iso,
            "modification": bool(r.get("modification")),
            "_modif_compact": md_compact,
            "_date_crea_compact": dc_compact,
        })
    return out


# ---------------------------------------------------------------
# Lookups en batch (pour enrichir les rows)
# ---------------------------------------------------------------

def load_salaries_minimal(ids: set[int]) -> dict[int, dict]:
    """Charge {id: {nom, prenom}} pour une liste d'ids salarie."""
    ids = {i for i in ids if i}
    if not ids:
        return {}
    db = get_pg_connection("rh")
    ids_sql = ",".join(str(i) for i in ids)
    rows = db.query(
        f"""SELECT id_salarie, nom, prenom FROM pgt_salarie
        WHERE id_salarie IN ({ids_sql})"""
    )
    out: dict[int, dict] = {}
    for r in rows:
        sid = _clean_id(_to_int(r.get("id_salarie")))
        if sid:
            out[sid] = {
                "nom": (r.get("nom") or "").strip(),
                "prenom": (r.get("prenom") or "").strip(),
            }
    return out


def search_organigrammes(q: str, limit: int = 30) -> list[dict]:
    """Recherche d'équipes (organigramme) par Lib_ORGA. Base rh."""
    search = (q or "").strip()
    if not search:
        return []
    db = get_pg_connection("rh")
    rows = db.query(
        f"""SELECT idorganigramme, lib_orga
        FROM pgt_organigramme
        WHERE LOWER(lib_orga) LIKE LOWER(?)
        ORDER BY lib_orga
        LIMIT {int(limit)}""",
        (f"%{search}%",),
    )
    out: list[dict] = []
    for r in rows:
        oid = _clean_id(_to_int(r.get("idorganigramme")))
        if oid:
            out.append({
                "id_organigramme": str(oid),
                "lib_orga": (r.get("lib_orga") or "").strip(),
            })
    return out


def get_organigramme_lib(id_orga: int) -> str:
    """Lib_ORGA d'une équipe (base rh)."""
    if not id_orga:
        return ""
    try:
        db = get_pg_connection("rh")
        r = db.query_one(
            "SELECT idorganigramme, lib_orga FROM pgt_organigramme "
            "WHERE idorganigramme = ?",
            (int(id_orga),),
        )
        return ((r.get("lib_orga") if r else "") or "").strip()
    except Exception:
        return ""


def salarie_infos_batch(ids: set[int]) -> dict[int, dict]:
    """{id: {nom, prenom, date_embauche(ISO), lib_societe}} pour une liste
    d'IDSalarie. Multi-embauche → priorité EnActivité=1. Base rh.
    """
    ids = {i for i in ids if i}
    if not ids:
        return {}
    db = get_pg_connection("rh")
    ids_sql = ",".join(str(i) for i in ids)
    out: dict[int, dict] = {}
    try:
        for r in db.query(
            f"SELECT id_salarie, nom, prenom FROM pgt_salarie "
            f"WHERE id_salarie IN ({ids_sql})"
        ):
            sid = _clean_id(_to_int(r.get("id_salarie")))
            if sid:
                out[sid] = {
                    "nom": (r.get("nom") or "").strip(),
                    "prenom": (r.get("prenom") or "").strip(),
                    "date_embauche": "",
                    "lib_societe": "",
                }
    except Exception:
        return out

    emb: dict[int, dict] = {}
    try:
        for r in db.query(
            f"SELECT id_salarie, date_debut, en_activite, id_ste "
            f"FROM pgt_salarie_embauche WHERE id_salarie IN ({ids_sql})"
        ):
            sid = _clean_id(_to_int(r.get("id_salarie")))
            if not sid:
                continue
            actif = bool(r.get("en_activite"))
            prev = emb.get(sid)
            if prev is None or (actif and not prev["actif"]):
                emb[sid] = {
                    "date_debut": date_only_to_iso(r.get("date_debut")),
                    "id_ste": _clean_id(_to_int(r.get("id_ste"))),
                    "actif": actif,
                }
    except Exception:
        emb = {}

    societes: dict[int, str] = {}
    try:
        for r in db.query("SELECT id_ste, rs_interne FROM pgt_societe"):
            stid = _clean_id(_to_int(r.get("id_ste")))
            if stid:
                societes[stid] = (r.get("rs_interne") or "").strip()
    except Exception:
        societes = {}

    for sid, info in out.items():
        e = emb.get(sid, {})
        info["date_embauche"] = e.get("date_debut", "")
        info["lib_societe"] = societes.get(e.get("id_ste", 0), "")
    return out


def search_salaries(q: str, limit: int = 30) -> list[dict]:
    """Recherche de salariés par début de NOM (équivalent
    Fen_RechercheNomSalarié / ReqListeSalarie_ByDebutNom).

    Fidèle au WinDev : liste TOUS les salariés (actifs ou non) dont le nom
    commence par `q` (NOM stocké en MAJ → q en MAJ), enrichi du sous-
    ensemble affiché par VérifInfo() : poste, société, date d'embauche,
    "en activité" (vert) / "plus dans les effectifs" (rouge).

    Sous-ensemble ciblé de DonneInfoSalarié (pas la structure complète :
    mutuelle/orga/photo/cooptation hors scope picker). 4 requêtes base rh.
    """
    search = (q or "").strip().upper()
    if not search:
        return []
    db = get_pg_connection("rh")
    base = db.query(
        f"""SELECT DISTINCT s.id_salarie, s.nom, s.prenom
        FROM pgt_salarie s
        WHERE s.nom LIKE ?
        ORDER BY s.nom, s.prenom
        LIMIT {int(limit)}""",
        (f"{search}%",),
    )
    ids = [
        _clean_id(_to_int(r.get("id_salarie")))
        for r in base
        if _clean_id(_to_int(r.get("id_salarie")))
    ]
    if not ids:
        return []
    ids_sql = ",".join(str(i) for i in ids)

    # salarie_embauche : multi-embauche possible → priorité en_activite=TRUE.
    emb_by_id: dict[int, dict] = {}
    try:
        emb_rows = db.query(
            f"""SELECT id_salarie, date_debut, en_activite, id_type_poste, id_ste
            FROM pgt_salarie_embauche
            WHERE id_salarie IN ({ids_sql})"""
        )
        for r in emb_rows:
            sid = _clean_id(_to_int(r.get("id_salarie")))
            if not sid:
                continue
            actif = bool(r.get("en_activite"))
            prev = emb_by_id.get(sid)
            if prev is None or (actif and not prev["actif"]):
                emb_by_id[sid] = {
                    "date_debut": date_only_to_iso(r.get("date_debut")),
                    "actif": actif,
                    "id_poste": _clean_id(_to_int(r.get("id_type_poste"))),
                    "id_ste": _clean_id(_to_int(r.get("id_ste"))),
                }
    except Exception:
        emb_by_id = {}

    poste_ids = {e["id_poste"] for e in emb_by_id.values() if e.get("id_poste")}
    postes: dict[int, str] = {}
    if poste_ids:
        try:
            p_sql = ",".join(str(i) for i in poste_ids)
            for r in db.query(
                f"SELECT id_type_poste, lib_poste FROM pgt_type_poste "
                f"WHERE id_type_poste IN ({p_sql})"
            ):
                pid = _clean_id(_to_int(r.get("id_type_poste")))
                if pid:
                    postes[pid] = (r.get("lib_poste") or "").strip()
        except Exception:
            postes = {}

    societes: dict[int, str] = {}
    try:
        for r in db.query("SELECT id_ste, rs_interne FROM pgt_societe"):
            stid = _clean_id(_to_int(r.get("id_ste")))
            if stid:
                societes[stid] = (r.get("rs_interne") or "").strip()
    except Exception:
        societes = {}

    out: list[dict] = []
    for r in base:
        sid = _clean_id(_to_int(r.get("id_salarie")))
        if not sid:
            continue
        e = emb_by_id.get(sid, {})
        out.append({
            "id_salarie": str(sid),
            "nom": (r.get("nom") or "").strip(),
            "prenom": (r.get("prenom") or "").strip(),
            "poste": postes.get(e.get("id_poste", 0), ""),
            "lib_societe": societes.get(e.get("id_ste", 0), ""),
            "date_embauche": e.get("date_debut", ""),
            "actif": e.get("actif", False),
        })
    return out


# ---------------------------------------------------------------
# Fen_TicketContenu — détail + saveTicket + historique
# ---------------------------------------------------------------

def get_lib_type_demande(id_type: int) -> str:
    """Lib_TypeDemande (mémo) d'un type — fetch isolé."""
    try:
        db = get_pg_connection("ticket")
        r = db.query_one(
            "SELECT lib_type_demande FROM pgt_tk_type_demande WHERE id_tk_type_demande = ?",
            (int(id_type),),
        )
        return ((r.get("lib_type_demande") if r else "") or "").strip()
    except Exception:
        return ""


def load_ticket_raw(id_ticket: int) -> dict | None:
    """Lit une ligne pgt_tk_liste (1 ticket) — mêmes champs que la liste."""
    db = get_pg_connection("ticket")
    r = db.query_one(
        """SELECT id_tk_liste, date_crea, op_crea, op_dest, service,
            id_tk_type_demande, id_tk_statut, date_report,
            cloturee, date_cloture, modif_date, modification,
            op_traitement_staff
        FROM pgt_tk_liste
        WHERE id_tk_liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        return None
    return {
        "id_ticket": _str_id(r.get("id_tk_liste")),
        "id_type_demande": _str_id(r.get("id_tk_type_demande")),
        "service": (r.get("service") or "").strip(),
        "id_statut": _to_int(r.get("id_tk_statut")),
        "date_crea": _windev_to_iso(r.get("date_crea")),
        "op_crea": _str_id(r.get("op_crea")),
        "op_dest": _str_id(r.get("op_dest")),
        "op_traitement_staff": _str_id(r.get("op_traitement_staff")),
        "cloturee": bool(r.get("cloturee")),
        "date_cloture": _windev_to_iso(r.get("date_cloture")),
        "date_report": _windev_to_iso(r.get("date_report")),
        "modif_date": _windev_to_iso(r.get("modif_date")),
    }


def apply_ouverture(id_ticket: int, user_id: int) -> dict | None:
    """Règle d'ouverture WinDev (code init Fen_TicketContenu) :
    si type ≠ 38/39 et IDTK_Statut < 2 → passe le statut à 2
    (ModifDate/ModifOP/ModifELEM='modif'). Pas d'historique sur ce passage.
    """
    raw = load_ticket_raw(id_ticket)
    if not raw:
        return None
    id_type = int(raw["id_type_demande"]) if raw["id_type_demande"].isdigit() else 0
    if id_type not in (38, 39) and raw["id_statut"] < 2:
        db = get_pg_connection("ticket")
        db.query(
            """UPDATE pgt_tk_liste
            SET id_tk_statut = 2, modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_tk_liste = ?""",
            (int(user_id), int(id_ticket)),
        )
        raw["id_statut"] = 2
    return raw


def maj_op_traitement_ticket(id_ticket: int, id_cial: int) -> None:
    """Transposition MajOpTraitementTicket (procédure globale WinDev) :
    UPDATE pgt_tk_liste SET op_traitement_staff = user, modif_date = NOW().
    Appelée par les FI_* après enregistrement.
    """
    db = get_pg_connection("ticket")
    db.query(
        """UPDATE pgt_tk_liste
        SET op_traitement_staff = ?, modif_date = NOW()
        WHERE id_tk_liste = ?""",
        (int(id_cial), int(id_ticket)),
    )


def date_only_to_iso(v) -> str:
    """Rubrique HFSQL 'Date' (AAAAMMJJ) → ISO 'YYYY-MM-DD' (vide si nul)."""
    s = "".join(c for c in str(v or "") if c.isdigit())
    if len(s) < 8:
        return ""
    if s[:8] == "00000000":
        return ""
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"


def iso_to_date_only(v) -> str:
    """ISO 'YYYY-MM-DD' (ou vide) → AAAAMMJJ pour rubrique HFSQL 'Date'."""
    s = "".join(c for c in str(v or "") if c.isdigit())
    return s[:8] if len(s) >= 8 else ""


_RTF_TOKEN = re.compile(
    r"\\([a-z]{1,32})(-?\d{1,10})?[ ]?|\\'([0-9a-fA-F]{2})|\\([^a-z])|([{}])"
    r"|[\r\n]+|(.)",
    re.IGNORECASE,
)
_RTF_DESTINATIONS = {
    "fonttbl", "colortbl", "stylesheet", "generator", "info", "pict",
    "object", "themedata", "colorschememapping", "latentstyles",
    "datastore", "nonshppict",
}
_RTF_SPECIALS = {
    "par": "\n", "sect": "\n", "line": "\n", "tab": "\t",
    "emdash": "—", "endash": "–", "lquote": "‘",
    "rquote": "’", "ldblquote": "“", "rdblquote": "”",
    "bullet": "•",
}


def rtf_to_text(text: str) -> str:
    """Extrait le texte brut d'un mémo « texte enrichi » WinDev (RTF).

    Les mémos saisis via un champ RichEdit WinDev sont stockés en RTF
    (`{\\rtf1\\ansi...}`). Renvoie la chaîne telle quelle si ce n'est pas
    du RTF (mémos texte simples). Décode les `\\'XX` en cp1252.
    """
    if not text:
        return ""
    if "\\rtf" not in text[:20]:
        return text.strip()
    stack: list[tuple[int, bool]] = []
    ignorable = False
    ucskip = 1
    curskip = 0
    out: list[str] = []
    for m in _RTF_TOKEN.finditer(text):
        word, arg, hexa, char, brace, tchar = m.groups()
        if brace:
            if brace == "{":
                stack.append((ucskip, ignorable))
            elif stack:
                ucskip, ignorable = stack.pop()
        elif char:
            if char == "~":
                out.append(" ")
            elif char in "{}\\":
                out.append(char)
            elif char == "*":
                ignorable = True
        elif word:
            if word in _RTF_DESTINATIONS:
                ignorable = True
            elif ignorable:
                continue
            elif word in _RTF_SPECIALS:
                out.append(_RTF_SPECIALS[word])
            elif word == "uc":
                ucskip = int(arg) if arg else 1
            elif word == "u":
                c = int(arg or 0)
                if c < 0:
                    c += 65536
                out.append(chr(c))
                curskip = ucskip
        elif hexa:
            if not ignorable:
                if curskip > 0:
                    curskip -= 1
                else:
                    out.append(bytes([int(hexa, 16)]).decode("cp1252", "replace"))
        elif tchar:
            if not ignorable:
                if curskip > 0:
                    curskip -= 1
                else:
                    out.append(tchar)
    return "".join(out).strip()


def ajout_histo_tk(id_ticket: int, id_statut: int, id_cial: int) -> None:
    """Ajoute une ligne pgt_tk_histo (transposition AjoutHistoTK globale)."""
    new_id = int(_now_windev())  # idEntierDateHeureSys() : YYYYMMDDHHMMSSmmm
    db = get_pg_connection("ticket")
    db.query(
        """INSERT INTO pgt_tk_histo
        (id_tk_histo, id_tk_liste, operateur, date_histo, id_tk_statut,
         modif_date, modif_elem, modif_op)
        VALUES (?, ?, ?, NOW(), ?, NOW(), 'new', ?)""",
        (new_id, int(id_ticket), int(id_cial), int(id_statut), int(id_cial)),
    )


def save_ticket_infos(
    id_ticket: int,
    id_statut: int,
    op_dest: str,
    op_traitement_staff: str,
    cloturee: bool,
    date_cloture: str,
    user_id: int,
    prendre_en_charge: bool = False,
) -> dict:
    """Transposition de saveTicket() : UPDATE TK_Liste + historique si le
    statut a changé. Renvoie {ok, closed}.
    """
    raw = load_ticket_raw(id_ticket)
    if not raw:
        return {"ok": False, "closed": False}
    old_statut = raw["id_statut"]

    sets = ["id_tk_statut = ?", "modif_op = ?", "modif_date = NOW()", "modif_elem = 'modif'"]
    params: list = [int(id_statut), int(user_id)]
    if op_dest and str(op_dest).isdigit():
        sets.append("op_dest = ?")
        params.append(int(op_dest))
    if prendre_en_charge:
        sets.append("op_traitement_staff = ?")
        params.append(int(user_id))
    elif op_traitement_staff and str(op_traitement_staff).isdigit():
        sets.append("op_traitement_staff = ?")
        params.append(int(op_traitement_staff))
    if cloturee:
        # date_cloture : 'YYYY-MM-DD' fourni, sinon NOW()
        dc_iso = (date_cloture or "").strip()
        if len(dc_iso) >= 10 and dc_iso[4] == "-":
            sets.append("cloturee = TRUE")
            sets.append("date_cloture = ?")
            params.append(dc_iso[:10])
        else:
            sets.append("cloturee = TRUE")
            sets.append("date_cloture = NOW()")
    else:
        sets.append("cloturee = FALSE")
    params.append(int(id_ticket))

    db = get_pg_connection("ticket")
    db.query(
        f"UPDATE pgt_tk_liste SET {', '.join(sets)} WHERE id_tk_liste = ?",
        tuple(params),
    )
    if int(id_statut) != int(old_statut):
        ajout_histo_tk(id_ticket, id_statut, user_id)
    return {"ok": True, "closed": bool(cloturee)}
