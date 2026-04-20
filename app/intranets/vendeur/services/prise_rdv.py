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
    db_rec = get_connection("recrutement")
    db_rh = get_connection("rh")
    db_divers = get_connection("divers")
    today = _today_windev()

    rows = db_rec.query(
        """SELECT IDprevisionRecrut, dateSession, IDCommunesFrance,
            IdRecruteur, IDcvLieuRdv
        FROM prevRecrut
        WHERE (IDprevRecrutEtat = 6 OR IDprevRecrutEtat = 2)
          AND LEFT(dateSession, 8) >= ?
        ORDER BY dateSession ASC""",
        (today,),
    )

    if not rows:
        return []

    commune_ids = {_to_int(r.get("IDCommunesFrance")) for r in rows}
    commune_ids.discard(0)
    communes_map: dict[int, str] = {}
    if commune_ids:
        ids_sql = ",".join(str(i) for i in commune_ids)
        crows = db_divers.query(
            f"SELECT IDCommunesFrance, NomVille FROM CommunesFrance "
            f"WHERE IDCommunesFrance IN ({ids_sql})"
        )
        for c in crows:
            communes_map[_to_int(c.get("IDCommunesFrance"))] = c.get("NomVille") or ""

    # Noms recruteurs
    rec_ids = {_to_int(r.get("IdRecruteur")) for r in rows}
    rec_ids.discard(0)
    rec_map: dict[int, str] = {}
    if rec_ids:
        ids_sql = ",".join(str(i) for i in rec_ids)
        rrows = db_rh.query(
            f"SELECT IDSalarie, NOM, PRENOM FROM salarie WHERE IDSalarie IN ({ids_sql})"
        )
        for r in rrows:
            nom = r.get("NOM") or ""
            prenom = (r.get("PRENOM") or "").capitalize()
            rec_map[_to_int(r.get("IDSalarie"))] = f"{nom} {prenom}".strip()

    result = []
    for r in rows:
        ville = communes_map.get(_to_int(r.get("IDCommunesFrance")), "")
        ds = r.get("dateSession") or ""
        if "-" in ds:
            date_disp = f"{ds[8:10]}/{ds[5:7]}/{ds[0:4]}"
        elif ds and len(ds) >= 8:
            date_disp = f"{ds[6:8]}/{ds[4:6]}/{ds[0:4]}"
        else:
            date_disp = ds
        id_recruteur = _to_int(r.get("IdRecruteur"))
        result.append({
            "id_prevision_recrut": str(_to_int(r.get("IDprevisionRecrut"))),
            "date_session": ds,
            "nom_ville": ville,
            "label": f"{date_disp} - {ville}".strip(" -"),
            "id_recruteur": str(id_recruteur),
            "recruteur_nom": rec_map.get(id_recruteur, ""),
            "id_lieu_rdv": _to_int(r.get("IDcvLieuRdv")),
        })
    return result


def lister_lieux_rdv() -> list[dict]:
    """Liste les lieux de RDV actifs (hors Visio qui est un cas spécial ID=1)."""
    db = get_connection("recrutement")
    rows = db.query(
        """SELECT IDcvLieuRdv, Lib_Lieu FROM cvLieuRdv
        WHERE IsActif = 1 AND ModifELEM NOT LIKE '%suppr%'
        ORDER BY Lib_Lieu ASC"""
    )
    return [
        {
            "id_cv_lieu_rdv": _to_int(r.get("IDcvLieuRdv")),
            "lib_lieu": r.get("Lib_Lieu") or "",
        }
        for r in rows
    ]


def info_lieu_rdv(id_lieu: int) -> dict | None:
    """Infos d'un lieu de RDV (adresse + CP/Ville via JOIN CommunesFrance)."""
    db_rec = get_connection("recrutement")
    db_divers = get_connection("divers")

    row = db_rec.query_one(
        """SELECT IDcvLieuRdv, Lib_Lieu, ADRESSE1, ADRESSE2, IDCommunesFrance,
            latitude_deg, longitude_deg
        FROM cvLieuRdv WHERE IDcvLieuRdv = ?""",
        (id_lieu,),
    )
    if not row:
        return None

    cp = ""
    ville = ""
    id_commune = _to_int(row.get("IDCommunesFrance"))
    if id_commune:
        c = db_divers.query_one(
            "SELECT CodePostal, NomVille FROM CommunesFrance WHERE IDCommunesFrance = ?",
            (id_commune,),
        )
        if c:
            cp = c.get("CodePostal") or ""
            ville = c.get("NomVille") or ""

    return {
        "id_cv_lieu_rdv": _to_int(row.get("IDcvLieuRdv")),
        "lib_lieu": row.get("Lib_Lieu") or "",
        "adresse1": row.get("ADRESSE1") or "",
        "adresse2": row.get("ADRESSE2") or "",
        "cp": cp,
        "nom_ville": ville,
        "latitude": float(row.get("latitude_deg") or 0),
        "longitude": float(row.get("longitude_deg") or 0),
    }


