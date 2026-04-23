"""
Worker Python pour l'extraction production.

Tourne en service NSSM séparé de l'API (OmayaProductionWorker).
Pop les jobs en statut 'pending' dans ProductionExtractionJob (Bdd_Omaya_Divers),
exécute l'extraction, stocke le résultat Parquet, MAJ le statut.

Polling 2s, 1 seul job à la fois (séquentiel pour ne pas saturer HFSQL).

Usage (dev) :
    .venv\\Scripts\\python.exe worker_production.py

En production (NSSM) :
    deploy\\install-worker.ps1
"""

import logging
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# Permet l'import du package app quand lancé à la racine
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import (
    PRODUCTION_EXTRACTS_DIR,
    PRODUCTION_EXTRACTS_RETENTION_DAYS,
)
from app.core.database import get_connection
from app.intranets.vendeur.services.production import _new_id, _now_windev
from app.intranets.vendeur.services.production_extraction import (
    extract_job_to_parquet,
)

# Logging
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "worker-production.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("prod-worker")

POLL_INTERVAL_S = 2


# ============================================================
# Accès table ProductionExtractionJob
# ============================================================

def _pop_next_pending_job() -> dict | None:
    """
    Prend le plus ancien job 'pending', le passe en 'running', retourne ses infos.
    On fait un UPDATE ... WHERE Statut='pending' pour éviter les doublons.
    """
    db = get_connection("divers")

    # 1. Trouver l'id + infos simples du plus ancien pending
    # IMPORTANT : ne PAS inclure le mémo ParamsJSON dans ce SELECT ;
    # le bridge WinDev tronque les mémos dans les SELECT multi-colonnes.
    rows = db.query(
        """SELECT TOP 1 IDProductionExtractionJob, IDSalarieUser, Titre
        FROM ProductionExtractionJob
        WHERE Statut = 'pending'
          AND ModifELEM <> 'suppr'
        ORDER BY DateCrea ASC"""
    )
    if not rows:
        return None

    job = rows[0]
    id_job = _to_int(job.get("IDProductionExtractionJob"))
    id_user = _to_int(job.get("IDSalarieUser"))
    titre = job.get("Titre") or ""
    now = _now_windev()

    # 2. Fetch séparé du mémo ParamsJSON (SELECT 1 seule colonne = mémo préservé)
    params_rows = db.query(
        """SELECT ParamsJSON FROM ProductionExtractionJob
        WHERE IDProductionExtractionJob = ?""",
        (id_job,),
    )
    params_json = (params_rows[0].get("ParamsJSON") if params_rows else "") or ""

    # 3. Tenter de le passer en 'running' (UPDATE conditionné sur le statut)
    db.query(
        """UPDATE ProductionExtractionJob
        SET Statut = 'running',
            DateDebutTrait = ?,
            ProgressionPct = 0,
            ProgressionMsg = 'Démarrage',
            ModifDate = ?,
            ModifELEM = ''
        WHERE IDProductionExtractionJob = ?
          AND Statut = 'pending'""",
        (now, now, id_job),
    )

    return {
        "id_job": id_job,
        "id_salarie_user": id_user,
        "params_json": params_json,
        "titre": titre,
    }


def _update_progress(id_job: int, pct: int, msg: str) -> None:
    """Met à jour la progression visible pendant le traitement."""
    db = get_connection("divers")
    now = _now_windev()
    try:
        db.query(
            """UPDATE ProductionExtractionJob
            SET ProgressionPct = ?, ProgressionMsg = ?, ModifDate = ?
            WHERE IDProductionExtractionJob = ?""",
            (min(max(pct, 0), 100), msg[:100], now, id_job),
        )
    except Exception as e:
        log.warning("progress update failed for job %s: %s", id_job, e)


def _complete_job(
    id_job: int,
    path_resultat: str,
    nb_lignes: int,
    duree_s: int,
) -> None:
    db = get_connection("divers")
    now = _now_windev()
    db.query(
        """UPDATE ProductionExtractionJob
        SET Statut = 'done',
            DateFinTrait = ?,
            ProgressionPct = 100,
            ProgressionMsg = 'Terminé',
            NbLignes = ?,
            DureeS = ?,
            PathResultat = ?,
            MessageErreur = '',
            ModifDate = ?
        WHERE IDProductionExtractionJob = ?""",
        (now, nb_lignes, duree_s, path_resultat, now, id_job),
    )


