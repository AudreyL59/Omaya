"""
Service Production — gestion des jobs d'extraction (CRUD).

Table : ProductionExtractionJob dans Bdd_Omaya_Divers.

Note : l'exécution réelle de l'extraction est faite par un worker Python
séparé (voir worker_production.py) qui pop les jobs en statut 'pending'.
"""

import base64
import json
import struct
from datetime import datetime
from typing import Any

from app.core.database import get_connection


# -- Helpers ---------------------------------------------------------

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
    """Filtre les IDs corrompus (> 9e18 = max uint64 / null HFSQL)."""
    if 0 < n < 9_000_000_000_000_000_000:
        return n
    return 0


def _now_windev() -> str:
    """Format WinDev : YYYYMMDDHHMMSSmmm (17 chars)."""
    now = datetime.now()
    return now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"


def _new_id() -> int:
    return int(_now_windev())


# -- Titre auto --------------------------------------------------------

def _make_titre(params: dict, user_nom: str, user_prenom: str) -> str:
    """Génère un titre humain pour le job à partir des params.

    ASCII pur : le titre est envoyé au bridge WinDev qui reçoit argv en CP1252.
    """
    mode = {1: "Vendeur", 2: "Equipe", 3: "Reseau", 4: "Reseau Hors Distrib"}.get(
        params.get("scope", 0), "?"
    )
    du = params.get("date_du", "")
    au = params.get("date_au", "")

    def fmt(ymd: str) -> str:
        if len(ymd) == 8 and ymd.isdigit():
            return f"{ymd[6:8]}/{ymd[4:6]}/{ymd[0:4]}"
        return ymd

    periode = f"{fmt(du)}-{fmt(au)}"
    if params.get("scope") == 1 and user_nom:
        prefix = "Prod Groupe" if params.get("prod_groupe") else "Prod Perso"
        return f"{prefix} {user_nom} {user_prenom} / {periode}"
    return f"{mode} / {periode}"


# -- CRUD jobs ---------------------------------------------------------

def create_job(id_salarie_user: int, params: dict, user_nom: str, user_prenom: str) -> str:
    """Crée un job en statut 'pending'. Retourne son id en string.

    On insère d'abord les colonnes de base, puis on met à jour ParamsJSON
    séparément — le bridge a parfois du mal avec les mémos volumineux en INSERT.
    """
    db = get_connection("divers")
    id_job = _new_id()
    now = _now_windev()
    titre = _make_titre(params, user_nom, user_prenom)

    # 1. INSERT avec ParamsJSON vide (sans le mémo volumineux)
    db.query(
        """INSERT INTO ProductionExtractionJob
        (IDProductionExtractionJob, IDSalarieUser, DateCrea,
         ParamsJSON, Statut, ProgressionPct, ProgressionMsg,
         NbLignes, DureeS, PathResultat, MessageErreur, Titre,
         ModifDate, ModifOP, ModifELEM)
        VALUES (?, ?, ?, '', 'pending', 0, '',
                0, 0, '', '', ?,
                ?, ?, '')""",
        (id_job, id_salarie_user, now, titre, now, id_salarie_user),
    )

    # 2. UPDATE du mémo ParamsJSON — encodé en base64 pour éviter que les
    # guillemets doubles et accolades du JSON ne cassent le bridge HFSQL
    params_json = json.dumps(params, ensure_ascii=True)
    params_b64 = base64.b64encode(params_json.encode("utf-8")).decode("ascii")
    db.query(
        """UPDATE ProductionExtractionJob
        SET ParamsJSON = ?
        WHERE IDProductionExtractionJob = ?""",
        (params_b64, id_job),
    )
    return str(id_job)


def list_jobs(id_salarie_user: int, limit: int = 50) -> list[dict]:
    """Liste les jobs de l'utilisateur, du plus récent au plus ancien."""
    db = get_connection("divers")
    rows = db.query(
        f"""SELECT TOP {int(limit)}
            IDProductionExtractionJob, IDSalarieUser, DateCrea,
            DateDebutTrait, DateFinTrait, Statut, ProgressionPct,
            ProgressionMsg, NbLignes, DureeS, PathResultat,
            MessageErreur, Titre, ParamsJSON
        FROM ProductionExtractionJob
        WHERE IDSalarieUser = ?
          AND ModifELEM <> 'suppr'
        ORDER BY DateCrea DESC""",
        (id_salarie_user,),
    )
    return [_row_to_dict(r) for r in rows]


def get_job(id_job: int, id_salarie_user: int) -> dict | None:
    """Lit un job (vérifie qu'il appartient bien à l'utilisateur)."""
    db = get_connection("divers")
    row = db.query_one(
        """SELECT IDProductionExtractionJob, IDSalarieUser, DateCrea,
            DateDebutTrait, DateFinTrait, Statut, ProgressionPct,
            ProgressionMsg, NbLignes, DureeS, PathResultat,
            MessageErreur, Titre, ParamsJSON
        FROM ProductionExtractionJob
        WHERE IDProductionExtractionJob = ?
          AND IDSalarieUser = ?
          AND ModifELEM <> 'suppr'""",
        (id_job, id_salarie_user),
    )
    if not row:
        return None
    return _row_to_dict(row)


