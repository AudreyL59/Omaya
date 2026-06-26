"""Service Fen_ImportSFR (ADM Imports Bases -> SFR/RED).

10 types d'import (cf combo TypeImport WinDev) :
  1. Base Journaliere Fibre   ImportJournalierFibre
  2. Base Journaliere Mobile  ImportJournalierMobile
  3. Base Journaliere CALL    ImportJournalierCALL
  4. Base Hebdo               ImportHebdo
  5. Import Options           ImportOptions
  6. RUN                      ImportRUN
  7. Call RET - KO            ImportCallRET_KO
  8. Call RET - Racc          ImportCallRET_Racc
  9. Call RET - Vente ADD     ImportCallRET_VentesADD
 10. Call RET - RDV Tech      ImportCallRET_RDVTech

Etat actuel : type 1 (Base Journ Fibre) detection only. Les 9 autres
types sont des squelettes a coder au fur et a mesure.

Ligne_départ : 2 pour types 3, 5, 7, 8, 9, 10 ; 3 pour les autres
(les fichiers SFR ont parfois 2 lignes d'entete).
"""

from __future__ import annotations

import base64
import io
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection
from app.shared.recrutement.services.recherche_cv import _int, _str
from app.intranets.adm.services.import_eni import (
    _new_id, _lookup_or_create_client,
    _col_letter_to_index, _cell, _parse_date_fr, _dernier_jour_mois,
    _parse_int,
)


# Mapping colonnes Base Journaliere Fibre (cf groupe grpJournalier Fibre)
COLS_BJ_FIBRE = {
    "num_bs": "A",                "date_signature": "C",
    "date_va": "D",               "date_ra": "E",
    "date_rdv": "G",              "date_rdv_actu": "H",
    "lib_statut": "I",            "statut_vente": "J",
    "motif_annul": "K",           "comment": "L",
    "instance": "M",              "cluster_ville": "AQ",
    "cluster_code": "AP",         "client_adresse": "AI",
    "client_cp": "AJ",            "client_ville": "AL",
    "type_install": "AM",         "type_vente": "AC",
    "code_offre": "AD",           "technologie": "AF",
    "box8": "AT",                 "internet_garantie": "AU",
    "portabilite": "BA",          "info_tech": "BG",
    "prise_existante": "BJ",      "num_prise": "BL",
    "date_resil": "BM",           "der_motif": "P",
    "parcours_chaine": "BO",      "parcours_degroupe": "BF",
    "prise_saisie": "BT",         "remise": "AR",
    "code_vendeur": "X",          "client_mail": "BN",
    "client_nom": "BQ",           "client_prenom": "BR",
    "client_gsm": "BS",
}


class ImportSfrParams(BaseModel):
    type_import: int                    # 1..10
    simulation: bool = True
    ligne_depart: int = 3               # 2 ou 3 selon type
    periode1_du: str = ""
    periode1_au: str = ""
    periode1_mois_paiement: str = ""
    periode2_du: str = ""
    periode2_au: str = ""
    periode2_mois_paiement: str = ""
    mois_paiement_distrib: str = ""


class ImportSfrResume(BaseModel):
    nb_fichiers: int = 0
    nb_ajoutes: int = 0
    nb_modifies: int = 0
    nb_modif_vend: int = 0
    nb_migrations: int = 0
    nb_non_modifies: int = 0
    nb_erreurs: int = 0
    nb_introuvables: int = 0
    nb_doublons: int = 0
    nb_hors_delai: int = 0


class ImportSfrResult(BaseModel):
    ok: bool
    type_import: int
    type_label: str
    simulation: bool
    resume: ImportSfrResume
    fichiers_traites: list[str] = []
    contrats_ajoutes: list[dict] = []
    contrats_modifies: list[dict] = []
    contrats_non_trouves: list[dict] = []
    contrats_migrations: list[dict] = []
    modif_vendeurs: list[dict] = []
    erreurs: list[dict] = []
    message: str = ""
    xlsx_b64: str = ""
    xlsx_name: str = ""
    mail_envoye: bool = False


TYPE_LABELS = {
    1: "Base Journalière Fibre",
    2: "Base Journalière Mobile",
    3: "Base Journalière CALL",
    4: "Base Hebdo",
    5: "Import Options",
    6: "RUN",
    7: "Call RET - KO",
    8: "Call RET - Racc",
    9: "Call RET - Vente ADD",
    10: "Call RET - RDV Tech",
}

# Helpers metier (transposition WinDev simplifiee)


