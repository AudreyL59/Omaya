"""FI_DocUlease (type 34 — Signature Doc ULEASE).

Même principe que FI_CttW / FI_CttCourtage (signature électronique) :
  - Plan 1 : document non validé → aperçu du doc à signer + Choisir le DA
    + « Valider document pour signature ».
  - Plan 2 : document validé → PDF signé (régénéré si signé) + pages
    validées + « Renvoyer en signature » (rejet) / « Ce document est
    valide » (validation finale) / « Rafraîchir ».

TK_DemandeSignUlease : base ticket_rh (Contenu docx mémo, Signature/
paraphe/luApp/PhotoSalarié mémos binaires, contratValidé/Signé,
ContenuValidation). salarie_docUlease : base rh. Le doc signé est classé
dans le dossier véhicule (si IdPC) ou salarié.
"""

from app.core.config import FTP_GESTION_RH_PATH
from app.core.database.pg import get_pg_connection
from app.shared.notifications.sms import envoi_sms

from ..service import (
    _clean_id,
    _now_windev,
    _to_int,
    ajout_histo_tk,
    date_only_to_iso,
    load_salaries_minimal,
    maj_op_traitement_ticket,
)

PDF_NON_SIGNE_URL = "https://interne.omaya.fr/TempCttw/{id}-DocUlease.pdf"

# kwargs de régénération PDF spécifiques ULEASE (cf. cttw_pdf paramétré)
# pg=True : table snake_case ticket_rh.pgt_tk_demande_sign_ulease.
_PDF_KWARGS = dict(
    table="ticket_rh.pgt_tk_demande_sign_ulease",
    db_key="ticket_rh",
    sign_suffix="UleaseSignature",
    luapp_suffix="UleaseLuApp",
    tmp_prefix="ulease_",
    pg=True,
)


def _salarie_nom(sid: int) -> str:
    if not sid:
        return ""
    info = load_salaries_minimal({sid}).get(sid, {})
    p = info.get("prenom", "")
    return (
        f"{info.get('nom', '')} {p[:1].upper() + p[1:].lower() if p else ''}"
        .strip()
    )


def _coord_salarie(id_salarie: int) -> tuple[str, str]:
    """(mail, gsm nettoye) depuis salarie_coordonnees (rh). Lecture pure PG."""
    if not id_salarie:
        return "", ""
    try:
        r = get_pg_connection("rh").query_one(
            "SELECT id_salarie, mail, tel_mob FROM pgt_salarie_coordonnees "
            "WHERE id_salarie = ?",
            (int(id_salarie),),
        )
        if not r:
            return "", ""
        mail = (r.get("mail") or "").strip()
        gsm = (r.get("tel_mob") or "")
        for c in (".", " ", "/", "-"):
            gsm = gsm.replace(c, "")
        return mail, gsm.strip()
    except Exception:
        return "", ""


def _id_vehicule(id_pc: int) -> int:
    """IDvehicule depuis vehicule_Conducteur (module vehicules, schema ulease).
    Lecture pure PG."""
    if not id_pc:
        return 0
    try:
        r = get_pg_connection("ulease").query_one(
            "SELECT id_vehicule_pc, id_vehicule FROM pgt_vehicule_conducteur "
            "WHERE id_vehicule_pc = ?",
            (int(id_pc),),
        )
        return _clean_id(_to_int(r.get("id_vehicule"))) if r else 0
    except Exception:
        return 0


# --------------------------------------------------------------------
# load / print_pdf / save
# --------------------------------------------------------------------

