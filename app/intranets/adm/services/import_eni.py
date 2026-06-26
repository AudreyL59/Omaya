"""Service Fen_ImportENI (ADM Imports Bases -> Import partenaire ENI/PLENITUDE).

5 types d'import :
 1. Base Journaliere CALL  -> ImportJournalier()
 2. RUN Valides             -> importRUNValides()
 3. RUN Resils              -> importRUNResil()
 4. Salesforce              -> ImportSalesforce()
 5. Base journaliere ENI    -> ImportJournalierENI()

Pour chaque type, lecture d'un Excel + analyse + 6 tables resultats :
 - Resume importation (compteurs)
 - Contrats modifies
 - Contrats non trouves
 - Contrats RUN
 - Probleme Vendeur
 - Contrat Import Journ ENI

Les procedures metier seront codees au fur et a mesure (placeholder
pour l'instant : retourne un resume vide + erreur 'pas encore code').
"""

from __future__ import annotations

import io
import re
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection


class ImportEniParams(BaseModel):
    type_import: int                  # 1..5
    simulation: bool = True
    periode1_du: str = ""
    periode1_au: str = ""
    periode1_mois_paiement: str = ""  # 'MM-YYYY'
    periode2_du: str = ""
    periode2_au: str = ""
    periode2_mois_paiement: str = ""
    mois_paiement_distrib: str = ""
    maj_produit_contrat_stand: bool = True
    maj_etats_contrats_existants: bool = False


# Mapping colonnes par defaut pour 'Base Journaliere ENI'
# (cf. ecran onglet 'Base Journ. ENI').
COLS_BJ_ENI = {
    "num_contrat": "A",
    "vendeur_nom": "D",
    "date_signature": "E",
    "type_offre": "F",
    "statut": "G",
    "offre": "I",
    "puissance": "J",
    "type_comptage": "K",
    "car": "L",
    "client_cp": "S",
    "client_gsm": "T",
    "date_heure_crea": "W",
    "addon": "AF",
    "opt_mail": "AH",
    "mandat_rib": "AI",
    "note_globale": "AJ",
    "info_notation": "AK",
}


# Mapping colonnes par defaut pour 'RUN Resils' (cf. ecran onglet
# 'RUN Resils').
COLS_RUN_R = {
    "num_contrat": "A",
    "vendeur_nom": "G",
    "type_offre": "H",
    "date_signature": "L",
}


# Mapping colonnes par defaut pour 'RUN Valides' (cf. ecran Fen_ImportENI
# onglet 'RUN Valide'). Les lettres correspondent aux colonnes Excel.
COLS_RUN_V = {
    "num_contrat": "A",
    "vendeur_nom": "G",
    "type_offre": "H",
    "offre_reclassifiee": "I",
    "statut_elec": "J",
    "statut_gaz": "K",
    "date_signature": "M",
    "car": "P",
    "puissance": "Q",
    "type_comptage": "R",
    "mail_fourni": "AB",
    "protection": "AC",
}


# Mapping colonnes Excel par defaut pour 'Base Journaliere CALL'
# (cf. ecran Fen_ImportENI). Les lettres correspondent aux colonnes Excel
# (A=1, B=2, ...). Sera surchargee via parametres BDD au fil de l'eau.
COLS_BJ_CALL = {
    "num_contrat": "A",
    "date_signature": "B",
    "vendeur_nom": "C",
    "client_nom": "D",
    "client_prenom": "E",
    "client_adresse": "F",
    "client_cplt": "G",
    "client_cp": "H",
    "client_ville": "I",
    "client_tel": "J",
    "client_gsm": "K",
    "client_mail": "L",
    "car": "M",
    "offre": "M",  # cf WinDev (doublon CAR/Offre M)
    "delai_retract": "N",
    "lib_statut": "S",
    "comment": "R",
    "heure": "U",
    "indice": "V",
    "date_naissance": "W",
    "serv_entretien": "X",
    "code_enr": "Y",
    "puissance": "Z",
}


def _col_letter_to_index(letter: str) -> int:
    """A->1, B->2, ..., Z->26, AA->27, etc."""
    letter = (letter or "").strip().upper()
    if not letter:
        return 0
    n = 0
    for c in letter:
        n = n * 26 + (ord(c) - 64)
    return n


class ImportEniResume(BaseModel):
    nb_valides: int = 0
    nb_deja_statues: int = 0
    nb_doublons: int = 0
    nb_introuvables: int = 0
    nb_decommissions: int = 0
    nb_resilies: int = 0
    nb_modifications: int = 0
    nb_erreurs_mails: int = 0
    nb_erreurs_entretien: int = 0
    nb_contrats_hors_delai: int = 0
    nb_erreurs_offres: int = 0
    nb_erreurs_type_comptage: int = 0
    nb_erreurs_energie_verte: int = 0
    nb_erreurs_car: int = 0
    nb_erreurs_puiss: int = 0
    nb_erreurs_reforest: int = 0
    nb_erreurs_protection: int = 0


class ImportEniResult(BaseModel):
    ok: bool
    type_import: int
    type_label: str
    simulation: bool
    resume: ImportEniResume
    contrats_modifies: list[dict] = []
    contrats_non_trouves: list[dict] = []
    contrats_run: list[dict] = []
    pb_vendeur: list[dict] = []
    contrat_import_journ_eni: list[dict] = []
    message: str = ""


TYPE_LABELS = {
    1: "Base Journalière CALL",
    2: "RUN Valides",
    3: "RUN Résils",
    4: "Base journalière ENI",
}


def run_import(p: ImportEniParams, file_bytes: bytes, op_id: int) -> ImportEniResult:
    """Dispatcher principal."""
    label = TYPE_LABELS.get(p.type_import, "?")
    if not file_bytes:
        return ImportEniResult(
            ok=False, type_import=p.type_import, type_label=label,
            simulation=p.simulation, resume=ImportEniResume(),
            message="Aucun fichier fourni.",
        )

    if p.type_import == 1:
        return _import_journalier_call(p, file_bytes, op_id)
    if p.type_import == 2:
        return _import_run_valides(p, file_bytes, op_id)
    if p.type_import == 3:
        return _import_run_resil(p, file_bytes, op_id)
    if p.type_import == 4:
        return _import_journalier_eni(p, file_bytes, op_id)

    # TODO : autres procedures
    return ImportEniResult(
        ok=True, type_import=p.type_import, type_label=label,
        simulation=p.simulation, resume=ImportEniResume(),
        message=(f"Import {label} : procedure non encore codée. "
                 f"Fichier reçu ({len(file_bytes)} octets), mode "
                 f"{'simulation' if p.simulation else 'PRODUCTION'}."),
    )


# ---------------------------------------------------------------------------
# Type 1 : Base Journaliere CALL (ImportJournalier)
# ---------------------------------------------------------------------------


def _cell(ws, row: int, col_idx: int):
    """Lit une cellule Excel et renvoie une str trim."""
    if col_idx <= 0:
        return ""
    v = ws.cell(row=row, column=col_idx).value
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, date):
        return v.strftime("%d/%m/%Y")
    return str(v).strip()


def _parse_date_fr(s: str) -> Optional[date]:
    """JJ/MM/AAAA ou variantes ISO -> date."""
    if not s:
        return None
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_int(s: str) -> int:
    if not s:
        return 0
    m = re.search(r"-?\d+", s.replace(" ", ""))
    return int(m.group(0)) if m else 0


