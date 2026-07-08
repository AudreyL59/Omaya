"""
Service Fen_ScoolFormation - Gestion des formations S'Cool.

Cf. WinDev Fen_ScoolFormation :
- Liste des formations (Liste_FormationScool)
- CRUD : Nouvelle / Dupliquer / Editer / Supprimer
- Modeles de formation (Fen_ScoolFormModele)
"""
from __future__ import annotations

import logging
from datetime import datetime

from datetime import timedelta

from app.core.database.pg import get_pg_connection
from app.intranets.adm.schemas.scool_formation import (
    AnalyseFormationResult, AnalysePromoParams,
    BaremeNotePayload, BaremeNoteRow, BulletinRow,
    ConvertirModelePayload, EffectifRow,
    EleveAjoutPayload, EleveRow,
    EvenementPayload, EvenementRow,
    FormateurCombo, FormationDetail,
    FormationPayload, FormationRow, ListeFormationsParams,
    ModeleFormationCombo, ModeleFormationPayload, ModeleFormationRow,
    ModeleProgrammePayload, ModeleProgrammeRow,
    ProgrammePayload, ProgrammeRow,
    SessionRecrutPayload, SessionRecrutRow,
    StagiaireRow,
)


_JOURS_FERIES_FR = {
    # dates recurrentes (jour, mois)
    (1, 1), (1, 5), (8, 5), (14, 7), (15, 8),
    (1, 11), (11, 11), (25, 12),
}

logger = logging.getLogger(__name__)


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
    """ID timestamp WinDev-style (cf. idEntierDateHeureSys)."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


def _is_ferie_fr(d) -> bool:
    """Retourne True si jour ferie fixe FR (approximation, sans Paques)."""
    if d is None:
        return False
    return (d.day, d.month) in _JOURS_FERIES_FR


def _next_working_day(d):
    """Cf. WinDev : si samedi/dimanche/ferie, avance jusqu'au prochain jour ouvre."""
    from datetime import date as _date
    while d.weekday() > 4 or _is_ferie_fr(d):
        d = d + timedelta(days=1)
    return d


def _formateur_lib(id_sal: str) -> str:
    """Format 'Prenom N' pour un formateur."""
    if not id_sal or id_sal == "0":
        return ""
    try:
        id_int = int(id_sal)
    except (TypeError, ValueError):
        return ""
    if not id_int:
        return ""
    db = get_pg_connection("rh")
    try:
        r = db.query_one(
            "SELECT nom, prenom FROM pgt_salarie WHERE id_salarie = ?",
            (id_int,),
        )
    except Exception:
        return ""
    if not r:
        return ""
    nom = (r.get("nom") or "").strip()
    prenom = _cap_prenom((r.get("prenom") or "").strip())
    if nom and prenom:
        return f"{prenom} {nom[0].upper()}"
    return prenom or nom


# --------------------------------------------------------------------
# Liste formations
# --------------------------------------------------------------------

def list_formations(p: ListeFormationsParams) -> list[FormationRow]:
    """Cf. WinDev Tableau Liste_FormationScool : SELECT Formation avec
    filtre date_fin >= afficher_depuis_le + formation_active.
    """
    db = get_pg_connection("scool")
    conditions = ["(f.modif_elem IS NULL OR f.modif_elem NOT LIKE '%suppr%')"]
    params: list = []
    if p.afficher_depuis_le and len(p.afficher_depuis_le) >= 10:
        # date_fin >= param OU date_fin NULL (formations non terminees)
        conditions.append("(f.date_fin >= ? OR f.date_fin IS NULL)")
        params.append(p.afficher_depuis_le[:10])
    if p.uniquement_actives:
        conditions.append("f.formation_active = TRUE")
    where = " AND ".join(conditions)
    try:
        rows = db.query(
            f"""SELECT f.id_formation, f.intitule,
                       f.date_debut, f.date_fin,
                       f.ville_formation, f.type_produit,
                       f.categorie,
                       f.formateur1, f.formateur2,
                       f.nb_heure_salle, f.nb_heure_terrain,
                       f.heure_jour_salle, f.heure_jour_terrain,
                       f.duree, f.formation_active, f.formation_cloturee
                  FROM scool.pgt_formation f
                 WHERE {where}
                 ORDER BY f.date_debut DESC NULLS LAST, f.intitule ASC""",
            tuple(params),
        ) or []
    except Exception:
        logger.exception("list_formations")
        return []

    # Enrichit avec libelles formateurs
    formateur_ids: set[str] = set()
    for r in rows:
        for k in ("formateur1", "formateur2"):
            v = _clean_id(r.get(k))
            if v:
                formateur_ids.add(v)
    libs: dict[str, str] = {}
    if formateur_ids:
        rh = get_pg_connection("rh")
        try:
            placeholders = ",".join(["?"] * len(formateur_ids))
            f_rows = rh.query(
                f"""SELECT id_salarie, nom, prenom FROM pgt_salarie
                     WHERE id_salarie IN ({placeholders})""",
                tuple(int(x) for x in formateur_ids),
            ) or []
        except Exception:
            f_rows = []
        for fr in f_rows:
            nom = (fr.get("nom") or "").strip()
            prenom = _cap_prenom((fr.get("prenom") or "").strip())
            libs[str(int(fr.get("id_salarie") or 0))] = (
                f"{prenom} {nom[0].upper()}" if nom and prenom else prenom or nom
            )

    return [
        FormationRow(
            id_formation=_clean_id(r.get("id_formation")),
            intitule=(r.get("intitule") or "").strip(),
            date_debut=_iso_date(r.get("date_debut")),
            date_fin=_iso_date(r.get("date_fin")),
            ville_formation=(r.get("ville_formation") or "").strip(),
            type_produit=(r.get("type_produit") or "").strip(),
            categorie=(r.get("categorie") or "").strip(),
            formateur1_nom=libs.get(_clean_id(r.get("formateur1")), ""),
            formateur2_nom=libs.get(_clean_id(r.get("formateur2")), ""),
            nb_heure_salle=int(r.get("nb_heure_salle") or 0),
            nb_heure_terrain=int(r.get("nb_heure_terrain") or 0),
            heure_jour_salle=int(r.get("heure_jour_salle") or 0),
            heure_jour_terrain=int(r.get("heure_jour_terrain") or 0),
            duree=int(r.get("duree") or 0),
            formation_active=bool(r.get("formation_active")),
            formation_cloturee=bool(r.get("formation_cloturee")),
        )
        for r in rows
    ]


# --------------------------------------------------------------------
# Detail formation
# --------------------------------------------------------------------

def get_formation(id_formation: str) -> FormationDetail | None:
    if not id_formation or id_formation == "0":
        return None
    db = get_pg_connection("scool")
    try:
        r = db.query_one(
            """SELECT f.*
                 FROM scool.pgt_formation f
                WHERE f.id_formation = ?""",
            (int(id_formation),),
        )
    except Exception:
        return None
    if not r:
        return None
    return FormationDetail(
        id_formation=_clean_id(r.get("id_formation")),
        intitule=(r.get("intitule") or "").strip(),
        date_debut=_iso_date(r.get("date_debut")),
        date_fin=_iso_date(r.get("date_fin")),
        ville_formation=(r.get("ville_formation") or "").strip(),
        type_produit=(r.get("type_produit") or "").strip(),
        categorie=(r.get("categorie") or "").strip(),
        dest_promo=(r.get("dest_promo") or "").strip(),
        formateur1_id=_clean_id(r.get("formateur1")),
        formateur2_id=_clean_id(r.get("formateur2")),
        formateur3_id=_clean_id(r.get("formateur3")),
        formateur4_id=_clean_id(r.get("formateur4")),
        formateur5_id=_clean_id(r.get("formateur5")),
        formateur1_nom=_formateur_lib(_clean_id(r.get("formateur1"))),
        formateur2_nom=_formateur_lib(_clean_id(r.get("formateur2"))),
        formateur3_nom=_formateur_lib(_clean_id(r.get("formateur3"))),
        formateur4_nom=_formateur_lib(_clean_id(r.get("formateur4"))),
        formateur5_nom=_formateur_lib(_clean_id(r.get("formateur5"))),
        nb_heure_salle=int(r.get("nb_heure_salle") or 0),
        nb_heure_terrain=int(r.get("nb_heure_terrain") or 0),
        heure_jour_salle=int(r.get("heure_jour_salle") or 0),
        heure_jour_terrain=int(r.get("heure_jour_terrain") or 0),
        duree=int(r.get("duree") or 0),
        formation_active=bool(r.get("formation_active")),
        formation_cloturee=bool(r.get("formation_cloturee")),
    )


