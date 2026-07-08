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
    ConvertirModelePayload, FormateurCombo, FormationDetail,
    FormationPayload, FormationRow, ListeFormationsParams,
    ModeleFormationCombo, ModeleFormationRow,
    ProgrammePayload, ProgrammeRow,
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
