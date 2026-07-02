"""
Onglet 'Mutuelle' de la fiche salarie ADM.

Transposition de la fenetre WinDev FI_SalarieMutuelle :
  - Formulaire (combo Mutuelle + checklists adhesion / dossier / att SS
    / RIB / doc envoyes / recep. certif + statuts speciaux 'N'adhere pas'
    + jusqu'au, 'Resilie' + le).
  - Tableau historique des tickets Demande Mutuelle (TK_DemandeMutuelle
    JOIN TK_Liste, tries par date crea DESC).
  - Bouton Enregistrer (visible si droit Sa_FicheModif).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection
from app.core.utils.sentinel_dates import is_sentinel


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _iso(v: Any) -> str:
    if v is None or is_sentinel(v):
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _iso_dt(v: Any) -> str:
    if v is None or is_sentinel(v):
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    s = str(v)
    if len(s) >= 19 and s[4] == "-" and s[7] == "-":
        return s[:19]
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _capitalize_first(s: str) -> str:
    if not s:
        return ""
    return s[0].upper() + s[1:].lower()


def list_mutuelles() -> list[dict]:
    """Combo Mutuelle : liste des mutuelles actives."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_mutuelle, lib_mutuelle
           FROM rh.pgt_mutuelle
           WHERE COALESCE(is_actif, FALSE) = TRUE
             AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
           ORDER BY lib_mutuelle ASC NULLS LAST"""
    )
    return [
        {
            "id_mutuelle": _int(r.get("id_mutuelle")),
            "lib_mutuelle": _str(r.get("lib_mutuelle")),
        }
        for r in rows
    ]


def _ensure_row(id_salarie: int, op_id: int) -> None:
    """Cree la ligne pgt_salarie_mutuelle si elle n'existe pas (cf. WinDev
    init avec reAjout)."""
    db = get_pg_connection("rh")
    r = db.query_one(
        "SELECT id_salarie FROM rh.pgt_salarie_mutuelle WHERE id_salarie = ?",
        (int(id_salarie),),
    )
    if r:
        return
    db.query(
        """INSERT INTO rh.pgt_salarie_mutuelle
              (id_salarie, adhesion, mutuelle_dossier, id_mutuelle,
               mutuelle_att_ss, mutuelle_rib, mutuelle_doc_envoyes,
               mutuelle_recep_certif, mutuelle_pas_adhesion,
               mutuelle_resilie,
               modif_date, modif_op, modif_elem)
           VALUES (?, FALSE, FALSE, 0,
                   FALSE, FALSE, FALSE,
                   FALSE, FALSE,
                   FALSE,
                   NOW(), ?, 'new')""",
        (int(id_salarie), int(op_id)),
    )


def load(id_salarie: int, op_id: int) -> dict:
    """Charge le formulaire (cree la ligne si absente)."""
    _ensure_row(int(id_salarie), int(op_id))
    db = get_pg_connection("rh")
    r = db.query_one(
        """SELECT id_salarie, adhesion, adhesion_date, id_mutuelle,
                  mutuelle_dossier, mutuelle_att_ss, mutuelle_rib,
                  mutuelle_doc_envoyes, mutuelle_recep_certif,
                  mutuelle_pas_adhesion, mutuelle_pas_adhesion_jusquau,
                  mutuelle_resilie, mutuelle_resilie_date,
                  modif_date, modif_op
           FROM rh.pgt_salarie_mutuelle WHERE id_salarie = ?""",
        (int(id_salarie),),
    ) or {}

    modif_op_id = _int(r.get("modif_op"))
    modif_op_lib = ""
    if modif_op_id:
        op = db.query_one(
            "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ?",
            (int(modif_op_id),),
        )
        if op:
            modif_op_lib = (
                f"{_str(op.get('nom'))} "
                f"{_capitalize_first(_str(op.get('prenom')))}"
            ).strip()

    return {
        "adhesion": bool(r.get("adhesion")),
        "adhesion_date": _iso(r.get("adhesion_date")),
        "id_mutuelle": _int(r.get("id_mutuelle")),
        "mutuelle_dossier": bool(r.get("mutuelle_dossier")),
        "mutuelle_att_ss": bool(r.get("mutuelle_att_ss")),
        "mutuelle_rib": bool(r.get("mutuelle_rib")),
        "mutuelle_doc_envoyes": bool(r.get("mutuelle_doc_envoyes")),
        "mutuelle_recep_certif": bool(r.get("mutuelle_recep_certif")),
        "mutuelle_pas_adhesion": bool(r.get("mutuelle_pas_adhesion")),
        "mutuelle_pas_adhesion_jusquau": _iso(r.get("mutuelle_pas_adhesion_jusquau")),
        "mutuelle_resilie": bool(r.get("mutuelle_resilie")),
        "mutuelle_resilie_date": _iso(r.get("mutuelle_resilie_date")),
        "modif_date": _iso_dt(r.get("modif_date")),
        "modif_op_lib": modif_op_lib,
        "mutuelles": list_mutuelles(),
        "tickets": list_tickets_mutuelle(int(id_salarie)),
    }


def save(id_salarie: int, payload: dict, op_id: int) -> dict:
    """Btn Enregistrer : UPDATE pgt_salarie_mutuelle."""
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_salarie_mutuelle SET
              adhesion = ?,
              adhesion_date = ?,
              id_mutuelle = ?,
              mutuelle_dossier = ?,
              mutuelle_att_ss = ?,
              mutuelle_rib = ?,
              mutuelle_doc_envoyes = ?,
              mutuelle_recep_certif = ?,
              mutuelle_pas_adhesion = ?,
              mutuelle_pas_adhesion_jusquau = ?,
              mutuelle_resilie = ?,
              mutuelle_resilie_date = ?,
              modif_date = NOW(),
              modif_op = ?,
              modif_elem = 'modif'
            WHERE id_salarie = ?""",
        (
            bool(payload.get("adhesion")),
            payload.get("adhesion_date") or None,
            _int(payload.get("id_mutuelle")),
            bool(payload.get("mutuelle_dossier")),
            bool(payload.get("mutuelle_att_ss")),
            bool(payload.get("mutuelle_rib")),
            bool(payload.get("mutuelle_doc_envoyes")),
            bool(payload.get("mutuelle_recep_certif")),
            bool(payload.get("mutuelle_pas_adhesion")),
            payload.get("mutuelle_pas_adhesion_jusquau") or None,
            bool(payload.get("mutuelle_resilie")),
            payload.get("mutuelle_resilie_date") or None,
            int(op_id),
            int(id_salarie),
        ),
    )
    return {"ok": True}


