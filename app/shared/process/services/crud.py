"""CRUD d'un process + resolution de son detail complet (fichiers + droits)."""

from __future__ import annotations

import logging
import re
from datetime import datetime

from app.core.database.pg import get_pg_connection
from app.shared.process.schemas.process import (
    Process, ProcessDroit, ProcessFichierMeta, ProcessSavePayload,
)
from app.shared.process.services._helpers import (
    _iso_datetime, _new_id_wd, _str_id, _to_int, nom_salarie,
)

logger = logging.getLogger(__name__)


def _normalize_mots_cles(raw: str) -> str:
    """Normalise la chaine de mots-cles : parse par RC/virgule/point-virgule,
    trim, dedupe case-insensitive (ordre preserve), rejoin en RC.
    Format de storage WinDev = un mot par ligne."""
    if not raw:
        return ""
    seen: set[str] = set()
    out: list[str] = []
    for t in re.split(r"[\n\r,;]+", raw):
        s = t.strip()
        if not s:
            continue
        k = s.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
    return "\n".join(out)


def get_process(id_process: int) -> Process | None:
    if not id_process:
        return None
    db = get_pg_connection("divers")
    try:
        row = db.query_one(
            """SELECT id_process, titre, service, mots_cles,
                      date_crea, derniere_modif, ope_crea, ope_modif
                 FROM divers.pgt_process
                WHERE id_process = ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                LIMIT 1""",
            (int(id_process),),
        )
    except Exception:
        logger.exception("get_process id=%s", id_process)
        return None
    if not row:
        return None
    ope_crea = int(row.get("ope_crea") or 0)
    ope_modif = int(row.get("ope_modif") or 0)
    p = Process(
        IDProcess=_str_id(row.get("id_process")),
        Titre=row.get("titre") or "",
        Service=row.get("service") or "",
        MotsCles=row.get("mots_cles") or "",
        DateCrea=_iso_datetime(row.get("date_crea")),
        DerniereModif=_iso_datetime(row.get("derniere_modif")),
        OpeCrea=_str_id(ope_crea) if ope_crea else "",
        NomOpeCrea=nom_salarie(ope_crea),
        OpeModif=_str_id(ope_modif) if ope_modif else "",
        NomOpeModif=nom_salarie(ope_modif),
    )
    p.Fichiers = _load_fichiers(int(id_process))
    p.Droits = _load_droits(int(id_process))
    from app.shared.process.services.diagramme import liste_diagrammes
    p.Diagrammes = liste_diagrammes(int(id_process))
    return p


def _load_fichiers(id_process: int) -> list[ProcessFichierMeta]:
    db = get_pg_connection("divers")
    try:
        rows = db.query(
            """SELECT id_process_fichier, titre, extension, taille_fic,
                      date_crea, derniere_modif, ope_crea
                 FROM divers.pgt_process_fichier
                WHERE id_process = ?
                  AND (lower(extension) <> '.excalidraw' OR extension IS NULL)
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY COALESCE(derniere_modif, date_crea) DESC""",
            (id_process,),
        ) or []
    except Exception:
        logger.exception("_load_fichiers id=%s", id_process)
        return []
    op_ids = {int(r.get("ope_crea") or 0) for r in rows}
    op_ids.discard(0)
    op_noms = {i: nom_salarie(i) for i in op_ids}
    return [
        ProcessFichierMeta(
            IDProcessFichier=_str_id(r.get("id_process_fichier")),
            Titre=r.get("titre") or "",
            Extension=r.get("extension") or "",
            TailleFic=int(r.get("taille_fic") or 0),
            DateCrea=_iso_datetime(r.get("date_crea")),
            DerniereModif=_iso_datetime(r.get("derniere_modif")),
            OpeCrea=_str_id(r.get("ope_crea") or 0) if r.get("ope_crea") else "",
            NomOpeCrea=op_noms.get(int(r.get("ope_crea") or 0), ""),
        )
        for r in rows
    ]


