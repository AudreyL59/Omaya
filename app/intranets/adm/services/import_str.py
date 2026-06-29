"""Service Fen_ImportSTR (ADM Imports Bases -> STRATO).

3 types d'import (cf combo TypeImport WinDev) :
  1. Base Journaliere   -> ImportJournalier
  2. RUN                -> ImportRUN
  3. Import Resil Hebdo -> ImportResilHebdo

Pattern multi-fichier (sFichier = noms separes par RC).
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
)


# Mapping colonnes Base Journaliere STR (cf groupe grAlexJournalier)
# Visible sur l'ecran : Date Signature E, Vendeur nom C, prenom D, Num BS N,
# Statut vente Q, Remarques R, Distributeur B, Client (Civilite I/Nom J/Prenom K),
# Client CP L, VILLE M
COLS_BJ_STR = {
    "distributeur": "B",        "vendeur_nom": "C",
    "vendeur_prenom": "D",      "date_signature": "E",
    "client_civilite": "I",     "client_nom": "J",
    "client_prenom": "K",       "client_cp": "L",
    "client_ville": "M",        "num_bs": "N",
    "statut_vente": "Q",        "remarques": "R",
}


# Mapping colonnes Import Resil Hebdo STR (cf groupe _AA1 dans grAlexJournalier)
# D'apres l'ecran : Date Sign E, Vendeur nom C/prenom D, Num BS S, Statut V,
# Remarques W, Client Civilite I, Nom J, Prenom K, adr1 L, adr2 M, CP N,
# VILLE O, Tel P, Mobile Q, DNAISS R
COLS_RH_STR = {
    "vendeur_nom": "C",         "vendeur_prenom": "D",
    "date_signature": "E",      "client_civilite": "I",
    "client_nom": "J",          "client_prenom": "K",
    "client_adr1": "L",         "client_adr2": "M",
    "client_cp": "N",           "client_ville": "O",
    "client_tel": "P",          "client_mobile": "Q",
    "client_naiss": "R",        "num_bs": "S",
    "statut": "V",              "remarques": "W",
}


# Mapping colonnes RUN STR (typique : num + mois paiement + montant)
COLS_RUN_STR = {
    "num_bs": "A",              "statut": "B",
    "montant": "C",
}


class ImportStrParams(BaseModel):
    type_import: int                    # 1, 2, 3
    simulation: bool = True
    periode1_du: str = ""
    periode1_au: str = ""
    periode1_mois_paiement: str = ""
    periode2_du: str = ""
    periode2_au: str = ""
    periode2_mois_paiement: str = ""
    mois_paiement_distrib: str = ""


class ImportStrResume(BaseModel):
    nb_fichiers: int = 0
    nb_ajoutes: int = 0
    nb_valides: int = 0
    nb_resilies: int = 0
    nb_decommissions: int = 0
    nb_deja_saisis: int = 0
    nb_deja_statues: int = 0
    nb_introuvables: int = 0
    nb_doublons: int = 0
    nb_hors_delai: int = 0
    nb_pb_vendeur: int = 0
    nb_erreurs: int = 0


class ImportStrResult(BaseModel):
    ok: bool
    type_import: int
    type_label: str
    simulation: bool
    resume: ImportStrResume
    fichiers_traites: list[str] = []
    contrats_ajoutes: list[dict] = []
    contrats_modifies: list[dict] = []
    contrats_non_trouves: list[dict] = []
    contrats_run: list[dict] = []
    pb_vendeur: list[dict] = []
    message: str = ""
    xlsx_b64: str = ""
    xlsx_name: str = ""
    mail_envoye: bool = False


TYPE_LABELS = {
    1: "Base Journalière",
    2: "RUN",
    3: "Import Résil Hebdo",
}


# ---------------------------------------------------------------------------
# Helpers STR
# ---------------------------------------------------------------------------


def _id_produit_str_by_lib(lib_produit: str) -> tuple[int, str]:
    """Lookup pgt_str_produit by lib_produit LIKE."""
    if not lib_produit:
        return (0, "")
    db = get_pg_connection("adv")
    r = db.query_one(
        """SELECT id_produit, lib_produit FROM adv.pgt_str_produit
            WHERE LOWER(lib_produit) LIKE LOWER(?)
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            LIMIT 1""",
        (f"%{lib_produit}%",),
    )
    return ((_int(r.get("id_produit")), _str(r.get("lib_produit")))
            if r else (0, ""))


def _id_etat_str_by_lib(lib_statut: str) -> int:
    """Lookup pgt_str_etat_contrat by lib_etat LIKE."""
    if not lib_statut:
        return 0
    db = get_pg_connection("adv")
    r = db.query_one(
        """SELECT id_etat FROM adv.pgt_str_etat_contrat
            WHERE LOWER(lib_etat) LIKE LOWER(?)
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            LIMIT 1""",
        (f"{lib_statut}%",),
    )
    return _int(r.get("id_etat")) if r else 0


def _lookup_vendeur_str_nom_prenom(nom: str, prenom: str) -> int:
    """Lookup salarie par nom + prenom exacts. Retourne 0 si introuvable
    ou ambigu (>1 match)."""
    if not nom or not prenom:
        return 0
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_salarie FROM rh.pgt_salarie
            WHERE UPPER(nom) = UPPER(?) AND UPPER(prenom) = UPPER(?)
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            LIMIT 2""",
        (nom.strip(), prenom.strip()),
    ) or []
    if len(rows) == 1:
        return int(rows[0]["id_salarie"])
    # Fallback : LIKE
    rows = db.query(
        """SELECT id_salarie FROM rh.pgt_salarie
            WHERE UPPER(nom) LIKE UPPER(?) AND UPPER(prenom) LIKE UPPER(?)
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            LIMIT 2""",
        (f"{nom.strip()}%", f"{prenom.strip()}%"),
    ) or []
    if len(rows) == 1:
        return int(rows[0]["id_salarie"])
    return 0