def _normaliser_nom(s: str) -> str:
    """Uppercase + sans accent + sans doubles espaces + sans tirets."""
    if not s:
        return ""
    s = s.upper().strip()
    # Strip accents (approximatif)
    for a, b in [("À", "A"), ("Â", "A"), ("Ä", "A"), ("É", "E"), ("È", "E"),
                 ("Ê", "E"), ("Ë", "E"), ("Î", "I"), ("Ï", "I"), ("Ô", "O"),
                 ("Ö", "O"), ("Ù", "U"), ("Û", "U"), ("Ü", "U"), ("Ç", "C")]:
        s = s.replace(a, b)
    s = s.replace("-", " ")
    while "  " in s:
        s = s.replace("  ", " ")
    return s.strip()


def _affectation_vendeur(id_salarie: int, _date_sign: Optional[date]) -> tuple[str, str]:
    """Retourne (lib_agence, lib_equipe) du vendeur a une date donnee.
    Pour l'instant : derniere affectation connue (simplification, pas
    de versioning historique date)."""
    if not id_salarie:
        return ("", "")
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT o.lib_orga, o.id_type_niveau_orga
             FROM rh.pgt_salarie_organigramme so
             JOIN rh.pgt_organigramme o ON o.idorganigramme = so.idorganigramme
            WHERE so.id_salarie = ?
              AND (so.modif_elem IS NULL OR so.modif_elem NOT LIKE '%suppr%')""",
        (int(id_salarie),),
    ) or []
    agence = ""
    equipe = ""
    for r in rows:
        lvl = r.get("id_type_niveau_orga")
        lib = r.get("lib_orga") or ""
        if lvl == 3 and not agence:
            agence = lib
        elif lvl == 4 and not equipe:
            equipe = lib
    return (agence, equipe)


def _info_salarie(id_salarie: int) -> dict:
    if not id_salarie:
        return {}
    db = get_pg_connection("rh")
    r = db.query_one(
        """SELECT id_salarie, nom, prenom
             FROM rh.pgt_salarie WHERE id_salarie = ?""",
        (int(id_salarie),),
    )
    return r or {}


def _import_journalier_call(
    p: ImportEniParams, file_bytes: bytes, op_id: int,
) -> ImportEniResult:
    """Import 'Base Journaliere CALL' ENI : pour chaque ligne, cherche
    le contrat dans adv.pgt_eni_contrat par num_bs et :
      - Si trouve : ajoute a contrats_modifies + check vendeur (-> pb_vendeur si mismatch)
        + applique etat_contrat (15=Refus CALL si 'refus' dans statut, 51->37)
        + si pas simulation : UPDATE code_enr + non_call=false
      - Si pas trouve : ajoute a contrats_non_trouves
    """
    from openpyxl import load_workbook

    label = TYPE_LABELS.get(1, "Base Journalière CALL")
    try:
        wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as e:
        return ImportEniResult(
            ok=False, type_import=1, type_label=label,
            simulation=p.simulation, resume=ImportEniResume(),
            message=f"Lecture Excel KO : {e}",
        )
    ws = wb.active

    # Mapping colonnes (defaut ; sera parametre BDD plus tard)
    cols = {k: _col_letter_to_index(v) for k, v in COLS_BJ_CALL.items()}

    resume = ImportEniResume()
    modifs: list[dict] = []
    non_trouves: list[dict] = []
    pb_vendeur: list[dict] = []

    db = get_pg_connection("adv")
    n_rows = ws.max_row or 0

    for i in range(2, n_rows + 1):
        num_contrat = _cell(ws, i, cols["num_contrat"]).upper()
        if not num_contrat:
            continue
        date_sign_s = _cell(ws, i, cols["date_signature"])
        date_sign = _parse_date_fr(date_sign_s)
        vendeur_cell = _cell(ws, i, cols["vendeur_nom"])
        car = _cell(ws, i, cols["car"])
        offre = _cell(ws, i, cols["offre"])
        lib_statut = _cell(ws, i, cols["lib_statut"])

        client = {
            "nom": _cell(ws, i, cols["client_nom"]),
            "prenom": _cell(ws, i, cols["client_prenom"]),
            "adresse": _cell(ws, i, cols["client_adresse"]),
            "cplt": _cell(ws, i, cols["client_cplt"]),
            "cp": _cell(ws, i, cols["client_cp"]),
            "ville": _cell(ws, i, cols["client_ville"]),
            "tel": _cell(ws, i, cols["client_tel"]),
            "gsm": _cell(ws, i, cols["client_gsm"]),
            "mail": _cell(ws, i, cols["client_mail"]),
            "date_naiss": _cell(ws, i, cols.get("date_naissance") or 0),
        }

        code_enr = _cell(ws, i, cols["code_enr"])
        heure = _cell(ws, i, cols["heure"])
        indice = _cell(ws, i, cols["indice"])
        if not code_enr:
            heure_norm = (heure or "0000").replace(":", "")[:4]
            code_enr = f"AGT_0000_IND_{indice}_TEL_123456789_TIME_{heure_norm}00"

        puiss = _parse_int(_cell(ws, i, cols["puissance"]))

        # Lookup contrat par num_bs (= num_contrat)
        r = db.query_one(
            """SELECT id_contrat, id_salarie, id_client, id_ste, num_bs,
                      id_produit, id_etat_contrat, date_signature,
                      gaz_car_relevee, elec_puissance, gaz_actif
                 FROM adv.pgt_eni_contrat
                WHERE UPPER(num_bs) = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (num_contrat,),
        )

        if not r:
            non_trouves.append({
                "NumCtt": num_contrat,
                "DateSign": date_sign_s,
                "Vendeur": vendeur_cell,
                "Produit": offre,
                "CAR": car,
                "Puiss": puiss,
                "LibStatut": lib_statut,
                "Nom Cli": client["nom"],
                "Prenom Cli": client["prenom"],
                "CP": client["cp"],
                "Ville": client["ville"],
                "GSM": client["gsm"],
                "CodeEnr": code_enr,
            })
            resume.nb_introuvables += 1
            continue

        # Trouve : on note la modif
        id_contrat = int(r["id_contrat"])
        id_salarie_db = int(r.get("id_salarie") or 0)
        etat_actuel = int(r.get("id_etat_contrat") or 0)
        nouvel_etat = etat_actuel
        if etat_actuel == 51:
            nouvel_etat = 37
        if "refus" in (lib_statut or "").lower():
            nouvel_etat = 15

        # Check vendeur cell vs vendeur en BDD
        sal_info = _info_salarie(id_salarie_db)
        nom_db = _normaliser_nom(
            f"{sal_info.get('nom', '')} {sal_info.get('prenom', '')}".strip()
        )
        nom_cell = _normaliser_nom(vendeur_cell)
        agence, equipe = _affectation_vendeur(id_salarie_db, date_sign)

        row_common = {
            "NumCtt": r.get("num_bs"),
            "DateSign": str(r.get("date_signature") or ""),
            "IdSalarie": id_salarie_db,
            "Societe": int(r.get("id_ste") or 0),
            "Agence": agence,
            "Equipe": equipe,
            "Produit": int(r.get("id_produit") or 0),
            "CAR": int(r.get("gaz_car_relevee") or 0),
            "Puiss Elec": int(r.get("elec_puissance") or 0),
            "Etat actuel": etat_actuel,
            "Nouvel etat": nouvel_etat,
            "Gaz actif": bool(r.get("gaz_actif")),
            "CodeEnr": code_enr,
            "Cli Nom": client["nom"],
            "Cli Prenom": client["prenom"],
            "Cli GSM": client["gsm"],
            "Cli Mail": client["mail"],
        }

        if nom_cell and nom_db and nom_cell != nom_db:
            pb_vendeur.append({
                **row_common,
                "Vendeur Import": vendeur_cell,
                "Vendeur OMAYA": nom_db,
            })

        modifs.append(row_common)
        resume.nb_modifications += 1

        # MAJ reelle (hors simulation)
        if not p.simulation:
            db.query(
                """UPDATE adv.pgt_eni_contrat
                      SET code_enr = ?,
                          non_call = FALSE,
                          id_etat_contrat = ?,
                          modif_date = NOW(),
                          modif_op = ?,
                          modif_elem = 'modif'
                    WHERE id_contrat = ?""",
                (code_enr, nouvel_etat, int(op_id), id_contrat),
            )

    wb.close()

    return ImportEniResult(
        ok=True, type_import=1, type_label=label,
        simulation=p.simulation, resume=resume,
        contrats_modifies=modifs,
        contrats_non_trouves=non_trouves,
        pb_vendeur=pb_vendeur,
        message=(
            f"{n_rows - 1} ligne(s) lue(s) | "
            f"{resume.nb_modifications} contrat(s) trouvé(s) | "
            f"{resume.nb_introuvables} introuvable(s) | "
            f"{len(pb_vendeur)} pb vendeur. "
            f"{'(SIMULATION : aucune écriture)' if p.simulation else '(PRODUCTION : MAJ appliquées)'}"
        ),
    )