# --------------------------------------------------------------------
# CRUD
# --------------------------------------------------------------------

def _to_date_or_none(v: str):
    return v[:10] if v and len(v) >= 10 else None


def _to_int_id(v: str) -> int:
    try:
        return int(v) if v and v != "0" else 0
    except (TypeError, ValueError):
        return 0


def create_formation(p: FormationPayload, op_id: int) -> str:
    """Cf. WinDev Btn Enregistrer de Fen_ScoolFormation_Ajout.

    Si p.id_modele_form != '0' :
    - Clone les lignes de scool.pgt_form_modele_programme dans
      scool.pgt_formation_programme (une par ligne modele)
    - Skip WE + jours feries (avance au prochain jour ouvre)
    - Recalcule date_fin = derniere date creee
    - Recalcule nb_heure_salle + nb_heure_terrain + duree = somme
    """
    if not p.intitule.strip():
        return ""

    # Force date_fin = date_debut si invalide ou < date_debut (cf. WinDev)
    date_debut = _to_date_or_none(p.date_debut)
    date_fin = _to_date_or_none(p.date_fin)
    if date_debut and (not date_fin or date_fin < date_debut):
        date_fin = date_debut

    new_id = _new_id()
    db = get_pg_connection("scool")
    db.execute(
        """INSERT INTO scool.pgt_formation
              (id_formation, intitule,
               date_debut, date_fin,
               ville_formation, type_produit, categorie,
               dest_promo,
               formateur1, formateur2, formateur3, formateur4, formateur5,
               nb_heure_salle, nb_heure_terrain,
               heure_jour_salle, heure_jour_terrain,
               duree, formation_active, formation_cloturee,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                   ?, ?, NOW(), ?, 'new')""",
        (
            new_id, p.intitule.strip(),
            date_debut, date_fin,
            p.ville_formation.strip(),
            p.type_produit.strip(),
            p.categorie.strip(),
            p.dest_promo.strip(),
            _to_int_id(p.formateur1_id),
            _to_int_id(p.formateur2_id),
            _to_int_id(p.formateur3_id),
            _to_int_id(p.formateur4_id),
            _to_int_id(p.formateur5_id),
            int(p.nb_heure_salle), int(p.nb_heure_terrain),
            int(p.heure_jour_salle), int(p.heure_jour_terrain),
            int(p.duree), p.formation_active, p.formation_cloturee,
            int(op_id),
        ),
    )

    # Clone programme si modele fourni
    id_modele = _to_int_id(p.id_modele_form)
    if id_modele and date_debut:
        _apply_modele_programme(
            new_id, id_modele, date_debut, op_id,
        )

    return str(new_id)


def _apply_modele_programme(
    id_formation: int, id_modele_form: int, date_debut_str: str, op_id: int,
) -> None:
    """Cf. WinDev partie 'si Combo_ModeleForm <>0' de Btn Enregistrer.

    Clone chaque ligne de pgt_form_modele_programme dans
    pgt_formation_programme. Avance de 1 jour ouvre par ligne (skip
    WE + feries FR). Puis met a jour la formation : date_fin,
    nb_heure_salle, nb_heure_terrain, duree.
    """
    from datetime import date as _date, datetime as _dt

    db = get_pg_connection("scool")
    try:
        progs = db.query(
            """SELECT date, salle, terrain, duree, horaires
                 FROM scool.pgt_form_modele_programme
                WHERE id_modele_form = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY date ASC""",
            (id_modele_form,),
        ) or []
    except Exception:
        logger.exception("_apply_modele_programme")
        return
    if not progs:
        return

    try:
        cur_date = _dt.strptime(date_debut_str[:10], "%Y-%m-%d").date()
    except Exception:
        return

    sem_ref = cur_date.isocalendar()[1] - 1
    nb_h_salle = 0
    nb_h_terrain = 0
    last_date = cur_date

    for prog in progs:
        # Skip WE / feries
        cur_date = _next_working_day(cur_date)
        salle = int(prog.get("salle") or 0)
        terrain = int(prog.get("terrain") or 0)
        duree = int(prog.get("duree") or 0)
        horaires = (prog.get("horaires") or "").strip()

        num_sem = cur_date.isocalendar()[1] - sem_ref
        if num_sem < 1:
            num_sem = 1

        try:
            db.execute(
                """INSERT INTO scool.pgt_formation_programme
                      (id_formation_programme, id_formation,
                       num_semaine, date, salle, terrain, duree,
                       horaires, objectif,
                       modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0,
                           NOW(), ?, 'new')""",
                (
                    _new_id(), id_formation, num_sem,
                    cur_date.isoformat(),
                    salle, terrain, duree, horaires,
                    op_id,
                ),
            )
        except Exception:
            logger.exception("INSERT programme %s", id_formation)

        nb_h_salle += salle
        nb_h_terrain += terrain
        last_date = cur_date
        cur_date = cur_date + timedelta(days=1)

    # Met a jour la formation : date_fin + heures + duree
    try:
        db.execute(
            """UPDATE scool.pgt_formation
                  SET date_fin = ?, nb_heure_salle = ?,
                      nb_heure_terrain = ?, duree = ?,
                      modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
                WHERE id_formation = ?""",
            (
                last_date.isoformat(), nb_h_salle,
                nb_h_terrain, nb_h_salle + nb_h_terrain,
                op_id, id_formation,
            ),
        )
    except Exception:
        logger.exception("UPDATE formation apres modele %s", id_formation)


def update_formation(
    id_formation: str, p: FormationPayload, op_id: int,
) -> bool:
    if not id_formation or id_formation == "0":
        return False
    db = get_pg_connection("scool")
    db.execute(
        """UPDATE scool.pgt_formation
              SET intitule = ?,
                  date_debut = ?, date_fin = ?,
                  ville_formation = ?, type_produit = ?, categorie = ?,
                  dest_promo = ?,
                  formateur1 = ?, formateur2 = ?, formateur3 = ?,
                  formateur4 = ?, formateur5 = ?,
                  nb_heure_salle = ?, nb_heure_terrain = ?,
                  heure_jour_salle = ?, heure_jour_terrain = ?,
                  duree = ?,
                  formation_active = ?, formation_cloturee = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_formation = ?""",
        (
            p.intitule.strip(),
            _to_date_or_none(p.date_debut),
            _to_date_or_none(p.date_fin),
            p.ville_formation.strip(),
            p.type_produit.strip(),
            p.categorie.strip(),
            p.dest_promo.strip(),
            _to_int_id(p.formateur1_id),
            _to_int_id(p.formateur2_id),
            _to_int_id(p.formateur3_id),
            _to_int_id(p.formateur4_id),
            _to_int_id(p.formateur5_id),
            int(p.nb_heure_salle), int(p.nb_heure_terrain),
            int(p.heure_jour_salle), int(p.heure_jour_terrain),
            int(p.duree), p.formation_active, p.formation_cloturee,
            int(op_id), int(id_formation),
        ),
    )
    return True


def delete_formation(id_formation: str, op_id: int) -> bool:
    """Cf. WinDev Btn Supprimer : soft delete."""
    if not id_formation or id_formation == "0":
        return False
    db = get_pg_connection("scool")
    db.execute(
        """UPDATE scool.pgt_formation
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_formation = ?""",
        (int(op_id), int(id_formation)),
    )
    return True