def _info_salarie_str(id_sal: int) -> dict:
    if not id_sal:
        return {}
    db = get_pg_connection("rh")
    r = db.query_one(
        """SELECT s.id_salarie, s.nom, s.prenom, e.id_ste
             FROM rh.pgt_salarie s
             LEFT JOIN rh.pgt_salarie_embauche e ON e.id_salarie = s.id_salarie
            WHERE s.id_salarie = ? LIMIT 1""",
        (int(id_sal),),
    )
    return r or {}


def _ajoute_histo_str_etat(id_contrat: int, old_etat: int, new_etat: int,
                            date_paiement: str, op_id: int) -> None:
    if not id_contrat:
        return
    db = get_pg_connection("adv")
    auto = db.query_one(
        "SELECT COALESCE(MAX(id_histo_auto), 0) + 1 AS n FROM adv.pgt_str_histo_etat_ctt"
    )
    db.query(
        """INSERT INTO adv.pgt_str_histo_etat_ctt
              (id_histo_auto, id_histo, id_contrat, op_saisie, date,
               old_etat, new_etat, date_paiement,
               modif_op, modif_date, modif_elem)
           VALUES (?, ?, ?, ?, NOW(), ?, ?, ?, ?, NOW(), 'new')""",
        (int(auto["n"]) if auto else 1, _new_id(),
         int(id_contrat), int(op_id),
         int(old_etat) if old_etat else 0,
         int(new_etat) if new_etat else 0,
         date_paiement or "", int(op_id)),
    )


def _create_str_contrat(td: dict, op_id: int) -> int:
    """INSERT pgt_str_contrat (avec lookup TK_Call pour le client)."""
    db = get_pg_connection("adv")
    id_contrat = _new_id()
    auto = db.query_one(
        "SELECT COALESCE(MAX(id_contrat_auto), 0) + 1 AS n FROM adv.pgt_str_contrat"
    )
    date_sign = td.get("date_signature")
    if isinstance(date_sign, str):
        date_sign = _parse_date_fr(date_sign)
    db.query(
        """INSERT INTO adv.pgt_str_contrat
              (id_contrat_auto, id_contrat, id_client, id_salarie, id_ste,
               num_bs, id_produit, id_etat_contrat,
               date_signature, op_saisie, date_saisie, non_call,
               opt_mandat, info_interne, code_enr,
               modif_op, modif_date, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?,
                   ?, ?, NOW(), ?, ?, ?, '',
                   ?, NOW(), 'new')""",
        (int(auto["n"]) if auto else 1, id_contrat,
         int(td.get("id_client") or 0),
         int(td.get("id_salarie") or 0),
         int(td.get("id_ste") or 0),
         td.get("num_bs") or "",
         int(td.get("id_produit") or 0),
         int(td.get("etat_contrat") or 1),
         date_sign, int(op_id),
         bool(td.get("non_call", True)),
         bool(td.get("opt_mandat")),
         td.get("info_interne") or "",
         int(op_id)),
    )
    return id_contrat


