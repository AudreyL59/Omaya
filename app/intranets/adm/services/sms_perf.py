"""
Service Fen_SMSPerf - Gestion SMS Perf-Exo (CRUD).

Ce module contient :
- toggle_perf_exo : active/desactive la config globale Perf-Exo
- get_staff / save_staff : jetons de staff destinataire
- CRUD RegleEnvoi (une ligne par code animation dans la table de gauche)
- CRUD Destinataire (equipes qui recoivent le SMS)
- CRUD EquipeScore (equipes incluses dans les scores)

L'envoi effectif des SMS est dans sms_perf_envoi.py (proc Animation_SmsPerf).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.core.database.pg import get_pg_connection
from app.intranets.adm.schemas.sms_perf import (
    DestinatairePayload, DestinataireRow, EquipeScorePayload, EquipeScoreRow,
    RegleEnvoi, RegleEnvoiPayload, StaffItem,
)

logger = logging.getLogger(__name__)

_TYPE_SMS = "Perf-Exo"


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _clean_id(v) -> str:
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _iso_date(v) -> str:
    if v is None:
        return ""
    s = str(v)[:10]
    if s.startswith("1900") or s.startswith("0000"):
        return ""
    return s


def _cap_prenom(p: str) -> str:
    if not p:
        return ""
    return p[0].upper() + p[1:].lower() if len(p) > 1 else p.upper()


def _new_id() -> int:
    """ID timestamp WinDev-style (cf. autres services)."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


def _hh_from_int(h) -> int:
    """Convertit une heure Time SQL (HH:MM:SS) en heures int, ou passe int direct."""
    if h is None:
        return 0
    if isinstance(h, int):
        return h
    if isinstance(h, str):
        try:
            return int(h.split(":")[0])
        except Exception:
            return 0
    try:
        # datetime.time
        return int(h.hour)
    except Exception:
        return 0


# --------------------------------------------------------------------
# Toggle Perf-Exo actif
# --------------------------------------------------------------------

def get_perf_exo_actif() -> bool:
    """Etat courant du toggle Perf-Exo."""
    db = get_pg_connection("rh")
    try:
        r = db.query_one(
            """SELECT is_actif FROM divers.pgt_smsanimation
                WHERE type_sms = ? LIMIT 1""",
            (_TYPE_SMS,),
        )
    except Exception:
        return False
    return bool(r and r.get("is_actif"))


def toggle_perf_exo(is_actif: bool) -> bool:
    """Cf. WinDev glissiere en haut a gauche : InterrupteurBascule.

    HLitRecherche(SmsAnimation,TypeSMS,"Perf-Exo") puis HModifie.
    Si absent, cree la ligne avec un id timestamp.
    """
    db = get_pg_connection("rh")
    try:
        r = db.query_one(
            """SELECT id_sms_animation FROM divers.pgt_smsanimation
                WHERE type_sms = ? LIMIT 1""",
            (_TYPE_SMS,),
        )
    except Exception:
        r = None
    if r:
        db.execute(
            """UPDATE divers.pgt_smsanimation
                  SET is_actif = ?
                WHERE id_sms_animation = ?""",
            (is_actif, int(r.get("id_sms_animation") or 0)),
        )
    else:
        db.execute(
            """INSERT INTO divers.pgt_smsanimation
                  (id_sms_animation, type_sms, is_actif, liste_num_staff)
               VALUES (?, ?, ?, '')""",
            (_new_id(), _TYPE_SMS, is_actif),
        )
    return True


# --------------------------------------------------------------------
# Staff Destinataire (jetons)
# --------------------------------------------------------------------

