"""
Service Fen_ScoolBulletin - Fiche bulletin S'Cool.

Cf. WinDev Fen_ScoolBulletin (Code Init + CalculProdSFR + CalculProdCoopt
+ CalculPresence + CalculerNotes + Btn Enregistrer).

3 procs principales :
1. list_stagiaires : combo stagiaires d'une formation
2. recuperer_prod : compte contrats SFR + cooptations + presences
3. calculer_notes : applique le bareme sur les taux calcules
"""
from __future__ import annotations

import logging
from datetime import datetime

from app.core.database.pg import get_pg_connection
from app.intranets.adm.schemas.scool_bulletin import (
    BulletinDetail, BulletinPayload, CalculerNotesParams,
    CalculerNotesResult, MentionCombo, NoteCalculee,
    RecupererProdParams, RecupererProdResult,
    StagiaireBulletinCombo,
)

logger = logging.getLogger(__name__)


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
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


# --------------------------------------------------------------------
# Combos
# --------------------------------------------------------------------

def list_stagiaires_formation(id_formation: str) -> list[StagiaireBulletinCombo]:
    """Cf. WinDev reqStagiaire (Code Init de Fen_ScoolBulletin) :
    Formation_salarie JOIN salarie [+ TypeSortieSalarie].
    Format 'NOM Prenom - Lib_Sortie' (si sortie).
    """
    if not id_formation or id_formation == "0":
        return []
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT DISTINCT fs.id_salarie, s.nom, s.prenom,
                      ts.lib_sortie
                 FROM scool.pgt_formation_salarie fs
                 JOIN pgt_salarie s ON s.id_salarie = fs.id_salarie
                 LEFT JOIN pgt_salarie_sortie ss
                        ON ss.id_salarie = fs.id_salarie
                       AND (ss.modif_elem IS NULL
                            OR ss.modif_elem NOT LIKE '%suppr%')
                 LEFT JOIN pgt_type_sortie_salarie ts
                        ON ts.id_type_sortie = ss.id_type_sortie
                WHERE fs.id_formation = ?
                  AND (fs.modif_elem IS NULL
                       OR fs.modif_elem NOT LIKE '%suppr%')
                ORDER BY s.nom ASC, s.prenom ASC""",
            (int(id_formation),),
        ) or []
    except Exception:
        logger.exception("list_stagiaires_formation")
        return []
    out: list[StagiaireBulletinCombo] = []
    for r in rows:
        nom = (r.get("nom") or "").strip()
        prenom = _cap_prenom((r.get("prenom") or "").strip())
        lib_sortie = (r.get("lib_sortie") or "").strip()
        libelle = f"{nom} {prenom}"
        if lib_sortie:
            libelle += f" - {lib_sortie}"
        out.append(StagiaireBulletinCombo(
            id_salarie=_clean_id(r.get("id_salarie")),
            nom_prenom=libelle,
        ))
    return out


def list_mentions() -> list[MentionCombo]:
    db = get_pg_connection("scool")
    try:
        rows = db.query(
            """SELECT id_bulletin_mention, lib_mention
                 FROM scool.pgt_bulletin_mention
                WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY id_bulletin_mention ASC""",
        ) or []
    except Exception:
        return []
    return [
        MentionCombo(
            id_bulletin_mention=str(r.get("id_bulletin_mention")),
            lib_mention=(r.get("lib_mention") or "").strip(),
        )
        for r in rows
    ]


# --------------------------------------------------------------------
# Detail bulletin / defaut initial
# --------------------------------------------------------------------

def get_bulletin(id_bulletin: str) -> BulletinDetail | None:
    if not id_bulletin or id_bulletin == "0":
        return None
    db = get_pg_connection("scool")
    try:
        r = db.query_one(
            """SELECT * FROM scool.pgt_formation_bulletin
                WHERE id_formation_bulletin = ?""",
            (int(id_bulletin),),
        )
    except Exception:
        return None
    if not r:
        return None
    return BulletinDetail(
        id_bulletin=_clean_id(r.get("id_formation_bulletin")),
        id_formation=_clean_id(r.get("id_formation")),
        id_salarie=_clean_id(r.get("id_salarie")),
        du=_iso_date(r.get("du")),
        au=_iso_date(r.get("au")),
        type_bulletin=int(r.get("type_bulletin") or 0),
        nb_jours_form=int(r.get("nb_jours_form") or 0),
        nb_jours_pres=int(r.get("nb_jours_pres") or 0),
        objectif_ctt=int(r.get("objectif_ctt") or 0),
        objectif_decale=int(r.get("objectif_decale") or 0),
        objectif_coopt=int(r.get("objectif_coopt") or 0),
        nb_ctt_hr=int(r.get("nb_ctt_hr") or 0),
        nb_cqt_hr=int(r.get("nb_cqt_hr") or 0),
        nb_prem_hr=int(r.get("nb_prem_hr") or 0),
        nb_mob_hr=int(r.get("nb_mob_hr") or 0),
        nb_coopt=int(r.get("nb_coopt") or 0),
        note_assiduite=float(r.get("note_assiduite") or 0),
        note_ctt_hr=float(r.get("note_ctt_hr") or 0),
        note_cqt=float(r.get("note_cqt") or 0),
        note_prem=float(r.get("note_prem") or 0),
        note_mob=float(r.get("note_mob") or 0),
        note_coopt=float(r.get("note_coopt") or 0),
        note_obj_decale=float(r.get("note_obj_decale") or 0),
        note_app_theo=float(r.get("note_app_theo") or 0),
        note_app_pratique=float(r.get("note_app_pratique") or 0),
        id_bulletin_mention=str(r.get("id_bulletin_mention") or 0),
        observation=(r.get("observation") or "").strip(),
        axe_travail=(r.get("axe_travail") or "").strip(),
    )


def initial_bulletin(
    id_formation: str, id_salarie: str,
) -> BulletinDetail:
    """Cf. WinDev Code Init (branche IdBulletin = 0) :
    charge Formation pour date_debut = Du et cherche derniere date Bilan
    ou Remise Diplome dans le programme <= aujourd'hui pour Au.
    """
    d = BulletinDetail(
        id_formation=id_formation, id_salarie=id_salarie,
    )
    if not id_formation:
        return d
    scool = get_pg_connection("scool")
    try:
        f = scool.query_one(
            """SELECT date_debut, date_fin
                 FROM scool.pgt_formation
                WHERE id_formation = ?""",
            (int(id_formation),),
        )
    except Exception:
        f = None
    if not f:
        return d
    d.du = _iso_date(f.get("date_debut"))

    # Cherche derniere date Bilan/Remise Diplome <= now
    from datetime import date as _date
    today_iso = _date.today().isoformat()
    try:
        r = scool.query_one(
            """SELECT date FROM scool.pgt_formation_programme
                WHERE id_formation = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                  AND (UPPER(horaires) LIKE '%BILAN%'
                       OR UPPER(horaires) LIKE '%REMISE%DIPLOME%')
                  AND date <= ?
                ORDER BY date DESC
                LIMIT 1""",
            (int(id_formation), today_iso),
        )
    except Exception:
        r = None
    if r:
        d.au = _iso_date(r.get("date"))
    else:
        d.au = _iso_date(f.get("date_fin"))
    return d


# --------------------------------------------------------------------
# CRUD bulletin
# --------------------------------------------------------------------

def _dt(v: str):
    return v[:10] if v and len(v) >= 10 else None


def create_bulletin(p: BulletinPayload, op_id: int) -> str:
    if not p.id_formation or not p.id_salarie:
        return ""
    db = get_pg_connection("scool")
    new_id = _new_id()
    try:
        db.execute(
            """INSERT INTO scool.pgt_formation_bulletin
                  (id_formation_bulletin, id_formation, id_salarie,
                   du, au, type_bulletin,
                   nb_jours_form, nb_jours_pres,
                   objectif_ctt, objectif_decale, objectif_coopt,
                   nb_ctt_hr, nb_cqt_hr, nb_prem_hr, nb_mob_hr, nb_coopt,
                   note_assiduite, note_ctt_hr, note_cqt, note_prem,
                   note_mob, note_coopt, note_obj_decale,
                   note_app_theo, note_app_pratique,
                   id_bulletin_mention, observation, axe_travail,
                   modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?,
                       ?, ?, ?, ?,
                       ?, ?, ?,
                       ?, ?,
                       ?, ?, ?,
                       NOW(), ?, 'new')""",
            (
                new_id, int(p.id_formation), int(p.id_salarie),
                _dt(p.du), _dt(p.au), int(p.type_bulletin),
                int(p.nb_jours_form), int(p.nb_jours_pres),
                int(p.objectif_ctt), int(p.objectif_decale),
                int(p.objectif_coopt),
                int(p.nb_ctt_hr), int(p.nb_cqt_hr), int(p.nb_prem_hr),
                int(p.nb_mob_hr), int(p.nb_coopt),
                float(p.note_assiduite), float(p.note_ctt_hr),
                float(p.note_cqt), float(p.note_prem),
                float(p.note_mob), float(p.note_coopt),
                float(p.note_obj_decale),
                float(p.note_app_theo), float(p.note_app_pratique),
                int(p.id_bulletin_mention or 0),
                p.observation.strip(), p.axe_travail.strip(),
                int(op_id),
            ),
        )
    except Exception:
        logger.exception("create_bulletin")
        return ""
    return str(new_id)


def update_bulletin(
    id_bulletin: str, p: BulletinPayload, op_id: int,
) -> bool:
    if not id_bulletin or id_bulletin == "0":
        return False
    db = get_pg_connection("scool")
    try:
        db.execute(
            """UPDATE scool.pgt_formation_bulletin
                  SET du = ?, au = ?, type_bulletin = ?,
                      nb_jours_form = ?, nb_jours_pres = ?,
                      objectif_ctt = ?, objectif_decale = ?,
                      objectif_coopt = ?,
                      nb_ctt_hr = ?, nb_cqt_hr = ?, nb_prem_hr = ?,
                      nb_mob_hr = ?, nb_coopt = ?,
                      note_assiduite = ?, note_ctt_hr = ?, note_cqt = ?,
                      note_prem = ?, note_mob = ?, note_coopt = ?,
                      note_obj_decale = ?,
                      note_app_theo = ?, note_app_pratique = ?,
                      id_bulletin_mention = ?, observation = ?,
                      axe_travail = ?,
                      modif_date = NOW(), modif_op = ?,
                      modif_elem = 'modif'
                WHERE id_formation_bulletin = ?""",
            (
                _dt(p.du), _dt(p.au), int(p.type_bulletin),
                int(p.nb_jours_form), int(p.nb_jours_pres),
                int(p.objectif_ctt), int(p.objectif_decale),
                int(p.objectif_coopt),
                int(p.nb_ctt_hr), int(p.nb_cqt_hr), int(p.nb_prem_hr),
                int(p.nb_mob_hr), int(p.nb_coopt),
                float(p.note_assiduite), float(p.note_ctt_hr),
                float(p.note_cqt), float(p.note_prem),
                float(p.note_mob), float(p.note_coopt),
                float(p.note_obj_decale),
                float(p.note_app_theo), float(p.note_app_pratique),
                int(p.id_bulletin_mention or 0),
                p.observation.strip(), p.axe_travail.strip(),
                int(op_id), int(id_bulletin),
            ),
        )
    except Exception:
        logger.exception("update_bulletin")
        return False
    return True


# --------------------------------------------------------------------
# Calcul prod (SFR + Coopt + Presence)
# --------------------------------------------------------------------

def _calc_prod_sfr(id_salarie: int, du: str, au: str) -> dict:
    """Cf. WinDev CalculProdSFR : compte contrats SFR Fibre/Mob par
    stagiaire dans la periode.
    """
    out = {"ctt_hr": 0, "cqt_hr": 0, "prem_hr": 0, "mob_hr": 0}
    if not du or not au:
        return out
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT COUNT(c.id_contrat) AS nbctt,
                      p.famille, p.sous_fam, e.id_type_etat,
                      e.id_etat, c.type_vente
                 FROM adv.pgt_sfr_produit p
                 JOIN adv.pgt_sfr_contrat c ON c.id_produit = p.id_produit
                 JOIN adv.pgt_sfr_etat_contrat e ON e.id_etat = c.id_etat_contrat
                WHERE (c.modif_elem IS NULL
                       OR c.modif_elem NOT LIKE '%suppr%')
                  AND c.id_salarie = ?
                  AND c.date_signature BETWEEN ? AND ?
                  AND e.id_type_etat <> 9
                  AND (e.id_type_etat <> 3 OR e.id_etat = 26)
                GROUP BY p.famille, p.sous_fam, e.id_type_etat,
                         e.id_etat, c.type_vente""",
            (id_salarie, du, au),
        ) or []
    except Exception:
        logger.exception("_calc_prod_sfr")
        return out
    for r in rows:
        fam = (r.get("famille") or "").strip()
        sous_fam = (r.get("sous_fam") or "").strip()
        etat = int(r.get("id_type_etat") or 0)
        type_vente = int(r.get("type_vente") or 0)
        n = int(r.get("nbctt") or 0)
        if fam == "FIBRE":
            if etat != 3:
                out["ctt_hr"] += n
                if sous_fam == "Premium":
                    out["prem_hr"] += n
                if type_vente in (1, 2):
                    out["cqt_hr"] += n
        else:
            out["mob_hr"] += n
    return out