def _fail_job(id_job: int, message: str) -> None:
    """
    Marque un job en erreur. On splitte en 2 UPDATEs pour que le mémo
    MessageErreur (qui contient souvent un traceback avec des " et { )
    ne casse pas l'UPDATE principal — le mémo est encodé en base64.
    """
    import base64
    db = get_connection("divers")
    now = _now_windev()

    # 1. UPDATE des champs simples (pas de mémo ici)
    try:
        db.query(
            """UPDATE ProductionExtractionJob
            SET Statut = 'error',
                DateFinTrait = ?,
                ModifDate = ?
            WHERE IDProductionExtractionJob = ?""",
            (now, now, id_job),
        )
    except Exception as e:
        log.error("impossible de marquer le job %s en error : %s", id_job, e)
        return

    # 2. UPDATE du mémo MessageErreur (base64 pour éviter les " et { )
    try:
        msg = (message or "")[:65000]
        msg_b64 = base64.b64encode(msg.encode("utf-8")).decode("ascii")
        db.query(
            """UPDATE ProductionExtractionJob
            SET MessageErreur = ?
            WHERE IDProductionExtractionJob = ?""",
            (msg_b64, id_job),
        )
    except Exception as e:
        log.warning("update MessageErreur du job %s a echoue : %s", id_job, e)


# ============================================================
# Purge des fichiers anciens (au démarrage)
# ============================================================

def _purge_old_extracts() -> None:
    """Supprime les fichiers Parquet plus vieux que PRODUCTION_EXTRACTS_RETENTION_DAYS."""
    if not PRODUCTION_EXTRACTS_DIR.exists():
        return
    cutoff = datetime.now() - timedelta(days=PRODUCTION_EXTRACTS_RETENTION_DAYS)
    n_deleted = 0
    try:
        for user_dir in PRODUCTION_EXTRACTS_DIR.iterdir():
            if not user_dir.is_dir():
                continue
            for f in user_dir.iterdir():
                if not f.is_file():
                    continue
                try:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    if mtime < cutoff:
                        f.unlink()
                        n_deleted += 1
                except Exception:
                    pass
    except Exception as e:
        log.warning("purge failed: %s", e)
    if n_deleted:
        log.info("purged %s old extracts", n_deleted)


# ============================================================
# Boucle principale
# ============================================================

def _to_int(v) -> int:
    if v is None or v == "":
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    try:
        return int(str(v))
    except Exception:
        return 0


def main() -> None:
    log.info("Worker production démarré")
    log.info("Dossier extractions : %s", PRODUCTION_EXTRACTS_DIR)
    log.info("Rétention : %s jours", PRODUCTION_EXTRACTS_RETENTION_DAYS)

    PRODUCTION_EXTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    _purge_old_extracts()

    while True:
        try:
            job = _pop_next_pending_job()
        except Exception as e:
            log.error("erreur pop_next_pending_job: %s", e)
            time.sleep(POLL_INTERVAL_S)
            continue

        if not job:
            time.sleep(POLL_INTERVAL_S)
            continue

        id_job = job["id_job"]
        log.info("▶ job %s : %s", id_job, job["titre"])

        try:
            import base64
            import json
            raw = (job["params_json"] or "").strip()
            params = {}
            if not raw:
                raise ValueError("ParamsJSON vide (memo non stocke ou tronque)")
            # Compat : d'abord base64 (format utilisé par l'API), sinon JSON brut
            try:
                decoded = base64.b64decode(raw).decode("utf-8")
                params = json.loads(decoded)
            except Exception:
                params = json.loads(raw)
            if not params.get("date_du") or not params.get("date_au"):
                raise ValueError(
                    f"ParamsJSON sans date_du/date_au : {list(params.keys())}"
                )
        except Exception as e:
            _fail_job(id_job, f"ParamsJSON invalide : {e} | raw len={len(job.get('params_json') or '')}")
            log.error("x job %s : ParamsJSON invalide : %s", id_job, e)
            continue

        try:
            result = extract_job_to_parquet(
                id_job=id_job,
                id_salarie_user=job["id_salarie_user"],
                params=params,
                progress_cb=lambda p, m: _update_progress(id_job, p, m),
            )
            _complete_job(
                id_job=id_job,
                path_resultat=result["path"],
                nb_lignes=result["nb_lignes"],
                duree_s=result["duree_s"],
            )
            log.info(
                "✔ job %s : %s lignes en %ss",
                id_job, result["nb_lignes"], result["duree_s"],
            )
        except Exception as e:
            tb = traceback.format_exc()
            _fail_job(id_job, f"{e}\n\n{tb}")
            log.error("✗ job %s : %s\n%s", id_job, e, tb)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Worker arrêté (Ctrl+C)")
        sys.exit(0)