# ---------------------------------------------------------------------------
# Type 2 : RUN Valides (importRUNValides)
# ---------------------------------------------------------------------------


def _conso_gaz_type(car: int) -> int:
    if 1000 <= car <= 6000: return 1
    if 6001 <= car <= 13000: return 2
    if car >= 13001: return 3
    return 0


def _conso_elec_type(puiss: int) -> int:
    if puiss == 3: return 1
    if puiss == 6: return 2
    if puiss == 9: return 3
    if puiss >= 12: return 4
    return 0


def _dernier_jour_mois(s: str) -> Optional[date]:
    """'06-2025' ou 'MM-YYYY' -> dernier jour du mois."""
    if not s:
        return None
    s = s.strip()
    try:
        if "-" in s:
            mm, yy = s.split("-")
            mois = int(mm); annee = int(yy)
        else:
            return None
        # Calcul dernier jour
        if mois == 12:
            return date(annee + 1, 1, 1) - __import__("datetime").timedelta(days=1)
        return date(annee, mois + 1, 1) - __import__("datetime").timedelta(days=1)
    except (ValueError, TypeError):
        return None


def _import_run_valides(
    p: ImportEniParams, file_bytes: bytes, op_id: int,
) -> ImportEniResult:
    """Import 'RUN Valides' ENI : analyse contrats valides et calcule
    nouvel etat (19/46/47/...) + MoisP selon la periode.

    Phase 1 : detection seulement (pas de MAJ), pas de XLSX/mail."""
    from openpyxl import load_workbook

    label = TYPE_LABELS.get(2, "RUN Valides")
    try:
        wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as e:
        return ImportEniResult(
            ok=False, type_import=2, type_label=label,
            simulation=p.simulation, resume=ImportEniResume(),
            message=f"Lecture Excel KO : {e}",
        )
    ws = wb.active

    cols = {k: _col_letter_to_index(v) for k, v in COLS_RUN_V.items()}

    # Dates des periodes
    d1_du = _parse_date_fr(p.periode1_du) or date(1900, 1, 1)
    d1_au = _parse_date_fr(p.periode1_au) or date(2100, 12, 31)
    d2_du = _parse_date_fr(p.periode2_du) or date(1900, 1, 1)
    d2_au = _parse_date_fr(p.periode2_au) or date(2100, 12, 31)
    mp1 = _dernier_jour_mois(p.periode1_mois_paiement)
    mp2 = _dernier_jour_mois(p.periode2_mois_paiement)
    mp_distrib = _dernier_jour_mois(p.mois_paiement_distrib)
    import datetime as _dt
    d1_du_m1 = d1_du.replace(month=d1_du.month - 1) if d1_du.month > 1 else d1_du.replace(year=d1_du.year - 1, month=12)
    d1_au_m1 = d1_au.replace(month=d1_au.month - 1) if d1_au.month > 1 else d1_au.replace(year=d1_au.year - 1, month=12)

    resume = ImportEniResume()
    contrats_run: list[dict] = []
    hors_delai: list[dict] = []
    doublons: list[dict] = []
    non_trouves: list[dict] = []

    db = get_pg_connection("adv")
    n_rows = ws.max_row or 0

    for i in range(2, n_rows + 1):
        num_contrat = _cell(ws, i, cols["num_contrat"])
        if not num_contrat:
            continue
        type_offre = _cell(ws, i, cols["type_offre"]).strip()
        vend_full = _cell(ws, i, cols["vendeur_nom"])
        vendeur_nom = vend_full.split(" / ")[0] if vend_full else ""
        offre_reclass = _cell(ws, i, cols["offre_reclassifiee"]).strip()
        statut_gaz = _cell(ws, i, cols["statut_gaz"]).upper()
        statut_elec = _cell(ws, i, cols["statut_elec"]).upper()
        b_gaz_actif = (statut_gaz == "ON_SUPPLY")
        b_elec_actif = (statut_elec == "ON_SUPPLY")
        date_sign = _parse_date_fr(_cell(ws, i, cols["date_signature"]))
        car = _parse_int(_cell(ws, i, cols["car"]))
        puiss_elec = _parse_int(_cell(ws, i, cols["puissance"]))
        type_comptage = _cell(ws, i, cols["type_comptage"])
        opt_hphc = "HPHC" in type_comptage.upper()
        montant_mails = _parse_int(_cell(ws, i, cols["mail_fourni"]))
        montant_protect = _parse_int(_cell(ws, i, cols["protection"]))
        opt_mails = montant_mails > 0
        opt_protect = montant_protect > 0

        # Lookup contrat(s)
        rows_ctt = db.query(
            """SELECT id_contrat, id_salarie, id_client, id_ste, num_bs,
                      id_produit, id_etat_contrat, date_signature,
                      gaz_car_relevee, gaz_car_declaree, elec_puissance,
                      gaz_actif, elec_actif, code_enr, non_call,
                      mois_p, notation
                 FROM adv.pgt_eni_contrat
                WHERE UPPER(num_bs) = UPPER(?)
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                """,
            (num_contrat,),
        ) or []

        if len(rows_ctt) == 0:
            non_trouves.append({
                "NumCtt": num_contrat,
                "DateSign": _cell(ws, i, cols["date_signature"]),
                "Vendeur": vendeur_nom,
                "CAR": car,
                "Puiss": puiss_elec,
                "GazActif": b_gaz_actif,
                "ElecActif": b_elec_actif,
                "TypeOffre": type_offre,
            })
            resume.nb_introuvables += 1
            continue
        if len(rows_ctt) > 1:
            resume.nb_doublons += 1
            for r in rows_ctt:
                doublons.append({
                    "NumCtt": num_contrat,
                    "id_contrat_OMAYA": r.get("id_contrat"),
                    "DateSign_OMAYA": str(r.get("date_signature") or ""),
                    "TypeOffre": type_offre,
                    "CAR": car,
                    "Puiss": puiss_elec,
                    "GazActif_OMAYA": bool(r.get("gaz_actif")),
                    "ElecActif_OMAYA": bool(r.get("elec_actif")),
                })
            continue

        r = rows_ctt[0]
        id_contrat = int(r["id_contrat"])
        date_sign_omaya = r.get("date_signature")
        etat_actuel = int(r.get("id_etat_contrat") or 0)
        car_omaya = int(r.get("gaz_car_relevee") or 0)
        puiss_omaya = int(r.get("elec_puissance") or 0)

        # Periode
        mois_paiement = None
        periode_lbl = ""
        if date_sign_omaya:
            if d1_du <= date_sign_omaya <= d1_au:
                mois_paiement = mp1; periode_lbl = "Période 1"
            elif d2_du <= date_sign_omaya <= d2_au:
                mois_paiement = mp2; periode_lbl = "Période 2"
            elif d1_du_m1 <= date_sign_omaya <= d1_au_m1:
                mois_paiement = mp1; periode_lbl = "Période -1 mois"
            else:
                resume.nb_contrats_hors_delai += 1
                hors_delai.append({
                    "NumCtt": num_contrat,
                    "DateSign": str(date_sign_omaya),
                    "TypeOffre": type_offre,
                    "CAR": car,
                    "Puiss": puiss_elec,
                })

        # Etat actuel : check IDTypeEtat
        etat_info = db.query_one(
            """SELECT id_type_etat, lib_etat FROM adv.pgt_eni_etat_contrat
                WHERE id_etat = ? LIMIT 1""",
            (etat_actuel,),
        )
        id_type_etat = int(etat_info.get("id_type_etat") or 0) if etat_info else 0

        # Determination du nouvel etat (cf WinDev)
        nouvel_etat = etat_actuel
        gaz_valide_nouv = b_gaz_actif
        elec_valide_nouv = b_elec_actif
        maj_etat_flag = False

        # IDTypeEtat 1 ou 2, ou IDetat 54 -> contrat eligible MAJ
        eligible = (id_type_etat in (1, 2)) or etat_actuel == 54
        if eligible:
            if not offre_reclass:
                nouvel_etat = 19  # Valide - Paye par l'opérateur
                if type_offre == "Dual":
                    gaz_valide_nouv = True; elec_valide_nouv = True
                elif "Gaz" in type_offre.lower() or "gaz" in type_offre.lower():
                    gaz_valide_nouv = True; elec_valide_nouv = False
                elif "Elec" in type_offre.lower() or "elec" in type_offre.lower():
                    gaz_valide_nouv = False; elec_valide_nouv = True
            else:
                if offre_reclass == "Solo Elec":
                    nouvel_etat = 46  # Partiel Elec
                    gaz_valide_nouv = False
                else:
                    nouvel_etat = 47  # Partiel Gaz
                    elec_valide_nouv = False
            maj_etat_flag = True
            resume.nb_valides += 1
        else:
            resume.nb_deja_statues += 1

        # Erreurs CAR / Puissance a la baisse
        maj_car_flag = False
        if car < car_omaya:
            resume.nb_erreurs_car += 1
            if p.maj_produit_contrat_stand:
                maj_car_flag = True
        if puiss_elec < puiss_omaya:
            resume.nb_erreurs_puiss += 1
            if p.maj_produit_contrat_stand:
                maj_car_flag = True

        # Options : look up
        opt = db.query_one(
            """SELECT opt_mail, opt_e_facture, opt_e_communication,
                      opt_optin_commercial, opt_hp_hc, opt_protection,
                      opt_entretien, opt_energie_verte_gaz,
                      opt_energie_verte_elec, opt_reforestation
                 FROM adv.pgt_eni_contrat_option WHERE id_contrat = ? LIMIT 1""",
            (id_contrat,),
        )
        if opt:
            if (not opt_mails and opt.get("opt_e_facture")
                    and opt.get("opt_e_communication")
                    and opt.get("opt_optin_commercial")):
                resume.nb_erreurs_mails += 1
            if not opt_hphc and opt.get("opt_hp_hc"):
                resume.nb_erreurs_type_comptage += 1
            if not opt_protect and opt.get("opt_protection"):
                resume.nb_erreurs_protection += 1

        contrats_run.append({
            "NumCtt": r.get("num_bs"),
            "DateSign": str(date_sign_omaya or ""),
            "Periode": periode_lbl,
            "MoisP": str(mois_paiement) if mois_paiement else "",
            "TypeOffre": type_offre,
            "OffreReclass": offre_reclass,
            "CAR Excel": car,
            "CAR OMAYA": car_omaya,
            "Puiss Excel": puiss_elec,
            "Puiss OMAYA": puiss_omaya,
            "GazActif Excel": b_gaz_actif,
            "ElecActif Excel": b_elec_actif,
            "ConsoGaz": _conso_gaz_type(car_omaya),
            "ConsoElec": _conso_elec_type(puiss_omaya),
            "Etat actuel": etat_actuel,
            "TypeEtat": id_type_etat,
            "Nouvel etat": nouvel_etat,
            "MAJ etat": maj_etat_flag,
            "MAJ car": maj_car_flag,
            "OptMail Excel": opt_mails,
            "OptHPHC Excel": opt_hphc,
            "OptProtec Excel": opt_protect,
        })

    wb.close()

    return ImportEniResult(
        ok=True, type_import=2, type_label=label,
        simulation=p.simulation, resume=resume,
        contrats_run=contrats_run + hors_delai,
        contrats_non_trouves=non_trouves,
        contrats_modifies=doublons,  # on reutilise cet onglet pour les doublons
        message=(
            f"{n_rows - 1} ligne(s) lue(s) | "
            f"Validés {resume.nb_valides} | "
            f"Déjà statués {resume.nb_deja_statues} | "
            f"Hors délai {resume.nb_contrats_hors_delai} | "
            f"Doublons {resume.nb_doublons} | "
            f"Introuvables {resume.nb_introuvables}. "
            f"{'(SIMULATION)' if p.simulation else '(PRODUCTION — phase 1 : pas encore de MAJ)'}"
        ),
    )


