"""
Service prise de RDV (CVthèque → Planifier un RDV).

Transposition de la fenêtre Fen_PriseRDV WinDev.
Tables : cvLieuRdv, prevRecrut, SalonVisio, TypeSalonVisio, CvSuivi,
AgendaEvénement (toutes en Bdd_Omaya_Recrutement).
CommunesFrance en Bdd_Omaya_Divers (cross-base).
"""

import base64
import re
import struct
from datetime import datetime

from app.core.config import DOCS_URL
from app.core.database import get_connection
from app.core.database.pg import get_pg_connection
from app.shared.notifications.sms import envoi_sms


def _to_int(v) -> int:
    if v is None or v == "":
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            pass
        try:
            raw = base64.b64decode(v)
            if len(raw) == 8:
                return struct.unpack("<q", raw)[0]
            if len(raw) == 4:
                return struct.unpack("<i", raw)[0]
        except Exception:
            pass
    return 0


def _new_id() -> int:
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


def _today_windev() -> str:
    return datetime.now().strftime("%Y%m%d")


def _format_tel(tel: str) -> str:
    return re.sub(r"\D", "", tel or "")


# --- Référentiels ---------------------------------------------------------

def lister_sessions() -> list[dict]:
    """
    Liste les sessions de recrutement actives (IDprevRecrutEtat = 2 ou 6)
    à partir d'aujourd'hui, avec le nom de ville + recruteur + lieu.
    """
    db_rec = get_pg_connection("recrutement")
    db_rh = get_pg_connection("rh")
    db_divers = get_pg_connection("divers")
    today = _today_windev()

    rows = db_rec.query(
        """SELECT id_prevision_recrut, date_session, id_communes_france,
            id_recruteur, id_cv_lieu_rdv
        FROM pgt_prev_recrut
        WHERE (id_prev_recrut_etat = 6 OR id_prev_recrut_etat = 2)
          AND date_session::date >= ?::date
        ORDER BY date_session ASC""",
        (today,),
    )

    if not rows:
        return []

    commune_ids = {_to_int(r.get("id_communes_france")) for r in rows}
    commune_ids.discard(0)
    communes_map: dict[int, str] = {}
    if commune_ids:
        ids_sql = ",".join(str(i) for i in commune_ids)
        crows = db_divers.query(
            f"SELECT id_communes_france, nom_ville FROM pgt_communes_france "
            f"WHERE id_communes_france IN ({ids_sql})"
        )
        for c in crows:
            communes_map[_to_int(c.get("id_communes_france"))] = c.get("nom_ville") or ""

    # Noms recruteurs
    rec_ids = {_to_int(r.get("id_recruteur")) for r in rows}
    rec_ids.discard(0)
    rec_map: dict[int, str] = {}
    if rec_ids:
        ids_sql = ",".join(str(i) for i in rec_ids)
        rrows = db_rh.query(
            f"SELECT id_salarie, nom, prenom FROM pgt_salarie WHERE id_salarie IN ({ids_sql})"
        )
        for r in rrows:
            nom = r.get("nom") or ""
            prenom = (r.get("prenom") or "").capitalize()
            rec_map[_to_int(r.get("id_salarie"))] = f"{nom} {prenom}".strip()

    result = []
    for r in rows:
        ville = communes_map.get(_to_int(r.get("id_communes_france")), "")
        ds = r.get("date_session") or ""
        if "-" in ds:
            date_disp = f"{ds[8:10]}/{ds[5:7]}/{ds[0:4]}"
        elif ds and len(ds) >= 8:
            date_disp = f"{ds[6:8]}/{ds[4:6]}/{ds[0:4]}"
        else:
            date_disp = ds
        id_recruteur = _to_int(r.get("id_recruteur"))
        result.append({
            "id_prevision_recrut": str(_to_int(r.get("id_prevision_recrut"))),
            "date_session": ds,
            "nom_ville": ville,
            "label": f"{date_disp} - {ville}".strip(" -"),
            "id_recruteur": str(id_recruteur),
            "recruteur_nom": rec_map.get(id_recruteur, ""),
            "id_lieu_rdv": _to_int(r.get("id_cv_lieu_rdv")),
        })
    return result