def duplicate_formation(
    id_formation: str, op_id: int, dupliquer_programme: bool = False,
) -> str:
    """Cf. WinDev Btn Dupliquer.

    Duplique la formation + '(- Copie)' au titre. Si dupliquer_programme,
    duplique aussi les lignes pgt_formation_programme.
    """
    if not id_formation or id_formation == "0":
        return ""
    db = get_pg_connection("scool")
    r = db.query_one(
        """SELECT intitule, date_debut, date_fin,
                  ville_formation, type_produit, categorie, dest_promo,
                  formateur1, formateur2, formateur3, formateur4, formateur5,
                  nb_heure_salle, nb_heure_terrain,
                  heure_jour_salle, heure_jour_terrain,
                  duree, formation_active, formation_cloturee
             FROM scool.pgt_formation
            WHERE id_formation = ?""",
        (int(id_formation),),
    )
    if not r:
        return ""
    new_id = _new_id()
    db.execute(
        """INSERT INTO scool.pgt_formation
              (id_formation, intitule, date_debut, date_fin,
               ville_formation, type_produit, categorie, dest_promo,
               formateur1, formateur2, formateur3, formateur4, formateur5,
               nb_heure_salle, nb_heure_terrain,
               heure_jour_salle, heure_jour_terrain,
               duree, formation_active, formation_cloturee,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                   ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id,
            (r.get("intitule") or "") + " - Copie",
            r.get("date_debut"), r.get("date_fin"),
            r.get("ville_formation") or "",
            r.get("type_produit") or "",
            r.get("categorie") or "",
            r.get("dest_promo") or "",
            int(r.get("formateur1") or 0),
            int(r.get("formateur2") or 0),
            int(r.get("formateur3") or 0),
            int(r.get("formateur4") or 0),
            int(r.get("formateur5") or 0),
            int(r.get("nb_heure_salle") or 0),
            int(r.get("nb_heure_terrain") or 0),
            int(r.get("heure_jour_salle") or 0),
            int(r.get("heure_jour_terrain") or 0),
            int(r.get("duree") or 0),
            bool(r.get("formation_active")),
            bool(r.get("formation_cloturee")),
            int(op_id),
        ),
    )

    # Duplique programme si demande
    if dupliquer_programme:
        try:
            progs = db.query(
                """SELECT * FROM scool.pgt_formation_programme
                    WHERE id_formation = ?
                      AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
                (int(id_formation),),
            ) or []
        except Exception:
            progs = []
        for p in progs:
            # Clone avec nouvel id + nouveau id_formation
            cols = {k: v for k, v in p.items()
                    if k not in (
                        "id_formation_programme_auto",
                        "id_formation_programme",
                        "id_formation",
                        "modif_date", "modif_op", "modif_elem",
                    )}
            keys = list(cols.keys())
            values = [cols[k] for k in keys]
            placeholders = ",".join(["?"] * (len(keys) + 5))
            columns = ",".join(keys + [
                "id_formation_programme", "id_formation",
                "modif_op", "modif_elem", "modif_date",
            ])
            try:
                db.execute(
                    f"""INSERT INTO scool.pgt_formation_programme
                          ({columns}) VALUES ({placeholders.replace('?,?', '?,?')
                                                        [:len(placeholders)-6]}?, ?, ?, ?, NOW())""",
                    tuple(values + [
                        _new_id(), new_id,
                        int(op_id), "new",
                    ]),
                )
            except Exception:
                logger.exception("duplicate programme")

    return str(new_id)


# --------------------------------------------------------------------
# Modeles de formation
# --------------------------------------------------------------------

def list_formateurs() -> list[FormateurCombo]:
    """Cf. WinDev combos Formateur1..5.

    SELECT Formateur JOIN salarie JOIN salarie_embauche
    WHERE en_activite = TRUE AND formateur_actif = TRUE.
    """
    rh = get_pg_connection("rh")
    # Nota : filtre sur en_activite du salarie uniquement.
    # Le champ formateur_actif de scool.pgt_formateur est mal
    # synchronise depuis HFSQL (tous a FALSE en dev), on l'ignore.
    try:
        rows = rh.query(
            """SELECT f.id_formateur, f.niveau, f.formateur_actif,
                      s.nom, s.prenom, e.en_activite
                 FROM scool.pgt_formateur f
                 JOIN pgt_salarie s ON s.id_salarie = f.id_formateur
                 LEFT JOIN pgt_salarie_embauche e
                        ON e.id_salarie = s.id_salarie
                       AND (e.modif_elem IS NULL
                            OR e.modif_elem NOT LIKE '%suppr%')
                WHERE f.id_formateur > 0
                  AND (f.modif_elem IS NULL
                       OR f.modif_elem NOT LIKE '%suppr%')
                  AND (s.modif_elem IS NULL
                       OR s.modif_elem NOT LIKE '%suppr%')
                ORDER BY s.nom ASC, s.prenom ASC""",
        ) or []
    except Exception:
        logger.exception("list_formateurs")
        return []
    seen: set[int] = set()
    out: list[FormateurCombo] = []
    for r in rows:
        id_f = int(r.get("id_formateur") or 0)
        if id_f in seen:
            continue
        seen.add(id_f)
        nom = (r.get("nom") or "").strip()
        prenom = _cap_prenom((r.get("prenom") or "").strip())
        niveau_raw = r.get("niveau")
        niveau = str(niveau_raw).strip() if niveau_raw not in (None, 0) else ""
        lib = f"{nom.upper()} {prenom}"
        if niveau:
            lib += f" ({niveau})"
        out.append(FormateurCombo(
            id_formateur=str(id_f),
            lib=lib,
            niveau=niveau,
            is_actif=bool(r.get("en_activite")),
        ))
    # Tri : actifs en premier
    out.sort(key=lambda f: (not f.is_actif, f.lib))
    return out


def list_modeles_combo() -> list[ModeleFormationCombo]:
    """Cf. WinDev reqListeModele : combo 'Utiliser ce modele' avec en
    premiere position 'Ne pas utiliser de modele' (id_modele=0).
    """
    db = get_pg_connection("scool")
    try:
        rows = db.query(
            """SELECT id_modele_form, intitule, categorie
                 FROM scool.pgt_form_modele
                WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        ) or []
    except Exception:
        return []
    out: list[ModeleFormationCombo] = [
        ModeleFormationCombo(id_modele="0", nom_formation="Ne pas utiliser de modèle"),
    ]
    tmp: list[ModeleFormationCombo] = []
    for r in rows:
        cat = (r.get("categorie") or "").strip()
        intitule = (r.get("intitule") or "").strip()
        nom = f"{cat} - {intitule}" if cat else intitule
        tmp.append(ModeleFormationCombo(
            id_modele=_clean_id(r.get("id_modele_form")),
            nom_formation=nom,
        ))
    tmp.sort(key=lambda m: m.nom_formation.lower())
    return out + tmp


def list_modeles() -> list[ModeleFormationRow]:
    db = get_pg_connection("scool")
    try:
        rows = db.query(
            """SELECT id_modele_form, intitule, categorie,
                      nb_heure_salle, nb_heure_terrain,
                      heure_jour_salle, heure_jour_terrain
                 FROM scool.pgt_form_modele
                WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY intitule ASC""",
        ) or []
    except Exception:
        return []
    return [
        ModeleFormationRow(
            id_modele=_clean_id(r.get("id_modele_form")),
            intitule=(r.get("intitule") or "").strip(),
            categorie=(r.get("categorie") or "").strip(),
            nb_heure_salle=int(r.get("nb_heure_salle") or 0),
            nb_heure_terrain=int(r.get("nb_heure_terrain") or 0),
            heure_jour_salle=int(r.get("heure_jour_salle") or 0),
            heure_jour_terrain=int(r.get("heure_jour_terrain") or 0),
        )
        for r in rows
    ]


# --------------------------------------------------------------------
# Programme de formation (onglet 1)
# --------------------------------------------------------------------

def list_programme(id_formation: str) -> list[ProgrammeRow]:
    """Cf. WinDev Table_ProgrammeFormation."""
    if not id_formation or id_formation == "0":
        return []
    db = get_pg_connection("scool")
    try:
        rows = db.query(
            """SELECT id_formation_programme, id_formation, num_semaine,
                      date, salle, terrain, duree, horaires, objectif
                 FROM scool.pgt_formation_programme
                WHERE id_formation = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY date ASC NULLS LAST, id_formation_programme ASC""",
            (int(id_formation),),
        ) or []
    except Exception:
        logger.exception("list_programme")
        return []
    return [
        ProgrammeRow(
            id_programme=_clean_id(r.get("id_formation_programme")),
            id_formation=_clean_id(r.get("id_formation")),
            num_semaine=int(r.get("num_semaine") or 0),
            date=_iso_date(r.get("date")),
            salle=int(r.get("salle") or 0),
            terrain=int(r.get("terrain") or 0),
            duree=int(r.get("duree") or 0),
            horaires=(r.get("horaires") or "").strip(),
            objectif=int(r.get("objectif") or 0),
        )
        for r in rows
    ]


def _calc_num_semaine(date_debut_form: str, date_prog: str) -> int:
    """Cf. WinDev DateVersNumeroDeSemaine - semRef."""
    from datetime import date as _date
    try:
        d0 = _date.fromisoformat(date_debut_form[:10])
        d = _date.fromisoformat(date_prog[:10])
    except Exception:
        return 1
    sem_ref = d0.isocalendar()[1] - 1
    n = d.isocalendar()[1] - sem_ref
    return max(1, n)


def add_programme(
    id_formation: str, p: ProgrammePayload, op_id: int,
) -> str:
    """Cf. WinDev Btn Ajouter une date."""
    if not id_formation or id_formation == "0":
        return ""
    if not p.date or len(p.date) < 10:
        return ""
    db = get_pg_connection("scool")
    row = db.query_one(
        "SELECT date_debut FROM scool.pgt_formation WHERE id_formation = ?",
        (int(id_formation),),
    )
    date_debut = (
        str(row.get("date_debut"))[:10]
        if row and row.get("date_debut") else p.date
    )
    num_sem = p.num_semaine if p.num_semaine > 0 else _calc_num_semaine(
        date_debut, p.date,
    )

    new_id = _new_id()
    db.execute(
        """INSERT INTO scool.pgt_formation_programme
              (id_formation_programme, id_formation, num_semaine, date,
               salle, terrain, duree, horaires, objectif,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id, int(id_formation), num_sem, p.date[:10],
            int(p.salle), int(p.terrain), int(p.duree),
            p.horaires.strip(), int(p.objectif),
            int(op_id),
        ),
    )
    return str(new_id)


