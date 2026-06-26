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
    4: "Salesforce",
    5: "Base journalière ENI",
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