# ---------------------------------------------------------------------------
# Type 3 : RUN Resils (importRUNResil)
# ---------------------------------------------------------------------------


def _import_run_resil(
    p: ImportEniParams, file_bytes: bytes, op_id: int,
) -> ImportEniResult:
    """Import 'RUN Resils' ENI : pour chaque ligne, determine si le
    contrat doit etre :
      - Resilie (etat 16) si type_etat in (1,2) ou etat=54 ou
        (type_etat=5 ET meme mois paiement)
      - Decommissionne (20=total, 49=partiel ELEC, 50=partiel GAZ)
        si type_etat=5 et mois paiement different
      - Deja statue sinon
    Phase 1 : detection seulement."""
    from openpyxl import load_workbook

    label = TYPE_LABELS.get(3, "RUN Résils")
    try:
        wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as e:
        return ImportEniResult(
            ok=False, type_import=3, type_label=label,
            simulation=p.simulation, resume=ImportEniResume(),
            message=f"Lecture Excel KO : {e}",
        )
    ws = wb.active

    cols = {k: _col_letter_to_index(v) for k, v in COLS_RUN_R.items()}

    d1_du = _parse_date_fr(p.periode1_du) or date(1900, 1, 1)
    d1_au = _parse_date_fr(p.periode1_au) or date(2100, 12, 31)
    d2_du = _parse_date_fr(p.periode2_du) or date(1900, 1, 1)
    d2_au = _parse_date_fr(p.periode2_au) or date(2100, 12, 31)
    mp1 = _dernier_jour_mois(p.periode1_mois_paiement)
    mp2 = _dernier_jour_mois(p.periode2_mois_paiement)
    d1_du_m1 = (d1_du.replace(month=d1_du.month - 1) if d1_du.month > 1
                else d1_du.replace(year=d1_du.year - 1, month=12))
    d1_au_m1 = (d1_au.replace(month=d1_au.month - 1) if d1_au.month > 1
                else d1_au.replace(year=d1_au.year - 1, month=12))

    resume = ImportEniResume()
    contrats_run: list[dict] = []
    doublons: list[dict] = []
    non_trouves: list[dict] = []
    hors_delai: list[dict] = []

    db = get_pg_connection("adv")
    n_rows = ws.max_row or 0

    for i in range(2, n_rows + 1):
        num_contrat = _cell(ws, i, cols["num_contrat"])
        if not num_contrat:
            continue
        type_offre = _cell(ws, i, cols["type_offre"]).strip()
        vend_full = _cell(ws, i, cols["vendeur_nom"])
        vendeur_nom = vend_full.split(" / ")[0] if vend_full else ""
        date_sign_s = _cell(ws, i, cols["date_signature"])

        rows_ctt = db.query(
            """SELECT id_contrat, id_salarie, id_client, num_bs,
                      id_etat_contrat, date_signature, mois_p
                 FROM adv.pgt_eni_contrat
                WHERE UPPER(num_bs) = UPPER(?)
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
            (num_contrat,),
        ) or []

        if len(rows_ctt) == 0:
            non_trouves.append({
                "NumCtt": num_contrat,
                "DateSign": date_sign_s,
                "Vendeur": vendeur_nom,
                "TypeOffre": type_offre,
                "Onglet": "RESIL",
            })
            resume.nb_introuvables += 1
            continue
        if len(rows_ctt) > 1:
            resume.nb_doublons += 1
            for r in rows_ctt:
                doublons.append({
                    "NumCtt": num_contrat,
                    "id_contrat_OMAYA": r.get("id_contrat"),
                    "DateSign_OMAYA": str(r.get("date_signature") or ""),
                    "TypeOffre": type_offre,
                    "Onglet": "RESIL",
                })
            continue

        r = rows_ctt[0]
        id_contrat = int(r["id_contrat"])
        date_sign_omaya = r.get("date_signature")
        etat_actuel = int(r.get("id_etat_contrat") or 0)
        mois_p_omaya = r.get("mois_p")

        # Periode + MoisP
        mois_paiement = None
        periode_lbl = ""
        if date_sign_omaya:
            if d1_du <= date_sign_omaya <= d1_au:
                mois_paiement = mp1; periode_lbl = "Période 1"
            elif d2_du <= date_sign_omaya <= d2_au:
                mois_paiement = mp2; periode_lbl = "Période 2"
            elif d1_du_m1 <= date_sign_omaya <= d1_au_m1:
                mois_paiement = mp1; periode_lbl = "Période -1 mois"
            else:
                resume.nb_contrats_hors_delai += 1
                hors_delai.append({
                    "NumCtt": num_contrat,
                    "DateSign": str(date_sign_omaya),
                    "TypeOffre": type_offre,
                    "Onglet": "RESIL HORS DELAI",
                })

        # Lookup type_etat
        etat_info = db.query_one(
            """SELECT id_type_etat, lib_etat FROM adv.pgt_eni_etat_contrat
                WHERE id_etat = ? LIMIT 1""",
            (etat_actuel,),
        )
        id_type_etat = int(etat_info.get("id_type_etat") or 0) if etat_info else 0
        lib_etat = (etat_info.get("lib_etat") or "") if etat_info else ""

        # Determination du nouvel etat (cf WinDev)
        nouvel_etat = etat_actuel
        nouveau_mois_p = ""
        majetat_flag = False
        traitement = "deja_statue"

        same_month = (
            mois_paiement and mois_p_omaya
            and mois_paiement.month == mois_p_omaya.month
            and mois_paiement.year == mois_p_omaya.year
        )

        is_resiliable = (
            id_type_etat in (1, 2) or etat_actuel == 54
            or (id_type_etat == 5 and same_month)
        )

        if is_resiliable:
            nouvel_etat = 16  # Resilie par operateur
            nouveau_mois_p = ""
            majetat_flag = True
            traitement = "resilie"
            resume.nb_resilies += 1
        elif id_type_etat == 5:
            # Decommissionne (mois_p_omaya different)
            majetat_flag = True
            if "partielle" in lib_etat.lower():
                if "elec" in lib_etat.lower():
                    nouvel_etat = 49  # Decommission Partielle ELEC
                    traitement = "decomm_part_elec"
                else:
                    nouvel_etat = 50  # Decommission Partielle GAZ
                    traitement = "decomm_part_gaz"
            else:
                nouvel_etat = 20  # Decommissionne total
                traitement = "decomm_total"
            nouveau_mois_p = str(mois_paiement) if mois_paiement else ""
            resume.nb_decommissions += 1
        else:
            # Deja statue (autres cas)
            resume.nb_deja_statues += 1

        contrats_run.append({
            "NumCtt": r.get("num_bs"),
            "DateSign": str(date_sign_omaya or ""),
            "Periode": periode_lbl,
            "TypeOffre": type_offre,
            "Etat actuel": etat_actuel,
            "TypeEtat": id_type_etat,
            "Lib Etat": lib_etat,
            "MoisP OMAYA": str(mois_p_omaya) if mois_p_omaya else "",
            "Nouvel etat": nouvel_etat,
            "Nouveau MoisP": nouveau_mois_p,
            "Traitement": traitement,
            "MAJ etat": majetat_flag,
        })

    wb.close()

    return ImportEniResult(
        ok=True, type_import=3, type_label=label,
        simulation=p.simulation, resume=resume,
        contrats_run=contrats_run + hors_delai,
        contrats_non_trouves=non_trouves,
        contrats_modifies=doublons,
        message=(
            f"{n_rows - 1} ligne(s) lue(s) | "
            f"Résiliés {resume.nb_resilies} | "
            f"Décommissions {resume.nb_decommissions} | "
            f"Déjà statués {resume.nb_deja_statues} | "
            f"Hors délai {resume.nb_contrats_hors_delai} | "
            f"Doublons {resume.nb_doublons} | "
            f"Introuvables {resume.nb_introuvables}. "
            f"{'(SIMULATION)' if p.simulation else '(PRODUCTION — phase 1)'}"
        ),
    )


# ---------------------------------------------------------------------------
# Type 4 : Base journaliere ENI (ImportJournalierENI)
# ---------------------------------------------------------------------------


def _parse_datetime_fr(s: str) -> Optional[datetime]:
    """Parse 'AAAA-MM-JJ HH:mm:SS.CCC' ou 'AAAA-JJ-MM HH:mm:SS.CCC'.

    Le code WinDev tente d'abord AAAA-JJ-MM puis bascule sur AAAA-MM-JJ
    si invalide. On essaie les 2 ordres ici aussi."""
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
                "%Y-%d-%m %H:%M:%S.%f", "%Y-%d-%m %H:%M:%S",
                "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _id_produit_from_type_offre(type_offre: str) -> int:
    """Dual=67, Elec=66, Gaz=65 (cf WinDev)."""
    if type_offre == "Dual":
        return 67
    if type_offre == "Elec":
        return 66
    return 65  # default = Gaz


def _etat_contrat_journ_eni(lib_statut: str, id_prod: int, offre: str,
                             non_call: bool) -> tuple[int, bool, bool]:
    """Determine (id_etat, gaz_actif, elec_actif) selon WinDev :
      - CANCELLED :
        - Dual : 43 (Resil partielle GAZ) ou 42 (partielle ELEC) selon offre
        - Sinon : 57 (Retractation Client) + gaz/elec off
      - Sinon :
        - Pas NonCALL : 37 (En cours traitement) ou 70 (En cours valid.)
        - NonCALL : 51 (Temporaire SF)
    """
    statut = (lib_statut or "").upper()
    if "CANCELLED" in statut:
        if id_prod == 67:  # Dual
            if "GAZ" in (offre or "").upper():
                return (43, False, True)  # Resil partielle GAZ
            else:
                return (42, True, False)  # Resil partielle ELEC
        return (57, False, False)  # Retractation Client
    # Pas CANCELLED
    if not non_call:
        if "COMPLETED" in statut:
            return (70, id_prod != 65, id_prod != 66)  # BS CALL En cours valid.
        return (37, id_prod != 65, id_prod != 66)  # En cours traitement
    return (51, id_prod != 65, id_prod != 66)  # Temporaire SF


# ---------------------------------------------------------------------------
# Helpers phase 2 (mode PRODUCTION)
# ---------------------------------------------------------------------------


def _new_id() -> int:
    """Id 8 octets construit depuis la date/heure (cf idEntierDateHeureSys
    WinDev)."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S")) * 1000 + n.microsecond // 1000