def _type_vente_fibre(s: str) -> int:
    """typeVenteFibre : 1=Nouvelle, 2=Retention, 3=Migration THD, 4=Mig FTTH..."""
    u = (s or "").upper()
    if "MIG" in u or "MTX" in u:
        return 3
    if "RET" in u:
        return 2
    return 1


def _type_techno_fibre(s: str) -> int:
    """1=FTTH, 2=FTTB, 3=ADSL"""
    u = (s or "").upper()
    if "FTTH" in u:
        return 1
    if "FTTB" in u or "THD" in u:
        return 2
    if "ADSL" in u:
        return 3
    return 0


def _type_offre_fibre(code_offre: str, techno: int,
                      date_sign: Optional[date]) -> int:
    """typeOffreFibre : lookup pgt_sfr_produit by code/lib.
    Fallback : 0 si introuvable."""
    if not code_offre:
        return 0
    try:
        db = get_pg_connection("adv")
        r = db.query_one(
            """SELECT id_produit FROM adv.pgt_sfr_produit
                WHERE LOWER(lib_produit) LIKE LOWER(?)
                LIMIT 1""",
            (f"%{code_offre}%",),
        )
        return _int(r.get("id_produit")) if r else 0
    except Exception:
        return 0


def _id_etat_fibre(lib_statut: str) -> int:
    """donneIdEtatFibre : lookup pgt_sfr_etat_contrat by lib_etat LIKE."""
    if not lib_statut:
        return 0
    try:
        db = get_pg_connection("adv")
        r = db.query_one(
            """SELECT id_etat FROM adv.pgt_sfr_etat_contrat
                WHERE LOWER(lib_etat) LIKE LOWER(?)
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (f"{lib_statut}%",),
        )
        return _int(r.get("id_etat")) if r else 0
    except Exception:
        return 0


def _test_cluster_fibre(code_vad: str) -> dict:
    """testClusterFibre : retourne {id_sfr_cluster, hors_cible}."""
    if not code_vad:
        return {"id_sfr_cluster": 0, "hors_cible": True}
    try:
        db = get_pg_connection("adv")
        r = db.query_one(
            """SELECT id_sfr_cluster, hors_cible FROM adv.pgt_sfr_cluster
                WHERE code_vad = ? LIMIT 1""",
            (code_vad,),
        )
        return {"id_sfr_cluster": _int(r.get("id_sfr_cluster")) if r else 0,
                "hors_cible": bool(r.get("hors_cible")) if r else True}
    except Exception:
        return {"id_sfr_cluster": 0, "hors_cible": True}


def _lookup_tk_call_sfr(num_bs: str) -> dict:
    """ReqTkCallSFR_ByNumCtt : lookup pgt_tk_call_sfr by num_bs."""
    if not num_bs:
        return {}
    try:
        db = get_pg_connection("ticket_bo")
        r = db.query_one(
            """SELECT id_salarie, nom_client, nom_marital_client, prenom_client,
                      datenaiss, adresse1, adresse2, cp, ville, mobile1, mobile2,
                      adr_mail, opt_partenaire, num_prise_optique, id_tk_liste
                 FROM ticket_bo.pgt_tk_call_sfr
                WHERE UPPER(num_bs) = UPPER(?) LIMIT 1""",
            (num_bs,),
        )
        return r or {}
    except Exception:
        return {}


def _import_journalier_fibre(
    p: ImportSfrParams, fname: str, content: bytes, op_id: int,
    ajoutes: list, modifies: list, migrations: list,
    modif_vendeurs: list, erreurs: list, resume: ImportSfrResume,
) -> None:
    """Procedure Base Journaliere Fibre (type 1)."""
    from openpyxl import load_workbook
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as e:
        resume.nb_erreurs += 1
        erreurs.append({"_erreur": f"Lecture {fname} : {e}"})
        return
    ws = wb.active
    cols = {k: _col_letter_to_index(v) for k, v in COLS_BJ_FIBRE.items()}
    db = get_pg_connection("adv")

    ligne_depart = p.ligne_depart or 3
    for i in range(ligne_depart, (ws.max_row or 0) + 1):
        num_bs = _cell(ws, i, cols["num_bs"]).upper()
        if not num_bs:
            continue

        date_sign = _parse_date_fr(_cell(ws, i, cols["date_signature"]))
        date_va = _parse_date_fr(_cell(ws, i, cols["date_va"]))
        date_ra = _parse_date_fr(_cell(ws, i, cols["date_ra"]))
        date_rdv = _parse_date_fr(_cell(ws, i, cols["date_rdv"]))
        date_rdv_actu = _parse_date_fr(_cell(ws, i, cols["date_rdv_actu"]))
        if date_rdv_actu:
            date_rdv = date_rdv_actu
        type_v_s = _cell(ws, i, cols["type_vente"])
        type_vente = _type_vente_fibre(type_v_s)
        techno = _type_techno_fibre(_cell(ws, i, cols["technologie"]))
        code_offre = _cell(ws, i, cols["code_offre"])
        offre = _type_offre_fibre(code_offre, techno, date_sign)
        lib_statut = _cell(ws, i, cols["lib_statut"])
        id_etat = _id_etat_fibre(lib_statut)
        cluster_code = _cell(ws, i, cols["cluster_code"]).replace("'", "")
        cluster_ville = _cell(ws, i, cols["cluster_ville"])
        client_cp = _cell(ws, i, cols["client_cp"])
        client_ville = _cell(ws, i, cols["client_ville"])
        client_adr = _cell(ws, i, cols["client_adresse"])
        client_mail = _cell(ws, i, cols["client_mail"])
        client_nom = _cell(ws, i, cols["client_nom"])
        client_prenom = _cell(ws, i, cols["client_prenom"])
        client_gsm = _cell(ws, i, cols["client_gsm"])
        if client_mail == "0":
            client_mail = ""
        if client_gsm and not client_gsm.startswith("0"):
            client_gsm = "0" + client_gsm

        box8 = "oui" in _cell(ws, i, cols["box8"]).lower()
        portabilite = "oui" in _cell(ws, i, cols["portabilite"]).lower()
        prise_existante = "oui" in _cell(ws, i, cols["prise_existante"]).lower()
        prise_saisie = "oui" in _cell(ws, i, cols["prise_saisie"]).lower()
        internet_garantie = "oui" in _cell(ws, i, cols["internet_garantie"]).lower()
        remise = bool(_cell(ws, i, cols["remise"]).strip())
        code_vendeur = _cell(ws, i, cols["code_vendeur"])
        comment = _cell(ws, i, cols["comment"])
        info_tech = _cell(ws, i, cols["info_tech"])
        if comment == "0":
            comment = ""
        if info_tech and info_tech != "0":
            comment += "\n" + info_tech
        motif_annul = _cell(ws, i, cols["motif_annul"])
        if motif_annul == "0":
            motif_annul = ""
        num_prise = _cell(ws, i, cols["num_prise"])
        date_resil = _parse_date_fr(_cell(ws, i, cols["date_resil"]))

        # Detection migration FTTB -> FTTH
        is_mig = ("MTX-THD" in code_offre.upper()
                  and "MIG" in type_v_s.upper())
        if is_mig and type_vente == 3:
            type_vente = 4
            migrations.append({
                "NumBS": num_bs, "DateSign": str(date_sign or ""),
                "ClientCP": client_cp, "ClientVille": client_ville,
                "LibStatut": lib_statut, "Box8": box8,
                "ClusterCode": cluster_code,
            })
            resume.nb_migrations += 1

        cluster = _test_cluster_fibre(cluster_code)

        # Lookup contrat existant
        ctt = db.query_one(
            """SELECT id_contrat, id_salarie, id_client, id_produit,
                      id_etat_contrat, type_vente, date_signature,
                      num_prise_vend, id_sfr_cluster
                 FROM adv.pgt_sfr_contrat
                WHERE UPPER(num_bs) = UPPER(?)
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (num_bs,),
        )

        if not ctt:
            tk = _lookup_tk_call_sfr(num_bs)
            id_salarie = int(tk.get("id_salarie") or 20200715153948361)
            ajoutes.append({
                "NumBS": num_bs,
                "DateSign": str(date_sign or ""),
                "DateVa": str(date_va or ""), "DateRa": str(date_ra or ""),
                "DateRDV": str(date_rdv or ""),
                "ClientCP": client_cp, "ClientVille": client_ville,
                "LibStatut": lib_statut, "IdProduit": offre,
                "TypeVente": type_vente, "Box8": box8,
                "ClusterCode": cluster_code,
                "_payload_create": {
                    "num_bs": num_bs, "id_salarie": id_salarie,
                    "id_produit": offre, "id_etat_contrat": id_etat,
                    "id_etat_sfr": id_etat, "type_vente": type_vente,
                    "technologie": techno, "box8": box8,
                    "portabilite": portabilite, "self_install": False,
                    "id_sfr_cluster": cluster["id_sfr_cluster"],
                    "date_signature": date_sign,
                    "date_validation": date_va,
                    "date_racc_activ": date_ra,
                    "date_rdv_tech": date_rdv,
                    "date_resil": date_resil,
                    "motif_annulation": motif_annul,
                    "info_vente_sfr": comment,
                    "info_interne": code_vendeur,
                    "internet_garanti": internet_garantie,
                    "num_prise_sfr": num_prise,
                    "prise_existante": prise_existante,
                    "prise_saisie": prise_saisie,
                    "remise": remise,
                    "_client": {
                        "nom": client_nom, "prenom": client_prenom,
                        "adresse": client_adr, "cp": client_cp,
                        "ville": client_ville, "mail": client_mail,
                        "gsm": client_gsm,
                    },
                },
            })
            resume.nb_ajoutes += 1
        else:
            # Detect modifs
            id_contrat = int(ctt["id_contrat"])
            id_sal_db = int(ctt.get("id_salarie") or 0)
            modifs = []
            if int(ctt.get("type_vente") or 0) != type_vente:
                modifs.append(f"TypeVente -> {type_vente}")
            if int(ctt.get("id_produit") or 0) != offre and offre:
                modifs.append(f"Offre -> {offre}")
            if id_sal_db in (0, 20200715153948361):
                tk = _lookup_tk_call_sfr(num_bs)
                tk_sal = int(tk.get("id_salarie") or 0)
                if tk_sal and tk_sal != id_sal_db:
                    modifs.append(f"Vendeur -> {tk_sal}")
                    modif_vendeurs.append({
                        "NumBS": num_bs, "OldIdSalarie": id_sal_db,
                        "NewIdSalarie": tk_sal,
                    })
                    resume.nb_modif_vend += 1

            if modifs:
                modifies.append({
                    "NumBS": num_bs,
                    "DateSign OMAYA": str(ctt.get("date_signature") or ""),
                    "Modifs": " | ".join(modifs),
                })
                resume.nb_modifies += 1
            else:
                resume.nb_non_modifies += 1

    wb.close()