def get_staff_destinataire() -> list[StaffItem]:
    """Cf. WinDev Code Init : parcourt SmsAnimation.ListeNumStaff (';')
    et renvoie prenom + init nom pour affichage jetons.
    """
    db = get_pg_connection("rh")
    try:
        r = db.query_one(
            """SELECT liste_num_staff FROM divers.pgt_smsanimation
                WHERE type_sms = ? LIMIT 1""",
            (_TYPE_SMS,),
        )
    except Exception:
        return []
    if not r:
        return []
    liste = (r.get("liste_num_staff") or "").strip()
    if not liste:
        return []
    ids = [x.strip() for x in liste.split(";") if x.strip().isdigit()]
    if not ids:
        return []
    # Charge les infos salaries
    placeholders = ",".join(["?"] * len(ids))
    try:
        rows = db.query(
            f"""SELECT id_salarie, nom, prenom FROM pgt_salarie
                 WHERE id_salarie IN ({placeholders})""",
            tuple(int(x) for x in ids),
        ) or []
    except Exception:
        return []
    by_id = {int(x.get("id_salarie") or 0): x for x in rows}
    out: list[StaffItem] = []
    for i in ids:
        row = by_id.get(int(i))
        if row:
            out.append(StaffItem(
                id_salarie=str(i),
                nom=(row.get("nom") or "").strip(),
                prenom=(row.get("prenom") or "").strip(),
            ))
    return out


def save_staff_destinataire(id_salaries: list[str]) -> bool:
    """Cf. WinDev SaveOpeStaff : concatene les ids en ';' et enregistre."""
    ids_clean = [str(int(x)) for x in id_salaries if str(x).strip().isdigit()]
    liste = ";".join(ids_clean)
    db = get_pg_connection("rh")
    try:
        r = db.query_one(
            """SELECT id_sms_animation FROM divers.pgt_smsanimation
                WHERE type_sms = ? LIMIT 1""",
            (_TYPE_SMS,),
        )
    except Exception:
        r = None
    if r:
        db.execute(
            """UPDATE divers.pgt_smsanimation
                  SET liste_num_staff = ?
                WHERE id_sms_animation = ?""",
            (liste, int(r.get("id_sms_animation") or 0)),
        )
    else:
        db.execute(
            """INSERT INTO divers.pgt_smsanimation
                  (id_sms_animation, type_sms, is_actif, liste_num_staff)
               VALUES (?, ?, FALSE, ?)""",
            (_new_id(), _TYPE_SMS, liste),
        )
    return True


# --------------------------------------------------------------------
# CRUD RegleEnvoi (tableau principal Fen_SMSPerf)
# --------------------------------------------------------------------

def _row_to_regle(r: dict) -> RegleEnvoi:
    return RegleEnvoi(
        id_regle=_clean_id(r.get("id_sms_animation_regle_envoi")),
        type_sms=(r.get("type_sms") or "").strip(),
        code_animation=(r.get("code_animation") or "").strip(),
        texte_sms=(r.get("texte_sms") or "").strip(),
        heure_envoi=_hh_from_int(r.get("heure_envoi")),
        heure_debut=_hh_from_int(r.get("heure_debut")),
        heure_fin=_hh_from_int(r.get("heure_fin")),
        ordre=int(r.get("ordre") or 0),
        sms_groupe=bool(r.get("sms_groupe")),
        partenaire=(r.get("partenaire") or "").strip(),
        prod_groupe=int(r.get("prod_groupe") or 1),
        periode_calcul=int(r.get("periode_calcul") or 1),
        nb_bs_min=int(r.get("nb_bs_min") or 1),
        is_actif=bool(r.get("is_actif")),
    )


