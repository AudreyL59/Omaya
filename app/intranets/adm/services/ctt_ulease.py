"""
Service Fen_ListeDocUlease (ADM Ulease -> Liste des documents Ulease).

Calque sur ctt_travail.py mais en plus simple :
- Pas de id_type_produit / doc_dpae / doc_dpae_distrib / photo_dpae.
- Tables : ulease.pgt_doc_ulease + ulease.pgt_doc_ulease_type.
- Societe (id_ste) en cross-schema rh.pgt_societe pour le libelle.

Boutons :
  - list_docs (glissiere actif/archive)
  - duplicate_doc (force prioritaire=False)
  - archive_doc / restore_doc (doc_actif=False/True)
  - delete_doc (soft delete)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection
from app.shared.notifications.mail import envoi_mail


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
    """idEntierDateHeureSys WinDev."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


def list_docs(doc_actif: bool = True) -> list[dict]:
    """ReqListeDocUlease : JOIN type + societe (cross-schema)."""
    db_ul = get_pg_connection("ulease")
    rows = db_ul.query(
        """SELECT d.id_doc_ulease, d.id_type_doc, d.titre, d.info_cpl,
                  d.datecrea, d.doc_actif, d.prioritaire, d.modif_date,
                  d.id_ste, t.lib_type
             FROM ulease.pgt_doc_ulease d
        LEFT JOIN ulease.pgt_doc_ulease_type t
               ON t.id_type_doc = d.id_type_doc
            WHERE (d.modif_elem IS NULL OR d.modif_elem NOT LIKE '%suppr%')
              AND COALESCE(d.doc_actif, FALSE) = ?
         ORDER BY t.lib_type ASC NULLS LAST, d.titre ASC""",
        (bool(doc_actif),),
    ) or []

    # Libelle societe (cross-schema rh)
    ids_ste = sorted({_int(r.get("id_ste")) for r in rows if _int(r.get("id_ste"))})
    ste_by_id: dict[int, str] = {}
    if ids_ste:
        db_rh = get_pg_connection("rh")
        placeholders = ",".join(["?"] * len(ids_ste))
        srows = db_rh.query(
            f"""SELECT id_ste, COALESCE(rs_interne, raison_sociale) AS lib
                  FROM rh.pgt_societe WHERE id_ste IN ({placeholders})""",
            tuple(ids_ste),
        ) or []
        ste_by_id = {_int(s.get("id_ste")): _str(s.get("lib")) for s in srows}

    return [
        {
            "id_doc_ulease": str(_int(r.get("id_doc_ulease")) or r.get("id_doc_ulease") or ""),
            "id_type_doc": str(_int(r.get("id_type_doc")) or ""),
            "lib_type": _str(r.get("lib_type")),
            "titre": _str(r.get("titre")),
            "info_cpl": _str(r.get("info_cpl")),
            "id_ste": str(_int(r.get("id_ste")) or ""),
            "ste_lib": ste_by_id.get(_int(r.get("id_ste")), ""),
            "prioritaire": bool(r.get("prioritaire")),
            "datecrea": _str(r.get("datecrea"))[:19],
            "modif_date": _str(r.get("modif_date"))[:19],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def duplicate_doc(
    id_doc_ulease: int, op_id: int, user_login: str = "",
    user_prenom: str = "",
) -> dict:
    """Btn Dupliquer : copie le doc, force prioritaire=False, modif_elem='new'."""
    db = get_pg_connection("ulease")
    src = db.query_one(
        "SELECT * FROM ulease.pgt_doc_ulease WHERE id_doc_ulease = ? LIMIT 1",
        (int(id_doc_ulease),),
    )
    if not src:
        return {"ok": False, "error": "Document introuvable"}

    new_id = _new_id()
    db.query(
        """INSERT INTO ulease.pgt_doc_ulease
              (id_doc_ulease, id_type_doc, titre, info_cpl, contenu,
               datecrea, doc_actif, prioritaire, id_ste,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?,
                   NOW(), TRUE, FALSE, ?,
                   NOW(), ?, 'new')""",
        (
            new_id,
            _int(src.get("id_type_doc")),
            _str(src.get("titre")),
            _str(src.get("info_cpl")),
            src.get("contenu"),
            _int(src.get("id_ste")),
            int(op_id),
        ),
    )

    # Mail a marie@exosphere.fr (cf. WinDev usersCial <> 256)
    if int(op_id) != 256 and user_login:
        try:
            envoi_mail(
                sujet=f"Document Ulease duplique {_str(src.get('titre'))} - {_str(src.get('info_cpl'))}",
                html=(
                    f"<p>Bonjour,</p>"
                    f"<p>Le document Ulease <b>{_str(src.get('titre'))} - "
                    f"{_str(src.get('info_cpl'))}</b> vient d'etre duplique par "
                    f"<b>{user_prenom or user_login}</b>.</p>"
                    f"<p>Cordialement.</p>"
                ),
                destinataires=["marie@exosphere.fr"],
                expediteur=user_login,
            )
        except Exception:
            pass
    return {"ok": True, "id_doc_ulease": str(new_id)}


def archive_doc(id_doc_ulease: int, op_id: int) -> dict:
    """Btn Archiver : doc_actif=FALSE."""
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_doc_ulease
              SET doc_actif = FALSE,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_doc_ulease = ?""",
        (int(op_id), int(id_doc_ulease)),
    )
    return {"ok": True}


def restore_doc(id_doc_ulease: int, op_id: int) -> dict:
    """Re-actif depuis l'archive."""
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_doc_ulease
              SET doc_actif = TRUE,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_doc_ulease = ?""",
        (int(op_id), int(id_doc_ulease)),
    )
    return {"ok": True}


def delete_doc(id_doc_ulease: int, op_id: int) -> dict:
    """Btn Supprimer : soft delete (modif_elem='suppr')."""
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_doc_ulease
              SET modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'suppr'
            WHERE id_doc_ulease = ?""",
        (int(op_id), int(id_doc_ulease)),
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Combo types doc
# ---------------------------------------------------------------------------


def list_types_doc() -> list[dict]:
    """Combo Type Doc Ulease."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT id_type_doc, lib_type FROM ulease.pgt_doc_ulease_type
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY lib_type""",
    ) or []
    return [
        {"id_type_doc": str(_int(r.get("id_type_doc"))), "lib": _str(r.get("lib_type"))}
        for r in rows
    ]
