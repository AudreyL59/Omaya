"""Portage WinDev Dialogue_Lu : marque un dialogue lu par un salarié.

UPSERT dans pgt_dialoguelu : (id_dialogues, id_salarie) est logiquement
unique bien que la PK soit id_dialogue_lu (autogen 8 octets).
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.core.database.pg import get_pg_connection
from app.shared.dialogues.schemas.dialogues import ReponseTK

logger = logging.getLogger(__name__)


def _new_id_wd() -> int:
    """idEntierDateHeureSys() de WinDev : entier 8 octets 'YYYYMMDDHHMMSSMMM'."""
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


def marquer_lu(id_dialogue: int, id_salarie: int) -> ReponseTK:
    db = get_pg_connection("divers")
    now = datetime.now()
    try:
        existing = db.query(
            """SELECT id_dialogue_lu
                 FROM divers.pgt_dialoguelu
                WHERE id_dialogues = ? AND id_salarie = ?
                LIMIT 1""",
            (int(id_dialogue), int(id_salarie)),
        ) or []
        if existing:
            id_lu = int(existing[0]["id_dialogue_lu"])
            db.query(
                """UPDATE divers.pgt_dialoguelu
                      SET date_lecture = ?, modif_date = ?, modif_op = ?, modif_elem = 'new'
                    WHERE id_dialogue_lu = ?""",
                (now, now, int(id_salarie), id_lu),
            )
        else:
            id_lu = _new_id_wd()
            db.query(
                """INSERT INTO divers.pgt_dialoguelu
                      (id_dialogue_lu, id_dialogues, id_salarie,
                       date_lecture, modif_date, modif_op, modif_elem)
                    VALUES (?, ?, ?, ?, ?, ?, 'new')""",
                (id_lu, int(id_dialogue), int(id_salarie),
                 now, now, int(id_salarie)),
            )
        return ReponseTK(nIdDemande=str(id_lu), sInfoData=now.isoformat(sep=" "))
    except Exception as e:
        logger.exception("marquer_lu")
        return ReponseTK(nIdDemande="0", sInfoData=str(e))
