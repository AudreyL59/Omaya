"""
Onglet 'Accès Omaya' (Droit d'accès) de la fiche salarie ADM.

Transposition de FI_SalarieDroitAcces.

Etape 1 :
  - Liste des droits du salarie (JOIN pgt_type_droit_acces /
    pgt_salarie_droit_acces) avec rupture par Categorie.
  - Bouton 'Activer/desactiver la selection' : toggle droit_actif
    pour chaque ligne cochee.
  - Bouton 'Supprimer' : soft delete (modif_elem='suppr').

Etape 2 (commit suivant) :
  - 2 popups d'ajout : Intranet/Appli (ADM=0, FDV=1) et Omaya Software
    (ADM=1, FDV=0, restreint aux droits de l'operateur connecte).
  - Bouton 'Choisir ce profil' (categorie pgt_profil_droit_acces).

Etape 3 :
  - Bouton 'Envoyer code Omaya' : genere/recupere MDP + envoie mail + SMS.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

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


def _new_id() -> int:
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


def load_droits(id_salarie: int) -> list[dict]:
    """Liste des droits attribues au salarie, JOIN sur le catalogue."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT
              sda.id_salarie_droit_acces,
              tda.id_type_droit_acces,
              tda.lib_droit,
              tda.code_interne,
              tda.description,
              tda.adm,
              tda.fdv,
              tda.categorie,
              sda.droit_actif
           FROM rh.pgt_salarie_droit_acces sda
           INNER JOIN rh.pgt_type_droit_acces tda
             ON sda.id_type_droit_acces = tda.id_type_droit_acces
           WHERE sda.id_salarie = ?
             AND sda.modif_elem NOT LIKE '%suppr%'
             AND tda.modif_elem NOT LIKE '%suppr%'
           ORDER BY tda.categorie ASC NULLS LAST, tda.lib_droit ASC""",
        (int(id_salarie),),
    )
    return [
        {
            "id_salarie_droit_acces": str(r.get("id_salarie_droit_acces") or ""),
            "id_type_droit_acces": _int(r.get("id_type_droit_acces")),
            "lib_droit": _str(r.get("lib_droit")),
            "code_interne": _str(r.get("code_interne")),
            "description": _str(r.get("description")),
            "adm": bool(r.get("adm")),
            "fdv": bool(r.get("fdv")),
            "categorie": _str(r.get("categorie")),
            "droit_actif": bool(r.get("droit_actif")),
        }
        for r in rows
    ]


def toggle_droits(id_salarie: int, id_types: list[int], op_id: int) -> dict:
    """Btn 'Activer/desactiver la selection' : toggle droit_actif pour
    chaque ligne cochee. Si la combinaison (id_salarie, id_type) n'existe
    pas en base, on l'ignore (cf. WinDev HLitRecherche puis HModifie)."""
    db = get_pg_connection("rh")
    nb_toggled = 0
    for id_type in id_types:
        if not id_type:
            continue
        row = db.query_one(
            """SELECT id_salarie_droit_acces, droit_actif
               FROM rh.pgt_salarie_droit_acces
               WHERE id_salarie = ? AND id_type_droit_acces = ?
                 AND modif_elem NOT LIKE '%suppr%'""",
            (int(id_salarie), int(id_type)),
        )
        if not row:
            continue
        new_actif = not bool(row.get("droit_actif"))
        db.query(
            """UPDATE rh.pgt_salarie_droit_acces SET
                  droit_actif = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
                WHERE id_salarie_droit_acces = ?""",
            (
                new_actif,
                int(op_id),
                int(row.get("id_salarie_droit_acces")),
            ),
        )
        nb_toggled += 1
    return {"ok": True, "nb_toggled": nb_toggled}


def soft_delete_droits(id_salarie: int, id_types: list[int], op_id: int) -> dict:
    """Btn 'Supprimer' : soft delete pour chaque (id_salarie, id_type)."""
    db = get_pg_connection("rh")
    nb_deleted = 0
    for id_type in id_types:
        if not id_type:
            continue
        row = db.query_one(
            """SELECT id_salarie_droit_acces
               FROM rh.pgt_salarie_droit_acces
               WHERE id_salarie = ? AND id_type_droit_acces = ?
                 AND modif_elem NOT LIKE '%suppr%'""",
            (int(id_salarie), int(id_type)),
        )
        if not row:
            continue
        db.query(
            """UPDATE rh.pgt_salarie_droit_acces SET
                  modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
                WHERE id_salarie_droit_acces = ?""",
            (int(op_id), int(row.get("id_salarie_droit_acces"))),
        )
        nb_deleted += 1
    return {"ok": True, "nb_deleted": nb_deleted}