def _calcul_points_eni(famille: str, sous_fam: str, car: int,
                        date_sign: Optional[date], _options_str: str,
                        puissance: int) -> float:
    """Calcule nb_points selon adv.pgt_eni_remun.

    Lookup par (famille, ss_fam, date_activation <= date_sign < date_desactivation,
    val_min <= valeur <= val_max), valeur = CAR pour Gaz, puissance pour Elec.
    """
    if not famille:
        return 0.0
    db = get_pg_connection("adv")

    sous_fam_up = (sous_fam or "").upper()
    valeur = car if "GAZ" in sous_fam_up else puissance

    sql_parts = [
        "famille = ?", "ss_fam = ?",
        "rem_active = TRUE",
        "(val_min IS NULL OR val_min <= ?)",
        "(val_max IS NULL OR val_max >= ?)",
    ]
    params: list = [famille, sous_fam, valeur, valeur]
    if date_sign:
        sql_parts.append("(date_activation IS NULL OR date_activation <= ?)")
        sql_parts.append("(date_desactivation IS NULL OR date_desactivation > ?)")
        params.extend([date_sign, date_sign])

    r = db.query_one(
        f"""SELECT nb_points FROM adv.pgt_eni_remun
            WHERE {' AND '.join(sql_parts)}
            ORDER BY date_activation DESC NULLS LAST LIMIT 1""",
        tuple(params),
    )
    return float(r.get("nb_points") or 0) if r else 0.0


