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
from app.core.database import get_connection
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
_PDF_KWARGS = dict(
    table="TK_DemandeSignUlease",
    db_key="ticket_rh",
    sign_suffix="UleaseSignature",
    luapp_suffix="UleaseLuApp",
    tmp_prefix="ulease_",
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
    db = get_connection("ticket_rh")
    r = db.query_one(
        """SELECT IDTK_Liste, IDSalarie, idDA, IdPC, contratGénéré,
            contratValidé, contratSigné, contratAnnul, datesignature,
            TitreContrat, TypeCttW
        FROM TK_DemandeSignUlease WHERE IDTK_Liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}
    id_salarie = _clean_id(_to_int(r.get("IDSalarie")))
    id_da = _clean_id(_to_int(r.get("idDA")))
    contrat_valide = bool(r.get("contratValidé"))
    contrat_signe = bool(r.get("contratSigné"))
    plan = 2 if contrat_valide else 1

    base = {
        "found": True,
        "plan": plan,
        "id_salarie": str(id_salarie) if id_salarie else "",
        "salarie_nom": _salarie_nom(id_salarie),
        "id_da": str(id_da) if id_da else "",
        "da_nom": _salarie_nom(id_da),
        "id_pc": str(_clean_id(_to_int(r.get("IdPC")))) or "",
        "titre_contrat": (r.get("TitreContrat") or "").strip(),
        "type_cttw": (r.get("TypeCttW") or "").strip(),
        "contrat_genere": bool(r.get("contratGénéré")),
        "contrat_valide": contrat_valide,
        "contrat_signe": contrat_signe,
        "contrat_annul": bool(r.get("contratAnnul")),
        "date_signature": date_only_to_iso(r.get("datesignature")),
    }
    if plan == 1:
        base["pdf_non_signe_url"] = PDF_NON_SIGNE_URL.format(id=id_ticket)
    else:
        base["has_signed_pdf"] = contrat_signe
    return base


def print_pdf(id_ticket: int, payload: dict) -> bytes:
    """Régénère le PDF ULEASE signé (Plan 2 + bouton Rafraîchir)."""
    from .cttw_pdf import regenerate_signed_pdf

    db = get_connection("ticket_rh")
    r = db.query_one(
        "SELECT IDTK_Liste, IDSalarie, idDA, datesignature "
        "FROM TK_DemandeSignUlease WHERE IDTK_Liste = ?",
        (int(id_ticket),),
    )
    if not r:
        raise ValueError("Document introuvable")
    return regenerate_signed_pdf(
        int(id_ticket),
        _salarie_nom(_clean_id(_to_int(r.get("IDSalarie")))),
        _salarie_nom(_clean_id(_to_int(r.get("idDA")))),
        date_only_to_iso(r.get("datesignature")) or "",
        **_PDF_KWARGS,
    )


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    action = str(payload.get("action") or "")
    now = _now_windev()
    db = get_connection("ticket_rh")

    # --- Choisir le DA ---
    if action == "da":
        id_da = str(payload.get("id_da") or "")
        if not id_da.isdigit():
            return {"ok": False, "error": "DA invalide"}
        db.query(
            "UPDATE TK_DemandeSignUlease SET idDA = ?, ModifDate = ?, "
            "ModifOP = ?, ModifELEM = 'modif' WHERE IDTK_Liste = ?",
            (int(id_da), now, int(user_id), int(id_ticket)),
        )
        return {"ok": True}

    # --- Valider document pour signature (Plan 1 → 2) ---
    if action == "valider":
        cur = db.query_one(
            "SELECT IDSalarie, idDA FROM TK_DemandeSignUlease "
            "WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Document introuvable"}
        id_da = _clean_id(_to_int(cur.get("idDA")))
        db.query(
            """UPDATE TK_DemandeSignUlease SET contratValidé = 1,
                contratSigné = 0, contratAnnul = 0, datesignature = '',
                ContenuValidation = '', PhotoSalarié = '', Signature = '',
                paraphe = '', luApp = '', ModifDate = ?, ModifOP = ?,
                ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (now, int(user_id), int(id_ticket)),
        )
        get_connection("ticket").query(
            "UPDATE TK_Liste SET IDTK_Statut = 22, ModifDate = ?, "
            "ModifElem = 'modif' WHERE IDTK_Liste = ?",
            (now, int(id_ticket)),
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
            "SELECT IDSalarie, idDA FROM TK_DemandeSignUlease "
            "WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Document introuvable"}
        id_salarie = _clean_id(_to_int(cur.get("IDSalarie")))
        id_da = _clean_id(_to_int(cur.get("idDA")))

        sets = [
            "contratValidé = 1", "contratSigné = 0", "contratAnnul = 0",
            "datesignature = ''", "ContenuValidation = ''",
        ]
        elems: list[str] = []
        if pb_sign:
            sets += ["PhotoSalarié = ''", "Signature = ''"]
            elems.append(" - la signature et la photo")
        if pb_par:
            sets.append("paraphe = ''")
            elems.append(" - la paraphe")
        if pb_mention:
            sets.append("luApp = ''")
            elems.append(" - la mention 'Lu et approuvé'")
        sets += ["ModifDate = ?", "ModifOP = ?", "ModifELEM = 'modif'"]
        db.query(
            f"UPDATE TK_DemandeSignUlease SET {', '.join(sets)} "
            "WHERE IDTK_Liste = ?",
            (now, int(user_id), int(id_ticket)),
        )
        if pb_sign and pb_par and pb_mention:
            statut = 7
        elif pb_mention:
            statut = 11
        elif pb_par:
            statut = 10
        else:
            statut = 9
        get_connection("ticket").query(
            """UPDATE TK_Liste SET IDTK_Statut = ?, modification = 1,
                opModif = ?, idModif = 0, TypeModif = 'TKSTATUT',
                ModifDate = ?, ModifOP = ?, ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (statut, int(user_id), now, int(user_id), int(id_ticket)),
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
            """SELECT IDTK_Liste, IDdemandeSignUlease, IDSalarie, idDA,
                IdPC, TypeCttW, IDSalarie_Ulease, datesignature
            FROM TK_DemandeSignUlease WHERE IDTK_Liste = ?""",
            (int(id_ticket),),
        )
        if not r:
            return {"ok": False, "error": "Document introuvable"}
        id_demande = _clean_id(_to_int(r.get("IDdemandeSignUlease")))
        id_salarie = _clean_id(_to_int(r.get("IDSalarie")))
        id_da = _clean_id(_to_int(r.get("idDA")))
        id_pc = _clean_id(_to_int(r.get("IdPC")))
        type_cttw = str(r.get("TypeCttW") or "").strip()
        id_doc_ulease = _clean_id(_to_int(r.get("IDSalarie_Ulease")))
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

        # 2. salarie_docUlease : marquer RECU (base rh)
        rh = get_connection("rh")
        try:
            target = id_doc_ulease or None
            if not target:
                ex = rh.query_one(
                    "SELECT IDsalarie_docUlease FROM salarie_docUlease "
                    "WHERE IDSalarie = ? AND RECU = 0 AND IDdocUleaseTYPE = ?",
                    (int(id_salarie), type_cttw),
                )
                if ex:
                    target = _clean_id(_to_int(ex.get("IDsalarie_docUlease")))
            if target:
                rh.query(
                    """UPDATE salarie_docUlease SET RECU = 1, RECUDATE = ?,
                        ModifOP = ?, ModifDate = ?, ModifELEM = 'modif'
                    WHERE IDsalarie_docUlease = ?""",
                    (now, int(user_id), now, int(target)),
                )
            else:
                new_id = int(now)
                rh.query(
                    """INSERT INTO salarie_docUlease
                    (IDsalarie_docUlease, IDdocUleaseTYPE, IDSalarie, ID_DA,
                     DATE_Edition, RECU, RECUDATE, ModifOP, ModifDate,
                     ModifELEM)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, 'new')""",
                    (new_id, type_cttw, int(id_salarie), int(id_da),
                     str(id_demande), now, int(user_id), now),
                )
                db.query(
                    "UPDATE TK_DemandeSignUlease SET IDSalarie_Ulease = ?, "
                    "ModifDate = ?, ModifOP = ?, ModifELEM = 'modif' "
                    "WHERE IDTK_Liste = ?",
                    (new_id, now, int(user_id), int(id_ticket)),
                )
        except Exception as e:
            return {"ok": False, "error": f"salarie_docUlease : {e}"}

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
            get_connection("ticket").query(
                """UPDATE TK_Liste SET Cloturée = 1, DateCloture = ?,
                    modification = 1, opModif = ?, idModif = 0,
                    TypeModif = 'TKSTATUT', ModifDate = ?, ModifOP = ?,
                    ModifELEM = 'modif'
                WHERE IDTK_Liste = ?""",
                (now, int(user_id), now, int(user_id), int(id_ticket)),
            )
            ajout_histo_tk(int(id_ticket), 4, int(user_id))

        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True, "closed": cloturer, "sms_result": sms_result}

    return {"ok": False, "error": "Action non disponible"}
