"""
Service Fen_ImportFournisseurCarte (ADM Ulease -> Import des releves
fournisseur depuis un fichier Excel).

Pour l'instant : import Total Energies. Autres fournisseurs a venir.

Pipeline ImportTotalEnergies (cf. WinDev) :
  Pour chaque ligne du fichier Excel :
    1. Lit les colonnes (CodeCarte, NumCarte, Date, Heure, Lieu, LibType,
       MontantHT, MontantTTC, IdFacturation, CompteClient).
    2. Match la carte (pgt_cartecarburant) par CodeCarte + NumCarte LIKE.
    3. Match (ou cree si pas simulation) le type de releve par Lib_Type.
    4. Verifie qu'un releve n'existe pas deja (meme fournisseur + date +
       heure) -> sinon INSERT dans pgt_cartecarbrelevefournisseur.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from openpyxl import load_workbook

from app.core.database.pg import get_pg_connection


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _float(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _new_id() -> int:
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


def _col_letter_to_idx(letter: str) -> int:
    """'A'->0, 'B'->1, ..., 'Z'->25, 'AA'->26."""
    s = (letter or "").strip().upper()
    if not s:
        return -1
    n = 0
    for c in s:
        if not ("A" <= c <= "Z"):
            return -1
        n = n * 26 + (ord(c) - ord("A") + 1)
    return n - 1


def _cell_str(row: tuple, idx: int) -> str:
    if idx < 0 or idx >= len(row):
        return ""
    v = row[idx]
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, (int, float)):
        # nombre lu : on retourne sans decimales si entier
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        return str(v)
    return str(v)


def _cell_date(row: tuple, idx: int):
    """Lit une cellule comme date. Excel peut renvoyer un datetime ou une
    chaine JJ/MM/AAAA."""
    if idx < 0 or idx >= len(row):
        return None
    v = row[idx]
    if v is None:
        return None
    if hasattr(v, "year") and hasattr(v, "month") and hasattr(v, "day"):
        return v.date() if hasattr(v, "hour") else v
    s = str(v).strip()
    if len(s) >= 10 and s[2] == "/" and s[5] == "/":
        try:
            return datetime(int(s[6:10]), int(s[3:5]), int(s[:2])).date()
        except Exception:
            return None
    if len(s) >= 10 and s[4] == "-":
        try:
            return datetime(int(s[:4]), int(s[5:7]), int(s[8:10])).date()
        except Exception:
            return None
    return None


def _cell_time(row: tuple, idx: int):
    """Lit une cellule comme heure HH:MM."""
    if idx < 0 or idx >= len(row):
        return None
    v = row[idx]
    if v is None:
        return None
    if hasattr(v, "hour") and hasattr(v, "minute"):
        return v.time() if hasattr(v, "year") else v
    s = str(v).strip()
    if len(s) >= 5 and s[2] == ":":
        try:
            return f"{s[:2]}:{s[3:5]}:00"
        except Exception:
            return None
    return None


def _format_norm(s: str) -> str:
    """ChaineFormate(..., ccSansEspace + ccMajuscule)."""
    return s.replace(" ", "").upper().strip()


def _format_no_accent_upper(s: str) -> str:
    """ChaineFormate(..., ccSansAccent + ccMajuscule)."""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).upper().strip()


def import_total_energies(
    file_bytes: bytes,
    id_carte_fournisseur: int,
    ligne_depart: int,
    cols: dict,
    simulation: bool,
    op_id: int,
) -> dict:
    """Import Excel Total Energies. cols est un dict des lettres de colonne :
      { 'id_facture': 'A', 'compte_client': 'B', 'num_carte': 'C',
        'code_carte': 'D', 'date': 'E', 'heure': 'F', 'lieu': 'G',
        'lib_type': 'H', 'montant_ht': 'I', 'montant_ttc': 'J' }
    """
    if not id_carte_fournisseur:
        return {"ok": False, "error": "Fournisseur manquant"}
    if not file_bytes:
        return {"ok": False, "error": "Fichier vide"}

    try:
        wb = load_workbook(io.BytesIO(file_bytes), data_only=True, read_only=True)
        ws = wb.active
    except Exception as e:
        return {"ok": False, "error": f"Fichier Excel illisible : {e}"}

    idx = {k: _col_letter_to_idx(v) for k, v in cols.items()}
    needed = ("id_facture", "compte_client", "num_carte", "code_carte",
              "date", "heure", "lieu", "lib_type", "montant_ht", "montant_ttc")
    for k in needed:
        if k not in idx:
            return {"ok": False, "error": f"Colonne manquante : {k}"}

    db = get_pg_connection("ulease")
    resume: list[str] = []
    nb_ajout = 0
    nb_lus = 0

    # Cache des types_releve dans la session
    types_known = {
        _format_no_accent_upper(r["lib_type"]): _int(r["id_type_releve_fournisseur"])
        for r in db.query(
            """SELECT id_type_releve_fournisseur, lib_type
                 FROM ulease.pgt_typerelevefournisseur
                WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')""",
        ) or []
    }

    start = max(1, int(ligne_depart))
    for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if r_idx < start:
            continue
        nb_lus += 1
        # Valeurs lues
        id_facture = _format_norm(_cell_str(row, idx["id_facture"]))
        cpte_client = _format_norm(_cell_str(row, idx["compte_client"]))
        num_carte = _format_norm(_cell_str(row, idx["num_carte"]))
        code_carte = _format_norm(_cell_str(row, idx["code_carte"]))
        date_v = _cell_date(row, idx["date"])
        heure_v = _cell_time(row, idx["heure"])
        lieu = _cell_str(row, idx["lieu"])
        lib_type_raw = _cell_str(row, idx["lib_type"])
        lib_type = _format_no_accent_upper(lib_type_raw)
        montant_ht = _float(row[idx["montant_ht"]]) if idx["montant_ht"] < len(row) else 0.0
        montant_ttc = _float(row[idx["montant_ttc"]]) if idx["montant_ttc"] < len(row) else 0.0

        # Ligne vide -> skip silencieux
        if not num_carte and not code_carte and not date_v:
            continue

        # 1. Match carte (CodeCarte + NumCarte LIKE)
        carte = db.query_one(
            """SELECT id_carte_carburant FROM ulease.pgt_cartecarburant
                WHERE code_carte = ?
                  AND num_carte LIKE ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                LIMIT 1""",
            (code_carte, num_carte + "%"),
        )
        if not carte:
            resume.append(f"Ligne {r_idx} : carte {cpte_client} {num_carte} inconnue")
            continue
        id_carte = _int(carte.get("id_carte_carburant"))

        # 2. Match (ou cree) type releve
        id_type = types_known.get(lib_type, 0)
        if id_type == 0:
            if simulation:
                resume.append(f"Ligne {r_idx} : type '{lib_type_raw}' inconnu")
            else:
                id_type = _new_id()
                db.query(
                    """INSERT INTO ulease.pgt_typerelevefournisseur
                         (id_type_releve_fournisseur, lib_type, categorie,
                          modif_op, modif_date, modif_elem)
                       VALUES (?, ?, 'Non déterminée', ?, NOW(), 'new')""",
                    (id_type, lib_type, int(op_id)),
                )
                types_known[lib_type] = id_type
                resume.append(f"Type '{lib_type_raw}' ajouté")

        # 3. Verifie existence releve (meme fournisseur + date + heure)
        if date_v and heure_v:
            exists = db.query_one(
                """SELECT id_carte_carb_releve_fournisseur
                     FROM ulease.pgt_cartecarbrelevefournisseur
                    WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
                      AND id_carte_fournisseur = ?
                      AND date = ?
                      AND heure = ?
                    LIMIT 1""",
                (int(id_carte_fournisseur), date_v, heure_v),
            )
        else:
            exists = None
        if exists:
            continue

        # 4. INSERT releve (si pas simulation)
        if not simulation:
            db.query(
                """INSERT INTO ulease.pgt_cartecarbrelevefournisseur
                     (id_carte_carb_releve_fournisseur, id_facturation,
                      id_carte_fournisseur, id_carte_carburant,
                      id_type_releve_fournisseur, date, heure, lieu,
                      montant_ht, montant_ttc,
                      modif_op, modif_date, modif_elem)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), 'new')""",
                (
                    _new_id(), id_facture, int(id_carte_fournisseur),
                    id_carte, id_type, date_v, heure_v, lieu,
                    montant_ht, montant_ttc, int(op_id),
                ),
            )
            nb_ajout += 1

    resume.append(f"nb Ajout : {nb_ajout}")
    resume.append("Import Terminé")
    return {
        "ok": True,
        "simulation": simulation,
        "nb_lus": nb_lus,
        "nb_ajout": nb_ajout,
        "resume": resume,
    }