def _import_placeholder(
    p: ImportSfrParams, fname: str, type_lbl: str,
    erreurs: list, resume: ImportSfrResume,
) -> None:
    """Placeholder pour les types non encore codes."""
    erreurs.append({
        "Fichier": fname,
        "Erreur": f"Type '{type_lbl}' non encore implementé (squelette).",
        "Note": "Logique métier WinDev à transposer.",
    })
    resume.nb_erreurs += 1


def run_import_sfr(
    p: ImportSfrParams, files: list[tuple[str, bytes]], op_id: int,
) -> ImportSfrResult:
    """Dispatcher principal."""
    label = TYPE_LABELS.get(p.type_import, "?")
    if not files:
        return ImportSfrResult(
            ok=False, type_import=p.type_import, type_label=label,
            simulation=p.simulation, resume=ImportSfrResume(),
            message="Aucun fichier fourni.",
        )

    resume = ImportSfrResume(nb_fichiers=len(files))
    ajoutes: list[dict] = []
    modifies: list[dict] = []
    non_trouves: list[dict] = []
    migrations: list[dict] = []
    modif_vendeurs: list[dict] = []
    erreurs: list[dict] = []
    fichiers_traites: list[str] = []

    for fname, content in files:
        fichiers_traites.append(fname)
        try:
            if p.type_import == 1:
                _import_journalier_fibre(
                    p, fname, content, op_id,
                    ajoutes, modifies, migrations, modif_vendeurs,
                    erreurs, resume,
                )
            else:
                _import_placeholder(p, fname, label, erreurs, resume)
        except Exception as e:
            erreurs.append({"Fichier": fname, "Erreur": str(e)})
            resume.nb_erreurs += 1

    # Cleanup payloads
    for row in ajoutes:
        row.pop("_payload_create", None)

    res = ImportSfrResult(
        ok=True, type_import=p.type_import, type_label=label,
        simulation=p.simulation, resume=resume,
        fichiers_traites=fichiers_traites,
        contrats_ajoutes=ajoutes,
        contrats_modifies=modifies,
        contrats_non_trouves=non_trouves,
        contrats_migrations=migrations,
        modif_vendeurs=modif_vendeurs,
        erreurs=erreurs,
        message=(
            f"{len(files)} fichier(s) | "
            f"Ajoutés {resume.nb_ajoutes} | Modifiés {resume.nb_modifies} | "
            f"Migr. FTTB->FTTH {resume.nb_migrations} | "
            f"Modif vend. {resume.nb_modif_vend} | "
            f"Non modifiés {resume.nb_non_modifies} | "
            f"Erreurs {resume.nb_erreurs}. "
            + ("(SIMULATION)" if p.simulation else "(PRODUCTION)")
        ),
    )
    _attach_xlsx_and_mail_sfr(res, op_id)
    return res


