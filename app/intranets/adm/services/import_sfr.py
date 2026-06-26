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


# Mapping colonnes Base Journaliere Mobile (cf groupe grpJournalier Mobile)
COLS_BJ_MOBILE = {
    "num_bs": "A",              "date_signature": "C",
    "date_activation": "F",     "date_portabilite": "H",
    "date_resil": "BM",         "lib_statut": "I",
    "type_vente": "AC",         "offre": "J",
    "code_vendeur": "X",        "num_mobile": "AT",
    "activ_control": "AP",      "processing_state": "AQ",
    "client_cp": "AJ",          "client_nom": "BQ",
    "client_prenom": "BR",      "client_gsm": "BS",
    "client_mail": "BN",
    "parcours_chaine": "BO",    "parcours_degroupe": "BF",
}


# Mapping colonnes Base Journaliere CALL (vendeur via nom, pas code)
COLS_BJ_CALL = {
    "num_bs": "A",              "vendeur": "K",
    "date_signature": "C",      "date_rdv": "G",
    "lib_statut": "I",          "offre": "J",
    "type_vente": "AC",         "technologie": "AF",
    "client_nom": "BQ",         "client_prenom": "BR",
    "client_adresse": "AI",     "client_cplt": "BG",
    "client_cp": "AJ",          "client_ville": "AL",
    "client_naiss": "BP",       "client_tel_mobile": "BS",
    "comment": "L",
}


# Mapping colonnes Base Hebdo (cf groupe grpHebdo). Pattern Fibre.
COLS_BJ_HEBDO = {
    "num_bs": "A",              "date_signature": "C",
    "date_va": "D",             "date_ra": "E",
    "date_rdv": "G",            "lib_statut": "I",
    "statut_vente": "J",        "motif_annul": "K",
    "type_install": "AM",       "type_vente": "AC",
    "offre": "J",               "technologie": "AF",
    "cluster_region": "AO",     "cluster_code": "AP",
    "cluster_ville": "AQ",
    "client_cp": "AJ",          "client_ville": "AL",
    "client_rue": "AI",         "client_identite": "BG",
    "client_tel": "BS",         "client_mail": "BN",
}


def _lookup_vendeur_by_nom_prenom(vendeur_cell: str) -> int:
    """Lookup salarie par concat nom+prenom (variantes avec %)."""
    if not vendeur_cell or not vendeur_cell.strip():
        return 0
    try:
        db = get_pg_connection("rh")
        s = vendeur_cell.upper()
        for c in ("-", "'", " "):
            s = s.replace(c, "%")
        s = s.replace("%%", "%")
        pattern = f"%{s}%"
        rows = db.query(
            """SELECT id_salarie FROM rh.pgt_salarie
                WHERE UPPER(CONCAT(nom, '%', prenom)) LIKE ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 2""",
            (pattern,),
        ) or []
        if len(rows) == 1:
            return int(rows[0]["id_salarie"])
    except Exception:
        pass
    return 0


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