def list_regles() -> list[RegleEnvoi]:
    """Cf. WinDev reqSmsAnimRegle : type_sms = 'Perf-Exo'.
    ORDER BY code_animation, ordre ASC.
    """
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT id_sms_animation_regle_envoi, type_sms, code_animation,
                      texte_sms, heure_envoi, heure_debut, heure_fin, ordre,
                      sms_groupe, partenaire, prod_groupe, periode_calcul,
                      nb_bs_min, is_actif
                 FROM divers.pgt_smsanimation_regleenvoi
                WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                  AND type_sms = ?
                ORDER BY code_animation ASC, ordre ASC""",
            (_TYPE_SMS,),
        ) or []
    except Exception:
        logger.exception("list_regles")
        return []
    return [_row_to_regle(r) for r in rows]


def create_regle(p: RegleEnvoiPayload, op_id: int) -> str:
    if not p.code_animation.strip():
        return ""
    new_id = _new_id()
    db = get_pg_connection("rh")
    db.execute(
        """INSERT INTO divers.pgt_smsanimation_regleenvoi
              (id_sms_animation_regle_envoi, type_sms, code_animation,
               texte_sms, heure_envoi, heure_debut, heure_fin, ordre,
               sms_groupe, partenaire, prod_groupe, periode_calcul,
               nb_bs_min, is_actif,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id, _TYPE_SMS, p.code_animation.strip(),
            p.texte_sms.strip(),
            int(p.heure_envoi), int(p.heure_debut), int(p.heure_fin),
            int(p.ordre),
            p.sms_groupe, p.partenaire.strip(),
            int(p.prod_groupe), int(p.periode_calcul),
            int(p.nb_bs_min), p.is_actif,
            int(op_id),
        ),
    )
    return str(new_id)


def update_regle(id_regle: str, p: RegleEnvoiPayload, op_id: int) -> bool:
    if not id_regle or id_regle == "0":
        return False
    db = get_pg_connection("rh")
    db.execute(
        """UPDATE divers.pgt_smsanimation_regleenvoi
              SET code_animation = ?, texte_sms = ?,
                  heure_envoi = ?, heure_debut = ?, heure_fin = ?,
                  ordre = ?, sms_groupe = ?, partenaire = ?,
                  prod_groupe = ?, periode_calcul = ?,
                  nb_bs_min = ?, is_actif = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_sms_animation_regle_envoi = ?""",
        (
            p.code_animation.strip(), p.texte_sms.strip(),
            int(p.heure_envoi), int(p.heure_debut), int(p.heure_fin),
            int(p.ordre), p.sms_groupe, p.partenaire.strip(),
            int(p.prod_groupe), int(p.periode_calcul),
            int(p.nb_bs_min), p.is_actif,
            int(op_id), int(id_regle),
        ),
    )
    return True


def delete_regle(id_regle: str, op_id: int) -> bool:
    if not id_regle or id_regle == "0":
        return False
    db = get_pg_connection("rh")
    db.execute(
        """UPDATE divers.pgt_smsanimation_regleenvoi
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_sms_animation_regle_envoi = ?""",
        (int(op_id), int(id_regle)),
    )
    return True


def duplicate_regle(id_regle: str, op_id: int) -> str:
    """Cf. WinDev Btn Duplique : HAjoute clone la ligne."""
    if not id_regle or id_regle == "0":
        return ""
    db = get_pg_connection("rh")
    r = db.query_one(
        """SELECT type_sms, code_animation, texte_sms, heure_envoi,
                  heure_debut, heure_fin, ordre, sms_groupe, partenaire,
                  prod_groupe, periode_calcul, nb_bs_min, is_actif
             FROM divers.pgt_smsanimation_regleenvoi
            WHERE id_sms_animation_regle_envoi = ?""",
        (int(id_regle),),
    )
    if not r:
        return ""
    new_id = _new_id()
    db.execute(
        """INSERT INTO divers.pgt_smsanimation_regleenvoi
              (id_sms_animation_regle_envoi, type_sms, code_animation,
               texte_sms, heure_envoi, heure_debut, heure_fin, ordre,
               sms_groupe, partenaire, prod_groupe, periode_calcul,
               nb_bs_min, is_actif,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id, r.get("type_sms") or _TYPE_SMS,
            r.get("code_animation") or "",
            r.get("texte_sms") or "",
            _hh_from_int(r.get("heure_envoi")),
            _hh_from_int(r.get("heure_debut")),
            _hh_from_int(r.get("heure_fin")),
            int(r.get("ordre") or 0),
            bool(r.get("sms_groupe")),
            r.get("partenaire") or "",
            int(r.get("prod_groupe") or 1),
            int(r.get("periode_calcul") or 1),
            int(r.get("nb_bs_min") or 1),
            bool(r.get("is_actif")),
            int(op_id),
        ),
    )
    return str(new_id)


# --------------------------------------------------------------------
# CRUD Destinataire (SmsAnimation_OrgaDest)
# --------------------------------------------------------------------

def list_destinataires(code_animation: str) -> list[DestinataireRow]:
    if not code_animation:
        return []
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT d.id_sms_animation_orga_dest, d.idorganigramme,
                      d.anim_code, d.du, d.au, d.is_actif,
                      o.lib_orga
                 FROM divers.pgt_smsanimation_orgadest d
                 LEFT JOIN pgt_organigramme o
                        ON o.idorganigramme = d.idorganigramme
                WHERE d.anim_code = ?
                  AND (d.modif_elem IS NULL OR d.modif_elem NOT LIKE '%suppr%')
                ORDER BY o.lib_orga ASC""",
            (code_animation.strip(),),
        ) or []
    except Exception:
        return []
    return [
        DestinataireRow(
            id_dest=_clean_id(r.get("id_sms_animation_orga_dest")),
            idorganigramme=_clean_id(r.get("idorganigramme")),
            lib_orga=(r.get("lib_orga") or "").strip(),
            anim_code=(r.get("anim_code") or "").strip(),
            du=_iso_date(r.get("du")),
            au=_iso_date(r.get("au")),
            is_actif=bool(r.get("is_actif")),
        )
        for r in rows
    ]


