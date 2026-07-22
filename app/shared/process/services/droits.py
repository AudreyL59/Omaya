"""CRUD des droits d'acces d'un process."""

from __future__ import annotations

import logging
from datetime import datetime

from app.core.database.pg import get_pg_connection
from app.shared.process.schemas.process import (
    ProfilItem, ProcessDroitSavePayload,
)
from app.shared.process.services._helpers import (
    _new_id_wd, _str_id, _to_int, PROFILS_KNOWN,
)

logger = logging.getLogger(__name__)


def liste_profils() -> list[ProfilItem]:
    """Referentiel statique des profils supportes."""
    # Ordre : STAFF top, puis filiere FDV (haut vers bas), puis CALL/CALLRH
    ordre = {"STAFF": 0,
             "FDV DR": 1, "FDV DA": 2, "FDV MAN": 3, "FDV VRP": 4,
             "CALL": 5, "CALLRH": 6}
    libs = {"STAFF": "STAFF",
            "FDV DR": "FDV DR", "FDV DA": "FDV DA",
            "FDV MAN": "FDV MAN", "FDV VRP": "FDV VRP",
            "CALL": "CALL", "CALLRH": "CALLRH"}
    return [
        ProfilItem(Code=p, Lib=libs.get(p, p), Ordre=ordre.get(p, 99))
        for p in PROFILS_KNOWN
    ]


def save_droit(payload: ProcessDroitSavePayload, user_id: int) -> str:
    """Ajoute ou met a jour un droit d'acces. Retourne l'IDProcessDroit."""
    db = get_pg_connection("divers")
    now = datetime.now()
    id_droit = _to_int(payload.IDProcessDroit)
    id_process = _to_int(payload.IDProcess)
    id_salarie = _to_int(payload.IDSalarie)
    id_ste = _to_int(payload.IdSte)
    type_profil = (payload.TypeProfil or "").strip()

    # Un droit doit cibler soit un salarie (id_salarie != 0) SOIT un profil.
    # Pas les deux, mais on tolere le cas et le salarie gagne.
    if id_salarie:
        type_profil = ""
    elif not type_profil:
        return ""  # rien de cible

    if not id_process:
        return ""

    if not id_droit:
        id_droit = _new_id_wd()
        try:
            db.query(
                """INSERT INTO divers.pgt_process_droit
                     (id_process_droit, id_process, id_salarie, type_profil,
                      id_ste, droit_actif,
                      modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                (id_droit, id_process, id_salarie, type_profil, id_ste,
                 bool(payload.DroitActif), now, int(user_id)),
            )
        except Exception:
            logger.exception("save_droit: insert")
            return ""
    else:
        try:
            db.query(
                """UPDATE divers.pgt_process_droit
                      SET id_salarie = ?, type_profil = ?, id_ste = ?,
                          droit_actif = ?,
                          modif_date = ?, modif_op = ?, modif_elem = 'modif'
                    WHERE id_process_droit = ?""",
                (id_salarie, type_profil, id_ste,
                 bool(payload.DroitActif), now, int(user_id), id_droit),
            )
        except Exception:
            logger.exception("save_droit: update")
            return ""
    return _str_id(id_droit)


def delete_droit(id_droit: int, user_id: int) -> bool:
    if not id_droit:
        return False
    db = get_pg_connection("divers")
    now = datetime.now()
    try:
        db.query(
            """UPDATE divers.pgt_process_droit
                  SET modif_date = ?, modif_op = ?, modif_elem = 'suppr'
                WHERE id_process_droit = ?""",
            (now, int(user_id), int(id_droit)),
        )
        return True
    except Exception:
        logger.exception("delete_droit id=%s", id_droit)
        return False
