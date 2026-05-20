"""FI_CttCourtage (type 23 — Contrat de Courtage / Attestation).

Même architecture que FI_CttW :
  - Plan 1 : contrat non validé → choix du Gérant (= idDistrib) +
    aperçu PDF non signé + « Valider pour signature »
  - Plan 2 : contrat validé → si signé, régénération du PDF signé
    (mêmes mémos Contenu/Signature/paraphe/luApp/PhotoSalarié), refus
    « Renvoyer en signature », validation finale.

Spécificités vs CttW :
  - TK_DemandeCttCourtage en base **ticket** (vs ticket_rh) — pas de
    `idDA`, le gérant est dans `idDistrib`.
  - docx tokens `S_SIGN_DISTRIB` / `S_MENTION_DISTRIB`.
  - URL signature suffixes `CttCourtageSignature` / `CttCourtageLuApp`.
  - URL PDF non signé : `TempCttCourtage/<id>-CttCourtage.pdf`.
  - `testAttest` (vs contrat) : si `docCourtage.IDGroupeOpérateur =
    281474976710657` (groupe « Autre docs et attestations ») → adapte
    libellé/SMS et nom de fichier.
  - LibDocument issu de `docCourtage.Titre`.
"""

from app.core.database import get_connection
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

GROUPE_ATTEST_AUTRE = 281474976710657
PDF_NON_SIGNE_URL = "https://interne.omaya.fr/TempCttCourtage/{id}-CttCourtage.pdf"

# Paramètres réutilisation de regenerate_signed_pdf (cf. cttw_pdf)
_PDF_KWARGS = dict(
    table="TK_DemandeCttCourtage",
    db_key="ticket",
    token_sign="S_SIGN_DISTRIB",
    token_mention="S_MENTION_DISTRIB",
    sign_suffix="CttCourtageSignature",
    luapp_suffix="CttCourtageLuApp",
    tmp_prefix="cttcourtage_",
)


def _salaire_nom(sid: int) -> str:
    if not sid:
        return ""
    info = load_salaries_minimal({sid}).get(sid, {})
    p = info.get("prenom", "")
    return (
        f"{info.get('nom', '')} {p[:1].upper() + p[1:].lower() if p else ''}"
        .strip()
    )


def _mail_salarie(id_salarie: int) -> str:
    if not id_salarie:
        return ""
    try:
        r = get_connection("rh").query_one(
            "SELECT IDSalarie, MAIL FROM salarie_coordonnées "
            "WHERE IDSalarie = ?",
            (int(id_salarie),),
        )
        return ((r.get("MAIL") if r else "") or "").strip()
    except Exception:
        return ""


def _gsm_salarie(id_salarie: int) -> str:
    if not id_salarie:
        return ""
    try:
        r = get_connection("rh").query_one(
            "SELECT IDSalarie, TélMob FROM salarie_coordonnées "
            "WHERE IDSalarie = ?",
            (int(id_salarie),),
        )
        tel = ((r.get("TélMob") if r else "") or "")
        for c in (".", " ", "/", "-"):
            tel = tel.replace(c, "")
        return tel.strip()
    except Exception:
        return ""


def _doc_courtage_info(id_societe_doc: int) -> dict:
    """Renvoie {lib_document, test_attest, lib_groupe} via
    societe_docCourtage -> docCourtage -> GroupeOpérateur."""
    out = {"lib_document": "", "test_attest": False, "lib_groupe": ""}
    if not id_societe_doc:
        return out
    try:
        rh = get_connection("rh")
        sd = rh.query_one(
            "SELECT IDsociete_docCourtage, IDdocCourtage "
            "FROM societe_docCourtage WHERE IDsociete_docCourtage = ?",
            (int(id_societe_doc),),
        )
        id_doc = _to_int(sd.get("IDdocCourtage")) if sd else 0
        if id_doc:
            d = rh.query_one(
                "SELECT IDdocCourtage, Titre, IDGroupeOpérateur "
                "FROM docCourtage WHERE IDdocCourtage = ?",
                (int(id_doc),),
            )
            if d:
                out["lib_document"] = (d.get("Titre") or "").strip()
                id_groupe = _to_int(d.get("IDGroupeOpérateur"))
                out["test_attest"] = id_groupe == GROUPE_ATTEST_AUTRE
                if id_groupe:
                    try:
                        g = get_connection("adv").query_one(
                            "SELECT IDGroupeOpérateur, LibGroupe "
                            "FROM GroupeOpérateur "
                            "WHERE IDGroupeOpérateur = ?",
                            (int(id_groupe),),
                        )
                        out["lib_groupe"] = (
                            (g.get("LibGroupe") if g else "") or ""
                        ).strip()
                    except Exception:
                        pass
    except Exception:
        pass
    return out