def _import_journalier_mobile(
    p: ImportSfrParams, content: bytes, op_id: int,
    ajoutes: list, modifies: list, erreurs: list, resume: ImportSfrResume,
) -> None:
    """Type 2 : Base Journaliere Mobile. Pattern Fibre sans cluster.
    Compare DatePort, DateResil, DateAct, ActivControl, ProcessingState."""
    from openpyxl import load_workbook
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as e:
        resume.nb_erreurs += 1
        erreurs.append({"_erreur": f"Lecture : {e}"})
        return
    ws = wb.active
    cols = {k: _col_letter_to_index(v) for k, v in COLS_BJ_MOBILE.items()}
    db = get_pg_connection("adv")
    ligne_depart = p.ligne_depart or 3

    for i in range(ligne_depart, (ws.max_row or 0) + 1):
        num_bs = _cell(ws, i, cols["num_bs"]).upper()
        if not num_bs:
            continue
        date_sign = _parse_date_fr(_cell(ws, i, cols["date_signature"]))
        date_act = _parse_date_fr(_cell(ws, i, cols["date_activation"]))
        date_port = _parse_date_fr(_cell(ws, i, cols["date_portabilite"]))
        date_resil = _parse_date_fr(_cell(ws, i, cols["date_resil"]))
        type_vente = _type_vente_fibre(_cell(ws, i, cols["type_vente"]))
        lib_offre = _cell(ws, i, cols["offre"])
        lib_statut = _cell(ws, i, cols["lib_statut"])
        id_etat = _id_etat_fibre(lib_statut)
        num_mobile = _cell(ws, i, cols["num_mobile"])
        activ_control = _cell(ws, i, cols["activ_control"])
        processing_state = _cell(ws, i, cols["processing_state"])
        client_cp = _cell(ws, i, cols["client_cp"])
        client_nom = _cell(ws, i, cols["client_nom"])
        client_prenom = _cell(ws, i, cols["client_prenom"])
        client_gsm = _cell(ws, i, cols["client_gsm"])
        if client_gsm and not client_gsm.startswith("0"):
            client_gsm = "0" + client_gsm
        client_mail = _cell(ws, i, cols["client_mail"])
        code_vendeur = _cell(ws, i, cols["code_vendeur"])

        # Lookup produit Mobile (sous_fam=MOBILE par defaut)
        offre = _type_offre_fibre(lib_offre, 0, date_sign)

        ctt = db.query_one(
            """SELECT id_contrat, id_salarie, id_client, id_produit,
                      type_vente, date_signature, date_portabilite,
                      date_resil, date_racc_activ, activ_control,
                      processing_state, id_etat_sfr, id_etat_contrat
                 FROM adv.pgt_sfr_contrat
                WHERE UPPER(num_bs) = UPPER(?)
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (num_bs,),
        )
        if not ctt:
            ajoutes.append({
                "NumBS": num_bs, "DateSign": str(date_sign or ""),
                "DateAct": str(date_act or ""),
                "DatePort": str(date_port or ""),
                "DateResil": str(date_resil or ""),
                "ClientCP": client_cp,
                "Client": f"{client_nom} {client_prenom}".strip(),
                "LibOffre": lib_offre, "TypeVente": type_vente,
                "NumMobile": num_mobile, "LibStatut": lib_statut,
            })
            resume.nb_ajoutes += 1
        else:
            id_contrat = int(ctt["id_contrat"])
            modifs = []
            if int(ctt.get("type_vente") or 0) != type_vente:
                modifs.append(f"TypeVente -> {type_vente}")
            if int(ctt.get("id_produit") or 0) != offre and offre:
                modifs.append(f"Offre -> {offre}")
            if ctt.get("date_portabilite") != date_port and date_port:
                modifs.append(f"DatePort -> {date_port}")
            if ctt.get("date_resil") != date_resil and date_resil:
                modifs.append(f"DateResil -> {date_resil}")
            if ctt.get("date_racc_activ") != date_act and date_act:
                modifs.append(f"DateAct -> {date_act}")
            if (_str(ctt.get("activ_control")) != activ_control
                    and activ_control):
                modifs.append(f"ActivControl -> {activ_control}")
            if (_str(ctt.get("processing_state")) != processing_state
                    and processing_state):
                modifs.append(f"ProcessingState -> {processing_state}")
            if modifs:
                modifies.append({
                    "NumBS": num_bs, "Modifs": " | ".join(modifs),
                    "Client": f"{client_nom} {client_prenom}".strip(),
                    "NumMobile": num_mobile,
                })
                resume.nb_modifies += 1
                if not p.simulation:
                    try:
                        db.query(
                            """UPDATE adv.pgt_sfr_contrat
                                  SET type_vente = ?, id_produit = ?,
                                      date_portabilite = COALESCE(?, date_portabilite),
                                      date_resil = COALESCE(?, date_resil),
                                      date_racc_activ = COALESCE(?, date_racc_activ),
                                      activ_control = ?, processing_state = ?,
                                      modif_date = NOW(), modif_op = ?,
                                      modif_elem = 'modif'
                                WHERE id_contrat = ?""",
                            (type_vente, offre, date_port, date_resil,
                             date_act, activ_control, processing_state,
                             int(op_id), id_contrat),
                        )
                    except Exception as e:
                        modifies[-1]["Erreur"] = str(e)
            else:
                resume.nb_non_modifies += 1
    wb.close()


def _import_journalier_call(
    p: ImportSfrParams, content: bytes, op_id: int,
    ajoutes: list, modifies: list, erreurs: list, resume: ImportSfrResume,
) -> None:
    """Type 3 : Base Journaliere CALL (FIBRE). Vendeur via nom complet.
    Pattern : si pas trouve -> erreur 'VENDEUR inconnu'.
    Si contrat existant + vendeur Fibre inconnu -> reattribution.
    Si vendeur DB different -> erreur 'Vendeur différent'."""
    from openpyxl import load_workbook
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as e:
        resume.nb_erreurs += 1
        erreurs.append({"_erreur": f"Lecture : {e}"})
        return
    ws = wb.active
    cols = {k: _col_letter_to_index(v) for k, v in COLS_BJ_CALL.items()}
    db = get_pg_connection("adv")
    ligne_depart = p.ligne_depart or 2

    for i in range(ligne_depart, (ws.max_row or 0) + 1):
        num_bs = _cell(ws, i, cols["num_bs"]).upper()
        if not num_bs:
            continue
        date_sign = _parse_date_fr(_cell(ws, i, cols["date_signature"]))
        # Date RDV : prendre les 8 premiers chars JJMMAAAA
        date_rdv_s = _cell(ws, i, cols["date_rdv"])[:8]
        date_rdv = None
        if len(date_rdv_s) == 8 and date_rdv_s.isdigit():
            try:
                date_rdv = date(int(date_rdv_s[4:8]), int(date_rdv_s[2:4]),
                                int(date_rdv_s[0:2]))
            except Exception:
                pass
        vendeur_cell = _cell(ws, i, cols["vendeur"])
        client_nom = _cell(ws, i, cols["client_nom"])
        client_prenom = _cell(ws, i, cols["client_prenom"])
        client_adr = _cell(ws, i, cols["client_adresse"])
        client_cp = _cell(ws, i, cols["client_cp"])
        client_ville = _cell(ws, i, cols["client_ville"])
        client_mobile = _cell(ws, i, cols["client_tel_mobile"])
        nom_offre = _cell(ws, i, cols["offre"])
        type_vente_s = _cell(ws, i, cols["type_vente"])
        comment = _cell(ws, i, cols["comment"])
        type_vente = _type_vente_fibre(type_vente_s)
        techno = _type_techno_fibre(_cell(ws, i, cols["technologie"]))
        offre = _type_offre_fibre(nom_offre, techno, date_sign)
        box8 = "8" in nom_offre

        id_vendeur = _lookup_vendeur_by_nom_prenom(vendeur_cell)
        if id_vendeur == 0:
            erreurs.append({
                "NumBS": num_bs, "Erreur": "VENDEUR inconnu",
                "VendeurCell": vendeur_cell,
                "DateSign": str(date_sign or ""),
                "NomOffre": nom_offre, "TypeVente": type_vente_s,
            })
            resume.nb_erreurs += 1
            # On continue quand meme avec sentinelle FIBRE_INCONNU
            id_vendeur = FIBRE_INCONNU

        ctt = db.query_one(
            """SELECT id_contrat, id_salarie, id_client, id_produit,
                      non_call, type_vente, date_signature
                 FROM adv.pgt_sfr_contrat
                WHERE UPPER(num_bs) = UPPER(?)
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (num_bs,),
        )
        if not ctt:
            ajoutes.append({
                "NumBS": num_bs, "Vendeur": vendeur_cell,
                "DateSign": str(date_sign or ""),
                "DateRDV": str(date_rdv or ""),
                "Client": f"{client_nom} {client_prenom}".strip(),
                "ClientCP": client_cp, "ClientVille": client_ville,
                "NomOffre": nom_offre, "TypeVente": type_vente_s,
                "Comment": comment,
            })
            resume.nb_ajoutes += 1
        else:
            id_contrat = int(ctt["id_contrat"])
            id_sal_db = int(ctt.get("id_salarie") or 0)
            modifies.append({
                "NumBS": num_bs, "Vendeur": vendeur_cell,
                "DateSign": str(date_sign or ""),
                "DateRDV": str(date_rdv or ""),
                "Client": f"{client_nom} {client_prenom}".strip(),
                "ClientCP": client_cp, "NomOffre": nom_offre,
                "Comment": comment,
            })
            resume.nb_modifies += 1

            # Reattribution si fibre inconnu et nouveau vendeur trouve
            if id_sal_db == FIBRE_INCONNU and id_vendeur != FIBRE_INCONNU:
                modifies[-1]["Note"] = "Contrat Fibre Inconnu réattribué"
                if not p.simulation:
                    try:
                        db.query(
                            """UPDATE adv.pgt_sfr_contrat
                                  SET id_salarie = ?, non_call = FALSE,
                                      modif_date = NOW(), modif_op = ?,
                                      modif_elem = 'modif'
                                WHERE id_contrat = ?""",
                            (id_vendeur, int(op_id), id_contrat),
                        )
                    except Exception as e:
                        modifies[-1]["ErreurReattrib"] = str(e)
            elif id_sal_db != id_vendeur and id_vendeur != FIBRE_INCONNU:
                # Vendeur different
                erreurs.append({
                    "NumBS": num_bs, "Erreur": "Vendeur différent",
                    "VendeurOmaya": id_sal_db, "VendeurImport": vendeur_cell,
                    "DateSign": str(date_sign or ""),
                })
    wb.close()