def list_tickets_mutuelle(id_salarie: int) -> list[dict]:
    """Historique des tickets Demande Mutuelle du salarie.

    Transposition reqTicketMutuelle :
      TK_DemandeMutuelle JOIN TK_Liste JOIN salarie (sur op_crea)
      WHERE TK_DemandeMutuelle.id_salarie = X
      ORDER BY date_crea DESC.
    """
    db_trh = get_pg_connection("ticket_rh")
    rows = db_trh.query(
        """SELECT dm.id_tk_liste, dm.demande_affiliation,
                  dm.demande_affiliation_date, dm.info_cplt
           FROM ticket_rh.pgt_tk_demande_mutuelle dm
           WHERE dm.id_salarie = ?
             AND (dm.modif_elem IS NULL OR dm.modif_elem NOT LIKE '%suppr%')""",
        (int(id_salarie),),
    )
    if not rows:
        return []

    ids = [int(r.get("id_tk_liste") or 0) for r in rows if r.get("id_tk_liste")]
    if not ids:
        return []

    db_t = get_pg_connection("ticket")
    placeholders = ",".join("?" * len(ids))
    list_rows = db_t.query(
        f"""SELECT id_tk_liste, date_crea, op_crea, cloturee
            FROM ticket.pgt_tk_liste
            WHERE id_tk_liste IN ({placeholders})
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        tuple(ids),
    )
    list_map = {int(r.get("id_tk_liste") or 0): r for r in list_rows}

    op_ids = {int(r.get("op_crea") or 0) for r in list_rows}
    op_ids.discard(0)
    op_map: dict[int, str] = {}
    if op_ids:
        db_rh = get_pg_connection("rh")
        ph = ",".join(str(i) for i in op_ids)
        ops = db_rh.query(
            f"SELECT id_salarie, nom, prenom FROM rh.pgt_salarie "
            f"WHERE id_salarie IN ({ph})"
        )
        for o in ops:
            op_map[int(o.get("id_salarie") or 0)] = (
                f"{_str(o.get('nom'))} "
                f"{_capitalize_first(_str(o.get('prenom')))}"
            ).strip()

    out: list[dict] = []
    for r in rows:
        idtk = int(r.get("id_tk_liste") or 0)
        l = list_map.get(idtk)
        if not l:
            continue
        op_id = int(l.get("op_crea") or 0)
        out.append({
            "id_tk_liste": str(idtk),
            "date_crea": _iso_dt(l.get("date_crea")),
            "op_lib": op_map.get(op_id, ""),
            "cloturee": bool(l.get("cloturee")),
            "demande_affiliation": bool(r.get("demande_affiliation")),
            "demande_affiliation_date": _iso(r.get("demande_affiliation_date")),
            "info_cplt": _str(r.get("info_cplt")),
        })
    out.sort(key=lambda x: x["date_crea"], reverse=True)
    return out
