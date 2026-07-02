"""
Onglet 'Organigramme' de la fiche salarie ADM.

Transposition de la fenetre WinDev FI_SalarieOrgaSuivi + popup Fen_salarieOrga :
  - Liste des rattachements (pgt_salarie_organigramme JOIN pgt_organigramme)
  - Liste des suivis (pgt_salarie_suivi : changements d'equipe, de poste, etc.)
  - Operations : creer / modifier / dupliquer / supprimer (soft delete via
    modif_elem)
  - Navigation dans l'organigramme (arbre IdParent->idorganigramme)

A la creation d'un rattachement :
  1. Insert pgt_salarie_organigramme
  2. Ferme le dernier suivi en cours (type=2 = changement d'equipe) en
     posant date_fin = today
  3. Cree un nouveau suivi (type=2, idorganigramme = nouveau)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection
from app.core.utils.sentinel_dates import is_sentinel


# --- Helpers --------------------------------------------------------------

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


def _new_id() -> int:
    """ID 8 octets timestamp (cf. WinDev idEntierDateHeureSys)."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


def _today_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")


# --- Lecture --------------------------------------------------------------

def load_orga_suivi(id_salarie: int) -> dict:
    """Charge les 2 listes affichees dans l'onglet 'Organigramme'.

    Retourne :
      {
        organigrammes: [{id_salarie_organigramme, lib_orga, type_produit_lib,
                          date_debut, date_fin, aff_actif, id_organigramme}, ...],
        suivis: [{id_suivi, type, type_lib, lib_orga, lib_poste,
                   date_debut, date_fin, modif_date}, ...]
      }
    """
    db = get_pg_connection("rh")

    organigrammes = db.query(
        """SELECT
              so.id_salarie_organigramme,
              so.idorganigramme,
              so.date_debut,
              so.date_fin,
              so.aff_actif,
              so.id_ste,
              o.lib_orga,
              o.id_type_produit,
              tp.lib AS type_produit_lib,
              soc.rs_interne
           FROM rh.pgt_salarie_organigramme so
           LEFT JOIN rh.pgt_organigramme o ON o.idorganigramme = so.idorganigramme
           LEFT JOIN rh.pgt_type_produit tp ON tp.id_type_produit = o.id_type_produit
           LEFT JOIN rh.pgt_societe soc ON soc.id_ste = so.id_ste
           WHERE so.id_salarie = ?
             AND so.modif_elem NOT LIKE '%suppr%'
           ORDER BY so.date_debut DESC""",
        (int(id_salarie),),
    )

    suivis = db.query(
        """SELECT
              ss.id_suivi,
              ss.type,
              ss.idorganigramme,
              ss.id_type_poste,
              ss.date_debut,
              ss.date_fin,
              ss.modif_date,
              o.lib_orga,
              tp.lib_poste
           FROM rh.pgt_salarie_suivi ss
           LEFT JOIN rh.pgt_organigramme o ON o.idorganigramme = ss.idorganigramme
           LEFT JOIN rh.pgt_type_poste tp ON tp.id_type_poste = ss.id_type_poste
           WHERE ss.id_salarie = ?
             AND ss.modif_elem NOT LIKE '%suppr%'
           ORDER BY ss.date_debut DESC, ss.modif_date DESC""",
        (int(id_salarie),),
    )

    return {
        "organigrammes": [
            {
                "id_salarie_organigramme": str(r.get("id_salarie_organigramme") or ""),
                "id_organigramme": str(r.get("idorganigramme") or ""),
                "lib_orga": _str(r.get("lib_orga")),
                "type_produit_lib": _str(r.get("type_produit_lib")),
                "date_debut": _iso(r.get("date_debut")),
                "date_fin": _iso(r.get("date_fin")),
                "aff_actif": bool(r.get("aff_actif")),
                "id_ste": str(r.get("id_ste") or ""),
                "rs_interne": _str(r.get("rs_interne")),
            }
            for r in organigrammes
        ],
        "suivis": [
            {
                "id_suivi": str(r.get("id_suivi") or ""),
                "type": _int(r.get("type")),
                "type_lib": _type_suivi_lib(_int(r.get("type"))),
                "id_organigramme": str(r.get("idorganigramme") or ""),
                "lib_orga": _str(r.get("lib_orga")),
                "id_type_poste": _int(r.get("id_type_poste")),
                "lib_poste": _str(r.get("lib_poste")),
                "date_debut": _iso(r.get("date_debut")),
                "date_fin": _iso(r.get("date_fin")),
                "modif_date": _iso_dt(r.get("modif_date")),
            }
            for r in suivis
        ],
    }


