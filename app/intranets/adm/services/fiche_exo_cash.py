"""
Onglet 'Exo Cash' (livret) de la fiche salarie ADM.

Transposition de FI_SalarieLivret :
  - Tableau des operations du livret (Date / Operateur / Type / Debit / Credit)
  - Boutons Nouveau / Modifier / Supprimer (soft delete ModifElem='suppr')
  - Pied : Somme Debit / Somme Credit (afficheur du tableau)
  - 3 lignes resultat : Solde Actuel, Commande en cours, Solde apres commande

Soldes :
  - Solde actuel = SUM(Credit) - SUM(Debit) sur les lignes non 'suppr'
    (NB: a remplacer par la transposition exacte de DonneSoldeExoCash
     fournie par l'utilisateur).
  - Commande en cours = a fournir par l'utilisateur (DonneCdeEC_nonDebitee)
    -> renvoie 0 pour l'instant.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _iso(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _num(v: Any) -> float:
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def load_livret(id_salarie: int) -> list[dict]:
    """Liste des operations du livret du salarie (non supprimees), tri DESC."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT sl.id_salarie_livret,
                  sl.date_operation,
                  sl.id_type_operation_livret,
                  sl.montant_debit,
                  sl.montant_credit,
                  sl.id_tk_liste,
                  sl.id_challenge,
                  sl.id_salarie,
                  sl.operateur,
                  s.nom AS op_nom,
                  s.prenom AS op_prenom,
                  tol.lib_opeation AS lib_type
           FROM rh.pgt_salarie_livret sl
           LEFT JOIN rh.pgt_salarie s
             ON s.id_salarie = sl.operateur
           LEFT JOIN rh.pgt_type_operation_livret tol
             ON tol.id_type_operation_livret = sl.id_type_operation_livret
           WHERE sl.id_salarie = ?
             AND (sl.modif_elem IS NULL OR sl.modif_elem NOT LIKE '%suppr%')
           ORDER BY sl.date_operation DESC""",
        (int(id_salarie),),
    )
    out = []
    for r in rows or []:
        prenom = _str(r.get("op_prenom"))
        nom_prenom = (
            f"{_str(r.get('op_nom'))} "
            f"{(prenom[:1].upper() + prenom[1:].lower()) if prenom else ''}"
        ).strip()
        out.append({
            "id_salarie_livret": _str(r.get("id_salarie_livret")),
            "date_operation": _iso(r.get("date_operation")),
            "id_type_operation_livret": r.get("id_type_operation_livret") or 0,
            "lib_type": _str(r.get("lib_type")),
            "montant_debit": _num(r.get("montant_debit")),
            "montant_credit": _num(r.get("montant_credit")),
            "id_tk_liste": _str(r.get("id_tk_liste")),
            "id_challenge": _str(r.get("id_challenge")),
            "operateur": _str(r.get("operateur")),
            "nom_prenom": nom_prenom,
        })
    return out


def calc_soldes(id_salarie: int) -> dict:
    """Calcule les 3 soldes affichees en bas de la fenetre.

    NB: implementation provisoire (somme simple). A remplacer par la
    transposition exacte de DonneSoldeExoCash + DonneCdeEC_nonDebitee
    fournie par l'utilisateur.
    """
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT COALESCE(SUM(montant_credit),0) AS tot_credit,
                  COALESCE(SUM(montant_debit),0) AS tot_debit
           FROM rh.pgt_salarie_livret
           WHERE id_salarie = ?
             AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_salarie),),
    )
    tot_credit = _num(rows[0].get("tot_credit")) if rows else 0.0
    tot_debit = _num(rows[0].get("tot_debit")) if rows else 0.0
    solde_actuel = tot_credit - tot_debit
    cde_en_cours = 0.0  # TODO: DonneCdeEC_nonDebitee
    return {
        "solde_actuel": solde_actuel,
        "cde_en_cours": cde_en_cours,
        "solde_apres_cde": solde_actuel - cde_en_cours,
        "somme_debit": tot_debit,
        "somme_credit": tot_credit,
    }


def soft_delete_livret(id_salarie_livret: int, operateur_id: int) -> dict:
    """Supprime (soft) une ligne de livret."""
    db = get_pg_connection("rh")
    db.execute(
        """UPDATE rh.pgt_salarie_livret
              SET modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'suppr'
            WHERE id_salarie_livret = ?""",
        (int(operateur_id), int(id_salarie_livret)),
    )
    return {"ok": True}