def _resp_orga_gsm(id_salarie: int) -> str:
    """Best-effort : si l'orga du salarié a un parent in (4, 14),
    cherche le mobile du responsable. Retourne "" si non trouvé."""
    if not id_salarie:
        return ""
    try:
        rh = get_connection("rh")
        so = rh.query_one(
            "SELECT IDSalarie, idorganigramme FROM salarie_organigramme "
            "WHERE IDSalarie = ?",
            (int(id_salarie),),
        )
        ido = _to_int(so.get("idorganigramme")) if so else 0
        if not ido:
            return ""
        o = rh.query_one(
            "SELECT idorganigramme, PARENT_ID FROM organigramme "
            "WHERE idorganigramme = ?",
            (int(ido),),
        )
        parent = _to_int(o.get("PARENT_ID")) if o else 0
        if parent not in (4, 14):
            return ""
        # Resp de l'orga parent : salarié avec IsResp = 1 dans l'orga
        r = rh.query(
            "SELECT IDSalarie FROM salarie_organigramme "
            f"WHERE idorganigramme = {int(parent)} AND IsResp = 1"
        )
        for row in r or []:
            sid = _clean_id(_to_int(row.get("IDSalarie")))
            gsm = _gsm_salarie(sid)
            if gsm:
                return gsm
    except Exception:
        pass
    return ""