# ---------------------------------------------------------------------------
# Type 1 : ImportJournalier (squelette en attente du code WinDev)
# ---------------------------------------------------------------------------


def _import_journalier_str(
    p: ImportStrParams, fname: str, content: bytes, op_id: int,
    ajoutes: list, modifies: list, pb_vendeur: list, resume: ImportStrResume,
) -> None:
    """Type 1 : Base Journaliere STR. Pour chaque ligne :
    - Lookup vendeur par nom+prenom
    - Lookup contrat par num_bs
      * Pas existant -> ajout (creation via _create_str_contrat en prod)
      * Existant -> deja saisi (+ reattribution vendeur si different)
    """
    from openpyxl import load_workbook
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as e:
        resume.nb_erreurs += 1
        modifies.append({"_erreur": f"Lecture {fname} : {e}"})
        return
    ws = wb.active
    cols = {k: _col_letter_to_index(v) for k, v in COLS_BJ_STR.items()}
    db = get_pg_connection("adv")

    for i in range(2, (ws.max_row or 0) + 1):
        num_bs = _cell(ws, i, cols["num_bs"]).upper()
        if not num_bs:
            continue
        distributeur = _cell(ws, i, cols["distributeur"])
        vendeur_nom = _cell(ws, i, cols["vendeur_nom"])
        vendeur_prenom = _cell(ws, i, cols["vendeur_prenom"])
        date_sign = _parse_date_fr(_cell(ws, i, cols["date_signature"]))
        client_civilite = _cell(ws, i, cols["client_civilite"])
        client_nom = _cell(ws, i, cols["client_nom"])
        client_prenom = _cell(ws, i, cols["client_prenom"])
        client_cp = _cell(ws, i, cols["client_cp"])
        client_ville = _cell(ws, i, cols["client_ville"])
        statut_vente = _cell(ws, i, cols["statut_vente"])
        remarques = _cell(ws, i, cols["remarques"])

        id_vendeur = _lookup_vendeur_str_nom_prenom(vendeur_nom, vendeur_prenom)
        info_sal = _info_salarie_str(id_vendeur) if id_vendeur else {}
        id_ste = int(info_sal.get("id_ste") or 0)
        id_etat = _id_etat_str_by_lib(statut_vente) or 1

        ctt = db.query_one(
            """SELECT id_contrat, id_salarie, num_bs, date_signature, id_produit
                 FROM adv.pgt_str_contrat
                WHERE UPPER(num_bs) = UPPER(?)
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (num_bs,),
        )

        if not ctt:
            ajoutes.append({
                "NumBS": num_bs, "DateSign": str(date_sign or ""),
                "Distributeur": distributeur,
                "Vendeur": f"{vendeur_nom} {vendeur_prenom}".strip(),
                "IdSalarie": id_vendeur, "Société": id_ste,
                "Client": f"{client_civilite} {client_nom} {client_prenom}".strip(),
                "ClientCP": client_cp, "ClientVille": client_ville,
                "StatutVente": statut_vente, "Remarques": remarques,
                "EtatContrat": id_etat,
                "_payload_create": {
                    "num_bs": num_bs, "id_salarie": id_vendeur,
                    "id_ste": id_ste, "id_produit": 0,
                    "etat_contrat": id_etat,
                    "date_signature": date_sign,
                    "non_call": True, "info_interne": remarques,
                },
            })
            if id_vendeur == 0:
                pb_vendeur.append({
                    "NumBS": num_bs, "DateSign": str(date_sign or ""),
                    "Vendeur Import": f"{vendeur_nom} {vendeur_prenom}".strip(),
                    "Erreur": "Vendeur introuvable",
                })
                resume.nb_pb_vendeur += 1
            resume.nb_ajoutes += 1
        else:
            id_contrat = int(ctt["id_contrat"])
            id_sal_db = int(ctt.get("id_salarie") or 0)
            modifies.append({
                "NumBS": ctt.get("num_bs"),
                "DateSign OMAYA": str(ctt.get("date_signature") or ""),
                "IdSalarie DB": id_sal_db,
                "Vendeur Import": f"{vendeur_nom} {vendeur_prenom}".strip(),
            })
            resume.nb_deja_saisis += 1
            if id_sal_db != id_vendeur and id_vendeur != 0:
                pb_vendeur.append({
                    "NumBS": ctt.get("num_bs"),
                    "Erreur": "vendeur réattribué",
                    "OldIdSalarie": id_sal_db, "NewIdSalarie": id_vendeur,
                    "_id_contrat": id_contrat,
                })
    wb.close()


def _import_run_str(
    p: ImportStrParams, fname: str, content: bytes, op_id: int,
    runs: list, modifies: list, non_trouves: list, pb_vendeur: list,
    resume: ImportStrResume,
) -> None:
    """Type 2 : RUN STR. Squelette en attente du code WinDev detaille."""
    from openpyxl import load_workbook
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as e:
        resume.nb_erreurs += 1
        modifies.append({"_erreur": f"Lecture {fname} : {e}"})
        return
    ws = wb.active
    cols = {k: _col_letter_to_index(v) for k, v in COLS_RUN_STR.items()}
    db = get_pg_connection("adv")

    for i in range(2, (ws.max_row or 0) + 1):
        num_bs = _cell(ws, i, cols["num_bs"]).upper()
        if not num_bs:
            continue
        statut = _cell(ws, i, cols["statut"])
        montant = _cell(ws, i, cols["montant"])

        ctt = db.query_one(
            """SELECT id_contrat, id_salarie, num_bs, date_signature,
                      id_etat_contrat, mois_p
                 FROM adv.pgt_str_contrat
                WHERE UPPER(num_bs) = UPPER(?)
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (num_bs,),
        )
        if not ctt:
            non_trouves.append({"NumBS": num_bs, "Statut": statut,
                                "Montant": montant})
            resume.nb_introuvables += 1
            continue
        runs.append({
            "NumBS": ctt.get("num_bs"),
            "DateSign": str(ctt.get("date_signature") or ""),
            "Statut": statut, "Montant": montant,
            "Note": "Logique RUN STR à compléter avec code WinDev",
        })
        resume.nb_valides += 1
    wb.close()


