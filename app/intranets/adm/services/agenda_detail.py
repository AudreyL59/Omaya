"""
Service pour le module Fen_AgendaDetail (detail d'un RDV de l'agenda
recrutement).

Endpoints associes : voir routers/agenda_detail.py.

Tables impliquees :
  - recrutement.pgt_agenda_evenement : le RDV (titre, contenu, dates,
    categorie, recruteur, lieu/salon visio, OPCrea, Pb_*)
  - recrutement.pgt_cv_suivi : suivi du candidat (lien cvtheque + IdCvStatut
    + OPCREA)
  - recrutement.pgt_prev_recrut : sessions de recrutement (dateSession + lieu)
  - recrutement.pgt_cv_lieu_rdv : referentiel des lieux + adresses
  - recrutement.pgt_salon_visio : salons visio par recruteur
  - recrutement.pgt_type_salon_visio : referentiel des types de salons
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _iso(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%dT%H:%M:%S")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:19] if len(s) >= 19 else s
    return s


def _iso_date(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _new_id() -> int:
    """Equivalent idEntierDateHeureSys WinDev : YYYYMMDDHHMMSSmmm."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


# ---------------------------------------------------------------------------
# Detail RDV
# ---------------------------------------------------------------------------


def load_rdv_detail(id_rdv: int) -> dict | None:
    """Charge tous les champs necessaires pour Fen_AgendaDetail.

    Retourne None si le RDV n'existe pas.
    """
    db = get_pg_connection("recrutement")
    row = db.query_one(
        """SELECT ae.id_agenda_evenement, ae.titre, ae.contenu,
                  ae.date_debut, ae.date_fin,
                  ae.id_categorie, ae.id_salarie AS id_recruteur,
                  ae.id_cv_suivi, ae.id_cv_lieux, ae.id_salon_visio,
                  ae.id_prevision_recrut, ae.op_crea, ae.motif_statut,
                  ae.pb_presentation, ae.pb_elocution,
                  ae.pb_motivation, ae.pb_horaires
             FROM recrutement.pgt_agenda_evenement ae
            WHERE ae.id_agenda_evenement = ?
              AND (ae.modif_elem IS NULL OR ae.modif_elem NOT LIKE '%suppr%')
            LIMIT 1""",
        (int(id_rdv),),
    )
    if not row:
        return None

    id_cv_suivi = _int(row.get("id_cv_suivi"))
    id_cvtheque = 0
    op_crea_from_suivi = 0
    if id_cv_suivi:
        suivi = db.query_one(
            """SELECT id_cvtheque, op_crea
                 FROM recrutement.pgt_cv_suivi
                WHERE id_cv_suivi = ? LIMIT 1""",
            (id_cv_suivi,),
        )
        if suivi:
            id_cvtheque = _int(suivi.get("id_cvtheque"))
            op_crea_from_suivi = _int(suivi.get("op_crea"))

    # OPCrea : prio sur AgendaEvenement, sinon CvSuivi (cf. WinDev qui lit
    # OPCrea depuis CvSuivi a l'ouverture)
    op_crea = _int(row.get("op_crea")) or op_crea_from_suivi
    op_crea_lib = ""
    if op_crea:
        db_rh = get_pg_connection("rh")
        sal = db_rh.query_one(
            """SELECT nom, prenom FROM rh.pgt_salarie
                WHERE id_salarie = ? LIMIT 1""",
            (op_crea,),
        )
        if sal:
            nom = _str(sal.get("nom"))
            prenom = _str(sal.get("prenom"))
            prenom_cap = (prenom[:1].upper() + prenom[1:].lower()) if prenom else ""
            op_crea_lib = f"{nom} {prenom_cap}".strip()

    id_cv_lieux = _int(row.get("id_cv_lieux"))
    # Cf. WinDev : si IdCvLieux <= 1 -> Visio, sinon Physique
    type_entretien = "Visio" if id_cv_lieux <= 1 else "Physique"

    return {
        "id_agenda_evenement": str(row.get("id_agenda_evenement")),
        "titre": _str(row.get("titre")),
        "contenu": _str(row.get("contenu")),
        "date_debut": _iso(row.get("date_debut")),
        "date_fin": _iso(row.get("date_fin")),
        "id_categorie": _int(row.get("id_categorie")),
        "id_recruteur": str(row.get("id_recruteur") or ""),
        "id_cv_suivi": str(id_cv_suivi) if id_cv_suivi else "",
        "id_cvtheque": str(id_cvtheque) if id_cvtheque else "",
        "id_cv_lieux": str(id_cv_lieux) if id_cv_lieux else "",
        "id_salon_visio": str(row.get("id_salon_visio") or ""),
        "id_prevision_recrut": str(row.get("id_prevision_recrut") or ""),
        "type_entretien": type_entretien,
        "op_crea": str(op_crea) if op_crea else "",
        "op_crea_lib": op_crea_lib,
        "motif_statut": _str(row.get("motif_statut")),
        "pb_presentation": bool(row.get("pb_presentation")),
        "pb_elocution": bool(row.get("pb_elocution")),
        "pb_motivation": bool(row.get("pb_motivation")),
        "pb_horaires": bool(row.get("pb_horaires")),
    }