def _type_suivi_lib(type_id: int) -> str:
    """Libelle du type de suivi (cf. WinDev TYPE in salarie_suivi).

    Mapping infere du code WinDev observe (TYPE=2 = changement d'equipe).
    A confirmer/completer avec la table de reference si elle existe.
    """
    return {
        1: "Changement de poste",
        2: "Changement d'équipe",
        3: "Changement d'entité",
    }.get(type_id, f"Type {type_id}" if type_id else "")


# --- Liste des societes (pour le combo de la popup) -----------------------

def list_societes() -> list[dict]:
    """Liste les societes racines (id_type_orga=1) pour le combo 'Societe'
    de la popup rattachement."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_ste, rs_interne, raison_sociale
           FROM rh.pgt_societe
           WHERE modif_elem NOT LIKE '%suppr%'
             AND id_type_orga = 1
           ORDER BY raison_sociale ASC NULLS LAST"""
    )
    return [
        {
            "id_ste": str(r.get("id_ste") or ""),
            "lib": _str(r.get("rs_interne")) or _str(r.get("raison_sociale")),
        }
        for r in rows
    ]


# --- Arbre organigramme ---------------------------------------------------

def load_orga_children(id_parent: int = 0) -> list[dict]:
    """Liste les organigrammes enfants d'un noeud (id_parent=0 = racine).

    Transposition de ReqRacineOrga (id_parent=0) et ReqEnfantOrga_ByIdOrga
    (id_parent=X). Retourne {id_organigramme, lib_orga, has_children}.
    """
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT idorganigramme, lib_orga,
                  (SELECT COUNT(*) FROM rh.pgt_organigramme c
                   WHERE c.id_parent = o.idorganigramme
                     AND c.modif_elem <> 'suppr'
                     AND c.idorganigramme <> 0) AS nb_enfants
           FROM rh.pgt_organigramme o
           WHERE o.id_parent = ?
             AND o.modif_elem <> 'suppr'
             AND o.idorganigramme <> 0
           ORDER BY o.lib_orga ASC""",
        (int(id_parent),),
    )
    return [
        {
            "id_organigramme": str(r.get("idorganigramme") or ""),
            "lib_orga": _str(r.get("lib_orga")),
            "has_children": _int(r.get("nb_enfants")) > 0,
        }
        for r in rows
    ]


# --- Ecriture -------------------------------------------------------------

def duplicate_rattachement(id_salarie_organigramme: int, op_id: int) -> dict:
    """Duplique la ligne (cf. WinDev Btn 'Dupliquer' : memes valeurs, ModifElem='new')."""
    db = get_pg_connection("rh")
    row = db.query_one(
        """SELECT id_salarie, idorganigramme, date_debut, date_fin, aff_actif, id_ste
           FROM rh.pgt_salarie_organigramme
           WHERE id_salarie_organigramme = ?""",
        (int(id_salarie_organigramme),),
    )
    if not row:
        return {"ok": False, "error": "Rattachement introuvable"}

    new_id = _new_id()
    db.query(
        """INSERT INTO rh.pgt_salarie_organigramme
              (id_salarie_organigramme, id_salarie, idorganigramme,
               date_debut, date_fin, aff_actif, id_ste,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id,
            _int(row.get("id_salarie")),
            _int(row.get("idorganigramme")),
            row.get("date_debut"),
            row.get("date_fin"),
            bool(row.get("aff_actif")),
            _int(row.get("id_ste")),
            _int(op_id),
        ),
    )
    return {"ok": True, "id_salarie_organigramme": str(new_id)}