def _import_resil_hebdo_str(
    p: ImportStrParams, fname: str, content: bytes, op_id: int,
    runs: list, modifies: list, non_trouves: list, pb_vendeur: list,
    resume: ImportStrResume,
) -> None:
    """Type 3 : Import Resil Hebdo STR. Pour chaque ligne :
    - Lookup contrat par num_bs
    - Si trouve + statut != 'VALIDE' :
      * Si type_etat in (1, 2) (en attente) -> passe a 16 (Resilie par
        operateur) ou 57 (Retractation client) si statut='RESILIE'.
        + concat 'Motif Resil' a info_partagee + reset mois_p + histo.
      * Sinon -> deja statue (sheet 3).
    - Si statut contient 'VALIDE' -> on ne fait rien (cf WinDev).
    - Si pas trouve -> contrat introuvable (sheet 2).
    """
    from openpyxl import load_workbook
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as e:
        resume.nb_erreurs += 1
        modifies.append({"_erreur": f"Lecture {fname} : {e}"})
        return
    ws = wb.active
    cols = {k: _col_letter_to_index(v) for k, v in COLS_RH_STR.items()}
    db = get_pg_connection("adv")

    for i in range(2, (ws.max_row or 0) + 1):
        num_bs = _cell(ws, i, cols["num_bs"]).upper()
        if not num_bs:
            continue
        statut = _cell(ws, i, cols["statut"])
        remarques = _cell(ws, i, cols["remarques"])
        vendeur_nom = _cell(ws, i, cols["vendeur_nom"])
        vendeur_prenom = _cell(ws, i, cols["vendeur_prenom"])
        client_nom = _cell(ws, i, cols["client_nom"])
        client_prenom = _cell(ws, i, cols["client_prenom"])
        client_adr1 = _cell(ws, i, cols["client_adr1"])
        client_cp = _cell(ws, i, cols["client_cp"])
        client_ville = _cell(ws, i, cols["client_ville"])

        ctt = db.query_one(
            """SELECT id_contrat, id_salarie, num_bs, date_signature,
                      id_etat_contrat, info_partagee
                 FROM adv.pgt_str_contrat
                WHERE UPPER(num_bs) = UPPER(?)
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (num_bs,),
        )
        if not ctt:
            non_trouves.append({
                "NumBS": num_bs, "ClientNom": client_nom,
                "ClientPrenom": client_prenom, "ClientCP": client_cp,
                "ClientVille": client_ville,
                "Vendeur": f"{vendeur_nom} {capitalise_str(vendeur_prenom)}".strip(),
                "Statut": statut, "Remarques": remarques,
            })
            resume.nb_introuvables += 1
            continue

        # Si statut contient VALIDE -> rien a faire
        if "VALIDE" in statut.upper():
            continue

        id_contrat = int(ctt["id_contrat"])
        id_etat_actuel = int(ctt.get("id_etat_contrat") or 0)
        date_sign_db = ctt.get("date_signature")

        # Lookup type_etat actuel
        etat_info = db.query_one(
            """SELECT id_type_etat, lib_etat FROM adv.pgt_str_etat_contrat
                WHERE id_etat = ? LIMIT 1""",
            (id_etat_actuel,),
        )
        id_type_etat = int(etat_info.get("id_type_etat") or 0) if etat_info else 0
        lib_etat_actuel = (etat_info.get("lib_etat") or "") if etat_info else ""

        info_sal = _info_salarie_str(int(ctt.get("id_salarie") or 0))
        nom_vend_db = f"{_str(info_sal.get('nom'))} {_str(info_sal.get('prenom'))}".strip()

        if id_type_etat in (1, 2):
            # En attente -> on resilie
            new_etat = 57 if statut.upper() == "RESILIE" else 16
            new_etat_info = db.query_one(
                """SELECT lib_etat FROM adv.pgt_str_etat_contrat
                    WHERE id_etat = ? LIMIT 1""",
                (new_etat,),
            )
            new_etat_lib = (new_etat_info.get("lib_etat") or "") if new_etat_info else ""

            modifies.append({
                "NumBS": num_bs, "ClientNom": client_nom,
                "ClientPrenom": client_prenom,
                "ClientAdr": client_adr1, "ClientCP": client_cp,
                "ClientVille": client_ville,
                "DateSign": str(date_sign_db or ""),
                "Vendeur": nom_vend_db,
                "AncienEtat": lib_etat_actuel,
                "NouvelEtat": new_etat_lib,
                "Remarques": remarques,
                "_id_contrat": id_contrat, "_old_etat": id_etat_actuel,
                "_new_etat": new_etat, "_info_existing": ctt.get("info_partagee") or "",
            })
            resume.nb_resilies += 1
        else:
            # Deja statue
            runs.append({
                "NumBS": num_bs, "ClientNom": client_nom,
                "ClientPrenom": client_prenom, "ClientCP": client_cp,
                "ClientVille": client_ville,
                "DateSign": str(date_sign_db or ""),
                "Vendeur": nom_vend_db,
                "StatutImport": statut, "EtatEnregistre": lib_etat_actuel,
            })
            resume.nb_deja_statues += 1

    # PASSE PROD : reset etat sur les modifies
    if not p.simulation:
        for row in modifies:
            id_ct = row.pop("_id_contrat", None)
            old_etat = row.pop("_old_etat", 0)
            new_etat = row.pop("_new_etat", 0)
            info_existing = row.pop("_info_existing", "")
            if not id_ct or not new_etat:
                continue
            try:
                new_info = (info_existing or "") + f"\nMotif Résil : {row.get('Remarques', '')}"
                db.query(
                    """UPDATE adv.pgt_str_contrat
                          SET id_etat_contrat = ?, info_partagee = ?,
                              mois_p = NULL,
                              modif_op = ?, modif_date = NOW(),
                              modif_elem = 'modif'
                        WHERE id_contrat = ?""",
                    (int(new_etat), new_info, int(op_id), int(id_ct)),
                )
                _ajoute_histo_str_etat(int(id_ct), int(old_etat), int(new_etat),
                                       "", op_id)
            except Exception as e:
                row["Erreur"] = str(e)
    else:
        # Nettoyage internal keys quand meme
        for row in modifies:
            row.pop("_id_contrat", None)
            row.pop("_old_etat", None)
            row.pop("_new_etat", None)
            row.pop("_info_existing", None)

    wb.close()


def capitalise_str(s: str) -> str:
    """Capitalise la 1ere lettre (equivalent WinDev capitalise)."""
    return s[:1].upper() + s[1:].lower() if s else ""


def run_import_str(
    p: ImportStrParams, files: list[tuple[str, bytes]], op_id: int,
) -> ImportStrResult:
    """Dispatcher principal."""
    label = TYPE_LABELS.get(p.type_import, "?")
    if not files:
        return ImportStrResult(
            ok=False, type_import=p.type_import, type_label=label,
            simulation=p.simulation, resume=ImportStrResume(),
            message="Aucun fichier fourni.",
        )

    resume = ImportStrResume(nb_fichiers=len(files))
    ajoutes: list[dict] = []; modifies: list[dict] = []
    non_trouves: list[dict] = []; runs: list[dict] = []
    pb_vendeur: list[dict] = []
    fichiers_traites: list[str] = []

    for fname, content in files:
        fichiers_traites.append(fname)
        if p.type_import == 1:
            _import_journalier_str(
                p, fname, content, op_id,
                ajoutes, modifies, pb_vendeur, resume,
            )
        elif p.type_import == 2:
            _import_run_str(
                p, fname, content, op_id,
                runs, modifies, non_trouves, pb_vendeur, resume,
            )
        elif p.type_import == 3:
            _import_resil_hebdo_str(
                p, fname, content, op_id,
                runs, modifies, non_trouves, pb_vendeur, resume,
            )

    # PASSE PROD
    nb_crees = 0; nb_reattrib = 0
    if not p.simulation:
        db = get_pg_connection("adv")
        for row in ajoutes:
            pl = row.pop("_payload_create", None)
            if not pl or not pl.get("id_salarie"):
                continue
            try:
                new_id = _create_str_contrat(pl, op_id)
                row["IdContratCree"] = new_id
                nb_crees += 1
            except Exception as e:
                row["Erreur"] = str(e)
        for row in pb_vendeur:
            id_ct = row.pop("_id_contrat", None)
            if not id_ct or row.get("Erreur") != "vendeur réattribué":
                continue
            try:
                db.query(
                    """UPDATE adv.pgt_str_contrat
                          SET id_salarie = ?,
                              modif_op = ?, modif_date = NOW(),
                              modif_elem = 'modif'
                        WHERE id_contrat = ?""",
                    (int(row["NewIdSalarie"]), int(op_id), int(id_ct)),
                )
                nb_reattrib += 1
            except Exception as e:
                row["ErreurMaj"] = str(e)

    for row in ajoutes:
        row.pop("_payload_create", None)
    for row in pb_vendeur:
        row.pop("_id_contrat", None)

    res = ImportStrResult(
        ok=True, type_import=p.type_import, type_label=label,
        simulation=p.simulation, resume=resume,
        fichiers_traites=fichiers_traites,
        contrats_ajoutes=ajoutes, contrats_modifies=modifies,
        contrats_non_trouves=non_trouves, contrats_run=runs,
        pb_vendeur=pb_vendeur,
        message=(
            f"{len(files)} fichier(s) | Ajoutés {resume.nb_ajoutes} | "
            f"Déjà saisis {resume.nb_deja_saisis} | Validés {resume.nb_valides} | "
            f"Résiliés {resume.nb_resilies} | Introuvables {resume.nb_introuvables} | "
            f"Pb vendeur {resume.nb_pb_vendeur}. "
            + (f"PRODUCTION : {nb_crees} créés, {nb_reattrib} reattributions."
               if not p.simulation else "(SIMULATION)")
        ),
    )
    _attach_xlsx_and_mail_str(res, op_id)
    return res


def _build_xlsx_str(res: ImportStrResult) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = Workbook(); ws = wb.active; ws.title = "Résumé"
    header_fill = PatternFill("solid", fgColor="17494E")
    header_font = Font(bold=True, color="FFFFFF")
    items = [
        ("NB Fichiers", res.resume.nb_fichiers),
        ("NB Ajoutés", res.resume.nb_ajoutes),
        ("NB Validés", res.resume.nb_valides),
        ("NB Résiliés", res.resume.nb_resilies),
        ("NB Déjà saisis", res.resume.nb_deja_saisis),
        ("NB Déjà statués", res.resume.nb_deja_statues),
        ("NB Introuvables", res.resume.nb_introuvables),
        ("NB Pb Vendeur", res.resume.nb_pb_vendeur),
        ("NB Erreurs", res.resume.nb_erreurs),
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
        ("Déjà saisis", res.contrats_modifies),
        ("Non trouvés", res.contrats_non_trouves),
        ("RUN", res.contrats_run),
        ("Pb Vendeur", res.pb_vendeur),
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


def _attach_xlsx_and_mail_str(res: ImportStrResult, op_id: int) -> None:
    from app.shared.notifications.mail import envoi_mail
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = "_SIMU" if res.simulation else ""
    prefix_map = {1: "ImportJournalierSTR", 2: "ImportRunSTR",
                  3: "ImportResilHebdoSTR"}
    xlsx_name = f"{prefix_map.get(res.type_import, 'ImportSTR')}_{ts}{suffix}.xlsx"
    try:
        xlsx_bytes = _build_xlsx_str(res)
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
    sujet = (f"{sujet_pref}Importation {res.type_label} STRATO "
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
