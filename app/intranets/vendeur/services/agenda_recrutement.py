"""
Services agenda de recrutement : listing RDV + recherche recruteur.

Transposition de PAGE_AgendaRec WinDev.
Table AgendaEvénement + AgendaCatégorie dans Bdd_Omaya_Recrutement.
Jointures sur CvSuivi + cvtheque + cvposte pour les infos candidat.
"""

import base64
import struct
from datetime import datetime
from urllib.parse import quote

from app.core.config import DOCS_URL
from app.core.database import get_connection
from app.shared.notifications.mail import envoi_mail_rh, verifier_email
from app.shared.notifications.sms import envoi_sms


def _now_windev() -> str:
    """Format date/heure WinDev : YYYYMMDDHHMMSSmmm (17 chars)."""
    now = datetime.now()
    return now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"


def _new_id() -> int:
    return int(_now_windev())


def _format_fr_datetime(raw: str) -> str:
    """Format WinDev: JJ/MM/AAAA à HH:mm depuis now()."""
    now = datetime.now()
    return now.strftime("%d/%m/%Y à %H:%M")


def _to_int(v) -> int:
    """Convertit une valeur HFSQL en int, en décodant base64 si nécessaire (8-byte integers)."""
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


def _to_hex(r: int | None, g: int | None, b: int | None) -> str:
    """Convertit RGB (entiers signés WinDev) en hex #RRGGBB."""
    rr = max(0, min(255, int(r or 0)))
    gg = max(0, min(255, int(g or 0)))
    bb = max(0, min(255, int(b or 0)))
    return f"#{rr:02X}{gg:02X}{bb:02X}"


def lister_rdvs(id_recruteur: int, date_from: str, date_to: str) -> list[dict]:
    """
    Liste des RDV de l'agenda d'un recruteur sur une plage de dates.

    date_from / date_to : format YYYYMMDD.
    """
    db = get_connection("recrutement")


    rows = db.query(
        """SELECT
            ae.IDAgendaEvénement,
            ae.DateDébut,
            ae.DateFin,
            ae.Titre,
            ae.Contenu,
            ae.IDCatégorie,
            ae.IDCvSuivi,
            ac.Lib_Catégorie,
            ac.CouleurR,
            ac.CouleurV,
            ac.CouleurB,
            ac.IdCvStatut,
            cs.IDcvtheque,
            cv.NOM,
            cv.PRENOM,
            cv.GSM,
            cv.MAIL,
            cv.Adresse,
            cv.Fic_CV,
            cv.OBSERV,
            cv.IDcvposte,
            cv.IDcvsource,
            cv.IdElemSource,
            cv.IDCommunesFrance,
            cp.Lib_Poste
        FROM AgendaEvénement ae
        INNER JOIN AgendaCatégorie ac ON ac.IDAgendaCatégorie = ae.IDCatégorie
        LEFT JOIN CvSuivi cs ON cs.IDCvSuivi = ae.IDCvSuivi
        LEFT JOIN cvtheque cv ON cv.IDcvtheque = cs.IDcvtheque
        LEFT JOIN cvposte cp ON cp.IDcvposte = cv.IDcvposte
        WHERE LEFT(ae.DateDébut, 8) >= ?
          AND LEFT(ae.DateDébut, 8) <= ?
          AND ae.IDSalarie = ?
          AND ae.ModifELEM NOT LIKE '%suppr%'
        ORDER BY ae.DateDébut ASC""",
        (date_from, date_to, id_recruteur),
    )

    # Récupérer CP/Ville depuis CommunesFrance (base divers)
    commune_ids = {_to_int(r.get("IDCommunesFrance")) for r in rows}
    commune_ids.discard(0)
    communes_map: dict[int, dict] = {}
    if commune_ids:
        db_divers = get_connection("divers")
        ids_list = ",".join(str(i) for i in commune_ids)
        commune_rows = db_divers.query(
            f"""SELECT IDCommunesFrance, CodePostal, NomVille
            FROM CommunesFrance
            WHERE IDCommunesFrance IN ({ids_list})"""
        )
        for cr in commune_rows:
            communes_map[int(cr.get("IDCommunesFrance") or 0)] = {
                "cp": cr.get("CodePostal") or "",
                "ville": cr.get("NomVille") or "",
            }

    return _build_rdv_list(rows, communes_map)


