"""Portage WinDev Dialogue_EnrPJ : enregistre une PJ apres upload.

Version simplifiee vs le WinDev original : on saute la logique de
detection de doublons + renommage `_{expediteur}` (WinDev le faisait
pour eviter d'ecraser un fichier deja envoye par un autre user). Ici
l'upload cote /upload-fichier ecrit deja dans DocConv/{id_dial}/ et
gere ses propres collisions. On se contente donc d'INSERT dans
pgt_dialoguepj.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from app.core.database.pg import get_pg_connection
from app.shared.dialogues.schemas.dialogues import DialoguePJ, DialoguePJPayload
from app.shared.dialogues.services._helpers import pj_url

logger = logging.getLogger(__name__)


def _new_id_wd() -> int:
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


def _to_int(v, default: int = 0) -> int:
    try:
        return int(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _str_id(v) -> str:
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _docs_base_path() -> str:
    return os.environ.get("DOCS_BASE_PATH", r"D:\OMAYA")


def enregistrer_pj(payload: DialoguePJPayload) -> DialoguePJ:
    """Cree une entree PJ dans pgt_dialoguepj (fichier deja uploade).

    id_dialogue_msg=0 : PJ pas encore rattachee a un message (le sera
    au prochain /msg/envoyer). L'upload physique doit avoir ete fait
    au prealable via /dialogues/upload-fichier.
    """
    db = get_pg_connection("divers")
    now = datetime.now()

    id_dialogue = _to_int(payload.IDDialogue)
    expediteur = _to_int(payload.Expediteur)
    nom_fic = (payload.NomFic or "").strip()

    if not id_dialogue or not nom_fic:
        return DialoguePJ()

    # Verif fichier physiquement present dans DocConv/{id_dial}/
    file_path = os.path.join(_docs_base_path(), "DocConv",
                              str(id_dialogue), nom_fic)
    if not os.path.exists(file_path):
        logger.warning("enregistrer_pj: fichier absent %s", file_path)
        # On enregistre quand meme l'entree DB : le fichier peut etre
        # sur OVH (chemin FTP different) et pas visible localement.

    id_pj = _new_id_wd()
    try:
        db.query(
            """INSERT INTO divers.pgt_dialoguepj
                 (id_dialogue_pj, id_dialogues, id_dialogue_msg,
                  nom_fic, date_heure_creation, expediteur,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, 0, ?, ?, ?, ?, ?, 'new')""",
            (id_pj, id_dialogue, nom_fic, now, expediteur,
             now, expediteur),
        )
    except Exception:
        logger.exception("enregistrer_pj: insert")
        return DialoguePJ()

    return DialoguePJ(
        IDPJ=str(id_pj),
        IDDialogue=_str_id(id_dialogue),
        NomFic=nom_fic,
        Url=pj_url(id_dialogue, nom_fic),
        DateHeureCreation=now.strftime("%Y-%m-%d %H:%M:%S"),
        Expediteur=_str_id(expediteur),
    )