def lister_salons_visio(id_salarie: int) -> list[dict]:
    """Liste les salons visio d'un recruteur."""
    db = get_connection("recrutement")
    rows = db.query(
        """SELECT DISTINCT sv.IDSalonVisio, tsv.Lib_Salon
        FROM SalonVisio sv
        INNER JOIN TypeSalonVisio tsv ON tsv.IDTypeSalonVisio = sv.IDTypeSalonVisio
        WHERE sv.ModifELEM NOT LIKE '%suppr%'
          AND sv.IDSalarie = ?
        ORDER BY tsv.Lib_Salon ASC""",
        (id_salarie,),
    )
    return [
        {
            "id_salon_visio": str(_to_int(r.get("IDSalonVisio"))),
            "lib_salon": r.get("Lib_Salon") or "",
        }
        for r in rows
    ]


def info_salon_visio(id_salon: int) -> dict | None:
    """Infos d'un salon visio (lien, id, mdp)."""
    db = get_connection("recrutement")
    row = db.query_one(
        """SELECT sv.IDSalonVisio, tsv.Lib_Salon, sv.LienSalon, sv.IdSalon, sv.MpdSalon
        FROM SalonVisio sv
        INNER JOIN TypeSalonVisio tsv ON tsv.IDTypeSalonVisio = sv.IDTypeSalonVisio
        WHERE sv.ModifELEM NOT LIKE '%suppr%'
          AND sv.IDSalonVisio = ?""",
        (id_salon,),
    )
    if not row:
        return None
    return {
        "id_salon_visio": str(_to_int(row.get("IDSalonVisio"))),
        "lib_salon": row.get("Lib_Salon") or "",
        "lien": row.get("LienSalon") or "",
        "id_reunion": row.get("IdSalon") or "",
        "mdp": row.get("MpdSalon") or "",
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
    db_rec = get_connection("recrutement")
    db_rh = get_connection("rh")
    db_divers = get_connection("divers")

    # Récup CV
    cv = db_rec.query_one(
        """SELECT NOM, PRENOM, GSM, MAIL, IDcvposte, IDcvsource, IdElemSource,
            PermisB, Véhicule, Adresse, IDCommunesFrance
        FROM cvtheque WHERE IDcvtheque = ?""",
        (id_cvtheque,),
    )
    if not cv:
        raise ValueError("CV introuvable")

    nom_cand = cv.get("NOM") or ""
    prenom_cand = (cv.get("PRENOM") or "").capitalize()

    # Nom recruteur
    rec = db_rh.query_one(
        "SELECT NOM, PRENOM FROM salarie WHERE IDSalarie = ?",
        (id_recruteur,),
    )
    if not rec:
        raise ValueError("Recruteur introuvable")
    nom_recruteur = f"{rec.get('NOM') or ''} {(rec.get('PRENOM') or '').capitalize()}".strip()

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
    adresse_cand = cv.get("Adresse") or ""
    id_commune_cand = _to_int(cv.get("IDCommunesFrance"))
    if id_commune_cand:
        c = db_divers.query_one(
            "SELECT CodePostal, NomVille, CodePays FROM CommunesFrance WHERE IDCommunesFrance = ?",
            (id_commune_cand,),
        )
        if c:
            adresse_cand += f", {c.get('CodePostal') or ''} {c.get('NomVille') or ''} - {c.get('CodePays') or 'FR'}"

    # Source label
    id_cv_source = _to_int(cv.get("IDcvsource"))
    id_elem_source = _to_int(cv.get("IdElemSource"))
    sources_map = {1: "Cooptation", 2: "Annonceurs"}
    source_label = sources_map.get(id_cv_source, "")
    if id_cv_source == 1 and id_elem_source:
        vend = db_rh.query_one(
            "SELECT NOM, PRENOM FROM salarie WHERE IDSalarie = ?", (id_elem_source,)
        )
        if vend:
            source_label += f" de {vend.get('NOM') or ''} {(vend.get('PRENOM') or '').capitalize()}"

    # Poste label
    poste_map = {0: "---sans profil---", 1: "VRP Énergie", 10: "Technicien Fibre", 13: "Commercial Fibre"}
    poste_label = poste_map.get(_to_int(cv.get("IDcvposte")), f"Poste #{_to_int(cv.get('IDcvposte'))}")

    # IdCvLieux : si Visio → 1, sinon = id_lieu_rdv
    id_cv_lieux = 1 if type_entretien == "Visio" else id_lieu_rdv

    # Titre + contenu
    titre = f"RDV : {nom_cand} {prenom_cand}"
    contenu = (
        f"Profil : {poste_label}\n"
        f"Permis : {'Oui' if cv.get('PermisB') else 'Non'}\n"
        f"Véhicule :  {'Oui' if cv.get('Véhicule') else 'Non'}\n"
        f"Adresse :  {adresse_cand}\n"
        f"Tél :  {cv.get('GSM') or ''}\n"
        f"Mail : {cv.get('MAIL') or ''}\n"
        f"Source : {source_label}\n"
    )

    now_wd = str(_new_id())

    # Création CvSuivi
    id_rdv = _new_id()
    id_suivi = _new_id() + 1

    obs_suivi = f"RDV pris avec {nom_recruteur}"
    obs_safe = obs_suivi.replace("'", "''")

    db_rec.query(
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

    db_rec.query(
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
    if envoyer_sms and cv.get("GSM"):
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

        gsm_clean = _format_tel(cv.get("GSM"))
        if gsm_clean:
            sms_result = envoi_sms(texte_sms, gsm_clean)

    return {
        "ok": True,
        "id_rdv": str(id_rdv),
        "sms_result": sms_result,
    }