def lister_statuts() -> list[dict]:
    """Liste des statuts modifiables (IdCvStatut > 6) triés par libellé."""
    db = get_connection("recrutement")
    rows = db.query(
        """SELECT IDAgendaCatégorie, Lib_Catégorie, IdCvStatut
        FROM AgendaCatégorie
        WHERE ModifELEM NOT LIKE '%suppr%' AND IdCvStatut > 6
        ORDER BY Lib_Catégorie ASC"""
    )
    return [
        {
            "id_categorie": _to_int(r.get("IDAgendaCatégorie")),
            "lib_categorie": r.get("Lib_Catégorie") or "",
            "id_cv_statut": _to_int(r.get("IdCvStatut")),
        }
        for r in rows
    ]


def statuer_rdv(
    id_rdv: int,
    id_categorie: int,
    motif: str,
    pb_presentation: bool,
    pb_elocution: bool,
    pb_motivation: bool,
    pb_horaires: bool,
    id_salarie_user: int,
    nom_user: str,
    prenom_user: str,
) -> None:
    """
    Statue un RDV : update AgendaEvénement, insert CvSuivi si lié à un candidat,
    append à l'historique Contenu.
    """
    db = get_connection("recrutement")

    # Récupérer les infos du statut choisi
    statut = db.query_one(
        "SELECT Lib_Catégorie, IdCvStatut FROM AgendaCatégorie WHERE IDAgendaCatégorie = ?",
        (id_categorie,),
    )
    if not statut:
        raise ValueError("Statut inconnu")
    lib_cat = statut.get("Lib_Catégorie") or ""
    id_cv_statut = _to_int(statut.get("IdCvStatut"))

    rdv = db.query_one(
        "SELECT Contenu, IDCvSuivi FROM AgendaEvénement WHERE IDAgendaEvénement = ?",
        (id_rdv,),
    )
    if not rdv:
        raise ValueError("RDV introuvable")

    id_cv_suivi = _to_int(rdv.get("IDCvSuivi"))
    contenu = rdv.get("Contenu") or ""

    # Construire la ligne d'historique
    info = f"RDV statué en {lib_cat} par {nom_user} {prenom_user.capitalize()} (via l'intranet)"
    if motif:
        info += f" : {motif}"

    now_fr = _format_fr_datetime("")
    new_contenu = f"{contenu}\n{now_fr} - {info}" if contenu else f"{now_fr} - {info}"
    now_wd = _now_windev()

    # Si le RDV est lié à un candidat, on ajoute un CvSuivi
    if id_cv_suivi != 0:
        cv_row = db.query_one(
            "SELECT IDcvtheque FROM CvSuivi WHERE IDCvSuivi = ?",
            (id_cv_suivi,),
        )
        if cv_row:
            id_cvtheque = _to_int(cv_row.get("IDcvtheque"))
            id_suivi = _new_id()
            # Échapper les quotes dans info
            obs_safe = info.replace("'", "''")
            db.query(
                f"""INSERT INTO CvSuivi (
                    IDCvSuivi, IDcvtheque, Datecrea, OPCREA, IdCvStatut,
                    TypeElem, IdElem, Observation, ModifDate, ModifOp, ModifElem
                ) VALUES ({id_suivi}, {id_cvtheque}, '{now_wd}', {id_salarie_user}, {id_cv_statut},
                    'RDV', {id_rdv}, '{obs_safe}', '{now_wd}', {id_salarie_user}, 'new')"""
            )

    # Update AgendaEvénement
    contenu_safe = new_contenu.replace("'", "''")
    motif_safe = motif.replace("'", "''")
    db.query(
        f"""UPDATE AgendaEvénement
        SET IDCatégorie = {id_categorie},
            Contenu = '{contenu_safe}',
            MotifStatut = '{motif_safe}',
            ModifDate = '{now_wd}',
            Pb_Presentation = {1 if pb_presentation else 0},
            Pb_Elocution = {1 if pb_elocution else 0},
            Pb_Motivation = {1 if pb_motivation else 0},
            Pb_Horaires = {1 if pb_horaires else 0}
        WHERE IDAgendaEvénement = {id_rdv}"""
    )