def save_rdv(
    *,
    id_rdv: int,
    titre: str,
    contenu: str,
    id_recruteur: int,
    id_categorie: int,
    date_debut: str,
    date_fin: str,
    id_prevision_recrut: int,
    type_entretien: str,
    id_cv_lieux: int,
    id_salon_visio: int,
    motif_statut: str,
    pb_presentation: bool,
    pb_elocution: bool,
    pb_motivation: bool,
    pb_horaires: bool,
    op_id: int,
) -> dict:
    """Sauvegarde complete du RDV. Si id_cv_lieux est 0 ou type=Visio, on
    force id_cv_lieux=1 (convention WinDev : 1 = Visio)."""
    if type_entretien == "Visio":
        id_cv_lieux = 1
    elif id_cv_lieux <= 1:
        # Mode Physique mais aucun lieu choisi : on garde 0 pour signaler
        id_cv_lieux = 0

    db = get_pg_connection("recrutement")
    db.execute(
        """UPDATE recrutement.pgt_agenda_evenement
              SET titre = ?,
                  contenu = ?,
                  id_salarie = ?,
                  id_categorie = ?,
                  date_debut = ?::timestamp,
                  date_fin = ?::timestamp,
                  id_prevision_recrut = ?,
                  id_cv_lieux = ?,
                  id_salon_visio = ?,
                  motif_statut = ?,
                  pb_presentation = ?,
                  pb_elocution = ?,
                  pb_motivation = ?,
                  pb_horaires = ?,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_agenda_evenement = ?""",
        (
            titre, contenu, int(id_recruteur), int(id_categorie),
            date_debut or None, date_fin or None,
            int(id_prevision_recrut), int(id_cv_lieux),
            int(id_salon_visio), motif_statut,
            bool(pb_presentation), bool(pb_elocution),
            bool(pb_motivation), bool(pb_horaires),
            int(op_id), int(id_rdv),
        ),
    )
    return {"ok": True}


def soft_delete_rdv(id_rdv: int, op_id: int) -> dict:
    db = get_pg_connection("recrutement")
    db.execute(
        """UPDATE recrutement.pgt_agenda_evenement
              SET modif_elem = 'suppr',
                  modif_date = NOW(),
                  modif_op = ?
            WHERE id_agenda_evenement = ?""",
        (int(op_id), int(id_rdv)),
    )
    return {"ok": True}


def set_op_crea(id_rdv: int, new_op: int, op_id: int) -> dict:
    """Btn 'Choisir l'Operateur' : maj OPCrea sur AgendaEvenement +
    CvSuivi lie."""
    db = get_pg_connection("recrutement")
    row = db.query_one(
        """SELECT id_cv_suivi FROM recrutement.pgt_agenda_evenement
            WHERE id_agenda_evenement = ? LIMIT 1""",
        (int(id_rdv),),
    )
    id_cv_suivi = _int((row or {}).get("id_cv_suivi"))

    db.execute(
        """UPDATE recrutement.pgt_agenda_evenement
              SET op_crea = ?, modif_date = NOW(), modif_op = ?
            WHERE id_agenda_evenement = ?""",
        (int(new_op), int(op_id), int(id_rdv)),
    )
    if id_cv_suivi:
        db.execute(
            """UPDATE recrutement.pgt_cv_suivi
                  SET op_crea = ?, modif_date = NOW(), modif_op = ?
                WHERE id_cv_suivi = ?""",
            (int(new_op), int(op_id), id_cv_suivi),
        )

    db_rh = get_pg_connection("rh")
    sal = db_rh.query_one(
        "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
        (int(new_op),),
    )
    if sal:
        nom = _str(sal.get("nom"))
        prenom = _str(sal.get("prenom"))
        prenom_cap = (prenom[:1].upper() + prenom[1:].lower()) if prenom else ""
        op_crea_lib = f"{nom} {prenom_cap}".strip()
    else:
        op_crea_lib = ""
    return {"ok": True, "op_crea_lib": op_crea_lib}


# ---------------------------------------------------------------------------
# Referentiels (combos)
# ---------------------------------------------------------------------------


