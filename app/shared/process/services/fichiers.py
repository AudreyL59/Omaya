"""CRUD des pieces jointes d'un process (stockage bytea en base)."""

from __future__ import annotations

import logging
import os
from datetime import datetime

import psycopg2

from app.core.database.pg import get_pg_connection
from app.shared.process.services._helpers import _new_id_wd, _str_id

logger = logging.getLogger(__name__)


def add_fichier(id_process: int, filename: str, content: bytes,
                 user_id: int) -> str:
    """Ecrit une PJ en bytea. Retourne l'IDProcessFichier ou "".

    Titre = filename sans extension. Extension = ext avec le point
    (ex: '.pdf'). TailleFic = len(content).
    """
    if not id_process or not filename or not content:
        return ""
    id_fic = _new_id_wd()
    now = datetime.now()
    base, ext = os.path.splitext(filename)
    ext = ext.lower()  # normalise ('.PDF' -> '.pdf')

    db = get_pg_connection("divers")
    try:
        db.query(
            """INSERT INTO divers.pgt_process_fichier
                 (id_process_fichier, id_process, titre,
                  date_crea, derniere_modif, ope_crea, ope_modif,
                  contenu_fichier, extension, taille_fic,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
            (id_fic, int(id_process), base or filename,
             now, now, int(user_id), int(user_id),
             psycopg2.Binary(content), ext, len(content),
             now, int(user_id)),
        )
        return _str_id(id_fic)
    except Exception:
        logger.exception("add_fichier id_process=%s", id_process)
        return ""


def get_fichier(id_fichier: int) -> tuple[bytes, str, str] | None:
    """Retourne (contenu, filename_original, mime) ou None si absent."""
    if not id_fichier:
        return None
    db = get_pg_connection("divers")
    try:
        row = db.query_one(
            """SELECT titre, extension, contenu_fichier
                 FROM divers.pgt_process_fichier
                WHERE id_process_fichier = ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                LIMIT 1""",
            (int(id_fichier),),
        )
    except Exception:
        logger.exception("get_fichier id=%s", id_fichier)
        return None
    if not row:
        return None
    titre = row.get("titre") or "fichier"
    ext = row.get("extension") or ""
    contenu = row.get("contenu_fichier")
    if contenu is None:
        return None
    if isinstance(contenu, memoryview):
        contenu = bytes(contenu)
    return contenu, f"{titre}{ext}", _mime_from_ext(ext)


def delete_fichier(id_fichier: int, user_id: int) -> bool:
    if not id_fichier:
        return False
    db = get_pg_connection("divers")
    now = datetime.now()
    try:
        db.query(
            """UPDATE divers.pgt_process_fichier
                  SET modif_date = ?, modif_op = ?, modif_elem = 'suppr'
                WHERE id_process_fichier = ?""",
            (now, int(user_id), int(id_fichier)),
        )
        return True
    except Exception:
        logger.exception("delete_fichier id=%s", id_fichier)
        return False


_MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain", ".csv": "text/csv",
    ".zip": "application/zip",
}


def _mime_from_ext(ext: str) -> str:
    return _MIME_BY_EXT.get((ext or "").lower(), "application/octet-stream")