def load(id_ticket: int) -> dict:
    db = get_connection("ticket")
    r = db.query_one(
        """SELECT IDTK_Liste, IDdemandeContratW, IDSalarie, idDistrib,
            IDsociete_docCourtage, contratGénéré, contratValidé,
            contratSigné, contratAnnul, datesignature, TitreContrat
        FROM TK_DemandeCttCourtage WHERE IDTK_Liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}

    id_salarie = _clean_id(_to_int(r.get("IDSalarie")))
    id_distrib = _clean_id(_to_int(r.get("idDistrib")))
    id_societe_doc = _to_int(r.get("IDsociete_docCourtage"))
    contrat_valide = bool(r.get("contratValidé"))
    contrat_signe = bool(r.get("contratSigné"))
    plan = 2 if contrat_valide else 1

    info_doc = _doc_courtage_info(id_societe_doc)

    base = {
        "found": True,
        "plan": plan,
        "id_salarie": str(id_salarie) if id_salarie else "",
        "salarie_nom": _salaire_nom(id_salarie),
        "id_distrib": str(id_distrib) if id_distrib else "",
        "da_nom": _salaire_nom(id_distrib),
        "titre_contrat": (r.get("TitreContrat") or "").strip(),
        "lib_document": info_doc["lib_document"],
        "lib_groupe": info_doc["lib_groupe"],
        "test_attest": info_doc["test_attest"],
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
    """Régénère le PDF signé (Plan 2). Réutilise cttw_pdf
    paramétré pour TK_DemandeCttCourtage."""
    from .cttw_pdf import regenerate_signed_pdf

    db = get_connection("ticket")
    r = db.query_one(
        """SELECT IDTK_Liste, IDSalarie, idDistrib, datesignature
        FROM TK_DemandeCttCourtage WHERE IDTK_Liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        raise ValueError("Contrat de courtage introuvable")
    id_salarie = _clean_id(_to_int(r.get("IDSalarie")))
    id_distrib = _clean_id(_to_int(r.get("idDistrib")))
    return regenerate_signed_pdf(
        int(id_ticket),
        _salaire_nom(id_salarie),
        _salaire_nom(id_distrib),
        date_only_to_iso(r.get("datesignature")) or "",
        **_PDF_KWARGS,
    )


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    action = str(payload.get("action") or "valider")
    now = _now_windev()
    db = get_connection("ticket")

    if action == "da":
        id_da = str(payload.get("id_da") or "")
        if not id_da.isdigit():
            return {"ok": False, "error": "Gérant invalide"}
        db.query(
            """UPDATE TK_DemandeCttCourtage SET idDistrib = ?, ModifDate = ?,
                ModifOP = ?, ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (int(id_da), now, int(user_id), int(id_ticket)),
        )
        return {"ok": True}

    if action == "valider":
        # « Valider le contrat de courtage / Attestation pour signature »
        cur = db.query_one(
            """SELECT IDSalarie, idDistrib, IDsociete_docCourtage
            FROM TK_DemandeCttCourtage WHERE IDTK_Liste = ?""",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Contrat introuvable"}
        id_salarie = _clean_id(_to_int(cur.get("IDSalarie")))
        id_distrib = _clean_id(_to_int(cur.get("idDistrib")))
        id_societe_doc = _to_int(cur.get("IDsociete_docCourtage"))

        db.query(
            """UPDATE TK_DemandeCttCourtage SET
                contratValidé = 1, contratSigné = 0, contratAnnul = 0,
                datesignature = '', ContenuValidation = '',
                PhotoSalarié = '', Signature = '', paraphe = '', luApp = '',
                ModifDate = ?, ModifOP = ?, ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (now, int(user_id), int(id_ticket)),
        )
        db.query(
            """UPDATE TK_Liste
            SET IDTK_Statut = 22, ModifDate = ?, ModifElem = 'modif'
            WHERE IDTK_Liste = ?""",
            (now, int(id_ticket)),
        )

        info_doc = _doc_courtage_info(id_societe_doc)
        # SMS au gérant
        sms_result = ""
        gsm_da = _gsm_salarie(id_distrib)
        if gsm_da:
            if info_doc["test_attest"]:
                txt = (
                    f"Votre {info_doc['lib_document']} est disponible à la "
                    "signature sur l'appli Omayapp, dispo sur Android et IOS."
                )
            else:
                txt = (
                    "Le contrat de courtage est disponible à la signature "
                    "sur l'appli Omayapp, dispo sur Android et IOS."
                )
            try:
                sms_result = envoi_sms(txt, gsm_da, "", "OMAYA-Info")
            except Exception as e:
                sms_result = f"SMS non envoyé : {e}"
        # SMS au Resp Orga si parent in (4, 14) — best-effort
        try:
            gsm_resp = _resp_orga_gsm(id_salarie)
            if gsm_resp:
                url = (
                    f"https://interne.omaya.fr/TempCttCourtage/"
                    f"{id_ticket}-CttCourtage.pdf"
                )
                txt2 = (
                    "Le contrat de courtage est disponible pour "
                    f"{_salaire_nom(id_distrib)} à la signature sur l'appli "
                    f"Omayapp.\nLien PDF : {url}"
                )
                envoi_sms(txt2, gsm_resp, "", "OMAYA-Info")
        except Exception:
            pass

        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True, "sms_result": sms_result}

    if action == "valider_signe":
        # « Ce contrat de courtage / Attestation est valide » : régénère
        # le PDF signé, upload FTP dossier salarié, SMS + mail, clôture.
        from app.core.config import FTP_GESTION_RH_PATH
        from app.shared.notifications.mail import envoi_mail_rh

        from .cttw_pdf import ftp_upload, regenerate_signed_pdf

        cloturer = bool(payload.get("cloturer"))
        r = db.query_one(
            """SELECT IDTK_Liste, IDSalarie, idDistrib, IDsociete_docCourtage,
                datesignature
            FROM TK_DemandeCttCourtage WHERE IDTK_Liste = ?""",
            (int(id_ticket),),
        )
        if not r:
            return {"ok": False, "error": "Contrat introuvable"}
        id_salarie = _clean_id(_to_int(r.get("IDSalarie")))
        id_distrib = _clean_id(_to_int(r.get("idDistrib")))
        info_doc = _doc_courtage_info(
            _to_int(r.get("IDsociete_docCourtage"))
        )
        salarie_nom = _salaire_nom(id_salarie)

        try:
            pdf = regenerate_signed_pdf(
                int(id_ticket), salarie_nom, _salaire_nom(id_distrib),
                date_only_to_iso(r.get("datesignature")) or "",
                **_PDF_KWARGS,
            )
            # Nom de fichier signé (cf. WinDev)
            if info_doc["test_attest"]:
                fname = (
                    f"{id_ticket}_{info_doc['lib_document'].replace(' ', '_')}"
                    "_Signé.pdf"
                )
            elif info_doc["lib_groupe"]:
                fname = (
                    f"{id_ticket}_{info_doc['lib_groupe']}_"
                    "CttCourtageSigné.pdf"
                )
            else:
                fname = f"{id_ticket}_CttCourtageSigné.pdf"
            ftp_upload(
                f"{FTP_GESTION_RH_PATH}/{id_salarie}/Fiches_Salaires",
                fname, pdf,
            )
        except Exception as e:
            return {"ok": False, "error": f"Génération/upload PDF : {e}"}

        # SMS + mail au salarié
        sms_result = ""
        gsm = _gsm_salarie(id_salarie)
        mail = _mail_salarie(id_salarie)
        if gsm:
            doc_lib = info_doc["lib_document"] or "contrat de courtage"
            txt = (
                f"Votre {doc_lib} est disponible sur votre espace salarié "
                f"(intranet ou appli Omaya).\n"
                f"Une copie est envoyée sur votre email : {mail}"
            )
            try:
                sms_result = envoi_sms(txt, gsm, "", salarie_nom)
            except Exception as e:
                sms_result = f"SMS non envoyé : {e}"
        if mail:
            doc_lib = info_doc["lib_document"] or "Contrat de Courtage"
            html = (
                f"<p>Bonjour,</p><p>Voici votre {doc_lib} signé.</p>"
                "<p>Cdt</p><p>Service RH</p>"
            )
            cci = [c for c in (_mail_salarie(id_distrib), "intranet@omaya.fr") if c]
            try:
                envoi_mail_rh(
                    f"{doc_lib} signé", html, [mail], cci,
                    "intranet@omaya.fr", [(fname, pdf)],
                )
            except Exception:
                pass

        if cloturer:
            db.query(
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
        # « Renvoyer ce contrat / Attestation en signature »
        pb_sign = bool(payload.get("pb_sign"))
        pb_par = bool(payload.get("pb_paraphe"))
        pb_mention = bool(payload.get("pb_mention"))
        if not (pb_sign or pb_par or pb_mention):
            return {"ok": False, "error": "Coche au moins un problème"}
        cur = db.query_one(
            "SELECT IDSalarie, idDistrib FROM TK_DemandeCttCourtage "
            "WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Contrat introuvable"}
        id_salarie = _clean_id(_to_int(cur.get("IDSalarie")))
        id_distrib = _clean_id(_to_int(cur.get("idDistrib")))

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
            f"UPDATE TK_DemandeCttCourtage SET {', '.join(sets)} "
            f"WHERE IDTK_Liste = ?",
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
        db.query(
            """UPDATE TK_Liste SET
                IDTK_Statut = ?, modification = 1, opModif = ?, idModif = 0,
                TypeModif = 'TKSTATUT', ModifDate = ?, ModifOP = ?,
                ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (statut, int(user_id), now, int(user_id), int(id_ticket)),
        )
        ajout_histo_tk(int(id_ticket), statut, int(user_id))

        sms_result = ""
        gsm_da = _gsm_salarie(id_distrib)
        if gsm_da:
            txt = (
                f"Le contrat de courtage pour {_salaire_nom(id_salarie)} "
                "n'est pas conforme, merci de faire refaire les éléments "
                "suivant :\n" + "\n".join(elems)
            )
            try:
                sms_result = envoi_sms(txt, gsm_da, "", "OMAYA-Info")
            except Exception as e:
                sms_result = f"SMS non envoyé : {e}"
        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True, "closed": True, "sms_result": sms_result}

    return {"ok": False, "error": "Action non disponible"}