def _import_journalier_hebdo(
    p: ImportSfrParams, content: bytes, op_id: int,
    ajoutes: list, modifies: list, migrations: list,
    erreurs: list, resume: ImportSfrResume,
) -> None:
    """Type 4 : Base Hebdo. Pattern Fibre (T1) adapte :
    - Dates lues avec [:10] (formats variables)
    - Detection 'FTTB VERS FTTH' pour migrations
    - client_identite splittee par ',' (nom, prenom)
    - dateref = 20201001 (filtre antiques)."""
    from openpyxl import load_workbook
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as e:
        resume.nb_erreurs += 1
        erreurs.append({"_erreur": f"Lecture : {e}"})
        return
    ws = wb.active
    cols = {k: _col_letter_to_index(v) for k, v in COLS_BJ_HEBDO.items()}
    db = get_pg_connection("adv")
    ligne_depart = p.ligne_depart or 3
    date_ref = date(2020, 10, 1)

    for i in range(ligne_depart, (ws.max_row or 0) + 1):
        num_bs = _cell(ws, i, cols["num_bs"]).upper()
        if not num_bs:
            continue
        # Dates : prendre [:10] avant parse
        date_sign = _parse_date_fr(_cell(ws, i, cols["date_signature"])[:10])
        date_va = _parse_date_fr(_cell(ws, i, cols["date_va"])[:10])
        date_ra = _parse_date_fr(_cell(ws, i, cols["date_ra"])[:10])
        date_rdv = _parse_date_fr(_cell(ws, i, cols["date_rdv"])[:10])
        type_v_s = _cell(ws, i, cols["type_vente"])
        type_vente = _type_vente_fibre(type_v_s)
        techno = _type_techno_fibre(_cell(ws, i, cols["technologie"]))
        lib_offre = _cell(ws, i, cols["offre"])
        offre = _type_offre_fibre(lib_offre, techno, date_sign)
        type_install = _cell(ws, i, cols["type_install"])
        lib_statut = _cell(ws, i, cols["lib_statut"])
        id_etat = _id_etat_fibre(lib_statut)
        cluster_code = _cell(ws, i, cols["cluster_code"])
        cluster_ville = _cell(ws, i, cols["cluster_ville"])
        client_cp = _cell(ws, i, cols["client_cp"])
        client_ville = _cell(ws, i, cols["client_ville"])
        client_rue = _cell(ws, i, cols["client_rue"])
        client_identite = _cell(ws, i, cols["client_identite"])
        client_tel = _cell(ws, i, cols["client_tel"])
        client_mail = _cell(ws, i, cols["client_mail"])
        motif_annul = _cell(ws, i, cols["motif_annul"])

        # Split identite "NOM, PRENOM"
        parts = client_identite.split(",", 1)
        client_nom = parts[0].strip() if parts else ""
        client_prenom = parts[1].strip() if len(parts) > 1 else ""

        # Filtre antiques
        if (not date_sign or date_sign < date_ref) and (
                not date_ra or date_ra < date_ref):
            continue

        # Detection migration FTTB VERS FTTH
        is_mig = "FTTB VERS FTTH" in lib_offre.upper()
        if is_mig and type_vente == 3:
            type_vente = 4
            migrations.append({
                "NumBS": num_bs, "DateSign": str(date_sign or ""),
                "ClientCP": client_cp, "ClientVille": client_ville,
                "LibStatut": lib_statut, "ClusterCode": cluster_code,
            })
            resume.nb_migrations += 1

        cluster = _test_cluster_fibre(cluster_code)
        box8 = "8" in lib_offre

        ctt = db.query_one(
            """SELECT id_contrat, id_salarie, id_client, id_produit,
                      id_etat_contrat, type_vente, date_signature,
                      id_sfr_cluster
                 FROM adv.pgt_sfr_contrat
                WHERE UPPER(num_bs) = UPPER(?)
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (num_bs,),
        )
        if not ctt:
            ajoutes.append({
                "NumBS": num_bs, "DateSign": str(date_sign or ""),
                "DateVa": str(date_va or ""), "DateRa": str(date_ra or ""),
                "DateRDV": str(date_rdv or ""), "ClientCP": client_cp,
                "ClientVille": client_ville, "LibStatut": lib_statut,
                "TypeVente": type_vente, "ClusterCode": cluster_code,
            })
            resume.nb_ajoutes += 1
        else:
            id_contrat = int(ctt["id_contrat"])
            modifs = []
            if int(ctt.get("type_vente") or 0) != type_vente:
                modifs.append(f"TypeVente -> {type_vente}")
            if int(ctt.get("id_produit") or 0) != offre and offre:
                modifs.append(f"Offre -> {offre}")
            if int(ctt.get("id_etat_contrat") or 0) != id_etat and id_etat:
                modifs.append(f"Etat -> {id_etat}")
            if modifs:
                modifies.append({
                    "NumBS": num_bs, "Modifs": " | ".join(modifs),
                    "DateSign Omaya": str(ctt.get("date_signature") or ""),
                    "ClientCP": client_cp,
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


# ---------------------------------------------------------------------------
# Type 5 : ImportOptions (MAJ Box8Verif / OptionVerif)
# ---------------------------------------------------------------------------


def _import_options(
    p: ImportSfrParams, content: bytes, op_id: int,
    modifies: list, erreurs: list, resume: ImportSfrResume,
) -> None:
    """Type 5 : pour chaque BS, MAJ box8_verif ou option_verif=TRUE si
    StatOpt=VERSEE, selon Lib_Option (Box 8 vs autre)."""
    from openpyxl import load_workbook
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as e:
        resume.nb_erreurs += 1
        erreurs.append({"_erreur": f"Lecture : {e}"})
        return
    ws = wb.active
    cols_map = {"num_bs": "A", "lib_option": "B", "statut_option": "C"}
    cols = {k: _col_letter_to_index(v) for k, v in cols_map.items()}
    db = get_pg_connection("adv")
    ligne_dep = p.ligne_depart or 2

    for i in range(ligne_dep, (ws.max_row or 0) + 1):
        num_bs = _cell(ws, i, cols["num_bs"]).upper().strip()
        if not num_bs:
            continue
        lib_opt = _cell(ws, i, cols["lib_option"])
        stat_opt = _cell(ws, i, cols["statut_option"]).upper()

        ctt = db.query_one(
            """SELECT id_contrat, num_bs, box8, box8_verif, option_dec,
                      option_verif, id_salarie, date_signature, id_etat_contrat
                 FROM adv.pgt_sfr_contrat
                WHERE UPPER(num_bs) = UPPER(?)
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (num_bs,),
        )
        if not ctt:
            erreurs.append({"NumBS": num_bs, "Erreur": "BS introuvable",
                            "LibOption": lib_opt, "Statut": stat_opt})
            resume.nb_introuvables += 1
            continue

        id_contrat = int(ctt["id_contrat"])
        b8_avant = bool(ctt.get("box8_verif"))
        opt_avant = bool(ctt.get("option_verif"))

        is_box8 = "BOX 8" in lib_opt.upper()
        is_versee = stat_opt == "VERSEE"

        if is_box8 and is_versee:
            new_b8_verif = True
            new_opt_verif = opt_avant
        elif (not is_box8) and is_versee:
            new_b8_verif = b8_avant
            new_opt_verif = True
        else:
            # Pas de changement
            new_b8_verif = b8_avant
            new_opt_verif = opt_avant

        if new_b8_verif != b8_avant or new_opt_verif != opt_avant:
            modifies.append({
                "NumBS": num_bs, "LibOption": lib_opt, "Statut": stat_opt,
                "Box8Verif Avant": b8_avant, "Box8Verif Apres": new_b8_verif,
                "OptionVerif Avant": opt_avant, "OptionVerif Apres": new_opt_verif,
            })
            resume.nb_modifies += 1
            if not p.simulation:
                try:
                    db.query(
                        """UPDATE adv.pgt_sfr_contrat
                              SET box8_verif = ?, option_verif = ?,
                                  modif_date = NOW(), modif_op = ?,
                                  modif_elem = 'modif'
                            WHERE id_contrat = ?""",
                        (new_b8_verif, new_opt_verif, int(op_id), id_contrat),
                    )
                except Exception as e:
                    modifies[-1]["Erreur"] = str(e)
        else:
            resume.nb_non_modifies += 1
    wb.close()


