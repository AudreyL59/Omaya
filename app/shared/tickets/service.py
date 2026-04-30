"""Service Tickets — accès aux tables TK_Liste / TK_TypeDemande / TK_Statut."""

from __future__ import annotations

import base64
import struct
import time
from datetime import datetime

from app.core.database import get_connection


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


def _windev_to_iso(s: str) -> str:
    """Format WinDev (YYYYMMDDHHMMSS[mmm]) → ISO 'YYYY-MM-DD HH:MM:SS'.

    Si la chaîne est déjà ISO ou un format reconnaissable, on la renvoie telle
    quelle (juste tronquée à 19 chars max).
    """
    if not s:
        return ""
    s = str(s).strip()
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
    db = get_connection("ticket")
    rows = db.query(
        f"""SELECT IDTK_TypeDemande, {droit_field}
        FROM TK_TypeDemande
        WHERE ModifELEM <> 'suppr'"""
    )
    droits_set = set(droits or [])
    out: set[int] = set()
    for r in rows:
        droit = (r.get(droit_field) or "").strip()
        if droit and droit not in droits_set:
            continue
        idt = _clean_id(_to_int(r.get("IDTK_TypeDemande")))
        if idt:
            out.add(idt)
    _type_ids_cache[cache_key] = (time.time(), out)
    return out


def list_types_par_droit(droits: list[str], droit_field: str) -> list[dict]:
    """Liste les types de demande accessibles selon les droits du user.

    droit_field : "DroitAccès" pour ADM, "DroitAccèsVend" pour Vendeur.
                  Si vide → un type sans droit configuré est visible
                  (sinon il faut que le code droit soit dans `droits`).

    Lib_TypeDemande est un mémo texte → fetch séparé pour éviter la
    troncature du bridge HFSQL sur les SELECT multi-colonnes.

    Cache TTL 60s — la table TK_TypeDemande change rarement.

    Retour trié par Service puis Lib_TypeDemande.
    """
    cache_key = (frozenset(droits or []), droit_field)
    cached = _cache_get(_types_cache, cache_key)
    if cached is not None:
        return cached
    db = get_connection("ticket")

    # 1. SELECT des champs simples (pas de mémo). Le champ droit est sélectionné
    #    directement (sans alias) — le bridge HFSQL ne supporte pas les
    #    "alias avec accent" sur certaines configs.
    rows = db.query(
        f"""SELECT IDTK_TypeDemande, Service, {droit_field}
        FROM TK_TypeDemande
        WHERE ModifELEM <> 'suppr'
        ORDER BY Service"""
    )
    droits_set = set(droits or [])
    visible: list[tuple[int, str, str]] = []  # (id, service, droit)
    for r in rows:
        # Le bridge peut renvoyer la clé droit_field telle quelle ou normalisée
        droit = (r.get(droit_field) or "").strip()
        if droit and droit not in droits_set:
            continue
        idt = _clean_id(_to_int(r.get("IDTK_TypeDemande")))
        if not idt:
            continue
        visible.append((idt, (r.get("Service") or "").strip(), droit))

    if not visible:
        return []

    # 2. Fetch séparé du mémo Lib_TypeDemande (1 SELECT par type — peu coûteux,
    #    une dizaine de types max en pratique). On garde l'ordre Service / Lib.
    libs: dict[int, str] = {}
    for idt, _svc, _dr in visible:
        try:
            r = db.query_one(
                "SELECT Lib_TypeDemande FROM TK_TypeDemande WHERE IDTK_TypeDemande = ?",
                (idt,),
            )
            libs[idt] = (r.get("Lib_TypeDemande") if r else "" or "").strip()
        except Exception:
            libs[idt] = ""

    out: list[dict] = []
    for idt, svc, _dr in visible:
        out.append({
            "id_type_demande": str(idt),
            "service": svc,
            "lib_type_demande": libs.get(idt, ""),
            "icone_data_url": "",  # mémo binaire — sera ajouté plus tard
        })
    out.sort(key=lambda x: (x["service"], x["lib_type_demande"].lower()))
    _types_cache[cache_key] = (time.time(), out)
    return out