def _calc_prod_coopt(id_salarie: int, du: str, au: str) -> int:
    """Cf. WinDev CalculProdCoopt."""
    if not du or not au:
        return 0
    rh = get_pg_connection("rh")
    try:
        r = rh.query_one(
            """SELECT COUNT(*) AS n
                 FROM recrutement.pgt_cvtheque
                WHERE id_cvsource = 1
                  AND id_elem_source = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                  AND date_saisie BETWEEN ? AND ?""",
            (id_salarie, du, au),
        )
    except Exception:
        return 0
    return int(r.get("n") or 0) if r else 0


def _calc_presence(
    id_formation: int, id_salarie: int, au: str,
) -> tuple[int, int]:
    """Cf. WinDev CalculPresence : parcourt le programme, compte les
    jours de formation + les presences.
    Return : (nb_jours_form, res_note_assiduite = nb_presents)
    """
    scool = get_pg_connection("scool")
    rh = get_pg_connection("rh")

    try:
        progs = scool.query(
            """SELECT date FROM scool.pgt_formation_programme
                WHERE id_formation = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                  AND date <= ?
                ORDER BY date ASC""",
            (id_formation, au),
        ) or []
    except Exception:
        return (0, 0)

    nb_jours_form = 0
    res_presence = 0
    for prog in progs:
        d = _iso_date(prog.get("date"))
        if not d:
            continue
        nb_jours_form += 1
        # Test decl presence
        try:
            decl = rh.query_one(
                """SELECT presence, motifabsence
                     FROM pgt_salarie_decl_presence
                    WHERE date = ? AND id_salarie = ?""",
                (d, id_salarie),
            )
        except Exception:
            decl = None
        if not decl:
            test_pres = True
        else:
            test_pres = bool(decl.get("presence"))
            if not test_pres and int(decl.get("motifabsence") or 0) == 6:
                test_pres = True
            if test_pres:
                # Verifie absence
                try:
                    abs_row = rh.query_one(
                        """SELECT id_absence FROM pgt_absence
                            WHERE id_salarie = ?
                              AND date_debut <= ? AND date_fin >= ?
                              AND (modif_elem IS NULL
                                   OR modif_elem NOT LIKE '%suppr%')
                            LIMIT 1""",
                        (id_salarie, d, d),
                    )
                except Exception:
                    abs_row = None
                if abs_row:
                    test_pres = False
        if test_pres:
            res_presence += 1
    return (nb_jours_form, res_presence)