def create_destinataire(p: DestinatairePayload, op_id: int) -> str:
    db = get_pg_connection("rh")
    new_id = _new_id()
    db.execute(
        """INSERT INTO divers.pgt_smsanimation_orgadest
              (id_sms_animation_orga_dest, idorganigramme, anim_code,
               du, au, is_actif, modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id, int(p.idorganigramme),
            p.anim_code.strip(),
            (p.du[:10] if p.du else None),
            (p.au[:10] if p.au else None),
            p.is_actif, int(op_id),
        ),
    )
    return str(new_id)


def update_destinataire(
    id_dest: str, p: DestinatairePayload, op_id: int,
) -> bool:
    if not id_dest or id_dest == "0":
        return False
    db = get_pg_connection("rh")
    db.execute(
        """UPDATE divers.pgt_smsanimation_orgadest
              SET idorganigramme = ?, anim_code = ?,
                  du = ?, au = ?, is_actif = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_sms_animation_orga_dest = ?""",
        (
            int(p.idorganigramme), p.anim_code.strip(),
            (p.du[:10] if p.du else None),
            (p.au[:10] if p.au else None),
            p.is_actif, int(op_id), int(id_dest),
        ),
    )
    return True


def delete_destinataire(id_dest: str, op_id: int) -> bool:
    if not id_dest or id_dest == "0":
        return False
    db = get_pg_connection("rh")
    db.execute(
        """UPDATE divers.pgt_smsanimation_orgadest
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_sms_animation_orga_dest = ?""",
        (int(op_id), int(id_dest)),
    )
    return True


def duplicate_destinataire(id_dest: str, op_id: int) -> str:
    if not id_dest or id_dest == "0":
        return ""
    db = get_pg_connection("rh")
    r = db.query_one(
        """SELECT idorganigramme, anim_code, du, au, is_actif
             FROM divers.pgt_smsanimation_orgadest
            WHERE id_sms_animation_orga_dest = ?""",
        (int(id_dest),),
    )
    if not r:
        return ""
    new_id = _new_id()
    db.execute(
        """INSERT INTO divers.pgt_smsanimation_orgadest
              (id_sms_animation_orga_dest, idorganigramme, anim_code,
               du, au, is_actif, modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id, int(r.get("idorganigramme") or 0),
            r.get("anim_code") or "",
            r.get("du"), r.get("au"),
            bool(r.get("is_actif")),
            int(op_id),
        ),
    )
    return str(new_id)