def _icone_to_data_url(blob) -> str:
    """Convertit le mémo binaire en data: URL si possible (PNG/JPEG/GIF)."""
    if not blob:
        return ""
    raw = blob if isinstance(blob, bytes) else None
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
    db = get_connection("ticket")
    rows = db.query(
        """SELECT IDTK_Statut, Lib_Statut FROM TK_Statut
        WHERE ModifELEM <> 'suppr'
        ORDER BY IDTK_Statut ASC"""
    )
    out = [
        {
            "id_statut": _to_int(r.get("IDTK_Statut")),
            "lib_statut": (r.get("Lib_Statut") or "").strip(),
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
    # Bornes WinDev : si pas de date fournie, on prend 2001-01-01 → 3061-01-01
    # (au format compact YYYYMMDDHHMMSSmmm 17 chars).
    if not date_du:
        date_du = "20010101000000000"
    if not date_au:
        date_au = "30610101000000000"

    db = get_connection("ticket")
    # NOTE : le bridge HFSQL ne supporte pas les colonnes accentuées entre
    # guillemets ni les alias avec accent. On utilise donc Cloturée
    # (sans quotes) dans le SELECT/WHERE et on lit la colonne via
    # r.get("Cloturée") côté Python.
    rows = db.query(
        f"""SELECT TOP {int(limit)}
            IDTK_Liste, DATECREA, OPCREA, OPDEST, Service,
            IDTK_TypeDemande, IDTK_Statut, DateReport,
            Cloturée, DateCloture,
            ModifDate, modification,
            OpTraitementStaff
        FROM TK_Liste
        WHERE IDTK_TypeDemande = ?
          AND ModifELEM NOT LIKE '%suppr%'
          AND Cloturée = ?
          AND DATECREA BETWEEN ? AND ?
          AND IDTK_Statut <> 28
        ORDER BY IDTK_Statut ASC, DATECREA DESC""",
        (int(id_type_demande), 1 if cloturee else 0, date_du, date_au),
    )
    out: list[dict] = []
    for r in rows:
        out.append({
            "id_ticket": _str_id(r.get("IDTK_Liste")),
            "id_type_demande": _str_id(r.get("IDTK_TypeDemande")),
            "service": (r.get("Service") or "").strip(),
            "id_statut": _to_int(r.get("IDTK_Statut")),
            "date_crea": _windev_to_iso(r.get("DATECREA")),
            "op_crea": _str_id(r.get("OPCREA")),
            "op_dest": _str_id(r.get("OPDEST")),
            "op_traitement_staff": _str_id(r.get("OpTraitementStaff")),
            "cloturee": bool(r.get("Cloturée")),
            "date_cloture": _windev_to_iso(r.get("DateCloture")),
            "date_report": _windev_to_iso(r.get("DateReport")),
            "modif_date": _windev_to_iso(r.get("ModifDate")),
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
    if not cursor_compact:
        cursor_compact = "00000000000000000"
    if not date_du:
        date_du = "20010101000000000"
    if not date_au:
        date_au = "30610101000000000"
    db = get_connection("ticket")
    rows = db.query(
        f"""SELECT TOP {int(limit)}
            IDTK_Liste, DATECREA, OPCREA, OPDEST, Service,
            IDTK_TypeDemande, IDTK_Statut, DateReport,
            Cloturée, DateCloture, ModifDate, modification,
            OpTraitementStaff
        FROM TK_Liste
        WHERE IDTK_TypeDemande = ?
          AND ModifELEM NOT LIKE '%suppr%'
          AND Cloturée = ?
          AND ModifDate > ?
          AND DATECREA BETWEEN ? AND ?
          AND IDTK_Statut <> 28
        ORDER BY ModifDate DESC""",
        (int(id_type_demande), 1 if cloturee else 0, cursor_compact, date_du, date_au),
    )
    out: list[dict] = []
    for r in rows:
        md_raw = str(r.get("ModifDate") or "").strip()
        dc_raw = str(r.get("DATECREA") or "").strip()
        out.append({
            "id_ticket": _str_id(r.get("IDTK_Liste")),
            "id_type_demande": _str_id(r.get("IDTK_TypeDemande")),
            "service": (r.get("Service") or "").strip(),
            "id_statut": _to_int(r.get("IDTK_Statut")),
            "date_crea": _windev_to_iso(dc_raw),
            "op_crea": _str_id(r.get("OPCREA")),
            "op_dest": _str_id(r.get("OPDEST")),
            "op_traitement_staff": _str_id(r.get("OpTraitementStaff")),
            "cloturee": bool(r.get("Cloturée")),
            "date_cloture": _windev_to_iso(r.get("DateCloture")),
            "date_report": _windev_to_iso(r.get("DateReport")),
            "modif_date": _windev_to_iso(md_raw),
            "modification": bool(r.get("modification")),
            "_modif_compact": md_raw,
            "_date_crea_compact": dc_raw,
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
    db = get_connection("rh")
    ids_sql = ",".join(str(i) for i in ids)
    rows = db.query(
        f"""SELECT IDSalarie, NOM, PRENOM FROM salarie
        WHERE IDSalarie IN ({ids_sql})"""
    )
    out: dict[int, dict] = {}
    for r in rows:
        sid = _clean_id(_to_int(r.get("IDSalarie")))
        if sid:
            out[sid] = {
                "nom": (r.get("NOM") or "").strip(),
                "prenom": (r.get("PRENOM") or "").strip(),
            }
    return out