def update_programme(
    id_programme: str, p: ProgrammePayload, op_id: int,
) -> bool:
    if not id_programme or id_programme == "0":
        return False
    db = get_pg_connection("scool")
    db.execute(
        """UPDATE scool.pgt_formation_programme
              SET date = ?, num_semaine = ?,
                  salle = ?, terrain = ?, duree = ?,
                  horaires = ?, objectif = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_formation_programme = ?""",
        (
            p.date[:10], int(p.num_semaine),
            int(p.salle), int(p.terrain), int(p.duree),
            p.horaires.strip(), int(p.objectif),
            int(op_id), int(id_programme),
        ),
    )
    return True


def delete_programme(id_programme: str, op_id: int) -> bool:
    if not id_programme or id_programme == "0":
        return False
    db = get_pg_connection("scool")
    db.execute(
        """UPDATE scool.pgt_formation_programme
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_formation_programme = ?""",
        (int(op_id), int(id_programme)),
    )
    return True


def delete_programme_all(id_formation: str, op_id: int) -> int:
    """Cf. WinDev Btn Supprimer la date - clic fleche."""
    if not id_formation or id_formation == "0":
        return 0
    db = get_pg_connection("scool")
    db.execute(
        """UPDATE scool.pgt_formation_programme
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_formation = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(op_id), int(id_formation)),
    )
    return 1


def duplicate_programme(id_programme: str, op_id: int) -> str:
    """Cf. WinDev Btn Dupliquer (onglet Prog)."""
    if not id_programme or id_programme == "0":
        return ""
    db = get_pg_connection("scool")
    r = db.query_one(
        """SELECT id_formation, num_semaine, date, salle, terrain,
                  duree, horaires, objectif
             FROM scool.pgt_formation_programme
            WHERE id_formation_programme = ?""",
        (int(id_programme),),
    )
    if not r:
        return ""
    new_id = _new_id()
    db.execute(
        """INSERT INTO scool.pgt_formation_programme
              (id_formation_programme, id_formation, num_semaine, date,
               salle, terrain, duree, horaires, objectif,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id, int(r.get("id_formation") or 0),
            int(r.get("num_semaine") or 0),
            r.get("date"),
            int(r.get("salle") or 0),
            int(r.get("terrain") or 0),
            int(r.get("duree") or 0),
            (r.get("horaires") or "").strip() + " - Copie",
            int(r.get("objectif") or 0),
            int(op_id),
        ),
    )
    return str(new_id)


# --------------------------------------------------------------------
# Convertir en modele (Btn Convertir en modele)
# --------------------------------------------------------------------

def convertir_en_modele(
    id_formation: str, p: ConvertirModelePayload, op_id: int,
) -> str:
    """Cf. WinDev Btn Convertir en modele.

    Cree un pgt_form_modele avec intitule 'Export - <intitule>' + copie
    de toutes les lignes pgt_formation_programme dans
    pgt_form_modele_programme.
    """
    if not id_formation or id_formation == "0":
        return ""
    if not p.intitule.strip():
        return ""
    db = get_pg_connection("scool")

    new_id = _new_id()
    db.execute(
        """INSERT INTO scool.pgt_form_modele
              (id_modele_form, intitule, categorie,
               nb_heure_salle, nb_heure_terrain,
               heure_jour_salle, heure_jour_terrain,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id,
            "Export - " + p.intitule.strip(),
            p.categorie.strip(),
            int(p.nb_heure_salle), int(p.nb_heure_terrain),
            int(p.heure_jour_salle), int(p.heure_jour_terrain),
            int(op_id),
        ),
    )

    try:
        progs = db.query(
            """SELECT date, salle, terrain, duree, horaires
                 FROM scool.pgt_formation_programme
                WHERE id_formation = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY date ASC""",
            (int(id_formation),),
        ) or []
    except Exception:
        progs = []

    for prog in progs:
        try:
            db.execute(
                """INSERT INTO scool.pgt_form_modele_programme
                      (id_modele_programme, id_modele_form, date,
                       salle, terrain, duree, horaires,
                       modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
                (
                    _new_id(), new_id,
                    prog.get("date"),
                    int(prog.get("salle") or 0),
                    int(prog.get("terrain") or 0),
                    int(prog.get("duree") or 0),
                    (prog.get("horaires") or "").strip(),
                    int(op_id),
                ),
            )
        except Exception:
            logger.exception("convertir modele INSERT prog")

    return str(new_id)


# --------------------------------------------------------------------
# FI_AnalysePromoScool - Analyse d'une formation
# --------------------------------------------------------------------

def _calcul_prod_sfr_stagiaire(
    id_salarie: int, date_deb: str, date_fin: str,
) -> dict:
    """Cf. WinDev CalculProdSFR : par stagiaire, compte les contrats
    SFR entre date_deb et date_fin (INCLUS mais avec IDTypeEtat != 9).
    Renvoie compteurs {nb_fibre_brut, nb_fibre_hr, nb_cqt_brut, nb_cqt_hr,
    nb_mig_brut, nb_mig_hr, nb_mob_brut, nb_mob_hr, nb_cqt_premium_hr}.
    """
    out = {
        "nb_fibre_brut": 0, "nb_fibre_hr": 0,
        "nb_cqt_brut": 0, "nb_cqt_hr": 0,
        "nb_mig_brut": 0, "nb_mig_hr": 0,
        "nb_mob_brut": 0, "nb_mob_hr": 0,
        "nb_cqt_premium_hr": 0,
    }
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT COUNT(c.id_contrat) AS nbctt,
                      p.famille, p.sous_fam,
                      e.id_type_etat, c.type_vente
                 FROM adv.pgt_sfr_produit p
                 JOIN adv.pgt_sfr_contrat c ON c.id_produit = p.id_produit
                 JOIN adv.pgt_sfr_etat_contrat e ON e.id_etat = c.id_etat_contrat
                WHERE (c.modif_elem IS NULL OR c.modif_elem NOT LIKE '%suppr%')
                  AND c.id_salarie = ?
                  AND c.date_signature BETWEEN ? AND ?
                  AND e.id_type_etat <> 9
                GROUP BY p.famille, p.sous_fam, e.id_type_etat, c.type_vente""",
            (int(id_salarie), date_deb, date_fin),
        ) or []
    except Exception:
        return out

    for r in rows:
        fam = (r.get("famille") or "").strip()
        sous_fam = (r.get("sous_fam") or "").strip()
        etat = int(r.get("id_type_etat") or 0)
        type_vente = int(r.get("type_vente") or 0)
        n = int(r.get("nbctt") or 0)
        is_hr = etat != 3  # 3 = rejete
        if fam == "FIBRE":
            out["nb_fibre_brut"] += n
            if is_hr:
                out["nb_fibre_hr"] += n
            if type_vente in (1, 2):
                out["nb_cqt_brut"] += n
                if is_hr:
                    out["nb_cqt_hr"] += n
                    if sous_fam == "Premium":
                        out["nb_cqt_premium_hr"] += n
            else:
                out["nb_mig_brut"] += n
                if is_hr:
                    out["nb_mig_hr"] += n
        else:
            out["nb_mob_brut"] += n
            if is_hr:
                out["nb_mob_hr"] += n
    return out


def _count_rdv_by_categorie(id_formation: int) -> tuple[int, int, int]:
    """Cf. WinDev Code Init reqRDV : compte les RDV agenda par IDCategorie
    JOIN Formation_PrevRecrut. Return (presents, retenus, jo).
    """
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT COUNT(a.id_agenda_evenement) AS comptage,
                      a.id_categorie
                 FROM recrutement.pgt_agenda_evenement a
                 JOIN scool.pgt_formation_prev_recrut fp
                      ON fp.id_prevision_recrut = a.id_prevision_recrut
                WHERE (a.modif_elem IS NULL OR a.modif_elem NOT LIKE '%suppr%')
                  AND (fp.modif_elem IS NULL OR fp.modif_elem NOT LIKE '%suppr%')
                  AND fp.id_formation = ?
                GROUP BY a.id_categorie""",
            (id_formation,),
        ) or []
    except Exception:
        return (0, 0, 0)
    presents = retenus = jo = 0
    for r in rows:
        cat = int(r.get("id_categorie") or 0)
        n = int(r.get("comptage") or 0)
        if cat in (4, 7):
            presents += n
        elif cat in (2, 3):
            presents += n
            retenus += n
        elif cat == 8:
            presents += n
            retenus += n
            jo += n
    return (presents, retenus, jo)


