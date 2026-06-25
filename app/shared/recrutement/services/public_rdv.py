"""Page externe de confirmation de RDV (accessible sans login).

Le candidat recoit un SMS avec un lien vers cette page, qu'il ouvre
pour voir le detail de son RDV puis le confirmer.

Aucune dependance d'auth : ces endpoints sont volontairement publics.
La securite par obscurite tient au fait que l'id_rdv est un timestamp
sur 8 octets (impossible a deviner).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection
from app.shared.recrutement.services.recherche_cv import _int, _str


def _new_id() -> int:
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S")) * 1000 + n.microsecond // 1000


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PublicRdvDetail(BaseModel):
    id_agenda_evenement: str
    candidat_nom: str = ""
    candidat_prenom: str = ""
    recruteur_nom: str = ""
    date_debut: str = ""           # ISO YYYY-MM-DDTHH:MM:SS
    date_fin: str = ""
    type_entretien: str = ""        # 'Physique' ou 'Visio'
    lib_lieu: str = ""
    adresse1: str = ""
    code_postal: str = ""
    nom_ville: str = ""
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    lien_salon: str = ""
    salon_id: str = ""
    salon_mdp: str = ""
    is_confirme: bool = False


class ConfirmPayload(BaseModel):
    confirme: bool = True


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------


def get_rdv_public(id_rdv: int) -> Optional[PublicRdvDetail]:
    """Detail public d'un RDV (vue candidat)."""
    db = get_pg_connection("recrutement")
    row = db.query_one(
        """SELECT ae.id_agenda_evenement, ae.titre, ae.date_debut, ae.date_fin,
                  ae.id_salarie, ae.id_cv_suivi, ae.id_cv_lieux, ae.id_salon_visio,
                  l.lib_lieu, l.adresse1, l.latitude_deg, l.longitude_deg,
                  l.id_communes_france,
                  cs.id_cvtheque
             FROM recrutement.pgt_agenda_evenement ae
             LEFT JOIN recrutement.pgt_cv_lieu_rdv l
                    ON l.id_cv_lieu_rdv = ae.id_cv_lieux
             LEFT JOIN recrutement.pgt_cvsuivi cs
                    ON cs.id_cv_suivi = ae.id_cv_suivi
            WHERE ae.id_agenda_evenement = ?
              AND (ae.modif_elem IS NULL OR ae.modif_elem NOT LIKE '%suppr%')""",
        (int(id_rdv),),
    )
    if not row:
        return None

    # Candidat (via cv_suivi -> cvtheque)
    cand_nom, cand_prenom = "", ""
    id_cv = _int(row.get("id_cvtheque"))
    if id_cv:
        cv = db.query_one(
            "SELECT nom, prenom FROM recrutement.pgt_cvtheque WHERE id_cvtheque = ?",
            (id_cv,),
        )
        if cv:
            cand_nom = _str(cv.get("nom")).upper()
            cand_prenom = _str(cv.get("prenom")).strip().title()

    # Recruteur
    rec_nom = ""
    id_rec = _int(row.get("id_salarie"))
    if id_rec:
        db_rh = get_pg_connection("rh")
        sal = db_rh.query_one(
            "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ?",
            (id_rec,),
        )
        if sal:
            n = _str(sal.get("nom")).upper()
            p = _str(sal.get("prenom")).strip().title()
            rec_nom = f"{n} {p}".strip()

    # Lieu (cp + ville via communes si on a)
    cp, ville = "", ""
    id_com = _int(row.get("id_communes_france"))
    if id_com:
        db_div = get_pg_connection("divers")
        com = db_div.query_one(
            "SELECT code_postal, nom_ville FROM divers.pgt_communes_france "
            "WHERE id_communes_france = ?",
            (id_com,),
        )
        if com:
            cp = _str(com.get("code_postal"))
            ville = _str(com.get("nom_ville"))

    # Visio (si applicable)
    lien_salon, salon_id, salon_mdp = "", "", ""
    id_salon = _int(row.get("id_salon_visio"))
    type_entr = "Visio" if id_salon else "Physique"
    if type_entr == "Visio":
        salon = db.query_one(
            """SELECT lien_salon, id_salon, mpd_salon FROM recrutement.pgt_salon_visio
                WHERE id_salon_visio = ?""",
            (id_salon,),
        )
        if salon:
            lien_salon = _str(salon.get("lien_salon"))
            salon_id = _str(salon.get("id_salon"))
            salon_mdp = _str(salon.get("mpd_salon"))

    # Verifie si deja confirme via la categorie de l'agenda (11 = Confirme)
    cat = db.query_one(
        "SELECT id_categorie FROM recrutement.pgt_agenda_evenement "
        "WHERE id_agenda_evenement = ?",
        (int(id_rdv),),
    )
    is_confirme = _int((cat or {}).get("id_categorie")) == 11

    return PublicRdvDetail(
        id_agenda_evenement=str(_int(row["id_agenda_evenement"])),
        candidat_nom=cand_nom,
        candidat_prenom=cand_prenom,
        recruteur_nom=rec_nom,
        date_debut=str(row.get("date_debut") or "")[:19],
        date_fin=str(row.get("date_fin") or "")[:19],
        type_entretien=type_entr,
        lib_lieu=_str(row.get("lib_lieu")),
        adresse1=_str(row.get("adresse1")),
        code_postal=cp,
        nom_ville=ville,
        latitude_deg=row.get("latitude_deg"),
        longitude_deg=row.get("longitude_deg"),
        lien_salon=lien_salon,
        salon_id=salon_id,
        salon_mdp=salon_mdp,
        is_confirme=is_confirme,
    )


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------