def _ajoute_histo_eni_etat(id_contrat: int, old_etat: int, new_etat: int,
                            date_paiement: str, op_id: int) -> None:
    """Ajoute une ligne dans adv.pgt_eni_histo_etat_ctt (transition etat)."""
    if not id_contrat:
        return
    db = get_pg_connection("adv")
    new_id = _new_id()
    auto = db.query_one(
        "SELECT COALESCE(MAX(id_histo_auto), 0) + 1 AS n FROM adv.pgt_eni_histo_etat_ctt"
    )
    auto_n = int(auto["n"]) if auto else 1
    db.query(
        """INSERT INTO adv.pgt_eni_histo_etat_ctt
              (id_histo_auto, id_histo, id_contrat, op_saisie, date,
               old_etat, new_etat, date_paiement,
               modif_op, modif_date, modif_elem)
           VALUES (?, ?, ?, ?, NOW(), ?, ?, ?, ?, NOW(), 'new')""",
        (auto_n, new_id, int(id_contrat), int(op_id),
         int(old_etat) if old_etat else 0,
         int(new_etat) if new_etat else 0,
         date_paiement or "", int(op_id)),
    )


def _lookup_or_create_client(info: dict, op_id: int) -> int:
    """Cherche un client existant par gsm (puis mail si pas de gsm),
    sinon en cree un nouveau. Retourne l'id_client.
    """
    db = get_pg_connection("adv")
    nom = (info.get("nom") or "").strip().upper()
    prenom = (info.get("prenom") or "").strip()
    gsm = "".join(c for c in (info.get("gsm") or "") if c.isdigit())
    mail = (info.get("mail") or "").strip().lower()

    # 1. Dedup par gsm + nom (le plus discriminant)
    if gsm and len(gsm) >= 9:
        r = db.query_one(
            """SELECT id_client FROM adv.pgt_client
                WHERE REGEXP_REPLACE(COALESCE(gsm, ''), '[^0-9]', '', 'g') = ?
                  AND UPPER(COALESCE(nom, '')) = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (gsm, nom),
        )
        if r:
            return int(r["id_client"])

    # 2. Dedup par mail + nom
    if mail and nom:
        r = db.query_one(
            """SELECT id_client FROM adv.pgt_client
                WHERE LOWER(COALESCE(mail, '')) = ?
                  AND UPPER(COALESCE(nom, '')) = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (mail, nom),
        )
        if r:
            return int(r["id_client"])

    # 3. Création
    new_id = _new_id()
    date_naiss = info.get("date_naiss")
    if isinstance(date_naiss, str):
        date_naiss = _parse_date_fr(date_naiss)
    db.query(
        """INSERT INTO adv.pgt_client
              (id_client, nom, prenom, date_naiss,
               adresse1, adresse2, cp, ville, pays,
               tel, gsm, mail,
               date_saisie, op_saisie,
               modif_op, modif_date, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'FRANCE',
                   ?, ?, ?, NOW(), ?, ?, NOW(), 'new')""",
        (new_id, nom, prenom, date_naiss,
         (info.get("adresse") or "").strip(),
         (info.get("cplt") or "").strip(),
         (info.get("cp") or "").strip(),
         (info.get("ville") or "").strip(),
         (info.get("tel") or "").strip(),
         gsm, mail,
         int(op_id), int(op_id)),
    )
    return new_id


def _create_eni_contrat(td: dict, op_id: int) -> int:
    """Cree un eni_contrat depuis un dict 'à créer' (cf TableImportCttJournENI).
    Retourne id_contrat cree."""
    db = get_pg_connection("adv")
    id_contrat = _new_id()
    auto = db.query_one(
        "SELECT COALESCE(MAX(id_contrat_auto), 0) + 1 AS n FROM adv.pgt_eni_contrat"
    )
    auto_n = int(auto["n"]) if auto else 1

    date_sign = td.get("date_signature")
    if isinstance(date_sign, str):
        date_sign = _parse_date_fr(date_sign)
    date_crea = td.get("date_crea")
    if isinstance(date_crea, str):
        date_crea = _parse_datetime_fr(date_crea)

    db.query(
        """INSERT INTO adv.pgt_eni_contrat
              (id_contrat_auto, id_contrat, id_client, id_salarie, id_ste,
               num_bs, id_produit, id_etat_contrat,
               date_signature, gaz_car_relevee, gaz_car_declaree,
               elec_puissance, gaz_actif, elec_actif,
               op_saisie, date_saisie, non_call, code_enr,
               notation, notation_info,
               modif_op, modif_date, modif_elem)
           VALUES (?, ?, ?, ?, ?,
                   ?, ?, ?,
                   ?, ?, ?,
                   ?, ?, ?,
                   ?, ?, ?, '',
                   ?, ?,
                   ?, NOW(), 'new')""",
        (auto_n, id_contrat,
         int(td.get("id_client") or 0),
         int(td.get("id_salarie") or 0),
         int(td.get("id_ste") or 0),
         td.get("num_bs") or "",
         int(td.get("id_produit") or 0),
         int(td.get("etat_contrat") or 0),
         date_sign, int(td.get("car") or 0), int(td.get("car") or 0),
         int(td.get("puissance") or 0),
         bool(td.get("gaz_actif")), bool(td.get("elec_actif")),
         int(op_id), date_crea or datetime.now(),
         bool(td.get("non_call")),
         float(td.get("note") or 0), td.get("info_note") or "",
         int(op_id)),
    )

    # Cree la ligne option vide (defaults)
    auto_o = db.query_one(
        "SELECT COALESCE(MAX(id_contrat_option_auto), 0) + 1 AS n FROM adv.pgt_eni_contrat_option"
    )
    auto_o_n = int(auto_o["n"]) if auto_o else 1
    db.query(
        """INSERT INTO adv.pgt_eni_contrat_option
              (id_contrat_option_auto, id_contrat, num_bs,
               opt_mail, opt_entretien, opt_hp_hc,
               opt_index_gaz, opt_index_elec, opt_delai_retra,
               opt_energie_verte_gaz, opt_energie_verte_elec,
               opt_deja_client_eni, opt_reforestation,
               opt_optin_commercial, opt_e_facture, opt_e_communication,
               opt_pdc, opt_accept_com_parte, opt_consent_consult_distri,
               opt_protection,
               modif_op, modif_date, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, FALSE, FALSE, FALSE,
                   FALSE, FALSE, FALSE, FALSE,
                   FALSE, FALSE, FALSE,
                   FALSE, FALSE, FALSE,
                   FALSE,
                   ?, NOW(), 'new')""",
        (auto_o_n, id_contrat, td.get("num_bs") or "",
         bool(td.get("opt_mail")), bool(td.get("opt_maint")),
         bool(td.get("opt_hphc")), int(op_id)),
    )
    return id_contrat