def _load_stagiaires(id_formation: int) -> list[dict]:
    """Charge la liste des stagiaires d'une formation."""
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT DISTINCT fs.id_salarie, s.nom, s.prenom, fs.livrable
                 FROM scool.pgt_formation_salarie fs
                 JOIN pgt_salarie s ON s.id_salarie = fs.id_salarie
                WHERE fs.id_formation = ?
                  AND (fs.modif_elem IS NULL OR fs.modif_elem NOT LIKE '%suppr%')""",
            (id_formation,),
        ) or []
    except Exception:
        return []
    return rows


def _load_salarie_status(id_salarie: int, ref_date: str) -> dict:
    """Retourne { en_activite, date_embauche, date_sortie_demandee,
    type_sortie }."""
    db = get_pg_connection("rh")
    try:
        r = db.query_one(
            """SELECT e.en_activite, e.date_debut AS date_embauche,
                      ss.date_sortie_demandee,
                      ts.lib_sortie
                 FROM pgt_salarie_embauche e
                 LEFT JOIN pgt_salarie_sortie ss ON ss.id_salarie = e.id_salarie
                       AND (ss.modif_elem IS NULL
                            OR ss.modif_elem NOT LIKE '%suppr%')
                 LEFT JOIN pgt_type_sortie_salarie ts
                       ON ts.id_type_sortie = ss.id_type_sortie
                WHERE e.id_salarie = ?
                ORDER BY e.date_debut DESC NULLS LAST
                LIMIT 1""",
            (id_salarie,),
        )
    except Exception:
        return {}
    return r or {}


def _load_effectif_dates(
    id_formation: int, date_debut: str,
) -> list[tuple[str, str]]:
    """Return liste (periode, date_iso) : Demarrage puis chaque Bilan
    et Livraison detectes dans le programme.
    """
    db = get_pg_connection("scool")
    try:
        rows = db.query(
            """SELECT date, horaires
                 FROM scool.pgt_formation_programme
                WHERE id_formation = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                  AND (UPPER(horaires) LIKE '%BILAN%'
                       OR UPPER(horaires) LIKE '%REMISE%DIPLOME%')
                ORDER BY date ASC""",
            (id_formation,),
        ) or []
    except Exception:
        rows = []
    out: list[tuple[str, str]] = [("Démarrage", date_debut)]
    num_bilan = 1
    seen_dates: set[str] = {date_debut}
    for r in rows:
        d = _iso_date(r.get("date"))
        if not d or d in seen_dates:
            continue
        seen_dates.add(d)
        horaires = (r.get("horaires") or "").upper()
        if "BILAN" in horaires:
            out.append((f"Bilan {num_bilan}", d))
            num_bilan += 1
        else:
            out.append(("Livraison", d))
    return out


def _count_bulletins(id_formation: int) -> tuple[int, int]:
    """Return (intermediaires, finaux)."""
    db = get_pg_connection("scool")
    try:
        rows = db.query(
            """SELECT type_bulletin, COUNT(*) AS n
                 FROM scool.pgt_formation_bulletin
                WHERE id_formation = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                GROUP BY type_bulletin""",
            (id_formation,),
        ) or []
    except Exception:
        return (0, 0)
    inter = final = 0
    for r in rows:
        t = int(r.get("type_bulletin") or 0)
        n = int(r.get("n") or 0)
        if t == 1:
            final += n
        else:
            inter += n
    return (inter, final)


def _sum_nb_jours_terrain(id_formation: int) -> int:
    db = get_pg_connection("scool")
    try:
        r = db.query_one(
            """SELECT COALESCE(SUM(terrain), 0) AS n
                 FROM scool.pgt_formation_programme
                WHERE id_formation = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
            (id_formation,),
        )
    except Exception:
        return 0
    return int(r.get("n") or 0) if r else 0


def analyser_formation(id_formation: str) -> AnalyseFormationResult:
    """Cf. WinDev FI_AnalysePromoScool Code Init."""
    detail = get_formation(id_formation)
    if not detail:
        return AnalyseFormationResult(id_formation=id_formation)

    id_form_int = int(id_formation)
    presents, retenus, jo = _count_rdv_by_categorie(id_form_int)
    stagiaires_raw = _load_stagiaires(id_form_int)
    nb_stagiaires_debut = len(stagiaires_raw)
    intermediaires, finaux = _count_bulletins(id_form_int)
    nb_jours_terrain = _sum_nb_jours_terrain(id_form_int)

    # Table effectif : Demarrage + Bilan/Livraison
    dates_effectif = _load_effectif_dates(id_form_int, detail.date_debut)

    # Salarie infos + calc prod SFR pour chaque stagiaire
    # (production de la fin de formation)
    date_ref_fin = detail.date_fin or (
        dates_effectif[-1][1] if dates_effectif else detail.date_debut
    )
    stagiaires: list[StagiaireRow] = []
    total_livrable = 0
    total_cqt = 0
    for s in stagiaires_raw:
        id_sal = int(s.get("id_salarie") or 0)
        if not id_sal:
            continue
        info = _load_salarie_status(id_sal, date_ref_fin)
        prod = _calcul_prod_sfr_stagiaire(
            id_sal, detail.date_debut, date_ref_fin,
        )
        stagiaires.append(StagiaireRow(
            id_stagiaire=str(id_sal),
            nom=(s.get("nom") or "").strip(),
            prenom=_cap_prenom((s.get("prenom") or "").strip()),
            du=_iso_date(info.get("date_embauche")),
            au=_iso_date(info.get("date_sortie_demandee")),
            en_activite=bool(info.get("en_activite")),
            type_sortie=(info.get("lib_sortie") or "").strip(),
            livrable=bool(s.get("livrable")),
            nb_fibre_brut=prod["nb_fibre_brut"],
            nb_fibre_hr=prod["nb_fibre_hr"],
            nb_cqt_brut=prod["nb_cqt_brut"],
            nb_cqt_hr=prod["nb_cqt_hr"],
            nb_mig_brut=prod["nb_mig_brut"],
            nb_mig_hr=prod["nb_mig_hr"],
            nb_mob_brut=prod["nb_mob_brut"],
            nb_mob_hr=prod["nb_mob_hr"],
        ))
        total_cqt += prod["nb_cqt_premium_hr"]
        if s.get("livrable"):
            total_livrable += 1

    # Table effectif : par etape, recompte le nb_vend (retire ceux
    # sortis avant la date de l'etape) et somme les prods
    effectif: list[EffectifRow] = []
    for periode, d in dates_effectif:
        # nb_vend = nb_stagiaires - sortis avant cette date
        nb_vend = nb_stagiaires_debut
        for s in stagiaires_raw:
            id_sal = int(s.get("id_salarie") or 0)
            info = _load_salarie_status(id_sal, d)
            date_sortie = _iso_date(info.get("date_sortie_demandee"))
            if (not info.get("en_activite")) and date_sortie and date_sortie < d:
                nb_vend -= 1

        # Agrege la prod pour tous les stagiaires du debut a cette date
        agg = {
            "nb_ctt_brut": 0, "nb_ctt_hr": 0,
            "nb_cqt": 0, "nb_cqt_hr": 0,
            "nb_mig": 0, "nb_mig_hr": 0,
            "nb_mob_brut": 0, "nb_mob_hr": 0,
        }
        nb_vend_prod = 0
        for s in stagiaires_raw:
            id_sal = int(s.get("id_salarie") or 0)
            if not id_sal:
                continue
            prod = _calcul_prod_sfr_stagiaire(
                id_sal, detail.date_debut, d,
            )
            has_prod = any(v > 0 for v in prod.values())
            if has_prod:
                nb_vend_prod += 1
            agg["nb_ctt_brut"] += prod["nb_fibre_brut"]
            agg["nb_ctt_hr"] += prod["nb_fibre_hr"]
            agg["nb_cqt"] += prod["nb_cqt_brut"]
            agg["nb_cqt_hr"] += prod["nb_cqt_hr"]
            agg["nb_mig"] += prod["nb_mig_brut"]
            agg["nb_mig_hr"] += prod["nb_mig_hr"]
            agg["nb_mob_brut"] += prod["nb_mob_brut"]
            agg["nb_mob_hr"] += prod["nb_mob_hr"]

        effectif.append(EffectifRow(
            periode=periode, date=d,
            nb_vend=nb_vend, nb_vend_prod=nb_vend_prod,
            **agg,
        ))

    total_prod = effectif[-1].nb_vend_prod if effectif else 0
    obj_cqt = nb_jours_terrain * 8

    return AnalyseFormationResult(
        id_formation=id_formation,
        intitule=detail.intitule,
        ville_formation=detail.ville_formation,
        du=detail.date_debut,
        au=detail.date_fin,
        formation_cloturee=detail.formation_cloturee,
        presents=presents, retenus=retenus, jo=jo,
        intermediaires=intermediaires, finaux=finaux,
        nb_jours_terrain=nb_jours_terrain,
        total_prod=total_prod,
        total_livrable=total_livrable,
        total_cqt=total_cqt,
        obj_cqt=obj_cqt,
        effectif=effectif,
        stagiaires=stagiaires,
    )


