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

from app.core.database.pg import get_pg_connection
from app.intranets.adm.schemas.scool_formation import (
    FormationDetail, FormationPayload, FormationRow,
    ListeFormationsParams, ModeleFormationRow,
)

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
    """Cf. WinDev Btn Nouvelle Formation."""
    if not p.intitule.strip():
        return ""
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
            int(op_id),
        ),
    )
    return str(new_id)


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