def convoquer_jo(
    id_rdv: int,
    id_salarie_user: int,
    nom_user: str,
    prenom_user: str,
    mail_user: str = "",
) -> dict:
    """
    Convoque le candidat en JO : crée TK_DemandeDPAE + TK_Liste,
    append à l'historique, envoie SMS + mail au candidat.

    Retourne : {"id_ticket": int, "sms_result": str, "mail_sent": bool}.
    """
    db_rec = get_connection("recrutement")
    db_tkdpae = get_connection("ticket_dpae")
    db_tk = get_connection("ticket")
    db_divers = get_connection("divers")

    # Récup RDV
    rdv = db_rec.query_one(
        "SELECT Contenu, IDCvSuivi, IDCatégorie FROM AgendaEvénement WHERE IDAgendaEvénement = ?",
        (id_rdv,),
    )
    if not rdv:
        raise ValueError("RDV introuvable")

    id_cv_suivi = _to_int(rdv.get("IDCvSuivi"))
    if id_cv_suivi == 0:
        raise ValueError("RDV non lié à un candidat")

    # Récup candidat via CvSuivi → cvtheque
    cand = db_rec.query_one(
        """SELECT cv.NOM, cv.PRENOM, cv.MAIL, cv.IDCommunesFrance, cv.GSM,
            cv.IDcvsource, cv.IdElemSource, cv.DateNaissance
        FROM cvtheque cv
        INNER JOIN CvSuivi cs ON cs.IDcvtheque = cv.IDcvtheque
        WHERE cs.IDCvSuivi = ?""",
        (id_cv_suivi,),
    )
    if not cand:
        raise ValueError("Candidat introuvable")

    nom = cand.get("NOM") or ""
    prenom = cand.get("PRENOM") or ""
    # Edge case : si prénom contient "IMPORT", on split à partir du NOM
    if "IMPORT" in prenom.upper():
        parts = nom.split(" ", 1)
        if len(parts) == 2:
            prenom = parts[0]
            nom = parts[1]
        else:
            prenom = ""
    mail = cand.get("MAIL") or ""
    gsm = cand.get("GSM") or ""
    date_naissance = cand.get("DateNaissance") or ""
    id_cv_source = _to_int(cand.get("IDcvsource"))
    id_elem_source = _to_int(cand.get("IdElemSource"))
    id_commune = _to_int(cand.get("IDCommunesFrance"))

    # CP / Ville
    cp = ""
    ville = ""
    if id_commune:
        commune = db_divers.query_one(
            "SELECT CodePostal, NomVille FROM CommunesFrance WHERE IDCommunesFrance = ?",
            (id_commune,),
        )
        if commune:
            cp = commune.get("CodePostal") or ""
            ville = commune.get("NomVille") or ""

    # Cooptation ?
    coopte = 1 if id_cv_source == 1 else 0
    coopteur = id_elem_source if coopte else 0

    id_ticket = _new_id()
    now_wd = _now_windev()

    nom_safe = nom.replace("'", "''")
    prenom_safe = prenom.replace("'", "''")
    mail_safe = mail.replace("'", "''")
    gsm_safe = gsm.replace("'", "''")
    ville_safe = ville.replace("'", "''")
    date_naiss_safe = str(date_naissance).replace("'", "''")

    # Insert TK_DemandeDPAE (base ticket_dpae)
    db_tkdpae.query(
        f"""INSERT INTO TK_DemandeDPAE (
            IDTK_DemandeDPAE, IDTK_Liste, Civilité, OPCrea, idorganigramme,
            NOM, NOM_MARITAL, PRENOM, NUMSS, DNAISS, LNAISS, DEPNAISS, NUMCIN,
            ADRESSE1, Cp, VILLE, GSM, MAIL, URGNOM, URGLIEN, URGTEL, DateDébut,
            Coopté, Coopteur, JOdirecte, JOCoopteur,
            MUTUELLE, MUTDATE, TravailleurHandi, SituationFam, AvecEnfant, NbEnfants,
            ModifOP, ModifDate, ModifELEM
        ) VALUES (
            {id_ticket}, {id_ticket}, 0, {id_salarie_user}, 0,
            '{nom_safe}', '', '{prenom_safe}', '', '{date_naiss_safe}', '', 0, '',
            '', '{cp}', '{ville_safe}', '{gsm_safe}', '{mail_safe}', '', '', '', '',
            {coopte}, {coopteur}, 0, 0,
            0, '', 0, 0, 0, 0,
            {id_salarie_user}, '{now_wd}', 'new'
        )"""
    )

    # Insert TK_Liste (base ticket)
    db_tk.query(
        f"""INSERT INTO TK_Liste (
            IDTK_Liste, DATECREA, OPCREA, OPDEST, Service,
            IDTK_TypeDemande, IDTK_Statut, DateReport, Cloturée, DateCloture,
            ModifDate, ModifOP, ModifELEM,
            OpTraitementStaff, OrdreTraitementStaff
        ) VALUES (
            {id_ticket}, '{now_wd}', {id_salarie_user}, {id_salarie_user}, 'RH',
            21, 1, '', 0, '',
            '{now_wd}', {id_salarie_user}, 'new',
            0, 0
        )"""
    )

    # Append au Contenu du RDV
    contenu = rdv.get("Contenu") or ""
    now_fr = _format_fr_datetime("")
    today_str = datetime.now().strftime("%d/%m/%Y")
    info = f"Poste accepté le {today_str} par {nom_user} {prenom_user.capitalize()}"
    new_contenu = f"{contenu}\n{now_fr} - {info}" if contenu else f"{now_fr} - {info}"
    contenu_safe = new_contenu.replace("'", "''")
    db_rec.query(
        f"""UPDATE AgendaEvénement
        SET Contenu = '{contenu_safe}', ModifDate = '{now_wd}'
        WHERE IDAgendaEvénement = {id_rdv}"""
    )

    lien = f"https://groupe-exo.omaya.fr/PAGESEXTERNES_WEB/FR/Page-JO.awp?P1={id_ticket}"

    # SMS
    texte_sms = (
        "Felicitation, vous allez rejoindre notre reseau."
        " Pour les besoins RH, merci d'aller sur ce lien pour remplir le formulaire "
        "et joindre les documents administratifs obligatoires.\n"
        f"{lien}\n"
        "Ceci est à faire AVANT le jour J.\n"
        "Bienvenue chez nous !"
    )
    sms_result = envoi_sms(texte_sms, gsm) if gsm else "Pas de GSM candidat"

    # Mail
    html = (
        "<p>Félicitation,</p>"
        "Vous allez rejoindre notre réseau.<br/>"
        "Pour les besoins RH, merci d'aller sur ce lien pour remplir le formulaire "
        "et joindre les documents administratifs obligatoires."
        f"<p><a href='{lien}'>{lien}</a></p>"
        "Ceci est à faire <b>AVANT</b> le jour J.<br/><br/>"
        "Bienvenue chez nous !<br/><br/>"
        "Cordialement.<br/><br/>"
        "<b>Le Service RH</b>"
    )
    sujet = "Préparation de votre journée d'observation"
    cci = ["intranet@omaya.fr"]
    if mail_user:
        cci.append(mail_user)

    destinataires: list[str] = []
    if verifier_email(mail):
        destinataires = [mail]
    elif mail_user:
        destinataires = [mail_user]
        sujet += " // Mail candidat invalide"

    mail_sent = False
    if destinataires:
        try:
            mail_sent = envoi_mail_rh(
                sujet=sujet,
                html=html,
                destinataires=destinataires,
                cci=cci,
            )
        except Exception:
            mail_sent = False

    return {
        "id_ticket": id_ticket,
        "sms_result": sms_result,
        "mail_sent": mail_sent,
    }


