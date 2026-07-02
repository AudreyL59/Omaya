"""
Onglet 'Contrat de travail' (Docs RH) de la fiche salarie ADM.

Transposition de la fenetre WinDev FI_SalarieDocRH :
  - Tableau des documents RH du salarie
    (pgt_salarie_doc_rh JOIN pgt_doc_rh + pgt_salarie pour le responsable)
  - Boutons :
    * Nouveau (popup Fen_SalarieDocRH a coder)
    * Supprimer (soft delete via modif_elem='suppr')
    * Cttw RECU (UPDATE recu=true + recu_date=now)
    * Voir le Ctt edite (resolve URL via pgt_tk_demande_cttw)
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


def _capitalize_first(s: str) -> str:
    if not s:
        return ""
    return s[0].upper() + s[1:].lower()


def load_doc_rh(id_salarie: int) -> list[dict]:
    """Liste des documents RH du salarie.

    JOIN :
      - pgt_doc_rh sur le titre du modele
      - pgt_doc_rhtype sur le libelle du type
      - pgt_salarie sur le nom du responsable (id_da)
    """
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT
              sdr.id_salarie_doc_rh,
              sdr.id_doc_rhtype,
              sdr.id_da,
              sdr.id_docusign,
              sdr.date_edition,
              sdr.recu,
              sdr.recu_date,
              dr.titre AS doc_titre,
              drt.lib_type AS doc_type_lib,
              da.nom AS da_nom,
              da.prenom AS da_prenom
           FROM rh.pgt_salarie_doc_rh sdr
           LEFT JOIN rh.pgt_doc_rh dr ON dr.id_doc_rh = sdr.id_doc_rhtype
           LEFT JOIN rh.pgt_doc_rhtype drt ON drt.id_type_doc = dr.id_type_doc
           LEFT JOIN rh.pgt_salarie da ON da.id_salarie = sdr.id_da
           WHERE sdr.id_salarie = ?
             AND sdr.modif_elem NOT LIKE '%suppr%'
           ORDER BY sdr.date_edition DESC NULLS LAST, sdr.modif_date DESC""",
        (int(id_salarie),),
    )
    return [
        {
            "id_salarie_doc_rh": str(r.get("id_salarie_doc_rh") or ""),
            "id_doc_rhtype": str(r.get("id_doc_rhtype") or ""),
            "type_doc_lib": (
                _str(r.get("doc_titre"))
                or _str(r.get("doc_type_lib"))
            ),
            "id_da": str(r.get("id_da") or ""),
            "responsable_nom": (
                f"{_str(r.get('da_nom'))} {_capitalize_first(_str(r.get('da_prenom')))}"
            ).strip(),
            "date_edition": _iso(r.get("date_edition")),
            "recu": bool(r.get("recu")),
            "recu_date": _iso(r.get("recu_date")),
            "signe_demat": bool(_str(r.get("id_docusign")).strip()),
            "id_docusign": _str(r.get("id_docusign")),
        }
        for r in rows
    ]


def mark_cttw_recu(id_salarie_doc_rh: int, op_id: int) -> dict:
    """Bouton 'Cttw RECU' : passe recu=true, recu_date=now."""
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_salarie_doc_rh SET
              recu = TRUE,
              recu_date = NOW(),
              modif_date = NOW(),
              modif_op = ?,
              modif_elem = 'modif'
            WHERE id_salarie_doc_rh = ?""",
        (_int(op_id), _int(id_salarie_doc_rh)),
    )
    return {"ok": True}


def soft_delete_doc_rh(id_salarie_doc_rh: int, op_id: int) -> dict:
    """Soft delete (modif_elem='suppr')."""
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_salarie_doc_rh SET
              modif_date = NOW(),
              modif_op = ?,
              modif_elem = 'suppr'
            WHERE id_salarie_doc_rh = ?""",
        (_int(op_id), _int(id_salarie_doc_rh)),
    )
    return {"ok": True}


