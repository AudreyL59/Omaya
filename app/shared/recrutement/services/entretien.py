"""Service Fen_EntretienAjout (shared : ADM + Vendeur).

Planifier un RDV de recrutement pour un candidat :
- combos : recruteurs actifs, sessions de recrutement a venir,
  lieux RDV actifs, salons visio d'un recruteur
- get_session_details : pour pre-remplir au choix d'une session
- get_lieu_details : pour afficher l'adresse + Maps
- list_agenda_recruteur : RDV existants pour visualisation semaine
- update_coordonnees_candidat : MAJ mail/mobile cvtheque
- create_rdv : ajoute cvsuivi statut=6 + agenda_evenement
  (SMS de confirmation et animation cooptation : V_later)
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Optional

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection
from app.shared.recrutement.services.recherche_cv import _int, _str


def _new_id() -> int:
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S")) * 1000 + n.microsecond // 1000


# ---------------------------------------------------------------------------
# Schemas inline (specifiques a entretien)
# ---------------------------------------------------------------------------


class ComboItem(BaseModel):
    id: str
    label: str


class SessionItem(BaseModel):
    id_prevision_recrut: str
    date_session: str        # YYYY-MM-DD
    nom_ville: str
    label: str               # ex : "29/06/2026 - PARIS"
    id_recruteur: str = ""
    id_cv_lieu_rdv: str = ""


class LieuRdvItem(BaseModel):
    id_cv_lieu_rdv: str
    lib_lieu: str
    adresse1: str = ""
    adresse2: str = ""
    code_postal: str = ""
    nom_ville: str = ""
    latitude_deg: float | None = None
    longitude_deg: float | None = None


class SalonVisioItem(BaseModel):
    id_salon_visio: str
    lib_salon: str
    lien_salon: str = ""
    id_salon: str = ""
    mpd_salon: str = ""


class AgendaEventItem(BaseModel):
    id_agenda_evenement: str
    titre: str
    contenu: str = ""
    date_debut: str         # ISO
    date_fin: str
    lib_categorie: str = ""
    couleur_r: int = 200
    couleur_v: int = 200
    couleur_b: int = 200
    lib_lieu: str = ""
    adresse_complete: str = ""
    op_crea_nom: str = ""


class CreateRdvPayload(BaseModel):
    id_recruteur: int
    date_debut: str         # ISO YYYY-MM-DDTHH:MM
    type_entretien: str     # 'Physique' ou 'Visio'
    id_cv_lieu_rdv: int = 0
    id_salon_visio: int = 0
    id_prevision_recrut: int = 0
    send_sms: bool = False
    choix_serveur: int = 1  # 1=classique, 2=secours


class UpdateCoordsPayload(BaseModel):
    gsm: str = ""
    mail: str = ""


# ---------------------------------------------------------------------------
# Combos
# ---------------------------------------------------------------------------


def list_recruteurs() -> list[ComboItem]:
    """Salaries actifs avec agenda_actif=true ET embauche en activite."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT s.id_salarie,
                  s.nom, s.prenom
             FROM rh.pgt_salarie s
             JOIN rh.pgt_salarie_embauche e ON e.id_salarie = s.id_salarie
            WHERE s.modif_elem NOT LIKE '%suppr%'
              AND s.agenda_actif = true
              AND e.en_activite = true
         ORDER BY s.nom ASC, s.prenom ASC"""
    ) or []
    # Dedup (un salarie peut avoir plusieurs embauches)
    seen: set[int] = set()
    out: list[ComboItem] = []
    for r in rows:
        sid = _int(r["id_salarie"])
        if sid in seen:
            continue
        seen.add(sid)
        nom = _str(r["nom"]).upper()
        prenom = _str(r["prenom"]).strip().title()
        out.append(ComboItem(id=str(sid), label=f"{nom} {prenom}".strip()))
    return out


def list_sessions_recrut() -> list[SessionItem]:
    """Sessions de recrutement a venir (etat 2 ou 6, date >= today)."""
    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT p.id_prevision_recrut, p.date_session,
                  p.id_recruteur, p.id_cv_lieu_rdv,
                  c.code_postal, c.nom_ville
             FROM recrutement.pgt_prev_recrut p
             LEFT JOIN divers.pgt_communes_france c
                    ON c.id_communes_france = p.id_communes_france
            WHERE (p.id_prev_recrut_etat = 2 OR p.id_prev_recrut_etat = 6)
              AND p.date_session >= ?
              AND (p.modif_elem IS NULL OR p.modif_elem NOT LIKE '%suppr%')
         ORDER BY p.date_session ASC""",
        (date.today(),),
    ) or []
    out: list[SessionItem] = []
    for r in rows:
        ds = r.get("date_session")
        ds_str = ds.isoformat() if hasattr(ds, "isoformat") else _str(ds)[:10]
        ville = _str(r.get("nom_ville"))
        label = f"{ds.strftime('%d/%m/%Y') if hasattr(ds, 'strftime') else ds_str} - {ville}"
        out.append(SessionItem(
            id_prevision_recrut=str(_int(r["id_prevision_recrut"])),
            date_session=ds_str,
            nom_ville=ville,
            label=label,
            id_recruteur=str(_int(r.get("id_recruteur"))) if _int(r.get("id_recruteur")) else "",
            id_cv_lieu_rdv=str(_int(r.get("id_cv_lieu_rdv"))) if _int(r.get("id_cv_lieu_rdv")) else "",
        ))
    return out