def _lookup_vendeur_by_nom_prenom(nom_complet: str) -> tuple[int, int]:
    """Cherche un salarie par 'NOM Prenom' ou variantes.
    Retourne (id_salarie, id_ste). 0,0 si introuvable."""
    if not nom_complet or not nom_complet.strip():
        return (0, 0)

    db = get_pg_connection("rh")
    # Normalise : uppercase, remplace tirets/apostrophes/espaces par %
    s = nom_complet.upper()
    for c in ("-", "'", " "):
        s = s.replace(c, "%")
    s = s.replace("%%", "%")

    # 1. Match exact concat nom+prenom (uppercased)
    rows = db.query(
        """SELECT s.id_salarie, e.id_ste
             FROM rh.pgt_salarie s
             LEFT JOIN rh.pgt_salarie_embauche e ON e.id_salarie = s.id_salarie
            WHERE UPPER(CONCAT(s.nom, '%', s.prenom)) LIKE ?
              AND (s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')
            LIMIT 2""",
        (f"%{s}%",),
    ) or []
    if len(rows) == 1:
        return (int(rows[0]["id_salarie"]),
                int(rows[0].get("id_ste") or 0))

    # 2. Tentative inverse prenom+nom
    parts = nom_complet.strip().split()
    if len(parts) >= 2:
        prenom = parts[0].upper()
        nom = parts[-1].upper()
        rows = db.query(
            """SELECT s.id_salarie, e.id_ste
                 FROM rh.pgt_salarie s
                 LEFT JOIN rh.pgt_salarie_embauche e ON e.id_salarie = s.id_salarie
                WHERE UPPER(s.nom) LIKE ? AND UPPER(s.prenom) LIKE ?
                  AND (s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')
                LIMIT 2""",
            (f"{nom}%", f"{prenom}%"),
        ) or []
        if len(rows) == 1:
            return (int(rows[0]["id_salarie"]),
                    int(rows[0].get("id_ste") or 0))
    return (0, 0)