def load(id_ticket: int) -> dict:
    # Migration PG (cf. SalarieDocUleaseModal + ParcAuto generer-pv qui
    # ecrivent dans pgt_tk_demande_sign_ulease en PG).
    db = get_pg_connection("ticket_rh")
    r = db.query_one(
        """SELECT id_tk_liste, id_salarie, id_da, id_pc, contrat_genere,
            contrat_valide, contrat_signe, contrat_annul, datesignature,
            titre_contrat, type_ctt_w
        FROM ticket_rh.pgt_tk_demande_sign_ulease WHERE id_tk_liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}
    id_salarie = _clean_id(_to_int(r.get("id_salarie")))
    id_da = _clean_id(_to_int(r.get("id_da")))
    contrat_valide = bool(r.get("contrat_valide"))
    contrat_signe = bool(r.get("contrat_signe"))
    plan = 2 if contrat_valide else 1

    base = {
        "found": True,
        "plan": plan,
        "id_salarie": str(id_salarie) if id_salarie else "",
        "salarie_nom": _salarie_nom(id_salarie),
        "id_da": str(id_da) if id_da else "",
        "da_nom": _salarie_nom(id_da),
        "id_pc": str(_clean_id(_to_int(r.get("id_pc")))) or "",
        "titre_contrat": (r.get("titre_contrat") or "").strip(),
        "type_cttw": (r.get("type_ctt_w") or "").strip(),
        "contrat_genere": bool(r.get("contrat_genere")),
        "contrat_valide": contrat_valide,
        "contrat_signe": contrat_signe,
        "contrat_annul": bool(r.get("contrat_annul")),
        "date_signature": date_only_to_iso(r.get("datesignature")),
    }
    if plan == 1:
        base["pdf_non_signe_url"] = PDF_NON_SIGNE_URL.format(id=id_ticket)
    else:
        base["has_signed_pdf"] = contrat_signe
    return base


def print_pdf(id_ticket: int, payload: dict) -> bytes:
    """Régénère le PDF ULEASE signé (Plan 2 + bouton Rafraîchir). PG."""
    from .cttw_pdf import regenerate_signed_pdf

    db = get_pg_connection("ticket_rh")
    r = db.query_one(
        "SELECT id_tk_liste, id_salarie, id_da, datesignature "
        "FROM ticket_rh.pgt_tk_demande_sign_ulease WHERE id_tk_liste = ?",
        (int(id_ticket),),
    )
    if not r:
        raise ValueError("Document introuvable")
    return regenerate_signed_pdf(
        int(id_ticket),
        _salarie_nom(_clean_id(_to_int(r.get("id_salarie")))),
        _salarie_nom(_clean_id(_to_int(r.get("id_da")))),
        date_only_to_iso(r.get("datesignature")) or "",
        **_PDF_KWARGS,
    )


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    """Migration PG complète : pgt_tk_demande_sign_ulease (ticket_rh),
    pgt_tk_liste (ticket), pgt_salarie_doc_ulease (rh)."""
    action = str(payload.get("action") or "")
    db = get_pg_connection("ticket_rh")

    # --- Choisir le DA ---
    if action == "da":
        id_da = str(payload.get("id_da") or "")
        if not id_da.isdigit():
            return {"ok": False, "error": "DA invalide"}
        db.query(
            "UPDATE ticket_rh.pgt_tk_demande_sign_ulease SET id_da = ?, "
            "modif_date = NOW(), modif_op = ?, modif_elem = 'modif' "
            "WHERE id_tk_liste = ?",
            (int(id_da), int(user_id), int(id_ticket)),
        )
        return {"ok": True}

    # --- Valider document pour signature (Plan 1 → 2) ---
    if action == "valider":
        cur = db.query_one(
            "SELECT id_salarie, id_da FROM ticket_rh.pgt_tk_demande_sign_ulease "
            "WHERE id_tk_liste = ?",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Document introuvable"}
        id_da = _clean_id(_to_int(cur.get("id_da")))
        db.query(
            """UPDATE ticket_rh.pgt_tk_demande_sign_ulease
                SET contrat_valide = TRUE, contrat_signe = FALSE,
                    contrat_annul = FALSE, datesignature = NULL,
                    contenu_validation = NULL, photo_salarie = NULL,
                    signature = NULL, paraphe = NULL, lu_app = NULL,
                    modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_tk_liste = ?""",
            (int(user_id), int(id_ticket)),
        )
        get_pg_connection("ticket").query(
            "UPDATE ticket.pgt_tk_liste SET id_tk_statut = 22, "
            "modif_date = NOW(), modif_elem = 'modif' "
            "WHERE id_tk_liste = ?",
            (int(id_ticket),),
        )
        sms_result = ""
        _, gsm_da = _coord_salarie(id_da)
        if gsm_da:
            try:
                sms_result = envoi_sms(
                    "Le document ULEASE est disponible à la signature sur "
                    "ton appli OMAYA.", gsm_da, "", "OMAYA-Info",
                )
            except Exception as e:
                sms_result = f"SMS non envoyé : {e}"
        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True, "sms_result": sms_result}

    # --- Renvoyer en signature (rejet) ---
    if action == "refuser":
        pb_sign = bool(payload.get("pb_sign"))
        pb_par = bool(payload.get("pb_paraphe"))
        pb_mention = bool(payload.get("pb_mention"))
        if not (pb_sign or pb_par or pb_mention):
            return {"ok": False, "error": "Coche au moins un problème"}
        cur = db.query_one(
            "SELECT id_salarie, id_da FROM ticket_rh.pgt_tk_demande_sign_ulease "
            "WHERE id_tk_liste = ?",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Document introuvable"}
        id_salarie = _clean_id(_to_int(cur.get("id_salarie")))
        id_da = _clean_id(_to_int(cur.get("id_da")))

        sets = [
            "contrat_valide = TRUE", "contrat_signe = FALSE",
            "contrat_annul = FALSE", "datesignature = NULL",
            "contenu_validation = NULL",
        ]
        elems: list[str] = []
        if pb_sign:
            sets += ["photo_salarie = NULL", "signature = NULL"]
            elems.append(" - la signature et la photo")
        if pb_par:
            sets.append("paraphe = NULL")
            elems.append(" - la paraphe")
        if pb_mention:
            sets.append("lu_app = NULL")
            elems.append(" - la mention 'Lu et approuvé'")
        sets += ["modif_date = NOW()", "modif_op = ?", "modif_elem = 'modif'"]
        db.query(
            f"UPDATE ticket_rh.pgt_tk_demande_sign_ulease SET {', '.join(sets)} "
            "WHERE id_tk_liste = ?",
            (int(user_id), int(id_ticket)),
        )
        if pb_sign and pb_par and pb_mention:
            statut = 7
        elif pb_mention:
            statut = 11
        elif pb_par:
            statut = 10
        else:
            statut = 9
        get_pg_connection("ticket").query(
            """UPDATE ticket.pgt_tk_liste SET id_tk_statut = ?,
                modification = TRUE, op_modif = ?, id_modif = 0,
                type_modif = 'TKSTATUT', modif_date = NOW(),
                modif_op = ?, modif_elem = 'modif'
            WHERE id_tk_liste = ?""",
            (statut, int(user_id), int(user_id), int(id_ticket)),
        )
        ajout_histo_tk(int(id_ticket), statut, int(user_id))
        sms_result = ""
        _, gsm_da = _coord_salarie(id_da)
        if gsm_da:
            txt = (
                f"Le document ULEASE pour {_salarie_nom(id_salarie)} n'est "
                "pas conforme, merci de faire refaire les elements "
                "suivant :\n" + "\n".join(elems)
            )
            try:
                sms_result = envoi_sms(txt, gsm_da, "", "OMAYA-Info")
            except Exception as e:
                sms_result = f"SMS non envoyé : {e}"
        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True, "closed": True, "sms_result": sms_result}

    # --- Ce document est valide (validation finale) ---
    if action == "valider_signe":
        from app.shared.notifications.mail import envoi_mail_rh

        from .cttw_pdf import ftp_upload, regenerate_signed_pdf

        cloturer = bool(payload.get("cloturer"))
        r = db.query_one(
            """SELECT id_tk_liste, id_demande_sign_ulease, id_salarie, id_da,
                id_pc, type_ctt_w, id_salarie_ulease, datesignature
            FROM ticket_rh.pgt_tk_demande_sign_ulease
            WHERE id_tk_liste = ?""",
            (int(id_ticket),),
        )
        if not r:
            return {"ok": False, "error": "Document introuvable"}
        id_demande = _clean_id(_to_int(r.get("id_demande_sign_ulease")))
        id_salarie = _clean_id(_to_int(r.get("id_salarie")))
        id_da = _clean_id(_to_int(r.get("id_da")))
        id_pc = _clean_id(_to_int(r.get("id_pc")))
        type_cttw = str(r.get("type_ctt_w") or "").strip()
        id_doc_ulease = _clean_id(_to_int(r.get("id_salarie_ulease")))
        salarie_nom = _salarie_nom(id_salarie)
        nom_pdf = f"{id_ticket}_DocUleaseSigne.pdf"

        # 1. Régénération + upload FTP (dossier véhicule ou salarié)
        try:
            pdf = regenerate_signed_pdf(
                int(id_ticket), salarie_nom, _salarie_nom(id_da),
                date_only_to_iso(r.get("datesignature")) or "",
                **_PDF_KWARGS,
            )
            if id_pc:
                id_veh = _id_vehicule(id_pc)
                if id_veh:
                    remote_dir = f"/OMAYA/Vehicules/{id_veh}/{id_pc}"
                else:
                    remote_dir = f"{FTP_GESTION_RH_PATH}/{id_salarie}/Fiches_Salaires"
            else:
                remote_dir = f"{FTP_GESTION_RH_PATH}/{id_salarie}/Fiches_Salaires"
            ftp_upload(remote_dir, nom_pdf, pdf)
        except Exception as e:
            return {"ok": False, "error": f"Génération/upload PDF : {e}"}

        # 2. salarie_doc_ulease : marquer RECU (base rh PG)
        rh = get_pg_connection("rh")
        try:
            target = id_doc_ulease or None
            if not target:
                ex = rh.query_one(
                    "SELECT id_salarie_doc_ulease FROM rh.pgt_salarie_doc_ulease "
                    "WHERE id_salarie = ? AND recu = FALSE "
                    "AND id_doc_ulease_type = ?",
                    (int(id_salarie), int(type_cttw) if type_cttw.isdigit() else 0),
                )
                if ex:
                    target = _clean_id(_to_int(ex.get("id_salarie_doc_ulease")))
            if target:
                rh.query(
                    """UPDATE rh.pgt_salarie_doc_ulease SET recu = TRUE,
                        recu_date = NOW(), modif_op = ?, modif_date = NOW(),
                        modif_elem = 'modif'
                    WHERE id_salarie_doc_ulease = ?""",
                    (int(user_id), int(target)),
                )
            else:
                from datetime import datetime
                new_id = int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])
                rh.query(
                    """INSERT INTO rh.pgt_salarie_doc_ulease
                    (id_salarie_doc_ulease, id_doc_ulease_type, id_salarie,
                     id_da, date_edition, recu, recu_date,
                     modif_op, modif_date, modif_elem)
                    VALUES (?, ?, ?, ?, NOW(), TRUE, NOW(), ?, NOW(), 'new')""",
                    (new_id, int(type_cttw) if type_cttw.isdigit() else 0,
                     int(id_salarie), int(id_da), int(user_id)),
                )
                db.query(
                    "UPDATE ticket_rh.pgt_tk_demande_sign_ulease "
                    "SET id_salarie_ulease = ?, modif_date = NOW(), "
                    "modif_op = ?, modif_elem = 'modif' "
                    "WHERE id_tk_liste = ?",
                    (new_id, int(user_id), int(id_ticket)),
                )
        except Exception as e:
            return {"ok": False, "error": f"salarie_doc_ulease : {e}"}

        # 3. SMS + mail au salarié
        sms_result = ""
        mail, gsm = _coord_salarie(id_salarie)
        if gsm:
            txt = (
                "Votre document ULEASE est disponible sur votre espace "
                "salarié (intranet ou appli Omaya).\n"
                f"Une copie est envoyée sur votre email : {mail}"
            )
            try:
                sms_result = envoi_sms(txt, gsm, "", "OMAYA-Info")
            except Exception as e:
                sms_result = f"SMS non envoyé : {e}"
        if mail:
            html = (
                "<p>Bonjour,</p><p>Voici votre document ULEASE signé.</p>"
                "<p>Cdt</p><p>Service RH</p>"
            )
            mail_da, _ = _coord_salarie(id_da)
            cci = [c for c in (mail_da, "intranet@omaya.fr") if c]
            try:
                envoi_mail_rh(
                    "Document ULEASE Signé", html, [mail], cci,
                    "intranet@omaya.fr", [(nom_pdf, pdf)],
                )
            except Exception:
                pass

        # 4. Clôture optionnelle
        if cloturer:
            get_pg_connection("ticket").query(
                """UPDATE ticket.pgt_tk_liste SET cloturee = TRUE,
                    date_cloture = NOW(), modification = TRUE,
                    op_modif = ?, id_modif = 0,
                    type_modif = 'TKSTATUT', modif_date = NOW(),
                    modif_op = ?, modif_elem = 'modif'
                WHERE id_tk_liste = ?""",
                (int(user_id), int(user_id), int(id_ticket)),
            )
            ajout_histo_tk(int(id_ticket), 4, int(user_id))

        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True, "closed": cloturer, "sms_result": sms_result}

    return {"ok": False, "error": "Action non disponible"}
