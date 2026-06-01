"""FI_CttW (type 4 — Contrat W Signature).

2 plans (cf. WinDev MaFenêtreInterne..Plan) :
  - Plan 1 : contrat non validé/signé → infos mutuelle (salarie_mutuelle,
    base rh) + Choisir le DA + aperçu du PDF non signé.
  - Plan 2 : contrat validé ET signé → affichage du PDF signé final
    (emplacement à brancher) + pages validées + actions (à venir, code
    WinDev à fournir).

TK_DemandeCttW : base ticket_rh (1 enr/ticket, clé IDTK_Liste).
salarie_mutuelle + mutuelle : base rh.
"""

from app.core.database import get_connection
from app.core.database.pg import get_pg_connection
from app.shared.notifications.sms import envoi_sms

from ..service import (
    _clean_id,
    _now_windev,
    _to_int,
    date_only_to_iso,
    iso_to_date_only,
    ajout_histo_tk,
    load_salaries_minimal,
    maj_op_traitement_ticket,
)


def _mail_salarie(id_salarie: int) -> str:
    """MAIL (salarie_coordonnées, base rh)."""
    if not id_salarie:
        return ""
    try:
        db = get_connection("rh")
        r = db.query_one(
            "SELECT IDSalarie, MAIL FROM salarie_coordonnées "
            "WHERE IDSalarie = ?",
            (int(id_salarie),),
        )
        return ((r.get("MAIL") if r else "") or "").strip()
    except Exception:
        return ""


def _gsm_salarie(id_salarie: int) -> str:
    """TélMob (salarie_coordonnées, base rh) nettoyé."""
    if not id_salarie:
        return ""
    try:
        db = get_connection("rh")
        r = db.query_one(
            "SELECT IDSalarie, TélMob FROM salarie_coordonnées "
            "WHERE IDSalarie = ?",
            (int(id_salarie),),
        )
        tel = (r.get("TélMob") if r else "") or ""
        for c in (".", " ", "/", "-"):
            tel = tel.replace(c, "")
        return tel.strip()
    except Exception:
        return ""

PDF_NON_SIGNE_URL = "https://interne.omaya.fr/TempCttw/{id}-cttW.pdf"


def _salaire_nom(sid: int) -> str:
    if not sid:
        return ""
    info = load_salaries_minimal({sid}).get(sid, {})
    p = info.get("prenom", "")
    return (
        f"{info.get('nom', '')} {p[:1].upper() + p[1:].lower() if p else ''}"
        .strip()
    )


def _load_mutuelle(id_salarie: int) -> dict:
    """Infos salarie_mutuelle (base rh) pour le Plan 1."""
    db = get_connection("rh")
    r = db.query_one(
        """SELECT IDsalarie_mutuelle, IDSalarie, Adhésion, AdhésionDate,
            Mutuelle_Dossier, IdMutuelle, Mutuelle_AttSS, Mutuelle_RIB,
            Mutuelle_DocEnvoyés, Mutuelle_RecepCertif, Mutuelle_PasAdhésion,
            Mutuelle_PasAdhésionJusquau, Mutuelle_Résilié,
            Mutuelle_RésiliéDate
        FROM salarie_mutuelle
        WHERE IDSalarie = ?""",
        (int(id_salarie),),
    )
    if not r:
        return {"mutuelle_found": False}
    return {
        "mutuelle_found": True,
        "adhesion": bool(r.get("Adhésion")),
        "adhesion_date": date_only_to_iso(r.get("AdhésionDate")),
        "mutuelle_dossier": bool(r.get("Mutuelle_Dossier")),
        "id_mutuelle": _to_int(r.get("IdMutuelle")),
        "att_ss": bool(r.get("Mutuelle_AttSS")),
        "rib": bool(r.get("Mutuelle_RIB")),
        "docs_envoyes": bool(r.get("Mutuelle_DocEnvoyés")),
        "recep_certif": bool(r.get("Mutuelle_RecepCertif")),
        "pas_adhesion": bool(r.get("Mutuelle_PasAdhésion")),
        "pas_adhesion_jusquau": date_only_to_iso(
            r.get("Mutuelle_PasAdhésionJusquau")
        ),
        "resilie": bool(r.get("Mutuelle_Résilié")),
        "resilie_date": date_only_to_iso(r.get("Mutuelle_RésiliéDate")),
    }


def _list_mutuelles() -> list[dict]:
    try:
        db = get_connection("rh")
        out = []
        for m in db.query(
            "SELECT IdMutuelle, Lib_Mutuelle FROM mutuelle WHERE IsActif = 1 "
            "ORDER BY Lib_Mutuelle"
        ):
            mid = _to_int(m.get("IdMutuelle"))
            out.append({
                "id": mid,
                "lib": (m.get("Lib_Mutuelle") or "").strip(),
            })
        return out
    except Exception:
        return []