def list_lieux_rdv() -> list[LieuRdvItem]:
    """Lieux RDV actifs (is_actif=true)."""
    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT l.id_cv_lieu_rdv, l.lib_lieu, l.adresse1, l.adresse2,
                  l.latitude_deg, l.longitude_deg,
                  c.code_postal, c.nom_ville
             FROM recrutement.pgt_cv_lieu_rdv l
             LEFT JOIN divers.pgt_communes_france c
                    ON c.id_communes_france = l.id_communes_france
            WHERE l.is_actif = true
              AND (l.modif_elem IS NULL OR l.modif_elem NOT LIKE '%suppr%')
         ORDER BY l.lib_lieu ASC"""
    ) or []
    return [LieuRdvItem(
        id_cv_lieu_rdv=str(_int(r["id_cv_lieu_rdv"])),
        lib_lieu=_str(r["lib_lieu"]),
        adresse1=_str(r["adresse1"]),
        adresse2=_str(r["adresse2"]),
        code_postal=_str(r["code_postal"]),
        nom_ville=_str(r["nom_ville"]),
        latitude_deg=r["latitude_deg"],
        longitude_deg=r["longitude_deg"],
    ) for r in rows]


def list_salons_visio(id_recruteur: int) -> list[SalonVisioItem]:
    """Salons visio d'un recruteur."""
    if not id_recruteur:
        return []
    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT sv.id_salon_visio, sv.lien_salon, sv.id_salon, sv.mpd_salon,
                  ts.lib_salon
             FROM recrutement.pgt_salon_visio sv
             LEFT JOIN recrutement.pgt_type_salon_visio ts
                    ON ts.id_type_salon_visio = sv.id_type_salon_visio
            WHERE sv.id_salarie = ?
              AND (sv.modif_elem IS NULL OR sv.modif_elem NOT LIKE '%suppr%')
         ORDER BY ts.lib_salon ASC""",
        (int(id_recruteur),),
    ) or []
    return [SalonVisioItem(
        id_salon_visio=str(_int(r["id_salon_visio"])),
        lib_salon=_str(r.get("lib_salon")) or "Salon",
        lien_salon=_str(r["lien_salon"]),
        id_salon=_str(r["id_salon"]),
        mpd_salon=_str(r["mpd_salon"]),
    ) for r in rows]


# ---------------------------------------------------------------------------
# Agenda recruteur (visualisation semaine)
# ---------------------------------------------------------------------------


def list_agenda_recruteur(
    id_salarie: int, semaine_du: str,
) -> list[AgendaEventItem]:
    """Agenda d'un recruteur : RDV de la semaine demarrant a 'semaine_du'."""
    if not id_salarie:
        return []
    try:
        d = datetime.strptime(semaine_du[:10], "%Y-%m-%d").date()
    except ValueError:
        d = date.today()
    # Aller au lundi
    lundi = d - timedelta(days=d.weekday())
    dimanche_soir = lundi + timedelta(days=7)
    dt_deb = datetime.combine(lundi, time(0, 0, 0))
    dt_fin = datetime.combine(dimanche_soir, time(0, 0, 0))

    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT ae.id_agenda_evenement, ae.titre, ae.contenu,
                  ae.date_debut, ae.date_fin, ae.op_crea,
                  ac.lib_categorie, ac.couleur_r, ac.couleur_v, ac.couleur_b,
                  l.lib_lieu, l.adresse1, l.id_communes_france,
                  c.code_postal, c.nom_ville
             FROM recrutement.pgt_agenda_evenement ae
             LEFT JOIN recrutement.pgt_agenda_categorie ac
                    ON ac.id_agenda_categorie = ae.id_categorie
             LEFT JOIN recrutement.pgt_cv_lieu_rdv l
                    ON l.id_cv_lieu_rdv = ae.id_cv_lieux
             LEFT JOIN divers.pgt_communes_france c
                    ON c.id_communes_france = l.id_communes_france
            WHERE ae.id_salarie = ?
              AND ae.date_debut >= ? AND ae.date_debut < ?
              AND (ae.modif_elem IS NULL OR ae.modif_elem NOT LIKE '%suppr%')
         ORDER BY ae.date_debut ASC""",
        (int(id_salarie), dt_deb, dt_fin),
    ) or []

    # Resolve op_crea -> nom
    op_ids = {_int(r["op_crea"]) for r in rows if _int(r.get("op_crea"))}
    ops: dict[int, str] = {}
    if op_ids:
        db_rh = get_pg_connection("rh")
        ph = ",".join(["?"] * len(op_ids))
        opr = db_rh.query(
            f"SELECT id_salarie, nom, prenom FROM rh.pgt_salarie WHERE id_salarie IN ({ph})",
            tuple(op_ids),
        ) or []
        ops = {_int(r["id_salarie"]):
               f"{_str(r['nom']).upper()} {_str(r['prenom']).strip().title()}"
               for r in opr}

    out: list[AgendaEventItem] = []
    for r in rows:
        adresse_parts = [_str(r.get("adresse1")), _str(r.get("code_postal")),
                         _str(r.get("nom_ville"))]
        adresse = " ".join(p for p in adresse_parts if p)
        out.append(AgendaEventItem(
            id_agenda_evenement=str(_int(r["id_agenda_evenement"])),
            titre=_str(r["titre"]),
            contenu=_str(r["contenu"]),
            date_debut=str(r["date_debut"] or "")[:19],
            date_fin=str(r["date_fin"] or "")[:19],
            lib_categorie=_str(r.get("lib_categorie")),
            couleur_r=_int(r.get("couleur_r") or 200),
            couleur_v=_int(r.get("couleur_v") or 200),
            couleur_b=_int(r.get("couleur_b") or 200),
            lib_lieu=_str(r.get("lib_lieu")),
            adresse_complete=adresse,
            op_crea_nom=ops.get(_int(r.get("op_crea")), ""),
        ))
    return out


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def update_coordonnees_candidat(
    id_cv: int, p: UpdateCoordsPayload, op_id: int,
) -> dict:
    """Btn validation a cote du Mobile/Mail : MAJ gsm + mail dans cvtheque."""
    db = get_pg_connection("recrutement")
    gsm = "".join(c for c in p.gsm if c.isdigit() or c == "+")
    mail = (p.mail or "").strip().lower().replace(" ", "")
    db.query(
        """UPDATE recrutement.pgt_cvtheque
              SET gsm = ?, mail = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'new'
            WHERE id_cvtheque = ?""",
        (gsm, mail, int(op_id), int(id_cv)),
    )
    return {"ok": True, "gsm": gsm, "mail": mail}


def create_rdv(id_cv: int, p: CreateRdvPayload, op_id: int) -> dict:
    """Btn 'Valider le RDV' :
    - INSERT cvsuivi (id_cv_statut=6 'Entretien planifie', type_elem='RDV',
      id_elem=idRdv, observation='RDV pris avec <recruteur>')
    - INSERT agenda_evenement (categorie=1, date_debut+30min, type lieu,
      id_salon_visio si visio)

    TODO V_later : envoi SMS de confirmation + animation cooptation.
    """
    db = get_pg_connection("recrutement")
    db_rh = get_pg_connection("rh")

    # Resolve nom du recruteur
    rec = db_rh.query_one(
        "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ?",
        (int(p.id_recruteur),),
    )
    if not rec:
        return {"ok": False, "error": "recruteur_inconnu"}
    recruteur_nom = (
        f"{_str(rec['nom']).upper()} {_str(rec['prenom']).strip().title()}"
    )

    # Resolve nom candidat (pour le titre AgendaEvenement)
    cv = db.query_one(
        "SELECT nom, prenom, id_cvposte FROM recrutement.pgt_cvtheque "
        "WHERE id_cvtheque = ?",
        (int(id_cv),),
    )
    if not cv:
        return {"ok": False, "error": "cv_inconnu"}
    cand_nom = _str(cv["nom"]).upper()
    cand_prenom = _str(cv["prenom"]).strip().title()

    # Parse date_debut + 30 min pour date_fin
    try:
        dt_deb = datetime.fromisoformat(p.date_debut.replace("Z", ""))
    except (ValueError, AttributeError):
        return {"ok": False, "error": "date_invalide"}
    dt_fin = dt_deb + timedelta(minutes=30)

    # ID du nouveau RDV
    id_rdv = _new_id()
    id_cv_suivi = _new_id() + 1   # eviter doublon avec id_rdv

    # 1) INSERT cvsuivi
    db.query(
        """INSERT INTO recrutement.pgt_cvsuivi
             (id_cv_suivi, id_cvtheque, datecrea, op_crea, id_cv_statut,
              type_elem, id_elem, observation,
              modif_date, modif_op, modif_elem)
           VALUES (?, ?, NOW(), ?, 6,
                   'RDV', ?, ?,
                   NOW(), ?, 'new')""",
        (id_cv_suivi, int(id_cv), int(op_id), id_rdv,
         f"RDV pris avec {recruteur_nom}", int(op_id)),
    )

    # 2) INSERT agenda_evenement
    # categorie=1 par defaut (cf. WinDev)
    # Si visio : id_cv_lieux=1 (cf. WinDev hardcode)
    id_lieu = 1 if p.type_entretien == "Visio" else int(p.id_cv_lieu_rdv or 0)
    titre = f"RDV : {cand_nom} {cand_prenom}".strip()
    auto_id = _next_auto(db, "recrutement", "pgt_agenda_evenement",
                         "id_agenda_evenement_auto")
    db.query(
        """INSERT INTO recrutement.pgt_agenda_evenement
             (id_agenda_evenement_auto, id_agenda_evenement,
              id_salarie, id_cv_suivi, id_categorie,
              titre, contenu, date_debut, date_fin,
              id_cv_lieux, id_salon_visio, id_prevision_recrut,
              id_tk_liste, pb_presentation, pb_elocution, pb_motivation,
              pb_horaires,
              op_crea, modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, 1,
                   ?, '', ?, ?,
                   ?, ?, ?, 0, 0, 0, 0, 0,
                   ?, NOW(), ?, 'new')""",
        (auto_id, id_rdv,
         int(p.id_recruteur), id_cv_suivi,
         titre, dt_deb, dt_fin,
         id_lieu, int(p.id_salon_visio or 0), int(p.id_prevision_recrut or 0),
         int(op_id), int(op_id)),
    )

    # TODO V_later : envoi SMS de confirmation + animation cooptation
    return {
        "ok": True,
        "id_rdv": str(id_rdv),
        "id_cv_suivi": str(id_cv_suivi),
        "send_sms_pending": bool(p.send_sms),
    }


def _next_auto(db, schema: str, table: str, auto_col: str) -> int:
    """COALESCE(MAX(auto_col),0)+1. Helper pour HFSQL-migrated sans sequence."""
    r = db.query(f"SELECT COALESCE(MAX({auto_col}),0)+1 AS n FROM {schema}.{table}")
    return _int(r[0]["n"]) if r else 1
