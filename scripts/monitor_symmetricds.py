"""Monitoring SymmetricDS : alerte si un batch sortant reste bloque en erreur.

Cas typique : un INSERT/UPDATE sur une table provoque une erreur de
contrainte cote target (ex: NOT NULL ajoute cote OVH mais pas cote
interne). SymmetricDS retry sans cesse et bloque toute la queue. Sans
monitoring, ca peut durer des jours (cas vu le 2026-06-24 : batch
bloque depuis 7 jours).

Comportement :
- Verifie sym_outgoing_batch WHERE error_flag = 1 cote interne.
- Si batch en erreur depuis > ALERT_AFTER_MINUTES (defaut 30 min) :
    * Log dans le fichier ROTATIF logs/symmetricds_monitor.log
    * Envoi email d'alerte aux destinataires NOTIFY_EMAILS
    * Envoi SMS aux numeros NOTIFY_GSMS
- Anti-spam : ne re-alerte pas si on a deja alerte sur le meme batch_id
    dans les ALERT_COOLDOWN_HOURS dernieres heures (file flag JSON).

A lancer via Task Scheduler Windows toutes les 15-30 min.

Pas de skip auto : volontaire, pour eviter perte silencieuse de donnees.
L'admin recoit l'alerte avec la requete UPDATE prete a coller.

Usage :
    python scripts/monitor_symmetricds.py
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Permet de lancer le script en standalone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database.pg import get_pg_connection
from app.shared.notifications.mail import envoi_mail
from app.shared.notifications.sms import envoi_sms


# ---------------------------------------------------------------------------
# Configuration (modifiable via .env ou en dur)
# ---------------------------------------------------------------------------

# Seuil avant alerte (eviter le bruit pour des batchs en erreur transitoire)
ALERT_AFTER_MINUTES = int(os.getenv("SYMDS_ALERT_AFTER_MIN", "30"))

# Cooldown : ne pas re-alerter sur le meme batch dans cet intervalle
ALERT_COOLDOWN_HOURS = int(os.getenv("SYMDS_ALERT_COOLDOWN_H", "12"))

# Destinataires
NOTIFY_EMAILS = [
    e.strip() for e in os.getenv(
        "SYMDS_NOTIFY_EMAILS",
        "a.loudieux@exosphere.fr",
    ).split(",") if e.strip()
]
NOTIFY_GSMS = [
    g.strip() for g in os.getenv(
        "SYMDS_NOTIFY_GSMS",
        "",  # par defaut vide -> pas de SMS
    ).split(",") if g.strip()
]

# Schema SymmetricDS dans PG
SYM_SCHEMA = os.getenv("SYMDS_SCHEMA", "symmetricds")

# Fichiers de logs / state (relatif a la racine du projet)
ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "symmetricds_monitor.log"
STATE_FILE = LOG_DIR / "symmetricds_monitor_state.json"


# ---------------------------------------------------------------------------
# Logger (rotation 1 fichier / semaine, garde 4 semaines)
# ---------------------------------------------------------------------------

logger = logging.getLogger("symds_monitor")
logger.setLevel(logging.INFO)
_handler = logging.handlers.TimedRotatingFileHandler(
    LOG_FILE, when="W0", backupCount=4, encoding="utf-8",
)
_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"),
)
logger.addHandler(_handler)
# Affiche aussi sur stdout pour Task Scheduler
_stdout = logging.StreamHandler(sys.stdout)
_stdout.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_stdout)


# ---------------------------------------------------------------------------
# State (anti-spam)
# ---------------------------------------------------------------------------


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(
        json.dumps(state, indent=2, default=str), encoding="utf-8",
    )


def should_alert(batch_id: int, state: dict) -> bool:
    """Anti-spam : retourne True si pas alerte dans le cooldown."""
    key = str(batch_id)
    last = state.get(key)
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
    except ValueError:
        return True
    return (datetime.now() - last_dt) > timedelta(hours=ALERT_COOLDOWN_HOURS)


# ---------------------------------------------------------------------------
# Diagnostic
# ---------------------------------------------------------------------------


def get_bloque_batchs() -> list[dict]:
    """Retourne les batchs en erreur depuis > ALERT_AFTER_MINUTES."""
    db = get_pg_connection("recrutement")  # n'importe quel schema = meme DB
    cutoff = datetime.now() - timedelta(minutes=ALERT_AFTER_MINUTES)
    rows = db.query(
        f"""SELECT batch_id, node_id, channel_id, status, error_flag,
                  create_time, last_update_time, sql_message
              FROM {SYM_SCHEMA}.sym_outgoing_batch
             WHERE error_flag = 1
               AND last_update_time < ?
          ORDER BY batch_id""",
        (cutoff,),
    ) or []
    return rows


# ---------------------------------------------------------------------------
# Alertes
# ---------------------------------------------------------------------------


def format_email_html(batchs: list[dict]) -> str:
    rows_html = ""
    for b in batchs:
        sql_short = (b.get("sql_message") or "")[:300]
        rows_html += (
            f"<tr>"
            f"<td>{b['batch_id']}</td>"
            f"<td>{b['node_id']}</td>"
            f"<td>{b['channel_id']}</td>"
            f"<td>{b['create_time']}</td>"
            f"<td>{b['last_update_time']}</td>"
            f"<td><pre style='white-space:pre-wrap;font-size:11px'>{sql_short}</pre></td>"
            f"</tr>"
        )
    update_sql = "\n".join(
        f"UPDATE {SYM_SCHEMA}.sym_outgoing_batch "
        f"SET status='OK', error_flag=0, "
        f"sql_message='Skip manuel {datetime.now().date()}' "
        f"WHERE batch_id={b['batch_id']};"
        for b in batchs
    )
    return f"""
    <html><body style="font-family:sans-serif">
      <h2 style="color:#B91C1C">SymmetricDS : {len(batchs)} batch(s) bloque(s) en erreur</h2>
      <p>La replication PG entre interne et OVH est bloquee.
         Verifier et debloquer rapidement.</p>
      <table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:12px">
        <thead style="background:#17494E;color:white">
          <tr><th>Batch ID</th><th>Node</th><th>Channel</th>
              <th>Cree</th><th>Dernier retry</th><th>Erreur</th></tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
      <h3>Si la perte de donnees est acceptable, skip via :</h3>
      <pre style="background:#F8F5F4;padding:8px;font-size:12px">{update_sql}</pre>
      <p style="color:#A68D8A;font-size:11px">
        Email automatique - <code>scripts/monitor_symmetricds.py</code> sur le serveur interne.
      </p>
    </body></html>
    """


def format_sms(batchs: list[dict]) -> str:
    if len(batchs) == 1:
        b = batchs[0]
        return (
            f"[SymmetricDS] Batch {b['batch_id']} bloque depuis "
            f"{b['create_time']}. Channel: {b['channel_id']}. "
            f"Voir mail pour detail."
        )
    return (
        f"[SymmetricDS] {len(batchs)} batchs bloques. "
        f"Replication PG arretee. Voir mail."
    )


def alert(batchs: list[dict]) -> None:
    """Envoie email + SMS."""
    html = format_email_html(batchs)
    sujet = f"[ALERTE] SymmetricDS : {len(batchs)} batch(s) bloque(s)"
    sms_text = format_sms(batchs)

    if NOTIFY_EMAILS:
        try:
            envoi_mail(
                sujet=sujet, html=html, destinataires=NOTIFY_EMAILS,
            )
            logger.info(f"Email envoye a {len(NOTIFY_EMAILS)} destinataire(s).")
        except Exception as e:
            logger.error(f"Echec email : {type(e).__name__}: {e}")

    for gsm in NOTIFY_GSMS:
        try:
            res = envoi_sms(sms_text, gsm, emetteur="OMAYA-Info")
            logger.info(f"SMS envoye a {gsm} : {res}")
        except Exception as e:
            logger.error(f"Echec SMS {gsm} : {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    logger.info("=== Demarrage du monitoring SymmetricDS ===")
    try:
        batchs = get_bloque_batchs()
    except Exception as e:
        logger.error(f"Echec lecture sym_outgoing_batch : {type(e).__name__}: {e}")
        return 1

    if not batchs:
        logger.info("Aucun batch bloque (apres seuil de %d min).", ALERT_AFTER_MINUTES)
        return 0

    logger.warning(
        f"{len(batchs)} batch(s) bloque(s) : {[b['batch_id'] for b in batchs]}"
    )

    # Filtre par cooldown anti-spam
    state = load_state()
    a_alerter = [b for b in batchs if should_alert(b["batch_id"], state)]

    if not a_alerter:
        logger.info(
            "Tous les batchs ont deja ete alertes dans le cooldown (%dh).",
            ALERT_COOLDOWN_HOURS,
        )
        return 0

    logger.warning(f"Alerte sur {len(a_alerter)} batch(s) nouveau(x).")
    alert(a_alerter)

    # Mets a jour le state
    now_iso = datetime.now().isoformat(timespec="seconds")
    for b in a_alerter:
        state[str(b["batch_id"])] = now_iso
    # Nettoyage : drop les entries trop anciennes (> 7j)
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    state = {k: v for k, v in state.items() if v > cutoff}
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