def _build_xlsx_sfr(res: ImportSfrResult) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = Workbook(); ws = wb.active; ws.title = "Résumé"
    header_fill = PatternFill("solid", fgColor="17494E")
    header_font = Font(bold=True, color="FFFFFF")
    items = [
        ("NB Fichiers", res.resume.nb_fichiers),
        ("NB Ajoutés", res.resume.nb_ajoutes),
        ("NB Modifiés", res.resume.nb_modifies),
        ("NB Modif vendeurs", res.resume.nb_modif_vend),
        ("NB Migrations FTTB→FTTH", res.resume.nb_migrations),
        ("NB Non modifiés", res.resume.nb_non_modifies),
        ("NB Erreurs", res.resume.nb_erreurs),
        ("NB Introuvables", res.resume.nb_introuvables),
        ("NB Doublons", res.resume.nb_doublons),
        ("NB Hors délai", res.resume.nb_hors_delai),
    ]
    ws.append(["Indicateur", "Nombre"])
    for c in ws[1]:
        c.font = header_font; c.fill = header_fill
        c.alignment = Alignment(horizontal="center")
    for lbl, n in items:
        ws.append([lbl, n])
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 12

    for title, rows in [
        ("Ajoutés", res.contrats_ajoutes),
        ("Modifiés", res.contrats_modifies),
        ("Migrations FTTB-FTTH", res.contrats_migrations),
        ("Modif Vendeurs", res.modif_vendeurs),
        ("Erreurs", res.erreurs),
    ]:
        if not rows:
            continue
        sh = wb.create_sheet(title=title[:31])
        keys = list(rows[0].keys())
        sh.append(keys)
        for c in sh[1]:
            c.font = header_font; c.fill = header_fill
            c.alignment = Alignment(horizontal="center", wrap_text=True)
        for r in rows:
            sh.append([str(r.get(k, "")) if r.get(k) is not None else "" for k in keys])
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return buf.read()


