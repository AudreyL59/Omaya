"""FI_CttCourtage (type 23 — Contrat de Courtage / Attestation).

Même architecture que FI_CttW :
  - Plan 1 : contrat non validé → choix du Gérant (= idDistrib) +
    aperçu PDF non signé + « Valider pour signature »
  - Plan 2 : contrat validé → si signé, régénération du PDF signé
    (mêmes mémos Contenu/Signature/paraphe/luApp/PhotoSalarié), refus
    « Renvoyer en signature », validation finale.

Spécificités vs CttW :
  - TK_DemandeCttCourtage en base **ticket_bo** (vs ticket_rh pour CttW)
    — pas de `idDA`, le gérant est dans `idDistrib`.
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
    db_key="ticket_bo",
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
    db = get_connection("ticket_bo")
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

    db = get_connection("ticket_bo")
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
    # TK_DemandeCttCourtage = base ticket_bo ; TK_Liste = base ticket
    bo = get_connection("ticket_bo")

    if action == "da":
        id_da = str(payload.get("id_da") or "")
        if not id_da.isdigit():
            return {"ok": False, "error": "Gérant invalide"}
        bo.query(
            """UPDATE TK_DemandeCttCourtage SET idDistrib = ?, ModifDate = ?,
                ModifOP = ?, ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (int(id_da), now, int(user_id), int(id_ticket)),
        )
        return {"ok": True}

    if action == "valider":
        # « Valider le contrat de courtage / Attestation pour signature »
        cur = bo.query_one(
            """SELECT IDSalarie, idDistrib, IDsociete_docCourtage
            FROM TK_DemandeCttCourtage WHERE IDTK_Liste = ?""",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Contrat introuvable"}
        id_salarie = _clean_id(_to_int(cur.get("IDSalarie")))
        id_distrib = _clean_id(_to_int(cur.get("idDistrib")))
        id_societe_doc = _to_int(cur.get("IDsociete_docCourtage"))

        bo.query(
            """UPDATE TK_DemandeCttCourtage SET
                contratValidé = 1, contratSigné = 0, contratAnnul = 0,
                datesignature = '', ContenuValidation = '',
                PhotoSalarié = '', Signature = '', paraphe = '', luApp = '',
                ModifDate = ?, ModifOP = ?, ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (now, int(user_id), int(id_ticket)),
        )
        get_connection("ticket").query(
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
        # le PDF signé, upload FTP dossier salarié, **mail juristes**,
        # upsert societe_docCourtage (base rh, RECU=1), si !testAttest
        # SMS + mail au salarié (avec CC Resp Orga si parent 4/14),
        # clôture optionnelle.
        from app.core.config import (
            FTP_GESTION_RH_PATH,
            MAIL_JURISTE_1,
            MAIL_RESP_JURISTE,
        )
        from app.shared.notifications.mail import envoi_mail_rh

        from .cttw_pdf import ftp_upload, regenerate_signed_pdf

        cloturer = bool(payload.get("cloturer"))
        r = bo.query_one(
            """SELECT IDTK_Liste, IDdemandeContratW, IDSalarie, idDistrib,
                IDsociete_docCourtage, datesignature
            FROM TK_DemandeCttCourtage WHERE IDTK_Liste = ?""",
            (int(id_ticket),),
        )
        if not r:
            return {"ok": False, "error": "Contrat introuvable"}
        id_salarie = _clean_id(_to_int(r.get("IDSalarie")))
        id_distrib = _clean_id(_to_int(r.get("idDistrib")))
        id_societe_doc = _to_int(r.get("IDsociete_docCourtage"))
        id_demande = _to_int(r.get("IDdemandeContratW"))
        info_doc = _doc_courtage_info(id_societe_doc)
        salarie_nom = _salaire_nom(id_salarie)

        try:
            pdf = regenerate_signed_pdf(
                int(id_ticket), salarie_nom, _salaire_nom(id_distrib),
                date_only_to_iso(r.get("datesignature")) or "",
                **_PDF_KWARGS,
            )
            if info_doc["test_attest"]:
                fname = (
                    f"{id_ticket}_"
                    f"{(info_doc['lib_document'] or 'Document').replace(' ', '_')}"
                    f"_Signé.pdf"
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

        # 1. Mail aux juristes (cf. WinDev MyEmail1)
        raison_sociale = ""
        try:
            rh = get_connection("rh")
            # idDistrib peut être un IdSte (cf. WinDev). À défaut, on
            # tente IdSte du salarié via salarie_embauche.
            if id_distrib:
                s = rh.query_one(
                    "SELECT IdSte, RaisonSociale FROM societe WHERE IdSte = ?",
                    (int(id_distrib),),
                )
                raison_sociale = (s.get("RaisonSociale") or "").strip() if s else ""
            if not raison_sociale and id_salarie:
                e = rh.query_one(
                    "SELECT IDSalarie, IdSte FROM salarie_embauche "
                    "WHERE IDSalarie = ?",
                    (int(id_salarie),),
                )
                id_ste = _to_int(e.get("IdSte")) if e else 0
                if id_ste:
                    s = rh.query_one(
                        "SELECT IdSte, RaisonSociale FROM societe "
                        "WHERE IdSte = ?",
                        (int(id_ste),),
                    )
                    raison_sociale = (s.get("RaisonSociale") or "").strip() if s else ""
        except Exception:
            pass

        juristes = [m for m in (MAIL_RESP_JURISTE, MAIL_JURISTE_1) if m]
        if juristes:
            doc_lib = info_doc["lib_document"] or "Contrat de courtage"
            html = (
                "<font face='arial' style='font-size:10pt;'>"
                "<p>Bonjour,</p>"
                f"<p>Le document {doc_lib} a été validé "
                f"pour la société {raison_sociale}.</p>"
                "<br/>---Cdt.<br/>"
                "<p><i>PS : Ceci est un mail automatique, "
                "ne pas répondre. Merci.</i></p></font>"
            )
            try:
                # CC bo@exosphere.fr ajouté aux destinataires
                # (envoi_mail_rh n'expose pas Cc séparément)
                envoi_mail_rh(
                    f"Validation {doc_lib} - {raison_sociale}",
                    html, juristes + ["bo@exosphere.fr"],
                    ["intranet@omaya.fr"],  # cci
                    "intranet@omaya.fr",
                )
            except Exception:
                pass

        # 2. Upsert societe_docCourtage (base rh)
        try:
            rh = get_connection("rh")
            target = id_societe_doc
            existing = None
            if target:
                existing = rh.query_one(
                    "SELECT IDsociete_docCourtage FROM societe_docCourtage "
                    "WHERE IDsociete_docCourtage = ?",
                    (int(target),),
                )
            if existing:
                rh.query(
                    """UPDATE societe_docCourtage SET RECU = 1,
                        RECUDATE = ?, NomCttSigné = ?, ModifOP = ?,
                        ModifDate = ?, ModifELEM = 'modif'
                    WHERE IDsociete_docCourtage = ?""",
                    (now, fname, int(user_id), now, int(target)),
                )
            else:
                new_id = int(now)
                rh.query(
                    """INSERT INTO societe_docCourtage
                    (IDsociete_docCourtage, IDSalarie, idDistrib,
                     DATE_Edition, RECU, RECUDATE, NomCttSigné,
                     ModifOP, ModifDate, ModifELEM)
                    VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, 'new')""",
                    (
                        new_id, int(id_salarie), int(id_distrib),
                        str(id_demande), now, fname,
                        int(user_id), now,
                    ),
                )
                bo.query(
                    """UPDATE TK_DemandeCttCourtage SET
                        IDsociete_docCourtage = ?, ModifDate = ?,
                        ModifOP = ?, ModifELEM = 'modif'
                    WHERE IDTK_Liste = ?""",
                    (new_id, now, int(user_id), int(id_ticket)),
                )
        except Exception as e:
            return {"ok": False, "error": f"societe_docCourtage : {e}"}

        # 3. Si !testAttest : SMS + mail au salarié avec PJ
        sms_result = ""
        if not info_doc["test_attest"]:
            gsm = _gsm_salarie(id_salarie)
            mail = _mail_salarie(id_salarie)
            if gsm:
                txt = (
                    "Votre contrat de courtage est disponible sur votre "
                    "espace salarié (intranet ou appli Omaya).\n"
                    f"Une copie est envoyee sur votre email : {mail}"
                )
                try:
                    sms_result = envoi_sms(txt, gsm, "", salarie_nom)
                except Exception as e:
                    sms_result = f"SMS non envoyé : {e}"
            if mail:
                html = (
                    "<font face='arial' style='font-size:10pt;'>"
                    "<p>Bonjour,</p>"
                    "<p>Voici votre contrat de courtage signé.</p>"
                    "<p>Cdt</p><p>Service RH</p></font>"
                )
                cci = [
                    c for c in (_mail_salarie(id_distrib), "intranet@omaya.fr")
                    if c
                ]
                # CC Resp Orga si parent in (4, 14)
                dests = [mail]
                resp_gsm_skip = _resp_orga_gsm(id_salarie)  # noqa: F841
                # On ne récupère pas le mail du Resp via _resp_orga_gsm
                # mais on ajoute son mail si on peut. Best-effort minimal :
                try:
                    rh = get_connection("rh")
                    so = rh.query_one(
                        "SELECT IDSalarie, idorganigramme "
                        "FROM salarie_organigramme WHERE IDSalarie = ?",
                        (int(id_salarie),),
                    )
                    ido = _to_int(so.get("idorganigramme")) if so else 0
                    if ido:
                        o = rh.query_one(
                            "SELECT idorganigramme, PARENT_ID "
                            "FROM organigramme WHERE idorganigramme = ?",
                            (int(ido),),
                        )
                        parent = _to_int(o.get("PARENT_ID")) if o else 0
                        if parent in (4, 14):
                            rr = rh.query(
                                "SELECT IDSalarie FROM salarie_organigramme "
                                f"WHERE idorganigramme = {int(parent)} "
                                f"AND IsResp = 1"
                            )
                            for row in rr or []:
                                sid = _clean_id(_to_int(row.get("IDSalarie")))
                                m_resp = _mail_salarie(sid)
                                if m_resp:
                                    dests.append(m_resp)
                                    break
                except Exception:
                    pass
                try:
                    envoi_mail_rh(
                        "Contrat de courtage Signé", html, dests, cci,
                        "intranet@omaya.fr", [(fname, pdf)],
                    )
                except Exception:
                    pass

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
        # « Renvoyer ce contrat / Attestation en signature »
        pb_sign = bool(payload.get("pb_sign"))
        pb_par = bool(payload.get("pb_paraphe"))
        pb_mention = bool(payload.get("pb_mention"))
        if not (pb_sign or pb_par or pb_mention):
            return {"ok": False, "error": "Coche au moins un problème"}
        cur = bo.query_one(
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
        bo.query(
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
        get_connection("ticket").query(
            """UPDATE TK_Liste SET
                IDTK_Statut = ?, modification = 1, opModif = ?, idModif = 0,
                TypeModif = 'TKSTATUT', ModifDate = ?, ModifOP = ?,
                ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (statut, int(user_id), now, int(user_id), int(id_ticket)),
        )
        # cf. WinDev : AjoutHistoTK(..., 7, ...) toujours sur refus
        ajout_histo_tk(int(id_ticket), 7, int(user_id))

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

    if action == "relance_sms":
        # « Relance SMS » au gérant (Plan 2 avant signature)
        cur = bo.query_one(
            """SELECT idDistrib, IDsociete_docCourtage
            FROM TK_DemandeCttCourtage WHERE IDTK_Liste = ?""",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Contrat introuvable"}
        id_distrib = _clean_id(_to_int(cur.get("idDistrib")))
        info_doc = _doc_courtage_info(_to_int(cur.get("IDsociete_docCourtage")))
        gsm_da = _gsm_salarie(id_distrib)
        if not gsm_da:
            return {"ok": False, "error": "Pas de mobile pour le gérant"}
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
        txt += " Merci faire la signature rapidement."
        try:
            res = envoi_sms(txt, gsm_da, "", "OMAYA-Info")
        except Exception as e:
            res = f"erreur : {e}"
        return {"ok": True, "sms_result": res}

    return {"ok": False, "error": "Action non disponible"}
