"""Portage WinDev Dialogue_EnrPJMSG / ModifMSG / SupprMSG."""

from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import quote

from app.core.database.pg import get_pg_connection
from app.shared.dialogues.schemas.dialogues import (
    DialogueMsg, DialogueMsgPayload, DialoguePJ,
    MsgModifPayload, MsgSupprPayload,
)
from app.shared.dialogues.services._helpers import pj_url

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


def _fmt_datetime_fr(dt) -> str:
    if not dt:
        return ""
    try:
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        jours = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        mois = ["Jan", "Fev", "Mar", "Avr", "Mai", "Juin",
                "Juil", "Aou", "Sep", "Oct", "Nov", "Dec"]
        return (f"{jours[dt.weekday()]} {dt.day:02d} {mois[dt.month - 1]} "
                f"{dt.year}, {dt.hour:02d}:{dt.minute:02d}")
    except Exception:
        return str(dt)


def _capitalise(v: str) -> str:
    return v[:1].upper() + v[1:].lower() if v else ""


def _nom_expediteur(id_salarie: int) -> str:
    if not id_salarie:
        return ""
    rh = get_pg_connection("rh")
    try:
        row = rh.query_one(
            "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
            (int(id_salarie),),
        )
        if row:
            return f"{row.get('nom') or ''} {_capitalise(row.get('prenom') or '')}".strip()
    except Exception:
        logger.exception("_nom_expediteur")
    return ""


# ---------------------------------------------------------------------------
#  ENVOI d'un message (+ attache les PJ deja uploadees)
# ---------------------------------------------------------------------------

def envoyer_msg(payload: DialogueMsgPayload) -> DialogueMsg:
    db = get_pg_connection("divers")
    now = datetime.now()
    id_msg = _new_id_wd()
    id_dialogue = _to_int(payload.IDDialogue)
    expediteur = _to_int(payload.Expediteur)

    try:
        db.query(
            """INSERT INTO divers.pgt_dialoguemsg
                 (id_dialogue_msg, id_dialogues, contenu,
                  date_heure_creation, expediteur,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'new')""",
            (id_msg, id_dialogue, payload.ContenuUni or "",
             now, expediteur, now, expediteur),
        )
    except Exception:
        logger.exception("envoyer_msg: insert msg")
        return DialogueMsg()

    # Attache les PJ eventuellement deja uploadees (via /pj/enregistrer)
    for pj in (payload.mesPJs or []):
        id_pj = _to_int(pj.IDPJ)
        if not id_pj:
            # PJ nouvelle -> INSERT direct
            id_pj = _new_id_wd()
            try:
                db.query(
                    """INSERT INTO divers.pgt_dialoguepj
                         (id_dialogue_pj, id_dialogues, id_dialogue_msg,
                          nom_fic, date_heure_creation, expediteur,
                          modif_date, modif_op, modif_elem)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                    (id_pj, id_dialogue, id_msg, pj.NomFic or "",
                     now, _to_int(pj.Expediteur) or expediteur,
                     now, expediteur),
                )
                pj.IDPJ = str(id_pj)
            except Exception:
                logger.exception("envoyer_msg: insert pj")
        else:
            # PJ existante (uploadee sans msg) -> UPDATE id_dialogue_msg
            try:
                db.query(
                    """UPDATE divers.pgt_dialoguepj
                          SET id_dialogue_msg = ?, id_dialogues = ?,
                              modif_date = ?, modif_op = ?, modif_elem = 'modif'
                        WHERE id_dialogue_pj = ?""",
                    (id_msg, id_dialogue, now, expediteur, id_pj),
                )
            except Exception:
                logger.exception("envoyer_msg: update pj")

    # TODO(push mobile) : EnvoiNotifPushDialogue

    # Reponse : le message tel qu'il vient d'etre stocke
    msg = DialogueMsg(
        IDMessage=str(id_msg),
        IDDialogue=_str_id(id_dialogue),
        DateHeureCreation=now.strftime("%Y-%m-%d %H:%M:%S"),
        Expediteur=_str_id(expediteur),
        NomExp=_nom_expediteur(expediteur),
        MsgSuppr=False,
        mesPJs=[DialoguePJ(
            **{**p.model_dump(),
               "Url": pj_url(id_dialogue, p.NomFic)},
        ) for p in (payload.mesPJs or [])],
    )
    if (payload.Contenu or "").upper() == "JSON":
        msg.Contenu = quote(payload.ContenuUni or "", safe="")
    else:
        msg.ContenuUni = payload.ContenuUni or ""
    return msg


# ---------------------------------------------------------------------------
#  MODIFICATION d'un message existant
# ---------------------------------------------------------------------------

def modifier_msg(payload: MsgModifPayload, id_vend: int) -> DialogueMsg:
    db = get_pg_connection("divers")
    now = datetime.now()
    id_msg = _to_int(payload.IDMessage)

    try:
        existing = db.query_one(
            """SELECT id_dialogues, expediteur, modif_elem
                 FROM divers.pgt_dialoguemsg
                WHERE id_dialogue_msg = ? LIMIT 1""",
            (id_msg,),
        )
    except Exception:
        logger.exception("modifier_msg: select")
        return DialogueMsg()
    if not existing:
        return DialogueMsg()

    try:
        db.query(
            """UPDATE divers.pgt_dialoguemsg
                  SET contenu = ?, modif_date = ?, modif_op = ?, modif_elem = 'modif'
                WHERE id_dialogue_msg = ?""",
            (payload.ContenuUni or "", now, int(id_vend), id_msg),
        )
    except Exception:
        logger.exception("modifier_msg: update")
        return DialogueMsg()

    msg = DialogueMsg(
        IDMessage=str(id_msg),
        IDDialogue=_str_id(existing.get("id_dialogues")),
        Expediteur=_str_id(existing.get("expediteur")),
        NomExp=_nom_expediteur(int(existing.get("expediteur") or 0)),
    )
    if (payload.Contenu or "").upper() == "JSON":
        msg.Contenu = quote(payload.ContenuUni or "", safe="")
    else:
        msg.ContenuUni = payload.ContenuUni or ""
    return msg


# ---------------------------------------------------------------------------
#  SUPPRESSION LOGIQUE d'un message (+ ses PJ)
# ---------------------------------------------------------------------------

def supprimer_msg(payload: MsgSupprPayload, id_vend: int) -> DialogueMsg:
    db = get_pg_connection("divers")
    now = datetime.now()
    id_msg = _to_int(payload.IDMessage)

    try:
        db.query(
            """UPDATE divers.pgt_dialoguemsg
                  SET modif_date = ?, modif_op = ?, modif_elem = 'suppr'
                WHERE id_dialogue_msg = ?""",
            (now, int(id_vend), id_msg),
        )
    except Exception:
        logger.exception("supprimer_msg: update msg")
        return DialogueMsg()

    # PJs liees : marquer 'suppr' aussi
    try:
        db.query(
            """UPDATE divers.pgt_dialoguepj
                  SET modif_date = ?, modif_op = ?, modif_elem = 'suppr'
                WHERE id_dialogue_msg = ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')""",
            (now, int(id_vend), id_msg),
        )
    except Exception:
        logger.exception("supprimer_msg: update pj")

    supr_txt = f"Message supprimé le {_fmt_datetime_fr(now)}"
    return DialogueMsg(
        IDMessage=str(id_msg),
        Contenu=supr_txt,
        ContenuUni=supr_txt,
        MsgSuppr=True,
    )