def soft_delete_rattachement(id_salarie_organigramme: int, op_id: int) -> dict:
    """Soft delete (modif_elem='suppr'). Retourne aussi id_salarie pour rafraichir."""
    db = get_pg_connection("rh")
    row = db.query_one(
        "SELECT id_salarie FROM rh.pgt_salarie_organigramme WHERE id_salarie_organigramme = ?",
        (int(id_salarie_organigramme),),
    )
    if not row:
        return {"ok": False, "error": "Rattachement introuvable"}

    db.query(
        f"""UPDATE rh.pgt_salarie_organigramme SET
              modif_date = NOW(),
              modif_op = {_int(op_id)},
              modif_elem = 'suppr'
            WHERE id_salarie_organigramme = {_int(id_salarie_organigramme)}"""
    )
    return {"ok": True, "id_salarie": str(_int(row.get("id_salarie")))}


def save_rattachement(
    *,
    id_salarie: int,
    id_salarie_organigramme: int,  # 0 = creation
    id_organigramme: int,
    date_debut: str,
    date_fin: str,
    aff_actif: bool,
    id_ste: int,
    op_id: int,
) -> dict:
    """Cree ou modifie un rattachement (transposition Fen_salarieOrga btn Enregistrer).

    En mode creation : ferme le dernier suivi 'changement d'equipe' (type=2) en
    cours et cree un nouveau suivi (type=2) pour tracer le changement.
    """
    db = get_pg_connection("rh")

    if id_salarie_organigramme:
        # Modification
        db.query(
            """UPDATE rh.pgt_salarie_organigramme SET
                  idorganigramme = ?,
                  date_debut = ?,
                  date_fin = ?,
                  aff_actif = ?,
                  id_ste = ?,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
                WHERE id_salarie_organigramme = ?""",
            (
                _int(id_organigramme),
                date_debut or None,
                date_fin or None,
                bool(aff_actif),
                _int(id_ste),
                _int(op_id),
                _int(id_salarie_organigramme),
            ),
        )
        return {"ok": True, "id_salarie_organigramme": str(id_salarie_organigramme)}

    # Creation
    new_id = _new_id()
    db.query(
        """INSERT INTO rh.pgt_salarie_organigramme
              (id_salarie_organigramme, id_salarie, idorganigramme,
               date_debut, date_fin, aff_actif, id_ste,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id,
            _int(id_salarie),
            _int(id_organigramme),
            date_debut or None,
            date_fin or None,
            bool(aff_actif),
            _int(id_ste),
            _int(op_id),
        ),
    )

    # Cloture du dernier suivi en cours (type=2) et creation du nouveau
    today = _today_iso()
    last = db.query_one(
        """SELECT id_suivi FROM rh.pgt_salarie_suivi
           WHERE id_salarie = ?
             AND type = 2
             AND (date_fin IS NULL OR date_fin = '' OR date_fin > ?)
             AND modif_elem NOT LIKE '%suppr%'
           ORDER BY date_debut DESC, modif_date DESC
           LIMIT 1""",
        (int(id_salarie), today),
    )
    if last:
        db.query(
            f"""UPDATE rh.pgt_salarie_suivi SET
                  date_fin = '{today}',
                  modif_date = NOW(),
                  modif_op = {_int(op_id)},
                  modif_elem = 'modif'
                WHERE id_suivi = {_int(last.get('id_suivi'))}"""
        )

    suivi_id = _new_id()
    db.query(
        """INSERT INTO rh.pgt_salarie_suivi
              (id_suivi, id_salarie, type, idorganigramme, id_type_poste,
               date_debut, date_fin, modif_date, modif_op, modif_elem)
           VALUES (?, ?, 2, ?, 0, ?, NULL, NOW(), ?, 'new')""",
        (
            suivi_id,
            _int(id_salarie),
            _int(id_organigramme),
            today,
            _int(op_id),
        ),
    )
    return {
        "ok": True,
        "id_salarie_organigramme": str(new_id),
        "id_suivi_cree": str(suivi_id),
    }