def _build_rdv_list(rows: list, communes_map: dict) -> list[dict]:
    result = []
    for r in rows:
        id_commune = _to_int(r.get("IDCommunesFrance"))
        commune = communes_map.get(id_commune, {})
        fic_cv = (r.get("Fic_CV") or "").strip()
        cv_url = f"{DOCS_URL.rstrip('/')}/cvtheque/{quote(fic_cv)}" if fic_cv else ""
        id_cv_statut = _to_int(r.get("IdCvStatut"))
        statut_modif = id_cv_statut <= 6
        result.append({
            "id_evenement": str(_to_int(r.get("IDAgendaEvénement"))),
            "date_debut": r.get("DateDébut") or "",
            "date_fin": r.get("DateFin") or "",
            "titre": r.get("Titre") or "",
            "contenu": r.get("Contenu") or "",
            "id_categorie": _to_int(r.get("IDCatégorie")),
            "lib_categorie": r.get("Lib_Catégorie") or "",
            "couleur_hex": _to_hex(r.get("CouleurR"), r.get("CouleurV"), r.get("CouleurB")),
            "id_cv_statut": id_cv_statut,
            "id_cvtheque": str(_to_int(r.get("IDcvtheque"))),
            "nom": r.get("NOM") or "",
            "prenom": r.get("PRENOM") or "",
            "gsm": r.get("GSM") or "",
            "mail": r.get("MAIL") or "",
            "adresse": r.get("Adresse") or "",
            "cp": commune.get("cp", ""),
            "ville": commune.get("ville", ""),
            "profil": r.get("Lib_Poste") or "",
            "observ": r.get("OBSERV") or "",
            "id_cv_source": _to_int(r.get("IDcvsource")),
            "id_elem_source": _to_int(r.get("IdElemSource")),
            "cv_url": cv_url,
            "statut_modif": statut_modif,
        })
    return result