def analyser_promotions(
    p: AnalysePromoParams,
) -> list[AnalyseFormationResult]:
    """Cf. WinDev Btn 'Faire l'analyse des sessions selectionnees'."""
    return [analyser_formation(id_f) for id_f in p.id_formations if id_f]


# ====================================================================
# ONGLET EVENEMENT
# ====================================================================

def list_evenements(id_formation: str) -> list[EvenementRow]:
    if not id_formation or id_formation == "0":
        return []
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT e.id_formation_evenement, e.date, e.id_salarie,
                      e.intitule, s.nom, s.prenom
                 FROM scool.pgt_formation_evenement e
                 LEFT JOIN pgt_salarie s ON s.id_salarie = e.id_salarie
                WHERE e.id_formation = ?
                  AND (e.modif_elem IS NULL OR e.modif_elem NOT LIKE '%suppr%')
                ORDER BY e.date DESC NULLS LAST""",
            (int(id_formation),),
        ) or []
    except Exception:
        return []
    return [
        EvenementRow(
            id_evenement=_clean_id(r.get("id_formation_evenement")),
            date=_iso_date(r.get("date")),
            id_salarie=_clean_id(r.get("id_salarie")),
            nom_prenom=(
                f"{(r.get('nom') or '').strip()} "
                f"{_cap_prenom((r.get('prenom') or '').strip())}"
            ).strip(),
            intitule=(r.get("intitule") or "").strip(),
        )
        for r in rows
    ]


def add_evenement(
    id_formation: str, p: EvenementPayload, op_id: int,
) -> str:
    if not id_formation or id_formation == "0":
        return ""
    if not p.date or len(p.date) < 10:
        return ""
    db = get_pg_connection("scool")
    new_id = _new_id()
    db.execute(
        """INSERT INTO scool.pgt_formation_evenement
              (id_formation_evenement, id_formation, id_salarie,
               date, intitule, modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id, int(id_formation),
            int(p.id_salarie) if p.id_salarie.isdigit() else 0,
            p.date[:10], p.intitule.strip(),
            int(op_id),
        ),
    )
    return str(new_id)


def update_evenement(
    id_evenement: str, p: EvenementPayload, op_id: int,
) -> bool:
    if not id_evenement or id_evenement == "0":
        return False
    db = get_pg_connection("scool")
    db.execute(
        """UPDATE scool.pgt_formation_evenement
              SET date = ?, id_salarie = ?, intitule = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_formation_evenement = ?""",
        (
            p.date[:10],
            int(p.id_salarie) if p.id_salarie.isdigit() else 0,
            p.intitule.strip(), int(op_id), int(id_evenement),
        ),
    )
    return True


def delete_evenement(id_evenement: str, op_id: int) -> bool:
    if not id_evenement or id_evenement == "0":
        return False
    db = get_pg_connection("scool")
    db.execute(
        """UPDATE scool.pgt_formation_evenement
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_formation_evenement = ?""",
        (int(op_id), int(id_evenement)),
    )
    return True


# ====================================================================
# ONGLET ELEVES (stagiaires)
# ====================================================================

def list_eleves(
    id_formation: str, uniquement_actifs: bool = False,
) -> list[EleveRow]:
    if not id_formation or id_formation == "0":
        return []
    detail = get_formation(id_formation)
    if not detail:
        return []

    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT fs.id_salarie, fs.date_debut, fs.date_fin,
                      fs.livrable,
                      s.nom, s.prenom,
                      e.en_activite, e.date_debut AS date_embauche,
                      ss.date_sortie_demandee, ts.lib_sortie
                 FROM scool.pgt_formation_salarie fs
                 JOIN pgt_salarie s ON s.id_salarie = fs.id_salarie
                 LEFT JOIN pgt_salarie_embauche e
                        ON e.id_salarie = fs.id_salarie
                       AND (e.modif_elem IS NULL
                            OR e.modif_elem NOT LIKE '%suppr%')
                 LEFT JOIN pgt_salarie_sortie ss ON ss.id_salarie = fs.id_salarie
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
        return []

    out: list[EleveRow] = []
    for r in rows:
        actif = bool(r.get("en_activite"))
        if uniquement_actifs and not actif:
            continue
        id_sal = int(r.get("id_salarie") or 0)
        date_ref_fin = detail.date_fin or detail.date_debut
        prod = _calcul_prod_sfr_stagiaire(
            id_sal, detail.date_debut, date_ref_fin,
        )
        out.append(EleveRow(
            id_salarie=str(id_sal),
            nom=(r.get("nom") or "").strip(),
            prenom=_cap_prenom((r.get("prenom") or "").strip()),
            du=_iso_date(r.get("date_embauche")),
            au=_iso_date(r.get("date_sortie_demandee")),
            en_activite=actif,
            type_sortie=(r.get("lib_sortie") or "").strip(),
            livrable=bool(r.get("livrable")),
            nb_fibre_brut=prod["nb_fibre_brut"],
            nb_fibre_hr=prod["nb_fibre_hr"],
            nb_cqt_brut=prod["nb_cqt_brut"],
            nb_cqt_hr=prod["nb_cqt_hr"],
        ))
    return out


