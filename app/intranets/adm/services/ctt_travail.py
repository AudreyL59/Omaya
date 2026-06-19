"""
Service Fen_ListeDocRH (ADM, Salaries -> Liste des contrats de travail).

Transposition WinDev :
- Table_DocRH_Actif : JOIN doc_rh + doc_rhtype (type doc) + type_produit
  (logo + libelle) filtre par DocActif (glissiere haut droit).
- Boutons : Nouveau / Dupliquer / Supprimer / Modifier / Archiver.

L'edition d'un docRH (Fen_EditionDocRH) sera dans un module dedie.
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


def list_docs(doc_actif: bool = True) -> list[dict]:
    """Cf. requete ReqListeDocRH WinDev (filtre DocActif via glissiere)."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT d.id_doc_rh, d.id_type_doc, d.titre, d.info_cpl,
                  d.id_type_produit, d.datecrea, d.doc_actif,
                  d.prioritaire, d.modif_date,
                  d.id_ste, d.doc_dpae,
                  t.lib_type,
                  tp.lib AS lib_produit
             FROM rh.pgt_doc_rh d
        LEFT JOIN rh.pgt_doc_rhtype t ON t.id_type_doc = d.id_type_doc
        LEFT JOIN rh.pgt_type_produit tp ON tp.id_type_produit = d.id_type_produit
            WHERE (d.modif_elem IS NULL OR d.modif_elem NOT LIKE '%suppr%')
              AND COALESCE(d.doc_actif, FALSE) = ?
         ORDER BY tp.lib ASC NULLS LAST, d.titre ASC""",
        (bool(doc_actif),),
    ) or []
    return [
        {
            "id_doc_rh": str(r.get("id_doc_rh") or ""),
            "id_type_doc": str(_int(r.get("id_type_doc")) or ""),
            "lib_type": _str(r.get("lib_type")),
            "titre": _str(r.get("titre")),
            "info_cpl": _str(r.get("info_cpl")),
            "id_type_produit": str(_int(r.get("id_type_produit")) or ""),
            "lib_produit": _str(r.get("lib_produit")),
            "id_ste": str(_int(r.get("id_ste")) or ""),
            "doc_dpae": bool(r.get("doc_dpae")),
            "prioritaire": bool(r.get("prioritaire")),
            "datecrea": _str(r.get("datecrea"))[:19],
            "modif_date": _str(r.get("modif_date"))[:19],
        }
        for r in rows
    ]


def duplicate_doc(id_doc_rh: int, op_id: int, user_login: str = "",
                  user_prenom: str = "") -> dict:
    """Btn Dupliquer : copie le doc avec une nouvelle pk, force
    prioritaire=False et doc_dpae=False. Cf. WinDev."""
    db = get_pg_connection("rh")
    src = db.query_one(
        "SELECT * FROM rh.pgt_doc_rh WHERE id_doc_rh = ? LIMIT 1",
        (int(id_doc_rh),),
    )
    if not src:
        return {"ok": False, "error": "Document introuvable"}

    new_id = _new_id()
    db.query(
        """INSERT INTO rh.pgt_doc_rh
              (id_doc_rh, id_type_doc, titre, info_cpl, id_type_produit,
               contenu, datecrea, doc_actif, prioritaire, id_ste, doc_dpae,
               doc_dpae_distrib, id_tk_type_photo_dpae,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?,
                   ?, NOW(), TRUE, FALSE, ?, FALSE,
                   ?, ?,
                   NOW(), ?, 'new')""",
        (
            new_id,
            _int(src.get("id_type_doc")),
            _str(src.get("titre")),
            _str(src.get("info_cpl")),
            _int(src.get("id_type_produit")),
            src.get("contenu"),
            _int(src.get("id_ste")),
            bool(src.get("doc_dpae_distrib")),
            _int(src.get("id_tk_type_photo_dpae")),
            int(op_id),
        ),
    )

    # Mail a marie@exosphere.fr (cf. WinDev usersCial <> 256)
    if int(op_id) != 256 and user_login:
        try:
            envoi_mail(
                sujet=f"Ctt de travail duplique {_str(src.get('titre'))} - {_str(src.get('info_cpl'))}",
                html=(
                    f"<p>Bonjour,</p>"
                    f"<p>Le contrat de travail <b>{_str(src.get('titre'))} - "
                    f"{_str(src.get('info_cpl'))}</b> vient d'etre duplique par "
                    f"<b>{user_prenom or user_login}</b>.</p>"
                    f"<p>Cordialement.</p>"
                ),
                destinataires=["marie@exosphere.fr"],
                expediteur=user_login,
            )
        except Exception:
            pass
    return {"ok": True, "id_doc_rh": str(new_id)}


def archive_doc(id_doc_rh: int, op_id: int) -> dict:
    """Btn Archiver : doc_actif=FALSE."""
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_doc_rh
              SET doc_actif = FALSE,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_doc_rh = ?""",
        (int(op_id), int(id_doc_rh)),
    )
    return {"ok": True}


def restore_doc(id_doc_rh: int, op_id: int) -> dict:
    """Re-actif depuis l'archive."""
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_doc_rh
              SET doc_actif = TRUE,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_doc_rh = ?""",
        (int(op_id), int(id_doc_rh)),
    )
    return {"ok": True}


def delete_doc(id_doc_rh: int, op_id: int) -> dict:
    """Btn Supprimer : soft delete (modif_elem='suppr')."""
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_doc_rh
              SET modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'suppr'
            WHERE id_doc_rh = ?""",
        (int(op_id), int(id_doc_rh)),
    )
    return {"ok": True}