def lister_lieux_rdv() -> list[dict]:
    """Liste les lieux de RDV actifs (hors Visio qui est un cas spécial ID=1)."""
    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT id_cv_lieu_rdv, lib_lieu FROM pgt_cv_lieu_rdv
        WHERE is_actif = TRUE AND modif_elem NOT LIKE '%suppr%'
        ORDER BY lib_lieu ASC"""
    )
    return [
        {
            "id_cv_lieu_rdv": _to_int(r.get("id_cv_lieu_rdv")),
            "lib_lieu": r.get("lib_lieu") or "",
        }
        for r in rows
    ]


def info_lieu_rdv(id_lieu: int) -> dict | None:
    """Infos d'un lieu de RDV (adresse + CP/Ville via JOIN CommunesFrance)."""
    db_rec = get_pg_connection("recrutement")
    db_divers = get_pg_connection("divers")

    row = db_rec.query_one(
        """SELECT id_cv_lieu_rdv, lib_lieu, adresse1, adresse2, id_communes_france,
            latitude_deg, longitude_deg
        FROM pgt_cv_lieu_rdv WHERE id_cv_lieu_rdv = ?""",
        (id_lieu,),
    )
    if not row:
        return None

    cp = ""
    ville = ""
    id_commune = _to_int(row.get("id_communes_france"))
    if id_commune:
        c = db_divers.query_one(
            "SELECT code_postal, nom_ville FROM pgt_communes_france WHERE id_communes_france = ?",
            (id_commune,),
        )
        if c:
            cp = c.get("code_postal") or ""
            ville = c.get("nom_ville") or ""

    return {
        "id_cv_lieu_rdv": _to_int(row.get("id_cv_lieu_rdv")),
        "lib_lieu": row.get("lib_lieu") or "",
        "adresse1": row.get("adresse1") or "",
        "adresse2": row.get("adresse2") or "",
        "cp": cp,
        "nom_ville": ville,
        "latitude": float(row.get("latitude_deg") or 0),
        "longitude": float(row.get("longitude_deg") or 0),
    }


def lister_salons_visio(id_salarie: int) -> list[dict]:
    """Liste les salons visio d'un recruteur."""
    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT DISTINCT sv.id_salon_visio, tsv.lib_salon
        FROM pgt_salon_visio sv
        INNER JOIN pgt_type_salon_visio tsv ON tsv.id_type_salon_visio = sv.id_type_salon_visio
        WHERE sv.modif_elem NOT LIKE '%suppr%'
          AND sv.id_salarie = ?
        ORDER BY tsv.lib_salon ASC""",
        (id_salarie,),
    )
    return [
        {
            "id_salon_visio": str(_to_int(r.get("id_salon_visio"))),
            "lib_salon": r.get("lib_salon") or "",
        }
        for r in rows
    ]


def info_salon_visio(id_salon: int) -> dict | None:
    """Infos d'un salon visio (lien, id, mdp)."""
    db = get_pg_connection("recrutement")
    row = db.query_one(
        """SELECT sv.id_salon_visio, tsv.lib_salon, sv.lien_salon, sv.id_salon, sv.mpd_salon
        FROM pgt_salon_visio sv
        INNER JOIN pgt_type_salon_visio tsv ON tsv.id_type_salon_visio = sv.id_type_salon_visio
        WHERE sv.modif_elem NOT LIKE '%suppr%'
          AND sv.id_salon_visio = ?""",
        (id_salon,),
    )
    if not row:
        return None
    return {
        "id_salon_visio": str(_to_int(row.get("id_salon_visio"))),
        "lib_salon": row.get("lib_salon") or "",
        "lien": row.get("lien_salon") or "",
        "id_reunion": row.get("id_salon") or "",
        "mdp": row.get("mpd_salon") or "",
    }


# --- Prise de RDV ---------------------------------------------------------