def delete_job(id_job: int, id_salarie_user: int) -> bool:
    """Soft-delete : ModifELEM='suppr'."""
    db = get_connection("divers")
    now = _now_windev()
    # On vérifie d'abord que le job appartient bien à l'utilisateur
    existing = db.query_one(
        """SELECT IDProductionExtractionJob FROM ProductionExtractionJob
        WHERE IDProductionExtractionJob = ?
          AND IDSalarieUser = ?
          AND ModifELEM <> 'suppr'""",
        (id_job, id_salarie_user),
    )
    if not existing:
        return False

    db.query(
        """UPDATE ProductionExtractionJob
        SET ModifELEM = 'suppr', ModifDate = ?, ModifOP = ?
        WHERE IDProductionExtractionJob = ?""",
        (now, id_salarie_user, id_job),
    )
    return True


def _row_to_dict(r: dict) -> dict:
    """Transforme une row HFSQL en dict compatible avec le schema ProductionJob."""
    params_raw = (r.get("ParamsJSON") or "").strip()
    params = None
    if params_raw:
        # Compat : d'abord essayer base64 (nouveau format), sinon JSON brut (legacy)
        try:
            decoded = base64.b64decode(params_raw).decode("utf-8")
            params = json.loads(decoded)
        except Exception:
            try:
                params = json.loads(params_raw)
            except Exception:
                params = None

    # MessageErreur peut être en base64 (stocké par le worker) ou en clair
    msg_err_raw = (r.get("MessageErreur") or "").strip()
    msg_err = msg_err_raw
    if msg_err_raw:
        try:
            msg_err = base64.b64decode(msg_err_raw).decode("utf-8")
        except Exception:
            msg_err = msg_err_raw

    return {
        "id_job": str(_clean_id(_to_int(r.get("IDProductionExtractionJob")))),
        "id_salarie_user": str(_clean_id(_to_int(r.get("IDSalarieUser")))),
        "date_crea": r.get("DateCrea") or "",
        "date_debut_trait": r.get("DateDebutTrait") or "",
        "date_fin_trait": r.get("DateFinTrait") or "",
        "statut": r.get("Statut") or "",
        "progression_pct": _to_int(r.get("ProgressionPct")),
        "progression_msg": r.get("ProgressionMsg") or "",
        "nb_lignes": _to_int(r.get("NbLignes")),
        "duree_s": _to_int(r.get("DureeS")),
        "path_resultat": r.get("PathResultat") or "",
        "message_erreur": msg_err,
        "titre": r.get("Titre") or "",
        "params": params,
    }


# -- Référentiels (pour remplir la page de sélection) ----------------

def list_partenaires() -> list[dict]:
    """Liste des partenaires disponibles (table Partenaire dans ADV)."""
    db = get_connection("adv")
    rows = db.query(
        """SELECT Lib_Partenaire, PréfixeBDD, IsActif,
            Couleur_R, Couleur_V, Couleur_B
        FROM Partenaire
        WHERE ModifELEM <> 'suppr'
          AND PréfixeBDD <> ''
        ORDER BY IsActif DESC, Lib_Partenaire ASC"""
    )
    out = []
    for r in rows:
        r_ = _to_int(r.get("Couleur_R"))
        g_ = _to_int(r.get("Couleur_V"))
        b_ = _to_int(r.get("Couleur_B"))
        out.append({
            "lib": r.get("Lib_Partenaire") or "",
            "prefix": r.get("PréfixeBDD") or "",
            "is_actif": bool(r.get("IsActif")),
            "couleur_hex": f"#{r_:02X}{g_:02X}{b_:02X}",
        })
    return out


def search_organigrammes(q: str, limit: int = 20) -> list[dict]:
    """Recherche d'orgas par libellé (pour le picker Équipe)."""
    q = (q or "").strip()
    if len(q) < 2:
        return []

    db = get_connection("rh")
    rows = db.query(
        f"""SELECT TOP {int(limit)} idorganigramme, Lib_ORGA, IdPARENT
        FROM organigramme
        WHERE ModifELEM <> 'suppr'
          AND Lib_ORGA LIKE ?
        ORDER BY Lib_ORGA ASC""",
        (f"%{q}%",),
    )

    # Charger les parents pour afficher "{Parent} → {Orga}"
    parent_ids = {_to_int(r.get("IdPARENT")) for r in rows}
    parent_ids.discard(0)
    parent_libs: dict[int, str] = {}
    if parent_ids:
        ids_sql = ",".join(str(i) for i in parent_ids)
        prows = db.query(
            f"""SELECT idorganigramme, Lib_ORGA FROM organigramme
            WHERE idorganigramme IN ({ids_sql})"""
        )
        parent_libs = {
            _to_int(p.get("idorganigramme")): p.get("Lib_ORGA") or ""
            for p in prows
        }

    out = []
    for r in rows:
        oid = _clean_id(_to_int(r.get("idorganigramme")))
        if not oid:
            continue
        pid = _to_int(r.get("IdPARENT"))
        out.append({
            "id_organigramme": str(oid),
            "lib_orga": r.get("Lib_ORGA") or "",
            "parent_lib": parent_libs.get(pid, ""),
        })
    return out


def list_types_etat() -> list[dict]:
    """Liste des types d'état (TypeEtatContrat dans ADV, table partagée)."""
    db = get_connection("adv")
    rows = db.query(
        """SELECT IDTypeEtat, LibType, Couleur_R, Couleur_V, Couleur_B
        FROM TypeEtatContrat
        WHERE ModifELEM <> 'suppr'
        ORDER BY LibType ASC"""
    )
    out = []
    for r in rows:
        r_ = _to_int(r.get("Couleur_R"))
        g_ = _to_int(r.get("Couleur_V"))
        b_ = _to_int(r.get("Couleur_B"))
        out.append({
            "id": _to_int(r.get("IDTypeEtat")),
            "lib": r.get("LibType") or "",
            "couleur_hex": f"#{r_:02X}{g_:02X}{b_:02X}",
        })
    return out