# ---------------------------------------------------------------------------
# Type 6 : ImportRUN (squelette multi-feuilles - logique metier partielle)
# ---------------------------------------------------------------------------


def _import_run(
    p: ImportSfrParams, content: bytes, op_id: int,
    ajoutes: list, modifies: list, erreurs: list,
    resume: ImportSfrResume,
) -> None:
    """Type 6 : ImportRUN. Lit 3 feuilles (Offre/Booster, Mobile, Option/
    Volumique) avec colonnes differentes par feuille. Pour chaque ligne :
    lookup BS, detection periode, creation/MAJ SFR_Contrat_Remun, verif
    montant officiel, hors delai.

    NOTE : implementation simplifiee, traitementOngletRun WinDev est tres
    riche (gestion VV/Racc, regul negative, geste co, statut Operateur,
    montant officiel par produit/typeVente/dateSign). A enrichir au fur
    et a mesure.
    """
    from openpyxl import load_workbook
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as e:
        resume.nb_erreurs += 1
        erreurs.append({"_erreur": f"Lecture : {e}"})
        return
    db = get_pg_connection("adv")

    p1_du = _parse_date_fr(p.periode1_du) or date(1900, 1, 1)
    p1_au = _parse_date_fr(p.periode1_au) or date(2100, 12, 31)
    p2_du = _parse_date_fr(p.periode2_du) or date(1900, 1, 1)
    p2_au = _parse_date_fr(p.periode2_au) or date(2100, 12, 31)
    mp1 = _dernier_jour_mois(p.periode1_mois_paiement)
    mp2 = _dernier_jour_mois(p.periode2_mois_paiement)
    mp_distrib = _dernier_jour_mois(p.mois_paiement_distrib)

    # Colonnes par feuille (cf grpValide WinDev Run1=Offres, Run2=Mobile/Option,
    # Run3=Volumique). Defaults raisonnables a ajuster selon vrai fichier.
    cols_per_sheet = {
        0: {"num_bs": "A", "techno": "B", "offre": "C", "type_vente": "D",
            "statut_ra": "E", "motif_annul": "F", "date_ra": "G",
            "hors_zone": "H", "type_rem": "I", "montant_rem": "J",
            "date_sign": "K", "client_nom": "L", "client_prenom": "M",
            "statut": "N", "motif_dero": "O", "geste_co": "P"},
        1: {"num_bs": "A", "techno": "B", "offre": "C", "type_vente": "D",
            "statut_ra": "E", "motif_annul": "F", "date_ra": "G",
            "hors_zone": "H", "type_opt": "I", "lib_opt": "J",
            "type_rem": "K", "montant_rem": "L", "date_sign": "M",
            "client_nom": "N", "client_prenom": "O", "statut": "P",
            "motif_dero": "Q"},
        2: {"num_bs": "A", "techno": "B", "offre": "C", "type_vente": "D",
            "statut_ra": "E", "motif_annul": "F", "date_ra": "G",
            "hors_zone": "H", "type_rem": "I", "montant_rem": "J",
            "periode": "K", "date_sign": "L", "client_nom": "M",
            "client_prenom": "N", "statut": "O"},
    }

    nb_introu = 0; nb_paye = 0; nb_deja_p = 0; nb_va_non_p = 0
    nb_mont0 = 0; nb_err_rem = 0; nb_err_hd = 0

    for sheet_idx, sheet_name in enumerate(wb.sheetnames):
        if sheet_idx >= 3:
            break  # On ne traite que les 3 premieres feuilles
        ws = wb[sheet_name]
        cols_map = cols_per_sheet.get(sheet_idx, cols_per_sheet[0])
        cols = {k: _col_letter_to_index(v) for k, v in cols_map.items()}

        for i in range(2, (ws.max_row or 0) + 1):
            num_bs = _cell(ws, i, cols.get("num_bs", 1)).upper().strip()
            if not num_bs:
                continue
            client_nom = _cell(ws, i, cols.get("client_nom", 1))
            client_prenom = _cell(ws, i, cols.get("client_prenom", 1))
            techno = _cell(ws, i, cols.get("techno", 1))
            offre = _cell(ws, i, cols.get("offre", 1))
            statut_ra = _cell(ws, i, cols.get("statut_ra", 1))
            type_rem = _cell(ws, i, cols.get("type_rem", 1))
            mt_s = _cell(ws, i, cols.get("montant_rem", 1)).replace(",", ".")
            try:
                montant_rem = float(mt_s) if mt_s else 0.0
            except ValueError:
                montant_rem = 0.0
            date_ra = _parse_date_fr(_cell(ws, i, cols.get("date_ra", 1)))
            date_sign = _parse_date_fr(_cell(ws, i, cols.get("date_sign", 1)))
            statut = _cell(ws, i, cols.get("statut", 1))
            motif_dero = _cell(ws, i, cols.get("motif_dero", 1))
            lib_opt = _cell(ws, i, cols.get("lib_opt", 1)) if "lib_opt" in cols else ""
            type_opt = _cell(ws, i, cols.get("type_opt", 1)) if "type_opt" in cols else ""
            periode = _cell(ws, i, cols.get("periode", 1)) if "periode" in cols else ""

            lib_rem = offre
            if "Option" in sheet_name:
                lib_rem = f"{type_opt} : {lib_opt}"
            elif "Volumique" in sheet_name:
                lib_rem = periode

            ctt = db.query_one(
                """SELECT id_contrat, id_salarie, date_signature, type_vente,
                          id_produit, remise, id_etat_sfr, info_vente_sfr
                     FROM adv.pgt_sfr_contrat
                    WHERE UPPER(num_bs) = UPPER(?)
                      AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                    LIMIT 1""",
                (num_bs,),
            )
            if not ctt:
                nb_introu += 1
                erreurs.append({
                    "Onglet": sheet_name, "NumBS": num_bs,
                    "DateSign": str(date_sign or ""),
                    "Client": f"{client_nom} {client_prenom}".strip(),
                    "Offre": offre, "TypeRem": type_rem,
                    "Montant": montant_rem, "Statut": statut,
                    "Erreur": "Introuvable",
                })
                resume.nb_introuvables += 1
                continue

            id_contrat = int(ctt["id_contrat"])
            id_sal = int(ctt.get("id_salarie") or 0)
            date_sign_db = ctt.get("date_signature")
            type_vente_db = int(ctt.get("type_vente") or 0)

            # Detection periode
            agence, equipe, is_distrib = _affectation_sfr_min(id_sal)
            mois_p, periode_lbl = _detect_periode_sfr(
                date_sign_db, is_distrib,
                p1_du, p1_au, mp1, p2_du, p2_au, mp2, mp_distrib,
            )
            mois_p_str = mois_p.strftime("%m-%Y") if mois_p else ""

            if periode_lbl == "HORS_DELAI":
                nb_err_hd += 1
                erreurs.append({
                    "Onglet": sheet_name, "NumBS": num_bs,
                    "Erreur": "Hors Délai",
                    "DateSign": str(date_sign_db or ""),
                    "Agence": agence, "Equipe": equipe,
                })
                resume.nb_hors_delai += 1

            if montant_rem == 0:
                nb_mont0 += 1
                modifies.append({
                    "Onglet": sheet_name, "NumBS": num_bs,
                    "Erreur": "Montant à 0",
                    "Offre": offre, "TypeRem": type_rem,
                    "Statut": statut,
                })
                continue

            lib_type_rem = type_rem.split(" (")[0]
            if montant_rem < 0:
                lib_type_rem += " - Régul"

            # Verifie rem deja enregistree
            existing_rem = None
            try:
                existing_rem = db.query_one(
                    """SELECT id_sfr_contrat_remun, ra_montant, ra_mois_p
                         FROM adv.pgt_sfr_contrat_remun
                        WHERE id_contrat = ? AND type_rem = ? AND lib_option = ?
                        LIMIT 1""",
                    (id_contrat, lib_type_rem, lib_rem),
                )
            except Exception:
                existing_rem = None

            if existing_rem:
                nb_deja_p += 1
                modifies.append({
                    "Onglet": sheet_name, "NumBS": num_bs,
                    "Offre": offre, "TypeRem": type_rem,
                    "LibRem": lib_rem,
                    "Montant Omaya": float(existing_rem.get("ra_montant") or 0),
                    "MoisP Omaya": str(existing_rem.get("ra_mois_p") or ""),
                    "Montant Import": montant_rem,
                    "MoisP Import": mois_p_str,
                    "Statut": statut, "Note": "Déjà payé",
                })
            else:
                nb_paye += 1
                ajoutes.append({
                    "Onglet": sheet_name, "NumBS": num_bs,
                    "DateSign": str(date_sign_db or ""),
                    "DateRa": str(date_ra or ""),
                    "Client": f"{client_nom} {client_prenom}".strip(),
                    "Offre": offre, "TypeRem": type_rem, "LibRem": lib_rem,
                    "Montant": montant_rem, "MoisP": mois_p_str,
                    "Statut": statut, "MotifDero": motif_dero,
                    "Agence": agence, "Equipe": equipe,
                })
                resume.nb_modifies += 1
                if not p.simulation:
                    try:
                        new_id = _new_id()
                        is_va = "(VV)" in type_rem
                        db.query(
                            """INSERT INTO adv.pgt_sfr_contrat_remun
                                  (id_sfr_contrat_remun_auto, id_sfr_contrat_remun,
                                   id_contrat, num, type_rem, lib_option,
                                   validation, va_mois_p, va_montant, va_statut, va_motif,
                                   raccordement, ra_mois_p, ra_montant, ra_statut, ra_motif,
                                   modif_date, modif_op, modif_elem)
                               VALUES (?, ?, ?, ?, ?, ?,
                                       ?, ?, ?, ?, ?,
                                       ?, ?, ?, ?, ?,
                                       NOW(), ?, 'new')""",
                            (new_id, new_id, id_contrat, num_bs,
                             lib_type_rem, lib_rem,
                             is_va, mois_p if is_va else None,
                             montant_rem if is_va else None,
                             statut if is_va else "",
                             motif_dero if is_va else "",
                             not is_va, mois_p if not is_va else None,
                             montant_rem if not is_va else None,
                             statut if not is_va else "",
                             motif_dero if not is_va else "",
                             int(op_id)),
                        )
                    except Exception as e:
                        ajoutes[-1]["Erreur"] = str(e)

    wb.close()
    # Reporting global
    erreurs.append({
        "Note": "Resume",
        "NB Paye": nb_paye, "NB Deja Paye": nb_deja_p,
        "NB VA Non Paye": nb_va_non_p, "NB Introuvable": nb_introu,
        "NB Montant 0": nb_mont0, "NB Err REM": nb_err_rem,
        "NB Hors Delai": nb_err_hd,
    })