def confirm_rdv(id_rdv: int) -> dict:
    """Le candidat confirme sa presence (transposition WinDev) :
      - UPDATE agenda_evenement.id_categorie = 11 (categorie 'Confirme')
      - UPDATE cv_suivi.observation : concat 'Rdv Confirme par SMS Auto le ...'
    Idempotent : si deja categorie=11, retourne ok sans rien faire.
    """
    db = get_pg_connection("recrutement")
    # Recupere id_cv_suivi + categorie actuelle
    rdv = db.query_one(
        """SELECT id_cv_suivi, id_categorie
             FROM recrutement.pgt_agenda_evenement
            WHERE id_agenda_evenement = ?""",
        (int(id_rdv),),
    )
    if not rdv:
        return {"ok": False, "error": "rdv_inconnu"}

    # Deja confirme ?
    if _int(rdv.get("id_categorie")) == 11:
        return {"ok": True, "already": True}

    # 1) UPDATE agenda_evenement.id_categorie = 11
    db.query(
        """UPDATE recrutement.pgt_agenda_evenement
              SET id_categorie = 11, modif_date = NOW()
            WHERE id_agenda_evenement = ?""",
        (int(id_rdv),),
    )

    # 2) UPDATE cv_suivi.observation (concat) si le RDV a un cvsuivi lie
    id_cv_suivi = _int(rdv.get("id_cv_suivi"))
    if id_cv_suivi:
        suivi = db.query_one(
            "SELECT observation FROM recrutement.pgt_cvsuivi WHERE id_cv_suivi = ?",
            (id_cv_suivi,),
        )
        old_obs = _str((suivi or {}).get("observation"))
        log_line = (
            f"Rdv Confirme par SMS Auto le "
            f"{datetime.now().strftime('%d/%m/%Y a %H:%M')}"
        )
        new_obs = (old_obs + "\n" + log_line) if old_obs else log_line
        db.query(
            """UPDATE recrutement.pgt_cvsuivi
                  SET observation = ?, modif_date = NOW()
                WHERE id_cv_suivi = ?""",
            (new_obs, id_cv_suivi),
        )
    return {"ok": True}