def planifier_rdv(
    id_cvtheque: int,
    id_recruteur: int,
    id_session: int,
    date_rdv: str,  # YYYY-MM-DD
    heure_rdv: str,  # HH:MM
    type_entretien: str,
    id_lieu_rdv: int,
    id_salon_visio: int,
    envoyer_sms: bool,
    id_salarie_user: int,
    prenom_user: str,
    nom_user: str,
) -> dict:
    """
    Planifie un RDV : CvSuivi + AgendaEvénement + SMS optionnel.
    """
    db_rec_hf = get_connection("recrutement")  # HFSQL pour les ecritures
    db_rec_pg = get_pg_connection("recrutement")  # PG pour les lectures
    db_rh = get_pg_connection("rh")
    db_divers = get_pg_connection("divers")

    # Récup CV
    cv = db_rec_pg.query_one(
        """SELECT nom, prenom, gsm, mail, id_cvposte, id_cvsource, id_elem_source,
            permis_b, vehicule, adresse, id_communes_france
        FROM pgt_cvtheque WHERE id_cvtheque = ?""",
        (id_cvtheque,),
    )
    if not cv:
        raise ValueError("CV introuvable")

    nom_cand = cv.get("nom") or ""
    prenom_cand = (cv.get("prenom") or "").capitalize()

    # Nom recruteur
    rec = db_rh.query_one(
        "SELECT nom, prenom FROM pgt_salarie WHERE id_salarie = ?",
        (id_recruteur,),
    )
    if not rec:
        raise ValueError("Recruteur introuvable")
    nom_recruteur = f"{rec.get('nom') or ''} {(rec.get('prenom') or '').capitalize()}".strip()

    # DateHeure RDV
    try:
        date_parts = date_rdv.split("-")
        h, m = heure_rdv.split(":")
        date_debut_iso = f"{date_parts[0]}-{date_parts[1]}-{date_parts[2]} {h.zfill(2)}:{m.zfill(2)}:00"
        date_obj = datetime(
            int(date_parts[0]), int(date_parts[1]), int(date_parts[2]),
            int(h), int(m)
        )
    except Exception:
        raise ValueError("Date ou heure invalide")

    # +30 min pour la fin
    from datetime import timedelta
    date_fin_obj = date_obj + timedelta(minutes=30)
    date_fin_iso = date_fin_obj.strftime("%Y-%m-%d %H:%M:%S")

    # Adresse complète du candidat
    adresse_cand = cv.get("adresse") or ""
    id_commune_cand = _to_int(cv.get("id_communes_france"))
    if id_commune_cand:
        c = db_divers.query_one(
            "SELECT code_postal, nom_ville, code_pays FROM pgt_communes_france WHERE id_communes_france = ?",
            (id_commune_cand,),
        )
        if c:
            adresse_cand += f", {c.get('code_postal') or ''} {c.get('nom_ville') or ''} - {c.get('code_pays') or 'FR'}"

    # Source label
    id_cv_source = _to_int(cv.get("id_cvsource"))
    id_elem_source = _to_int(cv.get("id_elem_source"))
    sources_map = {1: "Cooptation", 2: "Annonceurs"}
    source_label = sources_map.get(id_cv_source, "")
    if id_cv_source == 1 and id_elem_source:
        vend = db_rh.query_one(
            "SELECT nom, prenom FROM pgt_salarie WHERE id_salarie = ?", (id_elem_source,)
        )
        if vend:
            source_label += f" de {vend.get('nom') or ''} {(vend.get('prenom') or '').capitalize()}"

    # Poste label
    poste_map = {0: "---sans profil---", 1: "VRP Énergie", 10: "Technicien Fibre", 13: "Commercial Fibre"}
    poste_label = poste_map.get(_to_int(cv.get("id_cvposte")), f"Poste #{_to_int(cv.get('id_cvposte'))}")

    # IdCvLieux : si Visio → 1, sinon = id_lieu_rdv
    id_cv_lieux = 1 if type_entretien == "Visio" else id_lieu_rdv

    # Titre + contenu
    titre = f"RDV : {nom_cand} {prenom_cand}"
    contenu = (
        f"Profil : {poste_label}\n"
        f"Permis : {'Oui' if cv.get('permis_b') else 'Non'}\n"
        f"Véhicule :  {'Oui' if cv.get('vehicule') else 'Non'}\n"
        f"Adresse :  {adresse_cand}\n"
        f"Tél :  {cv.get('gsm') or ''}\n"
        f"Mail : {cv.get('mail') or ''}\n"
        f"Source : {source_label}\n"
    )

    now_wd = str(_new_id())

    # Création CvSuivi
    id_rdv = _new_id()
    id_suivi = _new_id() + 1

    obs_suivi = f"RDV pris avec {nom_recruteur}"
    obs_safe = obs_suivi.replace("'", "''")

    db_rec_hf.query(
        f"""INSERT INTO CvSuivi (
            IDCvSuivi, IDcvtheque, Datecrea, OPCREA, IdCvStatut,
            TypeElem, IdElem, Observation, ModifDate, ModifOp, ModifElem
        ) VALUES (
            {id_suivi}, {id_cvtheque}, '{now_wd}', {id_salarie_user}, 6,
            'RDV', {id_rdv}, '{obs_safe}', '{now_wd}', {id_salarie_user}, 'new'
        )"""
    )

    # Création AgendaEvénement
    titre_safe = titre.replace("'", "''")
    contenu_safe = contenu.replace("'", "''")

    db_rec_hf.query(
        f"""INSERT INTO AgendaEvénement (
            IDAgendaEvénement, IDSalarie, IDCvSuivi, IDCatégorie,
            Titre, Contenu, DateDébut, DateFin,
            IdCvLieux, IDSalonVisio, IDprevisionRecrut, IDTK_Liste,
            Pb_Presentation, Pb_Elocution, Pb_Motivation, Pb_Horaires,
            OPCrea, ModifDate, ModifOP, ModifELEM
        ) VALUES (
            {id_rdv}, {id_recruteur}, {id_suivi}, 1,
            '{titre_safe}', '{contenu_safe}', '{date_debut_iso}', '{date_fin_iso}',
            {id_cv_lieux}, {id_salon_visio}, {id_session}, 0,
            0, 0, 0, 0,
            {id_salarie_user}, '{now_wd}', {id_salarie_user}, 'new'
        )"""
    )

    # SMS optionnel
    sms_result = ""
    if envoyer_sms and cv.get("gsm"):
        # Construction du texte SMS selon type
        lieu_texte = ""
        if type_entretien == "Physique" and id_lieu_rdv:
            lieu_info = info_lieu_rdv(id_lieu_rdv)
            if lieu_info:
                lieu_lines = [lieu_info["lib_lieu"], lieu_info["adresse1"]]
                if lieu_info["adresse2"]:
                    lieu_lines.append(lieu_info["adresse2"])
                lieu_lines.append(f"{lieu_info['cp']} {lieu_info['nom_ville']}")
                lieu_texte = "Adresse : " + "\n".join(lieu_lines) + "\n"
                if lieu_info["latitude"] and lieu_info["longitude"]:
                    lieu_texte += f"Lien Maps : https://www.google.com/maps/?q={lieu_info['latitude']},{lieu_info['longitude']}"
        elif type_entretien == "Visio" and id_salon_visio:
            salon = info_salon_visio(id_salon_visio)
            if salon:
                lieu_texte = (
                    f"Le jour J, cliquez sur le lien suivant pour démarrer votre entretien VISIO "
                    f"{salon['lib_salon']} : \nLien : \n{salon['lien']}\n"
                )
                if salon["id_reunion"]:
                    lieu_texte += f"ID Reunion :{salon['id_reunion']}\n"
                if salon["mdp"]:
                    lieu_texte += f"Code secret :{salon['mdp']}\n"

        date_disp = date_obj.strftime("%d/%m/%Y %H:%M")
        conf_url = f"https://groupe-exo.omaya.fr/PAGESEXTERNES_WEB/FR/Page-ConfRDV.awp?P1={id_rdv}"

        texte_sms = (
            f"Bonjour,\n"
            f"Votre entretien aura lieu le {date_disp} avec {nom_recruteur}.\n\n"
            f"Pour confirmer : {conf_url}\n\n"
            f"{lieu_texte}"
        )

        gsm_clean = _format_tel(cv.get("gsm"))
        if gsm_clean:
            sms_result = envoi_sms(texte_sms, gsm_clean)

    return {
        "ok": True,
        "id_rdv": str(id_rdv),
        "sms_result": sms_result,
    }