def add_eleve(
    id_formation: str, p: EleveAjoutPayload, op_id: int,
) -> bool:
    if not id_formation or id_formation == "0":
        return False
    if not p.id_salarie.isdigit():
        return False
    db = get_pg_connection("scool")
    # Cherche si existe deja (peut-etre soft deleted)
    r = db.query_one(
        """SELECT id_formation_id_salarie
             FROM scool.pgt_formation_salarie
            WHERE id_formation = ? AND id_salarie = ?
            LIMIT 1""",
        (int(id_formation), int(p.id_salarie)),
    )
    if r:
        # Reactive
        db.execute(
            """UPDATE scool.pgt_formation_salarie
                  SET modif_date = NOW(), modif_op = ?, modif_elem = 'new'
                WHERE id_formation = ? AND id_salarie = ?""",
            (int(op_id), int(id_formation), int(p.id_salarie)),
        )
        return True
    key = f"{id_formation}_{p.id_salarie}"
    db.execute(
        """INSERT INTO scool.pgt_formation_salarie
              (id_formation_id_salarie, id_salarie, id_formation,
               livrable, modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, FALSE, NOW(), ?, 'new')""",
        (key, int(p.id_salarie), int(id_formation), int(op_id)),
    )
    return True


def toggle_livrable(id_formation: str, id_salarie: str, op_id: int) -> bool:
    if not id_formation or not id_salarie:
        return False
    db = get_pg_connection("scool")
    db.execute(
        """UPDATE scool.pgt_formation_salarie
              SET livrable = NOT COALESCE(livrable, FALSE),
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_formation = ? AND id_salarie = ?""",
        (int(op_id), int(id_formation), int(id_salarie)),
    )
    return True


def delete_eleve(id_formation: str, id_salarie: str, op_id: int) -> bool:
    if not id_formation or not id_salarie:
        return False
    db = get_pg_connection("scool")
    db.execute(
        """UPDATE scool.pgt_formation_salarie
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_formation = ? AND id_salarie = ?""",
        (int(op_id), int(id_formation), int(id_salarie)),
    )
    return True


# ====================================================================
# ONGLET SESSION DE RECRUT
# ====================================================================

def list_sessions_recrut(id_formation: str) -> list[SessionRecrutRow]:
    if not id_formation or id_formation == "0":
        return []
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT fp.id_formation_prev_recrut,
                      pr.id_prevision_recrut,
                      pr.idorganigramme,
                      pr.date_debut, pr.date_fin, pr.date_session,
                      o.lib_orga,
                      l.lib_lieu
                 FROM scool.pgt_formation_prev_recrut fp
                 JOIN recrutement.pgt_prev_recrut pr
                      ON pr.id_prevision_recrut = fp.id_prevision_recrut
                 LEFT JOIN pgt_organigramme o
                        ON o.idorganigramme = pr.idorganigramme
                 LEFT JOIN recrutement.pgt_cv_lieu_rdv l
                        ON l.id_cv_lieu_rdv = pr.id_cv_lieu_rdv
                WHERE fp.id_formation = ?
                  AND (fp.modif_elem IS NULL
                       OR fp.modif_elem NOT LIKE '%suppr%')
                ORDER BY pr.date_debut DESC NULLS LAST""",
            (int(id_formation),),
        ) or []
    except Exception:
        logger.exception("list_sessions_recrut")
        return []
    return [
        SessionRecrutRow(
            id_formation_prev_recrut=_clean_id(r.get("id_formation_prev_recrut")),
            id_prevision_recrut=_clean_id(r.get("id_prevision_recrut")),
            idorganigramme=_clean_id(r.get("idorganigramme")),
            lib_orga=(r.get("lib_orga") or "").strip(),
            date_debut=_iso_date(r.get("date_debut")),
            date_fin=_iso_date(r.get("date_fin")),
            date_session=_iso_date(r.get("date_session")),
            lib_lieu=(r.get("lib_lieu") or "").strip(),
        )
        for r in rows
    ]


def add_session_recrut(
    id_formation: str, p: SessionRecrutPayload, op_id: int,
) -> str:
    if not id_formation or id_formation == "0":
        return ""
    if not p.id_prevision_recrut.isdigit():
        return ""
    db = get_pg_connection("scool")
    new_id = _new_id()
    db.execute(
        """INSERT INTO scool.pgt_formation_prev_recrut
              (id_formation_prev_recrut, id_formation, id_prevision_recrut,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id, int(id_formation), int(p.id_prevision_recrut),
            int(op_id),
        ),
    )
    return str(new_id)


def delete_session_recrut(
    id_formation_prev_recrut: str, op_id: int,
) -> bool:
    if not id_formation_prev_recrut or id_formation_prev_recrut == "0":
        return False
    db = get_pg_connection("scool")
    db.execute(
        """UPDATE scool.pgt_formation_prev_recrut
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_formation_prev_recrut = ?""",
        (int(op_id), int(id_formation_prev_recrut)),
    )
    return True


# ====================================================================
# ONGLET BULLETINS
# ====================================================================

def list_bulletins(id_formation: str) -> list[BulletinRow]:
    if not id_formation or id_formation == "0":
        return []
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT b.id_formation_bulletin, b.id_salarie,
                      b.du, b.au, b.type_bulletin,
                      s.nom, s.prenom
                 FROM scool.pgt_formation_bulletin b
                 LEFT JOIN pgt_salarie s ON s.id_salarie = b.id_salarie
                WHERE b.id_formation = ?
                  AND (b.modif_elem IS NULL OR b.modif_elem NOT LIKE '%suppr%')
                ORDER BY b.du DESC NULLS LAST, s.nom ASC""",
            (int(id_formation),),
        ) or []
    except Exception:
        return []
    return [
        BulletinRow(
            id_bulletin=_clean_id(r.get("id_formation_bulletin")),
            id_salarie=_clean_id(r.get("id_salarie")),
            stagiaire=(
                f"{(r.get('nom') or '').strip()} "
                f"{_cap_prenom((r.get('prenom') or '').strip())}"
            ).strip(),
            du=_iso_date(r.get("du")),
            au=_iso_date(r.get("au")),
            type_bulletin=int(r.get("type_bulletin") or 0),
        )
        for r in rows
    ]


def delete_bulletin(id_bulletin: str, op_id: int) -> bool:
    if not id_bulletin or id_bulletin == "0":
        return False
    db = get_pg_connection("scool")
    db.execute(
        """UPDATE scool.pgt_formation_bulletin
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_formation_bulletin = ?""",
        (int(op_id), int(id_bulletin)),
    )
    return True


# ====================================================================
# ONGLET BAREME NOTES
# ====================================================================

def list_baremes(id_formation: str) -> list[BaremeNoteRow]:
    if not id_formation or id_formation == "0":
        return []
    db = get_pg_connection("scool")
    try:
        rows = db.query(
            """SELECT id_formation_bareme_note, type_note, palier,
                      note, sens_recherche
                 FROM scool.pgt_formation_bareme_note
                WHERE id_formation = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY type_note ASC, palier ASC""",
            (int(id_formation),),
        ) or []
    except Exception:
        return []
    return [
        BaremeNoteRow(
            id_bareme=_clean_id(r.get("id_formation_bareme_note")),
            type_note=(r.get("type_note") or "").strip(),
            palier=float(r.get("palier") or 0),
            note=float(r.get("note") or 0),
            sens_recherche=(r.get("sens_recherche") or "ASC"),
        )
        for r in rows
    ]


def add_bareme(
    id_formation: str, p: BaremeNotePayload, op_id: int,
) -> str:
    if not id_formation or id_formation == "0":
        return ""
    if not p.type_note.strip():
        return ""
    db = get_pg_connection("scool")
    new_id = _new_id()
    db.execute(
        """INSERT INTO scool.pgt_formation_bareme_note
              (id_formation_bareme_note, id_formation, type_note, palier,
               note, sens_recherche,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id, int(id_formation), p.type_note.strip(),
            float(p.palier), float(p.note),
            (p.sens_recherche.strip() or "ASC"), int(op_id),
        ),
    )
    return str(new_id)


def update_bareme(
    id_bareme: str, p: BaremeNotePayload, op_id: int,
) -> bool:
    if not id_bareme or id_bareme == "0":
        return False
    db = get_pg_connection("scool")
    db.execute(
        """UPDATE scool.pgt_formation_bareme_note
              SET type_note = ?, palier = ?, note = ?, sens_recherche = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_formation_bareme_note = ?""",
        (
            p.type_note.strip(), float(p.palier), float(p.note),
            (p.sens_recherche.strip() or "ASC"),
            int(op_id), int(id_bareme),
        ),
    )
    return True


def delete_bareme(id_bareme: str, op_id: int) -> bool:
    if not id_bareme or id_bareme == "0":
        return False
    db = get_pg_connection("scool")
    db.execute(
        """UPDATE scool.pgt_formation_bareme_note
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_formation_bareme_note = ?""",
        (int(op_id), int(id_bareme)),
    )
    return True