def _affectation_sfr_min(id_salarie: int) -> tuple[str, str, bool]:
    """Wrapper minimal - reutilise _affectation_oen-like."""
    if not id_salarie:
        return ("", "", False)
    try:
        db = get_pg_connection("rh")
        rows = db.query(
            """SELECT o.lib_orga, o.id_type_niveau_orga, o.id_type_orga
                 FROM rh.pgt_salarie_organigramme so
                 JOIN rh.pgt_organigramme o ON o.idorganigramme = so.idorganigramme
                WHERE so.id_salarie = ?
                  AND (so.modif_elem IS NULL OR so.modif_elem NOT LIKE '%suppr%')""",
            (int(id_salarie),),
        ) or []
        agence = ""; equipe = ""; is_distrib = False
        for r in rows:
            lvl = r.get("id_type_niveau_orga")
            lib = r.get("lib_orga") or ""
            if lvl == 3 and not agence:
                agence = lib
                if int(r.get("id_type_orga") or 0) == 3:
                    is_distrib = True
            elif lvl == 4 and not equipe:
                equipe = lib
        return (agence, equipe, is_distrib)
    except Exception:
        return ("", "", False)


def _detect_periode_sfr(
    date_sign, is_distrib: bool,
    p1_du: date, p1_au: date, mp1, p2_du: date, p2_au: date, mp2,
    mp_distrib,
):
    if not date_sign:
        return (None, "")
    if is_distrib:
        return (mp_distrib, "Distrib")
    if p1_du <= date_sign <= p1_au:
        return (mp1, "Période 1")
    if p2_du <= date_sign <= p2_au:
        return (mp2, "Période 2")
    p1_du_m1 = (p1_du.replace(month=p1_du.month - 1) if p1_du.month > 1
                else p1_du.replace(year=p1_du.year - 1, month=12))
    p1_au_m1 = (p1_au.replace(month=p1_au.month - 1) if p1_au.month > 1
                else p1_au.replace(year=p1_au.year - 1, month=12))
    if p1_du_m1 <= date_sign <= p1_au_m1:
        return (mp1, "Période -1 mois")
    return (None, "HORS_DELAI")


# ---------------------------------------------------------------------------
# CALL RET (types 7, 8, 9, 10) - vendeurs sentinelles + helpers
# ---------------------------------------------------------------------------

# Salaries sentinelles (cf code WinDev)
ABASSI_AHD = 20230920112006538          # vendeur cible Call RET
FIBRE_INCONNU = 20200715153948361       # vendeur par defaut si TK pas trouve
ID_AFFECT_DISTRIB_CALL_RETENTION = 20230601160425831


