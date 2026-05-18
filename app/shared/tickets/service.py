"""Service Tickets — accès aux tables TK_Liste / TK_TypeDemande / TK_Statut."""

from __future__ import annotations

import base64
import struct
import time
from concurrent.futures import ThreadPoolExecutor
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

    # 2. Fetch séparé des mémos Lib_TypeDemande (texte) et icone (binaire) :
    #    1 SELECT par mémo et par type (le bridge tronque les mémos en
    #    multi-colonnes). Parallélisé car chaque query ≈ 400 ms.
    def _fetch_lib(idt: int) -> tuple[int, str]:
        try:
            db_t = get_connection("ticket")
            r = db_t.query_one(
                "SELECT Lib_TypeDemande FROM TK_TypeDemande WHERE IDTK_TypeDemande = ?",
                (idt,),
            )
            return idt, ((r.get("Lib_TypeDemande") if r else "") or "").strip()
        except Exception:
            return idt, ""

    def _fetch_icone(idt: int) -> tuple[int, str]:
        try:
            db_t = get_connection("ticket")
            r = db_t.query_one(
                "SELECT icone FROM TK_TypeDemande WHERE IDTK_TypeDemande = ?",
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
    db = get_connection("rh")
    base = db.query(
        f"""SELECT DISTINCT TOP {int(limit)} s.IDSalarie, s.NOM, s.PRENOM
        FROM salarie s
        WHERE s.NOM LIKE ?
        ORDER BY s.NOM, s.PRENOM""",
        (f"{search}%",),
    )
    ids = [
        _clean_id(_to_int(r.get("IDSalarie")))
        for r in base
        if _clean_id(_to_int(r.get("IDSalarie")))
    ]
    if not ids:
        return []
    ids_sql = ",".join(str(i) for i in ids)

    # salarie_embauche : colonnes accentuées → SELECT brut sans alias.
    # Multi-embauche possible → on garde en priorité la ligne EnActivité=1.
    emb_by_id: dict[int, dict] = {}
    try:
        emb_rows = db.query(
            f"""SELECT IDSalarie, DateDébut, EnActivité, IdTypePoste, IdSte
            FROM salarie_embauche
            WHERE IDSalarie IN ({ids_sql})"""
        )
        for r in emb_rows:
            sid = _clean_id(_to_int(r.get("IDSalarie")))
            if not sid:
                continue
            actif = bool(r.get("EnActivité"))
            prev = emb_by_id.get(sid)
            if prev is None or (actif and not prev["actif"]):
                emb_by_id[sid] = {
                    "date_debut": _windev_to_iso(r.get("DateDébut"))[:10],
                    "actif": actif,
                    "id_poste": _clean_id(_to_int(r.get("IdTypePoste"))),
                    "id_ste": _clean_id(_to_int(r.get("IdSte"))),
                }
    except Exception:
        emb_by_id = {}

    poste_ids = {e["id_poste"] for e in emb_by_id.values() if e.get("id_poste")}
    postes: dict[int, str] = {}
    if poste_ids:
        try:
            p_sql = ",".join(str(i) for i in poste_ids)
            for r in db.query(
                f"SELECT IdTypePoste, Lib_Poste FROM TypePoste "
                f"WHERE IdTypePoste IN ({p_sql})"
            ):
                pid = _clean_id(_to_int(r.get("IdTypePoste")))
                if pid:
                    postes[pid] = (r.get("Lib_Poste") or "").strip()
        except Exception:
            postes = {}

    societes: dict[int, str] = {}
    try:
        for r in db.query("SELECT IdSte, RS_Interne FROM societe"):
            stid = _clean_id(_to_int(r.get("IdSte")))
            if stid:
                societes[stid] = (r.get("RS_Interne") or "").strip()
    except Exception:
        societes = {}

    out: list[dict] = []
    for r in base:
        sid = _clean_id(_to_int(r.get("IDSalarie")))
        if not sid:
            continue
        e = emb_by_id.get(sid, {})
        out.append({
            "id_salarie": str(sid),
            "nom": (r.get("NOM") or "").strip(),
            "prenom": (r.get("PRENOM") or "").strip(),
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
    """Lib_TypeDemande (mémo) d'un type — fetch isolé (troncature bridge)."""
    try:
        db = get_connection("ticket")
        r = db.query_one(
            "SELECT Lib_TypeDemande FROM TK_TypeDemande WHERE IDTK_TypeDemande = ?",
            (int(id_type),),
        )
        return ((r.get("Lib_TypeDemande") if r else "") or "").strip()
    except Exception:
        return ""


def load_ticket_raw(id_ticket: int) -> dict | None:
    """Lit une ligne TK_Liste (1 ticket) — mêmes champs que la liste."""
    db = get_connection("ticket")
    r = db.query_one(
        """SELECT IDTK_Liste, DATECREA, OPCREA, OPDEST, Service,
            IDTK_TypeDemande, IDTK_Statut, DateReport,
            Cloturée, DateCloture, ModifDate, modification,
            OpTraitementStaff
        FROM TK_Liste
        WHERE IDTK_Liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        return None
    return {
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
        now = _now_windev()
        db = get_connection("ticket")
        db.query(
            """UPDATE TK_Liste
            SET IDTK_Statut = 2, ModifDate = ?, ModifOP = ?, ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (now, int(user_id), int(id_ticket)),
        )
        raw["id_statut"] = 2
    return raw


def maj_op_traitement_ticket(id_ticket: int, id_cial: int) -> None:
    """Transposition MajOpTraitementTicket (procédure globale WinDev) :
    UPDATE TK_Liste SET OpTraitementStaff = user, ModifDate = now.
    Appelée par les FI_* après enregistrement.
    """
    db = get_connection("ticket")
    db.query(
        """UPDATE TK_Liste
        SET OpTraitementStaff = ?, ModifDate = ?
        WHERE IDTK_Liste = ?""",
        (int(id_cial), _now_windev(), int(id_ticket)),
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


def ajout_histo_tk(id_ticket: int, id_statut: int, id_cial: int) -> None:
    """Ajoute une ligne TK_Histo (transposition AjoutHistoTK globale)."""
    now = _now_windev()
    new_id = int(now)  # idEntierDateHeureSys()
    db = get_connection("ticket")
    db.query(
        """INSERT INTO TK_Histo
        (IDTK_Histo, IDTK_Liste, operateur, dateHisto, IDTK_Statut,
         ModifDate, ModifELEM, ModifOP)
        VALUES (?, ?, ?, ?, ?, ?, 'new', ?)""",
        (new_id, int(id_ticket), int(id_cial), now, int(id_statut), now, int(id_cial)),
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
    now = _now_windev()

    sets = ["IDTK_Statut = ?", "ModifOP = ?", "ModifDate = ?", "ModifELEM = 'modif'"]
    params: list = [int(id_statut), int(user_id), now]
    if op_dest and str(op_dest).isdigit():
        sets.append("OPDEST = ?")
        params.append(int(op_dest))
    if prendre_en_charge:
        # "Je m'occupe de ce ticket" : OpTraitementStaff = user courant
        sets.append("OpTraitementStaff = ?")
        params.append(int(user_id))
    elif op_traitement_staff and str(op_traitement_staff).isdigit():
        sets.append("OpTraitementStaff = ?")
        params.append(int(op_traitement_staff))
    if cloturee:
        dc = (date_cloture or "").replace("-", "")[:8]
        dc_wd = f"{dc}000000000" if len(dc) == 8 and dc.isdigit() else now
        sets.append("Cloturée = 1")
        sets.append("DateCloture = ?")
        params.append(dc_wd)
    else:
        sets.append("Cloturée = 0")
    params.append(int(id_ticket))

    db = get_connection("ticket")
    db.query(
        f"UPDATE TK_Liste SET {', '.join(sets)} WHERE IDTK_Liste = ?",
        tuple(params),
    )
    if int(id_statut) != int(old_statut):
        ajout_histo_tk(id_ticket, id_statut, user_id)
    return {"ok": True, "closed": bool(cloturee)}