# --------------------------------------------------------------------
# CRUD EquipeScore (SmsAnimation_OrgaPeriode)
# --------------------------------------------------------------------

def list_equipes_scores(code_animation: str) -> list[EquipeScoreRow]:
    if not code_animation:
        return []
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT p.id_sms_animation_orga, p.idorganigramme,
                      p.code_animation, p.type, p.du, p.au, p.is_actif,
                      o.lib_orga
                 FROM divers.pgt_sms_animation_orga_periode p
                 LEFT JOIN pgt_organigramme o
                        ON o.idorganigramme = p.idorganigramme
                WHERE p.code_animation = ?
                  AND p.type = ?
                  AND (p.modif_elem IS NULL OR p.modif_elem NOT LIKE '%suppr%')
                ORDER BY o.lib_orga ASC""",
            (code_animation.strip(), _TYPE_SMS),
        ) or []
    except Exception:
        return []
    return [
        EquipeScoreRow(
            id_orga_periode=_clean_id(r.get("id_sms_animation_orga")),
            idorganigramme=_clean_id(r.get("idorganigramme")),
            lib_orga=(r.get("lib_orga") or "").strip(),
            code_animation=(r.get("code_animation") or "").strip(),
            type=(r.get("type") or "").strip(),
            du=_iso_date(r.get("du")),
            au=_iso_date(r.get("au")),
            is_actif=bool(r.get("is_actif")),
        )
        for r in rows
    ]


def create_equipe_score(p: EquipeScorePayload, op_id: int) -> str:
    db = get_pg_connection("rh")
    new_id = _new_id()
    db.execute(
        """INSERT INTO divers.pgt_sms_animation_orga_periode
              (id_sms_animation_orga, idorganigramme, code_animation,
               type, du, au, is_actif,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id, int(p.idorganigramme),
            p.code_animation.strip(),
            p.type.strip() or _TYPE_SMS,
            (p.du[:10] if p.du else None),
            (p.au[:10] if p.au else None),
            p.is_actif, int(op_id),
        ),
    )
    return str(new_id)


def update_equipe_score(
    id_eq: str, p: EquipeScorePayload, op_id: int,
) -> bool:
    if not id_eq or id_eq == "0":
        return False
    db = get_pg_connection("rh")
    db.execute(
        """UPDATE divers.pgt_sms_animation_orga_periode
              SET idorganigramme = ?, code_animation = ?,
                  type = ?, du = ?, au = ?, is_actif = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_sms_animation_orga = ?""",
        (
            int(p.idorganigramme), p.code_animation.strip(),
            p.type.strip() or _TYPE_SMS,
            (p.du[:10] if p.du else None),
            (p.au[:10] if p.au else None),
            p.is_actif, int(op_id), int(id_eq),
        ),
    )
    return True


def delete_equipe_score(id_eq: str, op_id: int) -> bool:
    if not id_eq or id_eq == "0":
        return False
    db = get_pg_connection("rh")
    db.execute(
        """UPDATE divers.pgt_sms_animation_orga_periode
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_sms_animation_orga = ?""",
        (int(op_id), int(id_eq)),
    )
    return True


def duplicate_equipe_score(id_eq: str, op_id: int) -> str:
    if not id_eq or id_eq == "0":
        return ""
    db = get_pg_connection("rh")
    r = db.query_one(
        """SELECT idorganigramme, code_animation, type, du, au, is_actif
             FROM divers.pgt_sms_animation_orga_periode
            WHERE id_sms_animation_orga = ?""",
        (int(id_eq),),
    )
    if not r:
        return ""
    new_id = _new_id()
    db.execute(
        """INSERT INTO divers.pgt_sms_animation_orga_periode
              (id_sms_animation_orga, idorganigramme, code_animation,
               type, du, au, is_actif,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id, int(r.get("idorganigramme") or 0),
            r.get("code_animation") or "",
            r.get("type") or _TYPE_SMS,
            r.get("du"), r.get("au"),
            bool(r.get("is_actif")),
            int(op_id),
        ),
    )
    return str(new_id)
