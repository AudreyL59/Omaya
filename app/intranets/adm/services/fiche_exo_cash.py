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

    - solde_actuel  = SUM(credit) - SUM(debit) sur livret (non suppr)
                      = transposition de DonneSoldeExoCash
    - cde_en_cours  = SUM(montant_lot * qte) sur commandes ExoCash dont
                      le ticket est non cloture (statut != 28) ET dont
                      le IDTK_Liste n'a pas encore ete debite dans le
                      livret (transposition de DonneCdeEC_nonDebitee)
    - solde_apres_cde = solde_actuel - cde_en_cours
    """
    db_rh = get_pg_connection("rh")
    rows = db_rh.query(
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

    # DonneCdeEC_nonDebitee : cross-schema (ticket_rh + divers + ticket + rh)
    db_trh = get_pg_connection("ticket_rh")
    cde_rows = db_trh.query(
        """SELECT COALESCE(SUM(ecl.montant * tkcl.qte), 0) AS total
             FROM ticket_rh.pgt_tk_cde_exo_cash tkc
             INNER JOIN ticket_rh.pgt_tk_cde_exo_cash_lot tkcl
               ON tkcl.id_tk_cde_exo_cash = tkc.id_tk_cde_exo_cash
             INNER JOIN divers.pgt_exo_cash_lot ecl
               ON ecl.id_exo_cash_lot = tkcl.id_exo_cash_lot
             INNER JOIN ticket.pgt_tk_liste tkl
               ON tkl.id_tk_liste = tkcl.id_tk_liste
            WHERE (ecl.modif_elem IS NULL OR ecl.modif_elem <> 'suppr')
              AND (tkcl.modif_elem IS NULL OR tkcl.modif_elem NOT LIKE '%suppr%')
              AND tkc.id_salarie = ?
              AND tkl.cloturee = FALSE
              AND tkl.id_tk_statut <> 28
              AND tkc.id_tk_liste NOT IN (
                    SELECT sl.id_tk_liste
                      FROM rh.pgt_salarie_livret sl
                     WHERE sl.id_salarie = ?
                       AND sl.id_tk_liste IS NOT NULL
              )""",
        (int(id_salarie), int(id_salarie)),
    )
    cde_en_cours = _num(cde_rows[0].get("total")) if cde_rows else 0.0

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


# ===========================================================================
# Form Fen_SalarieLivretFiche (add/edit)
# ===========================================================================


def _new_id() -> int:
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


def list_types_operation() -> list[dict]:
    """Liste des types d'operation (combo Type Operation)."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_type_operation_livret, lib_opeation
             FROM rh.pgt_type_operation_livret
            WHERE modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%'
            ORDER BY lib_opeation""",
    )
    return [
        {
            "id_type_operation_livret": int(r.get("id_type_operation_livret") or 0),
            "lib_opeation": _str(r.get("lib_opeation")),
        }
        for r in rows or []
    ]


def list_challenges() -> list[dict]:
    """Liste des challenges (selecteur 'Choisir un challenge')."""
    db = get_pg_connection("divers")
    rows = db.query(
        """SELECT id_challenge_evenement, libelle, date_debut, date_fin
             FROM divers.pgt_challenge_evenement
            WHERE modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%'
            ORDER BY date_debut DESC NULLS LAST""",
    )
    out = []
    for r in rows or []:
        out.append({
            "id_challenge_evenement": _str(r.get("id_challenge_evenement")),
            "libelle": _str(r.get("libelle")),
            "date_debut": _iso(r.get("date_debut")),
            "date_fin": _iso(r.get("date_fin")),
        })
    return out


def load_livret_item(id_salarie_livret: int) -> dict:
    """Recupere une ligne de livret pour pre-remplir le formulaire."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_salarie_livret, id_salarie,
                  id_type_operation_livret, id_challenge, id_tk_liste,
                  montant_credit, montant_debit, date_operation
             FROM rh.pgt_salarie_livret
            WHERE id_salarie_livret = ?
            LIMIT 1""",
        (int(id_salarie_livret),),
    )
    if not rows:
        return {}
    r = rows[0]
    # Lib challenge (si renseigne)
    lib_challenge = ""
    id_chall = r.get("id_challenge") or 0
    if id_chall:
        db_d = get_pg_connection("divers")
        c_rows = db_d.query(
            """SELECT libelle, date_debut, date_fin
                 FROM divers.pgt_challenge_evenement
                WHERE id_challenge_evenement = ?
                LIMIT 1""",
            (int(id_chall),),
        )
        if c_rows:
            cr = c_rows[0]
            lib_challenge = (
                f"{_str(cr.get('libelle'))}, du {_iso(cr.get('date_debut'))}"
                f" au {_iso(cr.get('date_fin'))}"
            )
    return {
        "id_salarie_livret": _str(r.get("id_salarie_livret")),
        "id_salarie": _str(r.get("id_salarie")),
        "id_type_operation_livret": int(r.get("id_type_operation_livret") or 0),
        "id_challenge": _str(r.get("id_challenge")),
        "lib_challenge": lib_challenge,
        "id_tk_liste": _str(r.get("id_tk_liste")),
        "montant_credit": _num(r.get("montant_credit")),
        "montant_debit": _num(r.get("montant_debit")),
        "date_operation": _iso(r.get("date_operation")),
    }


def upsert_livret(
    id_salarie: int,
    id_salarie_livret: int | None,
    id_type_operation_livret: int,
    id_challenge: int,
    montant_credit: float,
    montant_debit: float,
    date_operation: str,
    operateur_id: int,
) -> dict:
    """Insert (id_salarie_livret None/0) ou Update d'une ligne de livret."""
    db = get_pg_connection("rh")
    if not id_salarie_livret:
        new_id = _new_id()
        db.execute(
            """INSERT INTO rh.pgt_salarie_livret
                  (id_salarie_livret, id_salarie, operateur,
                   id_type_operation_livret, id_challenge,
                   montant_credit, montant_debit, date_operation,
                   modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?,
                       ?, ?,
                       ?, ?, ?::timestamp,
                       NOW(), ?, 'new')""",
            (
                new_id, int(id_salarie), int(operateur_id),
                int(id_type_operation_livret), int(id_challenge or 0),
                float(montant_credit or 0), float(montant_debit or 0),
                date_operation or None,
                int(operateur_id),
            ),
        )
        return {"ok": True, "id_salarie_livret": str(new_id)}

    db.execute(
        """UPDATE rh.pgt_salarie_livret
              SET id_type_operation_livret = ?,
                  id_challenge = ?,
                  montant_credit = ?,
                  montant_debit = ?,
                  date_operation = ?::timestamp,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_salarie_livret = ?""",
        (
            int(id_type_operation_livret), int(id_challenge or 0),
            float(montant_credit or 0), float(montant_debit or 0),
            date_operation or None,
            int(operateur_id),
            int(id_salarie_livret),
        ),
    )
    return {"ok": True, "id_salarie_livret": str(id_salarie_livret)}