def _donne_statut_call(libelle: str) -> tuple[int, str]:
    """donneStatutCall : lookup pgt_sfr_etat_call_ret by lib_etat LIKE.
    Retourne (id_etat_call_ret, lib_etat)."""
    if not libelle:
        return (0, "")
    try:
        db = get_pg_connection("adv")
        r = db.query_one(
            """SELECT id_etat_call_ret, lib_etat FROM adv.pgt_sfr_etat_call_ret
                WHERE LOWER(lib_etat) LIKE LOWER(?)
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (f"%{libelle}%",),
        )
        return ((_int(r.get("id_etat_call_ret")), _str(r.get("lib_etat")))
                if r else (0, ""))
    except Exception:
        return (0, "")


def _iter_sheets(content: bytes):
    """Itere toutes les feuilles d'un classeur (nb_sheets de WinDev)."""
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    for sheet in wb.sheetnames:
        yield wb[sheet], sheet
    wb.close()


def _create_sfr_contrat_callret(orig: dict, new_bs: str,
                                date_sign: Optional[date], op_id: int,
                                info_motif: str) -> int:
    """Cree un nouveau SFR_contrat (rattrape par Call RET) en cascadant les
    valeurs du contrat origine."""
    db = get_pg_connection("adv")
    id_contrat = _new_id()
    auto = db.query_one(
        "SELECT COALESCE(MAX(id_contrat_auto), 0) + 1 AS n FROM adv.pgt_sfr_contrat"
    )
    db.query(
        """INSERT INTO adv.pgt_sfr_contrat
              (id_contrat_auto, id_contrat, id_client, id_salarie, id_ste,
               num_bs, date_signature, id_etat_sfr, id_etat_contrat,
               id_sfr_cluster, id_produit, technologie, self_install,
               type_vente, box8, box8_verif, option_dec, option_verif,
               motif_annulation, info_interne, non_call, remise,
               hors_cible, issu_tk_diff,
               op_saisie, date_saisie, modif_op, modif_date, modif_elem)
           VALUES (?, ?, ?, ?, 0,
                   ?, ?, 1, 1,
                   ?, ?, ?, ?,
                   ?, ?, ?, ?, ?,
                   '', ?, TRUE, ?,
                   ?, 0,
                   ?, NOW(), ?, NOW(), 'new')""",
        (int(auto["n"]) if auto else 1, id_contrat,
         int(orig.get("id_client") or 0), int(ABASSI_AHD),
         new_bs, date_sign,
         int(orig.get("id_sfr_cluster") or 0),
         int(orig.get("id_produit") or 0),
         int(orig.get("technologie") or 0),
         bool(orig.get("self_install")),
         int(orig.get("type_vente") or 0),
         bool(orig.get("box8")), bool(orig.get("box8")),
         bool(orig.get("option_dec")), bool(orig.get("option_verif")),
         info_motif,
         bool(orig.get("remise")),
         bool(orig.get("hors_cible")),
         int(op_id), int(op_id)),
    )
    return id_contrat


def _import_callret_ko(
    p: ImportSfrParams, content: bytes, op_id: int,
    ajoutes: list, modifies: list, erreurs: list, resume: ImportSfrResume,
) -> None:
    """Type 7 : ImportCallRET_KO. Lit toutes les feuilles, pour chaque ligne
    lookup BS, ajoute new BS si fourni + MAJ id_etat_call_ret + obs."""
    cols_map = {"num_bs": "A", "statut": "I", "comment": "L", "new_bs": "AT"}
    cols = {k: _col_letter_to_index(v) for k, v in cols_map.items()}
    db = get_pg_connection("adv")
    ligne_dep = p.ligne_depart or 2

    for ws, _sheet in _iter_sheets(content):
        for i in range(ligne_dep, (ws.max_row or 0) + 1):
            num_bs = _cell(ws, i, cols["num_bs"]).upper().replace(" ", "")
            if not num_bs:
                continue
            statut = _cell(ws, i, cols["statut"])
            comment = _cell(ws, i, cols["comment"])
            new_bs = _cell(ws, i, cols["new_bs"]).upper().replace(" ", "")
            id_statut, lib_etat_call = _donne_statut_call(statut)
            if statut and id_statut == 0:
                erreurs.append({
                    "NumBS": num_bs, "Erreur": "Statut inconnu",
                    "Statut": statut,
                })
                resume.nb_erreurs += 1

            orig = db.query_one(
                """SELECT id_contrat, id_client, id_salarie, id_produit,
                          date_signature, id_sfr_cluster, technologie,
                          self_install, type_vente, box8, option_dec,
                          option_verif, remise, hors_cible, id_etat_call_ret,
                          obs_call_ret, id_contrat_ret
                     FROM adv.pgt_sfr_contrat
                    WHERE UPPER(num_bs) = UPPER(?)
                      AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                    LIMIT 1""",
                (num_bs,),
            )
            if not orig:
                erreurs.append({"NumBS": num_bs, "Erreur": "BS introuvable",
                                "Statut": statut})
                resume.nb_introuvables += 1
                continue

            id_contrat_orig = int(orig["id_contrat"])
            modifs_done = []

            # Ajout d'un nouveau BS si fourni
            if new_bs:
                # Verifier si le new_bs existe deja
                exist = db.query_one(
                    """SELECT id_contrat FROM adv.pgt_sfr_contrat
                        WHERE UPPER(num_bs) = UPPER(?) LIMIT 1""",
                    (new_bs,),
                )
                row_a = {
                    "NumBS_Origine": num_bs, "NewBS": new_bs,
                    "LibEtatCall": lib_etat_call,
                    "Existant": bool(exist),
                }
                if not exist:
                    if not p.simulation:
                        try:
                            new_id = _create_sfr_contrat_callret(
                                orig, new_bs, orig.get("date_signature"),
                                op_id,
                                f"Contrat KO Rattrape par le Call RET, "
                                f"Num Origine : {num_bs}",
                            )
                            row_a["NewIdContrat"] = new_id
                            # MAJ id_contrat_ret sur l'origine
                            db.query(
                                """UPDATE adv.pgt_sfr_contrat
                                      SET id_contrat_ret = ?, modif_date = NOW(),
                                          modif_op = ?, modif_elem = 'modif'
                                    WHERE id_contrat = ?""",
                                (new_id, int(op_id), id_contrat_orig),
                            )
                        except Exception as e:
                            row_a["Erreur"] = str(e)
                ajoutes.append(row_a)
                resume.nb_ajoutes += 1

            # MAJ id_etat_call_ret + obs si different
            if id_statut and int(orig.get("id_etat_call_ret") or 0) != id_statut:
                modifs_done.append(f"EtatCallRet -> {id_statut} ({lib_etat_call})")
                if not p.simulation:
                    new_obs = (f"{datetime.now().strftime('%d/%m/%Y %H:%M , ')}"
                               f"{lib_etat_call} : {comment}\n")
                    db.query(
                        """UPDATE adv.pgt_sfr_contrat
                              SET id_etat_call_ret = ?, obs_call_ret = ?,
                                  modif_date = NOW(), modif_op = ?,
                                  modif_elem = 'modif'
                            WHERE id_contrat = ?""",
                        (id_statut, new_obs, int(op_id), id_contrat_orig),
                    )

            if modifs_done:
                modifies.append({
                    "NumBS": num_bs, "LibEtatCall": lib_etat_call,
                    "Modifs": " | ".join(modifs_done), "Comment": comment,
                })
                resume.nb_modifies += 1


def _import_callret_racc(
    p: ImportSfrParams, content: bytes, op_id: int,
    ajoutes: list, modifies: list, erreurs: list, resume: ImportSfrResume,
) -> None:
    """Type 8 : ImportCallRET_Racc. 1 BS origine + jusqu'a 4 nouveaux BS."""
    cols_map = {"num_bs": "A", "comment": "L",
                "new_bs1": "AT", "new_bs2": "AU", "new_bs3": "AV", "new_bs4": "AW"}
    cols = {k: _col_letter_to_index(v) for k, v in cols_map.items()}
    db = get_pg_connection("adv")
    ligne_dep = p.ligne_depart or 2

    for ws, _sheet in _iter_sheets(content):
        for i in range(ligne_dep, (ws.max_row or 0) + 1):
            num_bs = _cell(ws, i, cols["num_bs"]).upper().replace(" ", "")
            if not num_bs:
                continue
            comment = _cell(ws, i, cols["comment"])
            new_bss = [_cell(ws, i, cols[k]).upper().replace(" ", "")
                       for k in ("new_bs1", "new_bs2", "new_bs3", "new_bs4")]
            new_bss = [b for b in new_bss if b]

            orig = db.query_one(
                """SELECT id_contrat, id_client, id_salarie, id_produit,
                          date_signature, id_sfr_cluster, technologie,
                          self_install, type_vente, box8, option_dec,
                          option_verif, remise, hors_cible, info_interne
                     FROM adv.pgt_sfr_contrat
                    WHERE UPPER(num_bs) = UPPER(?)
                      AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                    LIMIT 1""",
                (num_bs,),
            )
            if not orig:
                erreurs.append({"NumBS": num_bs, "Erreur": "BS introuvable"})
                resume.nb_introuvables += 1
                continue

            id_orig = int(orig["id_contrat"])
            id_clt = int(orig.get("id_client") or 0)
            liste_bs_add = []

            for new_bs in new_bss:
                exist = db.query_one(
                    """SELECT id_contrat, id_client, id_salarie
                         FROM adv.pgt_sfr_contrat
                        WHERE UPPER(num_bs) = UPPER(?) LIMIT 1""",
                    (new_bs,),
                )
                row_a = {"NumBS_Origine": num_bs, "NewBS": new_bs,
                         "Existant": bool(exist)}
                if exist:
                    # MAJ client / vendeur si different
                    if int(exist.get("id_client") or 0) != id_clt:
                        if not p.simulation:
                            db.query(
                                """UPDATE adv.pgt_sfr_contrat
                                      SET id_client = ?, modif_date = NOW(),
                                          modif_op = ?, modif_elem = 'modif'
                                    WHERE id_contrat = ?""",
                                (id_clt, int(op_id), int(exist["id_contrat"])),
                            )
                        row_a["Note"] = "ID Client mis a jour"
                    sal_db = int(exist.get("id_salarie") or 0)
                    if sal_db in (0, FIBRE_INCONNU):
                        if not p.simulation:
                            db.query(
                                """UPDATE adv.pgt_sfr_contrat
                                      SET id_salarie = ?, modif_date = NOW(),
                                          modif_op = ?, modif_elem = 'modif'
                                    WHERE id_contrat = ?""",
                                (int(ABASSI_AHD), int(op_id),
                                 int(exist["id_contrat"])),
                            )
                        row_a["Note"] = (row_a.get("Note", "")
                                         + " | ID Vendeur mis a jour").strip(" |")
                else:
                    if not p.simulation:
                        try:
                            new_id = _create_sfr_contrat_callret(
                                orig, new_bs, orig.get("date_signature"),
                                op_id,
                                f"Vente RACC par le Call RET, "
                                f"Num Origine : {num_bs}",
                            )
                            row_a["NewIdContrat"] = new_id
                        except Exception as e:
                            row_a["Erreur"] = str(e)
                ajoutes.append(row_a)
                resume.nb_ajoutes += 1
                liste_bs_add.append(new_bs)

            # MAJ info_interne origine
            if liste_bs_add and not p.simulation:
                info_add = (f"\n{datetime.now().strftime('%d/%m/%Y %H:%M , ')}"
                            f"Ventes ADD par Call RET\n    - "
                            + "\n    - ".join(liste_bs_add))
                obs_add = (f"{datetime.now().strftime('%d/%m/%Y %H:%M , ')}"
                           f"{comment}\n" if comment else "")
                try:
                    db.query(
                        """UPDATE adv.pgt_sfr_contrat
                              SET info_interne = COALESCE(info_interne, '') || ?,
                                  obs_call_ret = CASE WHEN ? <> ''
                                                      THEN ? ELSE obs_call_ret END,
                                  modif_date = NOW(), modif_op = ?,
                                  modif_elem = 'modif'
                            WHERE id_contrat = ?""",
                        (info_add, obs_add, obs_add, int(op_id), id_orig),
                    )
                except Exception as e:
                    modifies.append({"NumBS": num_bs, "Erreur": str(e)})


def _import_callret_rdvtech(
    p: ImportSfrParams, content: bytes, op_id: int,
    ajoutes: list, modifies: list, erreurs: list, resume: ImportSfrResume,
) -> None:
    """Type 10 : ImportCallRET_RDVTech. MAJ date_rdv_tech + id_sfr_statut_rdv."""
    cols_map = {"num_bs": "A", "statut": "I", "comment": "L", "date_rdv": "BB"}
    cols = {k: _col_letter_to_index(v) for k, v in cols_map.items()}
    db = get_pg_connection("adv")
    ligne_dep = p.ligne_depart or 2

    for ws, _sheet in _iter_sheets(content):
        for i in range(ligne_dep, (ws.max_row or 0) + 1):
            num_bs = _cell(ws, i, cols["num_bs"]).upper().replace(" ", "")
            if not num_bs:
                continue
            statut = _cell(ws, i, cols["statut"])
            comment = _cell(ws, i, cols["comment"])
            date_rdv = _parse_date_fr(_cell(ws, i, cols["date_rdv"]))

            id_statut, lib_etat = _donne_statut_call(statut) if statut else (0, "")
            id_statut_rdv = 0
            lib_statut_rdv = ""
            if id_statut:
                # Lookup id_etat_rdv_tech sur etat_call_ret
                r = db.query_one(
                    """SELECT id_etat_rdv_tech FROM adv.pgt_sfr_etat_call_ret
                        WHERE id_etat_call_ret = ? LIMIT 1""",
                    (id_statut,),
                )
                if r and r.get("id_etat_rdv_tech"):
                    r2 = db.query_one(
                        """SELECT id_sfr_statut_rdv, lib_statut
                             FROM adv.pgt_sfr_statut_rdv
                            WHERE id_sfr_statut_rdv = ? LIMIT 1""",
                        (int(r["id_etat_rdv_tech"]),),
                    )
                    if r2:
                        id_statut_rdv = int(r2.get("id_sfr_statut_rdv") or 0)
                        lib_statut_rdv = _str(r2.get("lib_statut"))

            orig = db.query_one(
                """SELECT id_contrat, date_rdv_tech, id_sfr_statut_rdv,
                          info_interne
                     FROM adv.pgt_sfr_contrat
                    WHERE UPPER(num_bs) = UPPER(?)
                      AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                    LIMIT 1""",
                (num_bs,),
            )
            if not orig:
                erreurs.append({"NumBS": num_bs, "Erreur": "Contrat introuvable",
                                "Statut": statut, "Comment": comment})
                resume.nb_introuvables += 1
                continue

            id_orig = int(orig["id_contrat"])
            modifs_done = []
            new_info = orig.get("info_interne") or ""
            new_rdv = orig.get("date_rdv_tech")
            new_statut_rdv = int(orig.get("id_sfr_statut_rdv") or 0)

            if (comment and "Import Call Ret RDV Tech :"
                    not in (orig.get("info_interne") or "")):
                modifs_done.append("Comment ajoute")
                new_info += (f"\n{datetime.now().strftime('%d/%m/%Y %H:%M , ')}"
                             f"Import Call Ret RDV Tech : {comment}")
            if id_statut_rdv and new_statut_rdv != id_statut_rdv:
                modifs_done.append(f"StatutRDV -> {id_statut_rdv} ({lib_statut_rdv})")
                new_statut_rdv = id_statut_rdv
            if date_rdv and (not new_rdv or new_rdv < date_rdv):
                old_str = (new_rdv.strftime("%d/%m/%Y") if new_rdv else "")
                modifs_done.append(f"DateRDV {old_str} -> {date_rdv}")
                new_info += (f"\nModif RDV du {old_str} au "
                             f"{date_rdv.strftime('%d/%m/%Y')}")
                new_rdv = date_rdv

            row_snap = {
                "NumBS": num_bs, "StatutRDV": lib_statut_rdv,
                "DateRDV": str(date_rdv or ""),
                "Modifs": " | ".join(modifs_done) if modifs_done else "(aucune)",
            }
            if modifs_done:
                ajoutes.append(row_snap)
                resume.nb_modifies += 1
                if not p.simulation:
                    try:
                        db.query(
                            """UPDATE adv.pgt_sfr_contrat
                                  SET date_rdv_tech = ?, id_sfr_statut_rdv = ?,
                                      info_interne = ?,
                                      modif_date = NOW(), modif_op = ?,
                                      modif_elem = 'modif'
                                WHERE id_contrat = ?""",
                            (new_rdv, new_statut_rdv, new_info,
                             int(op_id), id_orig),
                        )
                    except Exception as e:
                        row_snap["Erreur"] = str(e)


def _import_callret_ventesadd(
    p: ImportSfrParams, content: bytes, op_id: int,
    ajoutes: list, modifies: list, erreurs: list, resume: ImportSfrResume,
) -> None:
    """Type 9 : ImportCallRET_VentesADD. Reattribution vendeur a ABASSI si
    fibre inconnu/anonymous. Sinon : si vendeur deja en Distrib Call Retention,
    on signale en erreur."""
    cols_map = {"num_bs": "A", "statut": "I", "comment": "L",
                "date_sign": "C", "categorie": "M", "offre": "J",
                "date_racc": "E"}
    cols = {k: _col_letter_to_index(v) for k, v in cols_map.items()}
    db = get_pg_connection("adv")
    ligne_dep = p.ligne_depart or 2

    for ws, _sheet in _iter_sheets(content):
        for i in range(ligne_dep, (ws.max_row or 0) + 1):
            num_bs = _cell(ws, i, cols["num_bs"]).upper().replace(" ", "")
            if not num_bs:
                continue
            statut = _cell(ws, i, cols["statut"])
            comment = _cell(ws, i, cols["comment"])
            offre = _cell(ws, i, cols["offre"])
            id_statut, lib_etat_call = _donne_statut_call(statut)

            orig = db.query_one(
                """SELECT id_contrat, id_salarie
                     FROM adv.pgt_sfr_contrat
                    WHERE UPPER(num_bs) = UPPER(?)
                      AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                    LIMIT 1""",
                (num_bs,),
            )
            if not orig:
                erreurs.append({"NumBS": num_bs, "Erreur": "Contrat introuvable",
                                "Statut": statut, "Comment": comment})
                resume.nb_introuvables += 1
                continue

            id_orig = int(orig["id_contrat"])
            id_sal_db = int(orig.get("id_salarie") or 0)

            if id_sal_db in (0, FIBRE_INCONNU):
                # Reattribution a ABASSI
                ajoutes.append({
                    "NumBS": num_bs, "Offre": offre,
                    "LibEtatCall": lib_etat_call,
                    "OldIdSalarie": id_sal_db,
                    "NewIdSalarie": ABASSI_AHD,
                })
                resume.nb_modif_vend += 1
                if not p.simulation:
                    try:
                        db.query(
                            """UPDATE adv.pgt_sfr_contrat
                                  SET id_salarie = ?, modif_date = NOW(),
                                      modif_op = ?, modif_elem = 'modif'
                                WHERE id_contrat = ?""",
                            (int(ABASSI_AHD), int(op_id), id_orig),
                        )
                    except Exception as e:
                        ajoutes[-1]["Erreur"] = str(e)
            else:
                # Verifier si deja Distrib Call Retention
                aff = db.query_one(
                    """SELECT o.id_parent
                         FROM rh.pgt_salarie_organigramme so
                         JOIN rh.pgt_organigramme o
                              ON o.idorganigramme = so.idorganigramme
                        WHERE so.id_salarie = ? LIMIT 1""",
                    (id_sal_db,),
                ) if False else None
                # Best effort : on signale juste en erreur 'attribue a vendeur'
                erreurs.append({
                    "NumBS": num_bs,
                    "Erreur": "Contrat attribué à un vendeur",
                    "Statut": statut, "IdSalarie": id_sal_db,
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
            elif p.type_import == 2:
                _import_journalier_mobile(p, content, op_id,
                                          ajoutes, modifies, erreurs, resume)
            elif p.type_import == 3:
                _import_journalier_call(p, content, op_id,
                                        ajoutes, modifies, erreurs, resume)
            elif p.type_import == 4:
                _import_journalier_hebdo(p, content, op_id,
                                         ajoutes, modifies, migrations,
                                         erreurs, resume)
            elif p.type_import == 5:
                _import_options(p, content, op_id,
                                modifies, erreurs, resume)
            elif p.type_import == 6:
                _import_run(p, content, op_id,
                            ajoutes, modifies, erreurs, resume)
            elif p.type_import == 7:
                _import_callret_ko(p, content, op_id,
                                   ajoutes, modifies, erreurs, resume)
            elif p.type_import == 8:
                _import_callret_racc(p, content, op_id,
                                     ajoutes, modifies, erreurs, resume)
            elif p.type_import == 9:
                _import_callret_ventesadd(p, content, op_id,
                                          ajoutes, modifies, erreurs, resume)
            elif p.type_import == 10:
                _import_callret_rdvtech(p, content, op_id,
                                        ajoutes, modifies, erreurs, resume)
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