def recuperer_prod(p: RecupererProdParams) -> RecupererProdResult:
    """Cf. WinDev Btn Recuperer la prod et les absences."""
    if not p.id_formation or not p.id_salarie:
        return RecupererProdResult(ok=False)
    id_form = int(p.id_formation)
    id_sal = int(p.id_salarie)

    sfr = _calc_prod_sfr(id_sal, p.du, p.au)
    coopt = _calc_prod_coopt(id_sal, p.du, p.au)
    nb_jours_form, res_pres = _calc_presence(id_form, id_sal, p.au)

    return RecupererProdResult(
        ok=True,
        nb_jours_form=nb_jours_form,
        nb_jours_pres=res_pres,
        res_note_ctt_hr=sfr["ctt_hr"],
        res_note_cqt=sfr["cqt_hr"],
        res_note_prem=sfr["prem_hr"],
        res_note_mob=sfr["mob_hr"],
        res_note_coopt=coopt,
    )


# --------------------------------------------------------------------
# Calcul notes (avec bareme)
# --------------------------------------------------------------------

_LIB_BY_TYPE = {
    "NoteAssiduite": "Assiduité",
    "NoteCttHR": "Objectif Ctt",
    "NoteCQT": "Conquête",
    "NotePREM": "Premium",
    "NoteMOB": "Mobile",
    "NoteCoopt": "Cooptation",
    "NoteObjDécalé": "Objectif Décalé",
    "NoteObjDecale": "Objectif Décalé",
}


