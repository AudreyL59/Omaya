"""Diagrammes Excalidraw stockes dans pgt_process_fichier avec
extension '.excalidraw'. Meme pattern que le WinDev original ou les
.wddiag etaient des fichiers du process. Un process peut avoir N
diagrammes.

Le champ pgt_process.diagramme_json (V2 legacy) est migre vers
pgt_process_fichier via migration/patches/migrate_process_diagramme_json_to_fichier.sql.
"""

from __future__ import annotations

import logging
from datetime import datetime

import psycopg2

from app.core.database.pg import get_pg_connection
from app.shared.process.schemas.process import (
    ProcessDiagramme, ProcessDiagrammeMeta, ProcessDiagrammeSavePayload,
)
from app.shared.process.services._helpers import (
    _iso_datetime, _new_id_wd, _str_id, _to_int, nom_salarie,
)

logger = logging.getLogger(__name__)

# Extension unique reservee aux diagrammes Excalidraw. Filtre les
# fichiers 'diagramme' de la liste des fichiers 'classiques'.
DIAG_EXT = ".excalidraw"


def liste_diagrammes(id_process: int) -> list[ProcessDiagrammeMeta]:
    """Meta des diagrammes d'un process (fichiers .excalidraw)."""
    if not id_process:
        return []
    db = get_pg_connection("divers")
    try:
        rows = db.query(
            """SELECT id_process_fichier, titre, date_crea, derniere_modif,
                      ope_crea
                 FROM divers.pgt_process_fichier
                WHERE id_process = ?
                  AND lower(extension) = ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY COALESCE(date_crea, modif_date) ASC""",
            (int(id_process), DIAG_EXT),
        ) or []
    except Exception:
        logger.exception("liste_diagrammes id_process=%s", id_process)
        return []
    op_ids = {int(r.get("ope_crea") or 0) for r in rows}
    op_ids.discard(0)
    op_noms = {i: nom_salarie(i) for i in op_ids}
    return [
        ProcessDiagrammeMeta(
            IDProcessDiagramme=_str_id(r.get("id_process_fichier")),
            Titre=r.get("titre") or "",
            DateCrea=_iso_datetime(r.get("date_crea")),
            DerniereModif=_iso_datetime(r.get("derniere_modif")),
            OpeCrea=_str_id(r.get("ope_crea") or 0) if r.get("ope_crea") else "",
            NomOpeCrea=op_noms.get(int(r.get("ope_crea") or 0), ""),
        )
        for r in rows
    ]


def get_diagramme(id_diagramme: int) -> ProcessDiagramme | None:
    """Diagramme complet (JSON depuis bytea decode UTF-8)."""
    if not id_diagramme:
        return None
    db = get_pg_connection("divers")
    try:
        row = db.query_one(
            """SELECT id_process_fichier, id_process, titre,
                      contenu_fichier, extension, date_crea,
                      derniere_modif, ope_crea
                 FROM divers.pgt_process_fichier
                WHERE id_process_fichier = ?
                  AND lower(extension) = ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                LIMIT 1""",
            (int(id_diagramme), DIAG_EXT),
        )
    except Exception:
        logger.exception("get_diagramme id=%s", id_diagramme)
        return None
    if not row:
        return None
    contenu = row.get("contenu_fichier")
    if isinstance(contenu, memoryview):
        contenu = bytes(contenu)
    try:
        json_str = contenu.decode("utf-8") if contenu else ""
    except Exception:
        json_str = ""
    return ProcessDiagramme(
        IDProcessDiagramme=_str_id(row.get("id_process_fichier")),
        IDProcess=_str_id(row.get("id_process")),
        Titre=row.get("titre") or "",
        ContenuJson=json_str,
        DateCrea=_iso_datetime(row.get("date_crea")),
        DerniereModif=_iso_datetime(row.get("derniere_modif")),
        OpeCrea=_str_id(row.get("ope_crea") or 0) if row.get("ope_crea") else "",
    )


def save_diagramme(payload: ProcessDiagrammeSavePayload,
                    user_id: int) -> str:
    """Cree ou met a jour un diagramme (INSERT/UPDATE pgt_process_fichier
    avec extension .excalidraw). Retourne l'ID."""
    db = get_pg_connection("divers")
    now = datetime.now()
    id_dia = _to_int(payload.IDProcessDiagramme)
    id_process = _to_int(payload.IDProcess)
    titre = (payload.Titre or "").strip() or "Diagramme"
    json_str = payload.ContenuJson or ""
    contenu_bytes = json_str.encode("utf-8") if json_str else b""

    if not id_process:
        return ""

    if not id_dia:
        id_dia = _new_id_wd()
        try:
            db.query(
                """INSERT INTO divers.pgt_process_fichier
                     (id_process_fichier, id_process, titre,
                      contenu_fichier, extension, taille_fic,
                      date_crea, derniere_modif, ope_crea, ope_modif,
                      modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                (id_dia, id_process, titre,
                 psycopg2.Binary(contenu_bytes), DIAG_EXT, len(contenu_bytes),
                 now, now, int(user_id), int(user_id),
                 now, int(user_id)),
            )
        except Exception:
            logger.exception("save_diagramme: insert")
            return ""
    else:
        try:
            db.query(
                """UPDATE divers.pgt_process_fichier
                      SET titre = ?, contenu_fichier = ?,
                          taille_fic = ?, derniere_modif = ?,
                          ope_modif = ?,
                          modif_date = ?, modif_op = ?, modif_elem = 'modif'
                    WHERE id_process_fichier = ?
                      AND lower(extension) = ?""",
                (titre, psycopg2.Binary(contenu_bytes),
                 len(contenu_bytes), now, int(user_id),
                 now, int(user_id), id_dia, DIAG_EXT),
            )
        except Exception:
            logger.exception("save_diagramme: update")
            return ""
    return _str_id(id_dia)


def delete_diagramme(id_diagramme: int, user_id: int) -> bool:
    if not id_diagramme:
        return False
    db = get_pg_connection("divers")
    now = datetime.now()
    try:
        db.query(
            """UPDATE divers.pgt_process_fichier
                  SET modif_date = ?, modif_op = ?, modif_elem = 'suppr'
                WHERE id_process_fichier = ?
                  AND lower(extension) = ?""",
            (now, int(user_id), int(id_diagramme), DIAG_EXT),
        )
        return True
    except Exception:
        logger.exception("delete_diagramme id=%s", id_diagramme)
        return False