def _attach_xlsx_and_mail_sfr(res: ImportSfrResult, op_id: int) -> None:
    from app.shared.notifications.mail import envoi_mail
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = "_SIMU" if res.simulation else ""
    prefix_map = {
        1: "ImportSFRFibre", 2: "ImportSFRMobile", 3: "ImportSFRCall",
        4: "ImportSFRHebdo", 5: "ImportSFROptions", 6: "ImportSFRRun",
        7: "ImportSFRCallRetKO", 8: "ImportSFRCallRetRacc",
        9: "ImportSFRCallRetVADD", 10: "ImportSFRCallRetRDVTech",
    }
    xlsx_name = f"{prefix_map.get(res.type_import, 'ImportSFR')}_{ts}{suffix}.xlsx"
    try:
        xlsx_bytes = _build_xlsx_sfr(res)
    except Exception:
        return
    res.xlsx_name = xlsx_name
    res.xlsx_b64 = base64.b64encode(xlsx_bytes).decode("ascii")

    try:
        db = get_pg_connection("rh")
        r = db.query_one(
            "SELECT mail FROM rh.pgt_salarie_coordonnees WHERE id_salarie = ? LIMIT 1",
            (int(op_id),),
        )
        op_mail = (r.get("mail") if r else "") or ""
    except Exception:
        op_mail = ""
    destinataires = [op_mail] if op_mail else ["intranet@omaya.fr"]
    cc = ["intranet@omaya.fr"] if op_mail and op_mail != "intranet@omaya.fr" else []

    sujet_pref = "SIMULATION : " if res.simulation else ""
    sujet = (f"{sujet_pref}Importation {res.type_label} SFR "
             f"du {date.today().strftime('%d/%m/%Y')}")
    html = (
        "<p>Bonjour,</p>"
        f"<p>Fin importation le : {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>"
        f"<p><strong>{res.message}</strong></p>"
        "<p>Service Importation EXOSPHERE</p>"
    )
    try:
        res.mail_envoye = envoi_mail(
            sujet=sujet, html=html,
            destinataires=destinataires, cc=cc,
            expediteur="intranet@omaya.fr",
            attachments=[(xlsx_name, xlsx_bytes)],
        )
    except Exception:
        res.mail_envoye = False