def _import_journalier_eni(
    p: ImportEniParams, file_bytes: bytes, op_id: int,
) -> ImportEniResult:
    """Import 'Base Journaliere ENI' : pour chaque ligne du fichier,
    cree le contrat s'il n'existe pas ou met a jour si necessaire.

    Phase 1 : detection only :
      - Si contrat n'existe pas : flag 'a creer' + recherche vendeur
        + determination idProduit + etat initial
      - Si contrat existe : compare valeurs Excel vs BDD, si modif et
        etat eligible (type_etat<=2 ou etat=70) : flag 'a modifier'
        + nouvel etat
    Pas de creation ni MAJ effective en phase 1."""
    from openpyxl import load_workbook

    label = TYPE_LABELS.get(4, "Base journalière ENI")
    try:
        wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as e:
        return ImportEniResult(
            ok=False, type_import=4, type_label=label,
            simulation=p.simulation, resume=ImportEniResume(),
            message=f"Lecture Excel KO : {e}",
        )
    ws = wb.active

    cols = {k: _col_letter_to_index(v) for k, v in COLS_BJ_ENI.items()}

    resume = ImportEniResume()
    journ_eni: list[dict] = []

    db = get_pg_connection("adv")
    n_rows = ws.max_row or 0
    nb_creer = 0
    nb_modif = 0
    nb_inchanges = 0

    for i in range(2, n_rows + 1):
        num_contrat = _cell(ws, i, cols["num_contrat"]).upper()
        if not num_contrat:
            continue

        date_sign_s = _cell(ws, i, cols["date_signature"])
        date_sign = _parse_date_fr(date_sign_s)
        date_crea = _parse_datetime_fr(_cell(ws, i, cols["date_heure_crea"]))
        lib_statut = _cell(ws, i, cols["statut"])
        vend_raw = _cell(ws, i, cols["vendeur_nom"])
        vendeur_nom = vend_raw.split("/")[0].strip() if vend_raw else ""

        offre = _cell(ws, i, cols["offre"])
        type_offre = _cell(ws, i, cols["type_offre"]).strip()
        car = _parse_int(_cell(ws, i, cols["car"]))
        puiss_s = _cell(ws, i, cols["puissance"])
        puiss = _parse_int(puiss_s.split(".")[0]) if puiss_s else 0
        type_comptage = _cell(ws, i, cols["type_comptage"])
        opt_hphc = "HPHC" in type_comptage.upper()
        opt_maint = "PCK_HOME_P" in _cell(ws, i, cols["addon"]).upper()
        opt_mail = "MAIL" in _cell(ws, i, cols["opt_mail"]).upper()
        mandat_rib = "/20" in _cell(ws, i, cols["mandat_rib"])
        note_g = _parse_int(_cell(ws, i, cols["note_globale"]))
        note_s5 = note_g / 2 if note_g else 0
        info_note = _cell(ws, i, cols["info_notation"])
        client_cp = _cell(ws, i, cols["client_cp"])
        client_gsm = _cell(ws, i, cols["client_gsm"])

        id_produit = _id_produit_from_type_offre(type_offre)

        # Lookup contrat (sans opt_mandat : colonne absente du schema PG)
        r = db.query_one(
            """SELECT id_contrat, id_salarie, id_etat_contrat,
                      date_signature, date_saisie,
                      gaz_car_relevee, elec_puissance,
                      gaz_actif, elec_actif, non_call,
                      notation, notation_info
                 FROM adv.pgt_eni_contrat
                WHERE UPPER(num_bs) = UPPER(?)
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (num_contrat,),
        )

        if not r:
            # ---- CONTRAT N'EXISTE PAS : a CREER ----
            non_call = True  # par defaut

            # Recherche vendeur
            id_vendeur, id_ste = _lookup_vendeur_by_nom_prenom(vendeur_nom)
            etat, gaz_actif, elec_actif = _etat_contrat_journ_eni(
                lib_statut, id_produit, offre, non_call=non_call,
            )

            journ_eni.append({
                "NumCtt": num_contrat,
                "Statut": "à créer",
                "DateSigne": str(date_sign or ""),
                "DateCrea": str(date_crea or ""),
                "NomVend": vendeur_nom,
                "IdSalarie": id_vendeur,
                "Vendeur trouvé": id_vendeur > 0,
                "Société": id_ste,
                "LibProduit (id)": id_produit,
                "TypeOffre": type_offre,
                "CAR": car,
                "Puissance": puiss,
                "OptHpHc": opt_hphc,
                "OptMail": opt_mail,
                "OptMaint": opt_maint,
                "OptMandatRib": mandat_rib,
                "Note": note_s5,
                "InfoNote": info_note,
                "EtatContrat (initial)": etat,
                "GazActif": gaz_actif,
                "ElecActif": elec_actif,
                "NonCALL": non_call,
                "CltCP": client_cp,
                "CltGSM": client_gsm,
                # ---- payload pour creation en mode prod ----
                "_client_info": {
                    "nom": "", "prenom": "",  # remplis depuis tk_call si possible
                    "gsm": client_gsm,
                    "cp": client_cp,
                },
                "_contrat_data": {
                    "num_bs": num_contrat,
                    "id_salarie": id_vendeur,
                    "id_ste": id_ste,
                    "id_produit": id_produit,
                    "etat_contrat": etat,
                    "date_signature": date_sign,
                    "date_crea": date_crea,
                    "car": car,
                    "puissance": puiss,
                    "gaz_actif": gaz_actif,
                    "elec_actif": elec_actif,
                    "non_call": non_call,
                    "note": note_s5,
                    "info_note": info_note,
                    "opt_mail": opt_mail,
                    "opt_maint": opt_maint,
                    "opt_hphc": opt_hphc,
                },
            })
            nb_creer += 1
            continue

        # ---- CONTRAT EXISTE : compare ----
        id_contrat = int(r["id_contrat"])
        non_call_bdd = bool(r.get("non_call"))
        etat_actuel = int(r.get("id_etat_contrat") or 0)
        car_bdd = int(r.get("gaz_car_relevee") or 0)
        puiss_bdd = int(r.get("elec_puissance") or 0)

        # Options actuelles
        opt = db.query_one(
            """SELECT opt_entretien, opt_mail
                 FROM adv.pgt_eni_contrat_option WHERE id_contrat = ? LIMIT 1""",
            (id_contrat,),
        ) or {}

        # Differences detectees
        diffs: list[str] = []
        if date_crea and r.get("date_saisie") != date_crea:
            diffs.append(f"date_saisie {r.get('date_saisie')} -> {date_crea}")
        if puiss > 0 and puiss != puiss_bdd:
            diffs.append(f"puissance {puiss_bdd} -> {puiss}")
        if car > 0 and car != car_bdd:
            diffs.append(f"car_gaz {car_bdd} -> {car}")
        if bool(opt.get("opt_entretien")) != opt_maint:
            diffs.append(f"opt_entretien -> {opt_maint}")
        if bool(opt.get("opt_mail")) != opt_mail:
            diffs.append(f"opt_mail -> {opt_mail}")

        # Eligibilite MAJ etat
        etat_info = db.query_one(
            """SELECT id_type_etat FROM adv.pgt_eni_etat_contrat
                WHERE id_etat = ? LIMIT 1""",
            (etat_actuel,),
        )
        id_type_etat = int(etat_info.get("id_type_etat") or 0) if etat_info else 0
        eligible_etat = (id_type_etat <= 2) or etat_actuel == 70

        nouvel_etat = etat_actuel
        if eligible_etat:
            nouvel_etat, _, _ = _etat_contrat_journ_eni(
                lib_statut, id_produit, offre, non_call=non_call_bdd,
            )
            if nouvel_etat != etat_actuel:
                diffs.append(f"etat {etat_actuel} -> {nouvel_etat}")

        if diffs:
            journ_eni.append({
                "NumCtt": num_contrat,
                "Statut": "à modifier",
                "DateSigne": str(r.get("date_signature") or ""),
                "EtatActuel": etat_actuel,
                "TypeEtat": id_type_etat,
                "NouvelEtat": nouvel_etat,
                "Diffs": " | ".join(diffs),
                "LibProduit (id)": id_produit,
                "TypeOffre": type_offre,
                "OptMail Excel": opt_mail,
                "OptMaint Excel": opt_maint,
                # Payload pour MAJ en prod
                "_maj_data": {
                    "id_contrat": id_contrat,
                    "date_saisie": date_crea,
                    "puissance": puiss,
                    "car": car,
                    "opt_maint": opt_maint,
                    "opt_mail": opt_mail,
                    "etat_actuel": etat_actuel,
                    "nouvel_etat": nouvel_etat if eligible_etat else etat_actuel,
                    "etat_change": eligible_etat and (nouvel_etat != etat_actuel),
                },
            })
            nb_modif += 1
        else:
            nb_inchanges += 1

    wb.close()

    # -- PASSE PROD : creation + MAJ si pas simulation --
    nb_crees = 0
    nb_majs = 0
    if not p.simulation:
        for row in journ_eni:
            try:
                if row.get("Statut") == "à créer":
                    ci = row.pop("_client_info", {})
                    cd = row.pop("_contrat_data", {})
                    if ci:
                        cd["id_client"] = _lookup_or_create_client(ci, op_id)
                    new_id = _create_eni_contrat(cd, op_id)
                    row["IdContratCree"] = new_id
                    nb_crees += 1
                elif row.get("Statut") == "à modifier":
                    md = row.pop("_maj_data", {})
                    if md and md.get("id_contrat"):
                        _apply_maj_eni_journ(md, op_id)
                        nb_majs += 1
            except Exception as e:
                row["Erreur"] = str(e)

    resume.nb_modifications = nb_modif
    resume.nb_valides = nb_creer

    return ImportEniResult(
        ok=True, type_import=4, type_label=label,
        simulation=p.simulation, resume=resume,
        contrat_import_journ_eni=journ_eni,
        message=(
            f"{n_rows - 1} ligne(s) lue(s) | "
            f"À créer : {nb_creer} | À modifier : {nb_modif} | "
            f"Inchangés : {nb_inchanges}. "
            + (f"PRODUCTION : {nb_crees} créés, {nb_majs} MAJ."
               if not p.simulation else "(SIMULATION)")
        ),
    )


def _apply_maj_eni_journ(md: dict, op_id: int) -> None:
    """MAJ eni_contrat + eni_contrat_option pour un contrat existant
    (ImportJournalierENI). Historise si l'etat change."""
    db = get_pg_connection("adv")
    id_contrat = int(md["id_contrat"])
    sets = []
    params: list = []
    if md.get("date_saisie"):
        sets.append("date_saisie = ?")
        params.append(md["date_saisie"])
    if md.get("puissance"):
        sets.append("elec_puissance = ?")
        params.append(int(md["puissance"]))
    if md.get("car"):
        sets.append("gaz_car_relevee = ?")
        params.append(int(md["car"]))
    if md.get("etat_change"):
        sets.append("id_etat_contrat = ?")
        params.append(int(md["nouvel_etat"]))

    if sets:
        sets.append("modif_date = NOW()")
        sets.append("modif_op = ?")
        sets.append("modif_elem = 'modif'")
        params.append(int(op_id))
        params.append(id_contrat)
        db.query(
            f"""UPDATE adv.pgt_eni_contrat
                  SET {', '.join(sets)}
                WHERE id_contrat = ?""",
            tuple(params),
        )

    # MAJ option
    db.query(
        """UPDATE adv.pgt_eni_contrat_option
              SET opt_entretien = ?, opt_mail = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_contrat = ?""",
        (bool(md.get("opt_maint")), bool(md.get("opt_mail")),
         int(op_id), id_contrat),
    )

    if md.get("etat_change"):
        _ajoute_histo_eni_etat(
            id_contrat, int(md["etat_actuel"]), int(md["nouvel_etat"]),
            "", op_id,
        )