def _load_droits(id_process: int) -> list[ProcessDroit]:
    db = get_pg_connection("divers")
    rh = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT id_process_droit, id_process, id_salarie, type_profil,
                      id_ste, droit_actif
                 FROM divers.pgt_process_droit
                WHERE id_process = ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')""",
            (id_process,),
        ) or []
    except Exception:
        logger.exception("_load_droits id=%s", id_process)
        return []
    # Cache libelles societes
    ste_ids = {int(r.get("id_ste") or 0) for r in rows}
    ste_ids.discard(0)
    ste_libs: dict[int, str] = {}
    if ste_ids:
        try:
            ids_sql = ",".join(str(i) for i in ste_ids)
            steRows = rh.query(
                f"""SELECT id_ste, rs_interne, raison_sociale
                     FROM rh.pgt_societe WHERE id_ste IN ({ids_sql})""",
            ) or []
            for s in steRows:
                ste_libs[int(s.get("id_ste") or 0)] = (
                    (s.get("rs_interne") or s.get("raison_sociale") or "").strip()
                )
        except Exception:
            logger.exception("_load_droits: cache societes")
    out: list[ProcessDroit] = []
    for r in rows:
        id_sal = int(r.get("id_salarie") or 0)
        id_ste = int(r.get("id_ste") or 0)
        out.append(ProcessDroit(
            IDProcessDroit=_str_id(r.get("id_process_droit")),
            IDProcess=_str_id(r.get("id_process")),
            IDSalarie=_str_id(id_sal) if id_sal else "",
            NomSalarie=nom_salarie(id_sal) if id_sal else "",
            TypeProfil=r.get("type_profil") or "",
            IdSte=_str_id(id_ste) if id_ste else "",
            LibSte=ste_libs.get(id_ste, ""),
            DroitActif=bool(r.get("droit_actif")),
        ))
    return out


def save_process(payload: ProcessSavePayload, user_id: int) -> str:
    """Cree ou met a jour un process. Retourne l'IDProcess (str)."""
    db = get_pg_connection("divers")
    now = datetime.now()
    id_process = _to_int(payload.IDProcess)
    if not id_process:
        # Create
        id_process = _new_id_wd()
        try:
            db.query(
                """INSERT INTO divers.pgt_process
                     (id_process, titre, service, mots_cles,
                      date_crea, derniere_modif, ope_crea, ope_modif,
                      modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                (id_process, payload.Titre or "", (payload.Service or "").upper(),
                 _normalize_mots_cles(payload.MotsCles or ""),
                 now, now, int(user_id), int(user_id),
                 now, int(user_id)),
            )
        except Exception:
            logger.exception("save_process: insert")
            return ""
    else:
        try:
            db.query(
                """UPDATE divers.pgt_process
                      SET titre = ?, service = ?, mots_cles = ?,
                          derniere_modif = ?, ope_modif = ?,
                          modif_date = ?, modif_op = ?, modif_elem = 'modif'
                    WHERE id_process = ?""",
                (payload.Titre or "", (payload.Service or "").upper(),
                 _normalize_mots_cles(payload.MotsCles or ""),
                 now, int(user_id), now, int(user_id), id_process),
            )
        except Exception:
            logger.exception("save_process: update")
            return ""
    return _str_id(id_process)


def delete_process(id_process: int, user_id: int) -> bool:
    """Suppression logique (modif_elem='suppr'). Ne supprime pas les
    fichiers/droits (ils suivront via la meme convention si besoin)."""
    if not id_process:
        return False
    db = get_pg_connection("divers")
    now = datetime.now()
    try:
        db.query(
            """UPDATE divers.pgt_process
                  SET modif_date = ?, modif_op = ?, modif_elem = 'suppr'
                WHERE id_process = ?""",
            (now, int(user_id), int(id_process)),
        )
        return True
    except Exception:
        logger.exception("delete_process id=%s", id_process)
        return False