# ====================================================================
# FEN_SCOOLFORMMODELE - Modeles de plan de formation
# ====================================================================

def create_modele(p: ModeleFormationPayload, op_id: int) -> str:
    """Cf. WinDev Btn Nouveau Modele -> Fen_ScoolFormModele_AjoutEdit."""
    if not p.intitule.strip():
        return ""
    db = get_pg_connection("scool")
    new_id = _new_id()
    db.execute(
        """INSERT INTO scool.pgt_form_modele
              (id_modele_form, intitule, categorie,
               nb_heure_salle, nb_heure_terrain,
               heure_jour_salle, heure_jour_terrain,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id, p.intitule.strip(), p.categorie.strip(),
            int(p.nb_heure_salle), int(p.nb_heure_terrain),
            int(p.heure_jour_salle), int(p.heure_jour_terrain),
            int(op_id),
        ),
    )
    return str(new_id)


def update_modele(
    id_modele: str, p: ModeleFormationPayload, op_id: int,
) -> bool:
    if not id_modele or id_modele == "0":
        return False
    db = get_pg_connection("scool")
    db.execute(
        """UPDATE scool.pgt_form_modele
              SET intitule = ?, categorie = ?,
                  nb_heure_salle = ?, nb_heure_terrain = ?,
                  heure_jour_salle = ?, heure_jour_terrain = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_modele_form = ?""",
        (
            p.intitule.strip(), p.categorie.strip(),
            int(p.nb_heure_salle), int(p.nb_heure_terrain),
            int(p.heure_jour_salle), int(p.heure_jour_terrain),
            int(op_id), int(id_modele),
        ),
    )
    return True


def delete_modele(id_modele: str, op_id: int) -> bool:
    """Cf. WinDev Btn Supprimer (haut)."""
    if not id_modele or id_modele == "0":
        return False
    db = get_pg_connection("scool")
    db.execute(
        """UPDATE scool.pgt_form_modele
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_modele_form = ?""",
        (int(op_id), int(id_modele)),
    )
    return True


def duplicate_modele(id_modele: str, op_id: int) -> str:
    """Cf. WinDev Btn Dupliquer (haut) : clone le modele + son programme."""
    if not id_modele or id_modele == "0":
        return ""
    db = get_pg_connection("scool")
    m = db.query_one(
        """SELECT intitule, categorie,
                  nb_heure_salle, nb_heure_terrain,
                  heure_jour_salle, heure_jour_terrain
             FROM scool.pgt_form_modele
            WHERE id_modele_form = ?""",
        (int(id_modele),),
    )
    if not m:
        return ""
    new_id = _new_id()
    db.execute(
        """INSERT INTO scool.pgt_form_modele
              (id_modele_form, intitule, categorie,
               nb_heure_salle, nb_heure_terrain,
               heure_jour_salle, heure_jour_terrain,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id, (m.get("intitule") or "") + " - Copie",
            m.get("categorie") or "",
            int(m.get("nb_heure_salle") or 0),
            int(m.get("nb_heure_terrain") or 0),
            int(m.get("heure_jour_salle") or 0),
            int(m.get("heure_jour_terrain") or 0),
            int(op_id),
        ),
    )
    # Clone du programme
    try:
        progs = db.query(
            """SELECT date, salle, terrain, duree, horaires
                 FROM scool.pgt_form_modele_programme
                WHERE id_modele_form = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY date ASC""",
            (int(id_modele),),
        ) or []
    except Exception:
        progs = []
    for p in progs:
        try:
            db.execute(
                """INSERT INTO scool.pgt_form_modele_programme
                      (id_modele_programme, id_modele_form, date,
                       salle, terrain, duree, horaires,
                       modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
                (
                    _new_id(), new_id,
                    int(p.get("date") or 0),
                    int(p.get("salle") or 0),
                    int(p.get("terrain") or 0),
                    int(p.get("duree") or 0),
                    (p.get("horaires") or "").strip(),
                    int(op_id),
                ),
            )
        except Exception:
            logger.exception("duplicate_modele INSERT prog")
    return str(new_id)


# --- Programme du modele ---

def list_modele_programme(id_modele: str) -> list[ModeleProgrammeRow]:
    if not id_modele or id_modele == "0":
        return []
    db = get_pg_connection("scool")
    try:
        rows = db.query(
            """SELECT id_modele_programme, id_modele_form, date,
                      salle, terrain, duree, horaires
                 FROM scool.pgt_form_modele_programme
                WHERE id_modele_form = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY date ASC""",
            (int(id_modele),),
        ) or []
    except Exception:
        logger.exception("list_modele_programme")
        return []
    return [
        ModeleProgrammeRow(
            id_modele_programme=_clean_id(r.get("id_modele_programme")),
            id_modele_form=_clean_id(r.get("id_modele_form")),
            num_jour=int(r.get("date") or 0),
            salle=int(r.get("salle") or 0),
            terrain=int(r.get("terrain") or 0),
            duree=int(r.get("duree") or 0),
            horaires=(r.get("horaires") or "").strip(),
        )
        for r in rows
    ]


def add_modele_programme(
    id_modele: str, p: ModeleProgrammePayload, op_id: int,
) -> str:
    """Cf. WinDev Btn Ajouter un jour : num_jour = MAX(date) + 1 si
    payload.num_jour <= 0.
    """
    if not id_modele or id_modele == "0":
        return ""
    db = get_pg_connection("scool")
    num_jour = int(p.num_jour or 0)
    if num_jour <= 0:
        try:
            r = db.query_one(
                """SELECT COALESCE(MAX(date), 0) AS m
                     FROM scool.pgt_form_modele_programme
                    WHERE id_modele_form = ?
                      AND (modif_elem IS NULL
                           OR modif_elem NOT LIKE '%suppr%')""",
                (int(id_modele),),
            )
            num_jour = int((r.get("m") if r else 0) or 0) + 1
        except Exception:
            num_jour = 1
    new_id = _new_id()
    db.execute(
        """INSERT INTO scool.pgt_form_modele_programme
              (id_modele_programme, id_modele_form, date,
               salle, terrain, duree, horaires,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id, int(id_modele), num_jour,
            int(p.salle), int(p.terrain), int(p.duree),
            p.horaires.strip(), int(op_id),
        ),
    )
    return str(new_id)


def update_modele_programme(
    id_prog: str, p: ModeleProgrammePayload, op_id: int,
) -> bool:
    if not id_prog or id_prog == "0":
        return False
    db = get_pg_connection("scool")
    db.execute(
        """UPDATE scool.pgt_form_modele_programme
              SET date = ?, salle = ?, terrain = ?, duree = ?,
                  horaires = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_modele_programme = ?""",
        (
            int(p.num_jour), int(p.salle), int(p.terrain),
            int(p.duree), p.horaires.strip(),
            int(op_id), int(id_prog),
        ),
    )
    return True


def delete_modele_programme(id_prog: str, op_id: int) -> bool:
    if not id_prog or id_prog == "0":
        return False
    db = get_pg_connection("scool")
    db.execute(
        """UPDATE scool.pgt_form_modele_programme
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_modele_programme = ?""",
        (int(op_id), int(id_prog)),
    )
    return True


def duplicate_modele_programme(id_prog: str, op_id: int) -> str:
    """Cf. WinDev Btn Dupliquer bas."""
    if not id_prog or id_prog == "0":
        return ""
    db = get_pg_connection("scool")
    r = db.query_one(
        """SELECT id_modele_form, date, salle, terrain, duree, horaires
             FROM scool.pgt_form_modele_programme
            WHERE id_modele_programme = ?""",
        (int(id_prog),),
    )
    if not r:
        return ""
    new_id = _new_id()
    db.execute(
        """INSERT INTO scool.pgt_form_modele_programme
              (id_modele_programme, id_modele_form, date,
               salle, terrain, duree, horaires,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id, int(r.get("id_modele_form") or 0),
            int(r.get("date") or 0),
            int(r.get("salle") or 0),
            int(r.get("terrain") or 0),
            int(r.get("duree") or 0),
            (r.get("horaires") or "").strip() + " - Copie",
            int(op_id),
        ),
    )
    return str(new_id)