def list_sessions_en_cours() -> list[dict]:
    """ReqPrevRecEncours : sessions de recrutement actuelles (date_session
    >= 2007-01-01 - cf. seuil WinDev). On joint le lieu pour afficher
    'JJ/MM/AAAA - Lib_Lieu'."""
    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT pr.id_prevision_recrut, pr.date_session,
                  l.lib_lieu
             FROM recrutement.pgt_prev_recrut pr
             LEFT JOIN recrutement.pgt_cv_lieu_rdv l
               ON l.id_cv_lieu_rdv = pr.id_cv_lieu_rdv
            WHERE pr.date_session >= '2007-01-01'::date
              AND (pr.modif_elem IS NULL OR pr.modif_elem NOT LIKE '%suppr%')
            ORDER BY pr.date_session DESC NULLS LAST"""
    )
    return [
        {
            "id_prevision_recrut": str(r.get("id_prevision_recrut") or ""),
            "date_session": _iso_date(r.get("date_session")),
            "lib_lieu": _str(r.get("lib_lieu")),
        }
        for r in (rows or [])
    ]


def list_lieux() -> list[dict]:
    """Referentiel des lieux de RDV (cv_lieu_rdv)."""
    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT id_cv_lieu_rdv, lib_lieu, adresse1, adresse2,
                  id_communes_france, latitude_deg, longitude_deg, is_actif
             FROM recrutement.pgt_cv_lieu_rdv
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            ORDER BY is_actif DESC NULLS LAST, lib_lieu"""
    )
    return [
        {
            "id_cv_lieu_rdv": str(r.get("id_cv_lieu_rdv") or ""),
            "lib_lieu": _str(r.get("lib_lieu")),
            "adresse1": _str(r.get("adresse1")),
            "adresse2": _str(r.get("adresse2")),
            "id_communes_france": str(r.get("id_communes_france") or ""),
            "latitude_deg": float(r.get("latitude_deg") or 0),
            "longitude_deg": float(r.get("longitude_deg") or 0),
            "is_actif": bool(r.get("is_actif")),
        }
        for r in (rows or [])
    ]


def get_lieu(id_cv_lieu_rdv: int) -> dict | None:
    """ReqInfoCvLieuRDV : detail d'un lieu (adresse + commune)."""
    if not id_cv_lieu_rdv:
        return None
    db = get_pg_connection("recrutement")
    row = db.query_one(
        """SELECT id_cv_lieu_rdv, lib_lieu, adresse1, adresse2,
                  id_communes_france, latitude_deg, longitude_deg
             FROM recrutement.pgt_cv_lieu_rdv
            WHERE id_cv_lieu_rdv = ? LIMIT 1""",
        (int(id_cv_lieu_rdv),),
    )
    if not row:
        return None
    # Resolution code postal + ville si id_communes_france est mappe vers
    # une table referentielle - sinon on retourne les valeurs brutes.
    cp = ""
    ville = ""
    id_com = _int(row.get("id_communes_france"))
    if id_com:
        try:
            db_divers = get_pg_connection("divers")
            com = db_divers.query_one(
                """SELECT code_postal, nom_ville
                     FROM divers.pgt_communes_france
                    WHERE id_communes_france = ? LIMIT 1""",
                (id_com,),
            )
            if com:
                cp = _str(com.get("code_postal"))
                ville = _str(com.get("nom_ville"))
        except Exception:
            # Pas de divers.pgt_communes_france : on continue sans CP/ville
            pass
    return {
        "id_cv_lieu_rdv": str(row.get("id_cv_lieu_rdv") or ""),
        "lib_lieu": _str(row.get("lib_lieu")),
        "adresse1": _str(row.get("adresse1")),
        "adresse2": _str(row.get("adresse2")),
        "cp": cp,
        "ville": ville,
        "latitude_deg": float(row.get("latitude_deg") or 0),
        "longitude_deg": float(row.get("longitude_deg") or 0),
    }


def list_salons_visio_by_recruteur(id_recruteur: int) -> list[dict]:
    """ReqListeTypeVisioByRecruteur : salons visio du recruteur + libelle
    du type associe."""
    if not id_recruteur:
        return []
    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT sv.id_salon_visio, tsv.lib_salon
             FROM recrutement.pgt_salon_visio sv
             LEFT JOIN recrutement.pgt_type_salon_visio tsv
               ON tsv.id_type_salon_visio = sv.id_type_salon_visio
            WHERE sv.id_salarie = ?
              AND (sv.modif_elem IS NULL OR sv.modif_elem NOT LIKE '%suppr%')
            ORDER BY tsv.lib_salon""",
        (int(id_recruteur),),
    )
    return [
        {
            "id_salon_visio": str(r.get("id_salon_visio") or ""),
            "lib_salon": _str(r.get("lib_salon")),
        }
        for r in (rows or [])
    ]


def get_salon_visio(id_salon_visio: int) -> dict | None:
    """ReqListeSalonVisioByIdSalon : lien + id + mdp du salon."""
    if not id_salon_visio:
        return None
    db = get_pg_connection("recrutement")
    row = db.query_one(
        """SELECT id_salon_visio, lien_salon, id_salon, mpd_salon
             FROM recrutement.pgt_salon_visio
            WHERE id_salon_visio = ? LIMIT 1""",
        (int(id_salon_visio),),
    )
    if not row:
        return None
    return {
        "id_salon_visio": str(row.get("id_salon_visio") or ""),
        "lien": _str(row.get("lien_salon")),
        "id_salon": _str(row.get("id_salon")),
        "mdp": _str(row.get("mpd_salon")),
    }