def load(id_ticket: int) -> dict:
    db = get_pg_connection("ticket_rh")
    r = db.query_one(
        """SELECT id_tk_liste, id_salarie, id_da, contrat_genere,
            contrat_valide, contrat_signe, contrat_annul, datesignature,
            titre_contrat, type_ctt_w
        FROM pgt_tk_demande_ctt_w
        WHERE id_tk_liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}

    id_salarie = _clean_id(_to_int(r.get("id_salarie")))
    id_da = _clean_id(_to_int(r.get("id_da")))
    contrat_valide = bool(r.get("contrat_valide"))
    contrat_signe = bool(r.get("contrat_signe"))
    # cf. code init WinDev : Plan 2 dès que validé (le PDF signé n'est
    # régénéré QUE si en plus signé).
    plan = 2 if contrat_valide else 1

    base = {
        "found": True,
        "plan": plan,
        "id_salarie": str(id_salarie) if id_salarie else "",
        "salarie_nom": _salaire_nom(id_salarie),
        "id_da": str(id_da) if id_da else "",
        "da_nom": _salaire_nom(id_da),
        "titre_contrat": (r.get("titre_contrat") or "").strip(),
        "type_cttw": (r.get("type_ctt_w") or "").strip(),
        "contrat_genere": bool(r.get("contrat_genere")),
        "contrat_valide": contrat_valide,
        "contrat_signe": contrat_signe,
        "contrat_annul": bool(r.get("contrat_annul")),
        "date_signature": date_only_to_iso(r.get("datesignature")),
    }

    if plan == 1:
        base.update(_load_mutuelle(id_salarie))
        base["mutuelles"] = _list_mutuelles()
        base["pdf_non_signe_url"] = PDF_NON_SIGNE_URL.format(id=id_ticket)
    else:
        # Plan 2 : le PDF signé n'est régénéré (endpoint /form/print)
        # QUE si le contrat est signé. Sinon : en attente de signature.
        base["has_signed_pdf"] = contrat_signe

    return base


def print_pdf(id_ticket: int, payload: dict) -> bytes:
    """Régénère le PDF de contrat signé (FI_CttW Plan 2)."""
    from .cttw_pdf import regenerate_signed_pdf

    db = get_connection("ticket_rh")
    r = db.query_one(
        "SELECT IDTK_Liste, IDSalarie, idDA, datesignature "
        "FROM TK_DemandeCttW WHERE IDTK_Liste = ?",
        (int(id_ticket),),
    )
    if not r:
        raise ValueError("Contrat introuvable")
    id_salarie = _clean_id(_to_int(r.get("IDSalarie")))
    id_da = _clean_id(_to_int(r.get("idDA")))
    return regenerate_signed_pdf(
        int(id_ticket),
        _salaire_nom(id_salarie),
        _salaire_nom(id_da),
        date_only_to_iso(r.get("datesignature")) or "",
    )


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    """Plan 1 :
      - action 'mutuelle' : Enregistrer les infos mutuelle (salarie_mutuelle)
      - action 'da'       : Choisir le DA (TK_DemandeCttW.idDA)
    """
    action = str(payload.get("action") or "mutuelle")
    now = _now_windev()

    if action == "valider":
        # « Valider le contrat de travail pour signature »
        db = get_connection("ticket_rh")
        cur = db.query_one(
            "SELECT IDSalarie, idDA FROM TK_DemandeCttW WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Contrat introuvable"}
        id_salarie = _clean_id(_to_int(cur.get("IDSalarie")))
        id_da = _clean_id(_to_int(cur.get("idDA")))

        db.query(
            """UPDATE TK_DemandeCttW SET
                contratValidé = 1, contratSigné = 0, contratAnnul = 0,
                datesignature = '', ContenuValidation = '',
                PhotoSalarié = '', Signature = '', paraphe = '', luApp = '',
                ModifDate = ?, ModifOP = ?, ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (now, int(user_id), int(id_ticket)),
        )
        # TK_Liste → statut 22 (base ticket)
        get_connection("ticket").query(
            """UPDATE TK_Liste
            SET IDTK_Statut = 22, ModifDate = ?, ModifElem = 'modif'
            WHERE IDTK_Liste = ?""",
            (now, int(id_ticket)),
        )
        # SMS au DA (best-effort, comme le WinDev)
        sms_result = ""
        gsm_da = _gsm_salarie(id_da)
        if gsm_da:
            txt = (
                f"Le contrat de travail pour {_salaire_nom(id_salarie)} "
                "est disponible à la signature sur ton appli OMAYA."
            )
            try:
                sms_result = envoi_sms(txt, gsm_da, "", "OMAYA-Info")
            except Exception as e:
                sms_result = f"SMS non envoyé : {e}"
        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True, "sms_result": sms_result}

    if action == "valider_signe":
        # « Ce contrat de travail est valide » : régénère le PDF signé,
        # l'upload dans le dossier salarié (FTP), maj salarie_docRH,
        # SMS + mail au salarié, clôture optionnelle du ticket.
        from app.core.config import FTP_GESTION_RH_PATH
        from app.shared.notifications.mail import envoi_mail_rh

        from .cttw_pdf import ftp_upload, regenerate_signed_pdf

        cloturer = bool(payload.get("cloturer"))
        db = get_connection("ticket_rh")
        r = db.query_one(
            """SELECT IDTK_Liste, IDSalarie, idDA, IDdocRHEDIT, TypeCttW,
                IDdemandeContratW, datesignature
            FROM TK_DemandeCttW WHERE IDTK_Liste = ?""",
            (int(id_ticket),),
        )
        if not r:
            return {"ok": False, "error": "Contrat introuvable"}
        id_salarie = _clean_id(_to_int(r.get("IDSalarie")))
        id_da = _clean_id(_to_int(r.get("idDA")))
        id_doc_edit = _clean_id(_to_int(r.get("IDdocRHEDIT")))
        type_cttw = str(r.get("TypeCttW") or "").strip()
        id_dem = str(r.get("IDdemandeContratW") or "").strip()
        salarie_nom = _salaire_nom(id_salarie)

        # 1. Régénération + upload FTP dossier salarié
        try:
            pdf = regenerate_signed_pdf(
                int(id_ticket), salarie_nom, _salaire_nom(id_da),
                date_only_to_iso(r.get("datesignature")) or "",
            )
            ftp_upload(
                f"{FTP_GESTION_RH_PATH}/{id_salarie}/Fiches_Salaires",
                f"{id_ticket}_CttWSigne.pdf",
                pdf,
            )
        except Exception as e:
            return {"ok": False, "error": f"Génération/upload PDF : {e}"}

        # 2. salarie_docRH : marquer RECU (base rh)
        rh = get_connection("rh")
        try:
            target = None
            if id_doc_edit:
                target = id_doc_edit
            else:
                ex = rh.query_one(
                    """SELECT IDsalarie_docRH FROM salarie_docRH
                    WHERE IDSalarie = ? AND RECU = 0 AND IDdocRHTYPE = ?""",
                    (int(id_salarie), type_cttw),
                )
                if ex:
                    target = _clean_id(_to_int(ex.get("IDsalarie_docRH")))
            if target:
                rh.query(
                    """UPDATE salarie_docRH SET RECU = 1, RECUDATE = ?,
                        ModifOP = ?, ModifDate = ?, ModifELEM = 'modif'
                    WHERE IDsalarie_docRH = ?""",
                    (now, int(user_id), now, int(target)),
                )
            else:
                new_id = int(now)
                rh.query(
                    """INSERT INTO salarie_docRH
                    (IDsalarie_docRH, IDdocRHTYPE, IDSalarie, ID_DA,
                     DATE_Edition, RECU, RECUDATE, ModifOP, ModifDate,
                     ModifELEM)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, 'new')""",
                    (new_id, type_cttw, int(id_salarie), int(id_da),
                     id_dem, now, int(user_id), now),
                )
                db.query(
                    "UPDATE TK_DemandeCttW SET IDdocRHEDIT = ?, "
                    "ModifDate = ?, ModifOP = ?, ModifELEM = 'modif' "
                    "WHERE IDTK_Liste = ?",
                    (new_id, now, int(user_id), int(id_ticket)),
                )
        except Exception as e:
            return {"ok": False, "error": f"salarie_docRH : {e}"}

        # 3. SMS + mail au salarié
        sms_result = ""
        gsm = _gsm_salarie(id_salarie)
        mail = _mail_salarie(id_salarie)
        if gsm:
            txt = (
                "Votre contrat de travail est disponible sur votre espace "
                "salarié (intranet ou appli Omaya).\n"
                f"Une copie est envoyée sur votre email : {mail}"
            )
            try:
                sms_result = envoi_sms(txt, gsm, "", salarie_nom)
            except Exception as e:
                sms_result = f"SMS non envoyé : {e}"
        if mail:
            html = (
                "<p>Bonjour,</p><p>Voici votre contrat de Travail signé.</p>"
                "<p>Cdt</p><p>Service RH</p>"
            )
            cci = [c for c in (_mail_salarie(id_da), "intranet@omaya.fr") if c]
            try:
                envoi_mail_rh(
                    "Contrat de Travail Signé", html, [mail], cci,
                    "intranet@omaya.fr",
                    [(f"{id_ticket}_CttWSigne.pdf", pdf)],
                )
            except Exception:
                pass

        # 4. Clôture optionnelle du ticket
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

    if action == "refuser":
        # « Renvoyer ce contrat en signature » (refus). 100% transposable
        # (pas de PDF). Cases : pb_sign / pb_paraphe / pb_mention.
        pb_sign = bool(payload.get("pb_sign"))
        pb_par = bool(payload.get("pb_paraphe"))
        pb_mention = bool(payload.get("pb_mention"))
        if not (pb_sign or pb_par or pb_mention):
            return {"ok": False, "error": "Coche au moins un problème"}

        db = get_connection("ticket_rh")
        cur = db.query_one(
            "SELECT IDSalarie, idDA FROM TK_DemandeCttW WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Contrat introuvable"}
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
            f"UPDATE TK_DemandeCttW SET {', '.join(sets)} "
            f"WHERE IDTK_Liste = ?",
            (now, int(user_id), int(id_ticket)),
        )

        # Statut TK_Liste (cascade fidèle au WinDev : 3 cases → 7,
        # sinon Mention→11, sinon Par→10, sinon Sign→9)
        if pb_sign and pb_par and pb_mention:
            statut = 7
        elif pb_mention:
            statut = 11
        elif pb_par:
            statut = 10
        else:
            statut = 9
        get_connection("ticket").query(
            """UPDATE TK_Liste SET
                IDTK_Statut = ?, modification = 1, opModif = ?, idModif = 0,
                TypeModif = 'TKSTATUT', ModifDate = ?, ModifOP = ?,
                ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (statut, int(user_id), now, int(user_id), int(id_ticket)),
        )
        ajout_histo_tk(int(id_ticket), statut, int(user_id))

        # SMS au DA (best-effort)
        sms_result = ""
        gsm_da = _gsm_salarie(id_da)
        if gsm_da:
            txt = (
                f"Le contrat de travail pour {_salaire_nom(id_salarie)} "
                "n'est pas conforme, merci de faire refaire les elements "
                "suivant :\n" + "\n".join(elems)
            )
            try:
                sms_result = envoi_sms(txt, gsm_da, "", "OMAYA-Info")
            except Exception as e:
                sms_result = f"SMS non envoyé : {e}"
        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True, "closed": True, "sms_result": sms_result}

    if action == "da":
        id_da = str(payload.get("id_da") or "")
        if not id_da.isdigit():
            return {"ok": False, "error": "DA invalide"}
        db = get_connection("ticket_rh")
        db.query(
            """UPDATE TK_DemandeCttW
            SET idDA = ?, ModifDate = ?, ModifOP = ?, ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (int(id_da), now, int(user_id), int(id_ticket)),
        )
        return {"ok": True}

    # action mutuelle
    id_salarie = str(payload.get("id_salarie") or "")
    if not id_salarie.isdigit():
        return {"ok": False, "error": "Salarié inconnu"}

    def b(k):
        return 1 if payload.get(k) else 0

    db = get_connection("rh")
    exists = db.query_one(
        "SELECT IDsalarie_mutuelle FROM salarie_mutuelle WHERE IDSalarie = ?",
        (int(id_salarie),),
    )
    if not exists:
        return {"ok": False, "error": "Fiche mutuelle introuvable"}

    db.query(
        """UPDATE salarie_mutuelle SET
            Adhésion = ?, AdhésionDate = ?, Mutuelle_Dossier = ?,
            IdMutuelle = ?, Mutuelle_AttSS = ?, Mutuelle_RIB = ?,
            Mutuelle_DocEnvoyés = ?, Mutuelle_RecepCertif = ?,
            Mutuelle_PasAdhésion = ?, Mutuelle_PasAdhésionJusquau = ?,
            Mutuelle_Résilié = ?, Mutuelle_RésiliéDate = ?,
            ModifDate = ?, ModifOp = ?, ModifElem = 'modif'
        WHERE IDSalarie = ?""",
        (
            b("adhesion"), iso_to_date_only(payload.get("adhesion_date")),
            b("mutuelle_dossier"), _to_int(payload.get("id_mutuelle")),
            b("att_ss"), b("rib"), b("docs_envoyes"), b("recep_certif"),
            b("pas_adhesion"),
            iso_to_date_only(payload.get("pas_adhesion_jusquau")),
            b("resilie"), iso_to_date_only(payload.get("resilie_date")),
            now, int(user_id), int(id_salarie),
        ),
    )
    return {"ok": True}