def _lookup_note(
    db, id_formation: int, type_note: str, palier_calc: float,
    sens: str,
) -> float:
    """Cherche la note dans le bareme selon palier_calc + sens."""
    if sens.upper() == "DESC":
        op = "<="
        order = "DESC"
    else:
        op = ">="
        order = "ASC"
    try:
        r = db.query_one(
            f"""SELECT note FROM scool.pgt_formation_bareme_note
                 WHERE id_formation = ?
                   AND type_note = ?
                   AND palier {op} ?
                   AND (modif_elem IS NULL
                        OR modif_elem NOT LIKE '%suppr%')
                   AND type_note NOT LIKE 'NoteAPP%'
                 ORDER BY palier {order}
                 LIMIT 1""",
            (id_formation, type_note, palier_calc),
        )
    except Exception:
        return 0.0
    if not r:
        return 0.0
    return float(r.get("note") or 0)


def calculer_notes(p: CalculerNotesParams) -> CalculerNotesResult:
    """Cf. WinDev Btn CalculerNotes.

    Calcule 7 taux/paliers puis applique le bareme de la formation
    pour chaque type_note actif.
    """
    if not p.id_formation:
        return CalculerNotesResult(ok=False)

    # 7 paliers cf. WinDev CalculerNotes
    obj_ctt = max(1, p.objectif_ctt)
    obj_coopt = max(1, p.objectif_coopt)
    paliers: dict[str, float] = {
        # nb_jours_form - res_note_assiduite (= nb_absences saisi)
        "NoteAssiduite": float(p.nb_absences),
        "NoteCttHR": (p.res_note_ctt_hr / obj_ctt) * 100,
        "NoteCoopt": (p.res_note_coopt / obj_coopt) * 100,
        "NoteObjDécalé": float(p.objectif_decale),
    }
    if p.res_note_ctt_hr > 0:
        paliers["NoteCQT"] = (p.res_note_cqt / p.res_note_ctt_hr) * 100
        paliers["NotePREM"] = (
            p.res_note_prem / p.res_note_ctt_hr
        ) * 100
    else:
        paliers["NoteCQT"] = 0
        paliers["NotePREM"] = 0

    total_mob_ctt = p.res_note_ctt_hr + p.res_note_mob
    if total_mob_ctt > 0:
        paliers["NoteMOB"] = (p.res_note_mob / total_mob_ctt) * 100
    else:
        paliers["NoteMOB"] = 0

    # Charge les types de note actifs pour cette formation
    db = get_pg_connection("scool")
    try:
        rows = db.query(
            """SELECT DISTINCT type_note, sens_recherche
                 FROM scool.pgt_formation_bareme_note
                WHERE id_formation = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
            (int(p.id_formation),),
        ) or []
    except Exception:
        rows = []

    out: list[NoteCalculee] = []
    for r in rows:
        type_note = (r.get("type_note") or "").strip()
        if not type_note or type_note.startswith("NoteAPP"):
            continue
        sens = (r.get("sens_recherche") or "ASC").strip() or "ASC"
        palier_calc = paliers.get(type_note, 0)
        note = _lookup_note(
            db, int(p.id_formation), type_note, palier_calc, sens,
        )
        out.append(NoteCalculee(
            type_note=type_note,
            lib_note=_LIB_BY_TYPE.get(type_note, type_note),
            palier_calc=round(palier_calc, 2),
            note=note,
        ))

    return CalculerNotesResult(ok=True, notes=out)
