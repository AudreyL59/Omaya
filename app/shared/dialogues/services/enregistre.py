"""Portage WinDev Dialogue_Enr : creation ou modification d'un dialogue.

Cas creation (IDDialogue == 0) :
  - INSERT dans pgt_dialogues (statut=0, prive=false)
  - INSERT n destinataires dans pgt_dialoguedest
  - mkdir DocConv/{id_dialogue} local (interne) ou via FTP (OVH)
  - TODO : appel EnvoiNotifPushDialogue (push mobile)

Cas modif :
  - UPDATE sujet + id_dialogue_theme
  - Diff des destinataires : marque 'suppr' ceux disparus, INSERT les nouveaux
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from app.core.database.pg import get_pg_connection
from app.shared.dialogues.schemas.dialogues import (
    Dialogue, DialogueDest, DialogueSavePayload,
)

logger = logging.getLogger(__name__)


def _new_id_wd() -> int:
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


def _str_id(v) -> str:
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _to_int(v, default: int = 0) -> int:
    try:
        return int(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _docs_base_path() -> str:
    """Repertoire racine des documents. Configurable via DOCS_BASE_PATH."""
    return os.environ.get("DOCS_BASE_PATH", r"D:\OMAYA")


def _mkdir_docconv(id_dialogue: int) -> None:
    """Cree le dossier DocConv/{id_dialogue}. Silencieux si echec."""
    try:
        path = os.path.join(_docs_base_path(), "DocConv", str(id_dialogue))
        os.makedirs(path, exist_ok=True)
    except Exception:
        logger.exception("_mkdir_docconv id=%s", id_dialogue)


def enregistrer_dialogue(payload: DialogueSavePayload,
                          id_vend: int) -> Dialogue:
    db = get_pg_connection("divers")
    now = datetime.now()

    id_dialogue = _to_int(payload.IDDialogue)

    if not id_dialogue:
        # -- Creation ---------------------------------------------------
        id_dialogue = _new_id_wd()
        expediteur = _to_int(payload.Expediteur) or int(id_vend)
        try:
            db.query(
                """INSERT INTO divers.pgt_dialogues
                     (id_dialogues, expediteur, sujet,
                      id_dialogue_statut, id_dialogue_theme,
                      a_conserve, prive, date_heure_creation,
                      modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, 0, ?, '0', FALSE, ?, ?, ?, 'new')""",
                (id_dialogue, expediteur, payload.Sujet or "",
                 int(payload.IdTheme or 0), now, now, int(id_vend)),
            )
        except Exception:
            logger.exception("enregistrer_dialogue: insert dialogues")
            return Dialogue()

        # Destinataires
        for dest in (payload.Dests or []):
            id_dest = _new_id_wd()
            try:
                db.query(
                    """INSERT INTO divers.pgt_dialoguedest
                         (id_dialogue_dest, id_dialogues, dest_ope, dest_orga,
                          modif_date, modif_op, modif_elem)
                       VALUES (?, ?, ?, ?, ?, ?, 'new')""",
                    (id_dest, id_dialogue,
                     _to_int(dest.Dest_Ope), _to_int(dest.Dest_Orga),
                     now, int(id_vend)),
                )
                dest.IDDialogueDEST = str(id_dest)
            except Exception:
                logger.exception("enregistrer_dialogue: insert dest")

        _mkdir_docconv(id_dialogue)
        # TODO(push mobile) : EnvoiNotifPushDialogue via WS externe
    else:
        # -- Modification -----------------------------------------------
        try:
            db.query(
                """UPDATE divers.pgt_dialogues
                      SET sujet = ?, id_dialogue_theme = ?,
                          modif_date = ?, modif_op = ?, modif_elem = 'modif'
                    WHERE id_dialogues = ?""",
                (payload.Sujet or "", int(payload.IdTheme or 0),
                 now, int(id_vend), id_dialogue),
            )
        except Exception:
            logger.exception("enregistrer_dialogue: update dialogues")

        # Diff destinataires : supprime ceux disparus, ajoute les nouveaux
        try:
            existing = db.query(
                """SELECT id_dialogue_dest
                     FROM divers.pgt_dialoguedest
                    WHERE id_dialogues = ?
                      AND (modif_elem IS NULL OR modif_elem <> 'suppr')""",
                (id_dialogue,),
            ) or []
        except Exception:
            existing = []
        existing_ids = {int(r.get("id_dialogue_dest") or 0) for r in existing}
        payload_ids = {_to_int(d.IDDialogueDEST) for d in (payload.Dests or [])
                       if _to_int(d.IDDialogueDEST)}
        # A supprimer : dans existing mais pas dans payload
        for id_dest_del in existing_ids - payload_ids:
            try:
                db.query(
                    """UPDATE divers.pgt_dialoguedest
                          SET modif_date = ?, modif_op = ?, modif_elem = 'suppr'
                        WHERE id_dialogue_dest = ?""",
                    (now, int(id_vend), id_dest_del),
                )
            except Exception:
                logger.exception("enregistrer_dialogue: suppr dest")
        # A ajouter : dans payload avec IDDialogueDEST == 0
        for dest in (payload.Dests or []):
            if _to_int(dest.IDDialogueDEST) != 0:
                continue
            id_dest = _new_id_wd()
            try:
                db.query(
                    """INSERT INTO divers.pgt_dialoguedest
                         (id_dialogue_dest, id_dialogues, dest_ope, dest_orga,
                          modif_date, modif_op, modif_elem)
                       VALUES (?, ?, ?, ?, ?, ?, 'new')""",
                    (id_dest, id_dialogue,
                     _to_int(dest.Dest_Ope), _to_int(dest.Dest_Orga),
                     now, int(id_vend)),
                )
                dest.IDDialogueDEST = str(id_dest)
            except Exception:
                logger.exception("enregistrer_dialogue: insert dest (modif)")

        # TODO(push mobile) : EnvoiNotifPushDialogue

    # Reponse
    resp = Dialogue(
        IDDialogue=_str_id(id_dialogue),
        Sujet=payload.Sujet or "",
        IdTheme=int(payload.IdTheme or 0),
        Expediteur=_str_id(_to_int(payload.Expediteur) or int(id_vend)),
        Dests=[DialogueDest(**d.model_dump()) for d in (payload.Dests or [])],
    )
    return resp