def list_types_produit_fdv() -> list[dict]:
    """Combo 'Type Produit' de la popup nouveau doc RH.

    Filtre WinDev : TypeProduit.Type LIKE '%FDV%' (force de vente).
    """
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_type_produit, lib
           FROM rh.pgt_type_produit
           WHERE type LIKE '%FDV%'
             AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
           ORDER BY lib ASC NULLS LAST"""
    )
    return [
        {
            "id_type_produit": str(r.get("id_type_produit") or ""),
            "lib": _str(r.get("lib")),
        }
        for r in rows
    ]


def get_type_produit_salarie(id_salarie: int) -> str:
    """Recupere le type produit par defaut du salarie via son organigramme
    courant (cf. WinDev ReqOrgaCourantetParentByVendeur)."""
    db = get_pg_connection("rh")
    row = db.query_one(
        """SELECT o.id_type_produit
           FROM rh.pgt_salarie_organigramme so
           LEFT JOIN rh.pgt_organigramme o ON o.idorganigramme = so.idorganigramme
           WHERE so.id_salarie = ?
             AND so.modif_elem NOT LIKE '%suppr%'
             AND COALESCE(so.aff_actif, FALSE) = TRUE
           ORDER BY so.date_debut DESC NULLS LAST
           LIMIT 1""",
        (int(id_salarie),),
    )
    return str(row.get("id_type_produit") or "") if row else ""


def list_docs_disponibles(id_salarie: int, id_type_produit: int) -> list[dict]:
    """Liste des modeles de docs RH disponibles pour ce salarie + type produit.

    Transposition WinDev Table_ReqListeDocRH_ByProdBySte :
      societe.IdSte = docRH.IdSte
      AND docRH.IdSte IN (salarie.IdSte, 0)   # 0 = tous
      AND docRH.IDTypeProduit = ?
      AND docRH.IDTypeDoc <> 12               # exclu type 12
      AND docRH.DocActif = TRUE
      AND docRH.ModifElem <> 'suppr'
      ORDER BY IdSte DESC
    """
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT
              dr.id_doc_rh, dr.id_ste, dr.titre, dr.info_cpl,
              dr.id_type_produit, dr.prioritaire,
              dr.id_type_doc,
              drt.lib_type,
              soc.rs_interne
           FROM rh.pgt_doc_rh dr
           LEFT JOIN rh.pgt_societe soc ON soc.id_ste = dr.id_ste
           LEFT JOIN rh.pgt_doc_rhtype drt ON drt.id_type_doc = dr.id_type_doc
           WHERE dr.modif_elem NOT LIKE '%suppr%'
             AND COALESCE(dr.doc_actif, FALSE) = TRUE
             AND (dr.id_ste = ? OR dr.id_ste = 0)
             AND dr.id_type_produit = ?
             AND dr.id_type_doc <> 12
           ORDER BY dr.id_ste DESC, dr.titre ASC""",
        (_get_id_ste_salarie(id_salarie), int(id_type_produit)),
    )
    return [
        {
            "id_doc_rh": str(r.get("id_doc_rh") or ""),
            "id_ste": str(r.get("id_ste") or ""),
            "rs_interne": _str(r.get("rs_interne")) or ("Tous" if not r.get("id_ste") else ""),
            "id_type_doc": str(r.get("id_type_doc") or ""),
            "type_doc_lib": _str(r.get("lib_type")),
            "titre": _str(r.get("titre")),
            "info_cpl": _str(r.get("info_cpl")),
            "prioritaire": bool(r.get("prioritaire")),
        }
        for r in rows
    ]


def _get_id_ste_salarie(id_salarie: int) -> int:
    """Recupere id_ste du salarie via son embauche."""
    db = get_pg_connection("rh")
    row = db.query_one(
        "SELECT id_ste FROM rh.pgt_salarie_embauche WHERE id_salarie = ?",
        (int(id_salarie),),
    )
    return _int(row.get("id_ste")) if row else 0


def find_ctt_edite_url(id_salarie_doc_rh: int) -> dict:
    """Bouton 'Voir le Ctt edite' : retourne l'URL du PDF si un ticket
    TK_DemandeCttW est associe a ce doc.

    URL : https://interne.omaya.fr/TempCttw/{id_tk_liste}-cttW.pdf
    """
    db = get_pg_connection("ticket_rh")
    row = db.query_one(
        """SELECT id_tk_liste FROM ticket_rh.pgt_tk_demande_ctt_w
           WHERE id_doc_rhedit = ?
           LIMIT 1""",
        (int(id_salarie_doc_rh),),
    )
    if not row:
        return {"url": "", "error": "Pas de ticket associé"}
    id_tk_liste = _int(row.get("id_tk_liste"))
    return {
        "url": f"https://interne.omaya.fr/TempCttw/{id_tk_liste}-cttW.pdf",
    }
