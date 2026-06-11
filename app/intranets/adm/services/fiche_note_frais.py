"""
Onglet 'Note de frais' de la fiche salarie ADM.

Transposition de la fenetre WinDev FI_SalarieNoteFrais.

Etape 1 (ce commit) :
  - Liste filtree par periode (mois + annee) avec rupture par mois.
  - GET d'une ligne pour pre-remplir le formulaire d'edition.
  - Save (UPDATE) d'une ligne existante.
  - Soft delete.
  - Liste des types de note de frais (combo).
  - Aperçu photo (bytea -> response binaire).

Etape 2 (commit suivant) : INSERT via Fen_NoteFraisAjout + upload photo.
Etape 3 : Impression PDF complete (EtatNoteFrais + EtatPhotoTicket).
"""

from __future__ import annotations

from datetime import date, datetime
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


def _iso(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _float(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def list_types() -> list[dict]:
    """Combo Type de note de frais."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_note_frais_type, lib_type_note_frais
           FROM rh.pgt_note_frais_type
           WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
           ORDER BY lib_type_note_frais ASC NULLS LAST"""
    )
    return [
        {
            "id_note_frais_type": _int(r.get("id_note_frais_type")),
            "lib_type_note_frais": _str(r.get("lib_type_note_frais")),
        }
        for r in rows
    ]


def list_notes(id_salarie: int, mois: int, annee: int) -> list[dict]:
    """Liste les notes de frais d'un salarie pour la periode 1er du mois.

    periode_note attendue = date('YYYY-MM-01'). Tri WinDev (DATE ASC).
    """
    if not mois or not annee:
        return []
    try:
        periode = date(int(annee), int(mois), 1)
    except (ValueError, TypeError):
        return []
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT nf.id_note_frais, nf.id_note_frais_type, nf.date,
                  nf.description, nf.montant_ht, nf.montant_tva,
                  nf.montant_ttc, nf.verifiee,
                  (nf.photo_ticket IS NOT NULL AND octet_length(nf.photo_ticket) > 0)
                    AS has_photo,
                  t.lib_type_note_frais
           FROM rh.pgt_note_frais nf
           LEFT JOIN rh.pgt_note_frais_type t
             ON t.id_note_frais_type = nf.id_note_frais_type
           WHERE nf.id_salarie = ?
             AND nf.periode_note = ?
             AND nf.modif_elem NOT LIKE '%suppr%'
           ORDER BY nf.date ASC NULLS LAST""",
        (int(id_salarie), periode),
    )
    return [
        {
            "id_note_frais": str(r.get("id_note_frais") or ""),
            "id_note_frais_type": _int(r.get("id_note_frais_type")),
            "lib_type_note_frais": _str(r.get("lib_type_note_frais")),
            "date": _iso(r.get("date")),
            "description": _str(r.get("description")),
            "montant_ht": _float(r.get("montant_ht")),
            "montant_tva": _float(r.get("montant_tva")),
            "montant_ttc": _float(r.get("montant_ttc")),
            "verifiee": bool(r.get("verifiee")),
            "has_photo": bool(r.get("has_photo")),
        }
        for r in rows
    ]


def get_note(id_note_frais: int) -> dict | None:
    """Detail d'une ligne pour pre-remplir le formulaire d'edition."""
    db = get_pg_connection("rh")
    r = db.query_one(
        """SELECT id_note_frais, id_note_frais_type, date, description,
                  montant_ht, montant_tva, montant_ttc, verifiee,
                  (photo_ticket IS NOT NULL AND octet_length(photo_ticket) > 0)
                    AS has_photo
           FROM rh.pgt_note_frais WHERE id_note_frais = ?""",
        (int(id_note_frais),),
    )
    if not r:
        return None
    return {
        "id_note_frais": str(r.get("id_note_frais") or ""),
        "id_note_frais_type": _int(r.get("id_note_frais_type")),
        "date": _iso(r.get("date")),
        "description": _str(r.get("description")),
        "montant_ht": _float(r.get("montant_ht")),
        "montant_tva": _float(r.get("montant_tva")),
        "montant_ttc": _float(r.get("montant_ttc")),
        "verifiee": bool(r.get("verifiee")),
        "has_photo": bool(r.get("has_photo")),
    }


def save_note(
    *,
    id_note_frais: int,
    id_note_frais_type: int,
    date_iso: str,
    description: str,
    montant_ht: float,
    montant_tva: float,
    montant_ttc: float,
    verifiee: bool,
    op_id: int,
) -> dict:
    """UPDATE d'une note existante (cf. WinDev SaveNoteFrais)."""
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_note_frais SET
              id_note_frais_type = ?,
              date = ?,
              description = ?,
              montant_ht = ?,
              montant_tva = ?,
              montant_ttc = ?,
              verifiee = ?,
              modif_date = NOW(),
              modif_op = ?,
              modif_elem = 'modif'
            WHERE id_note_frais = ?""",
        (
            int(id_note_frais_type),
            date_iso or None,
            description,
            float(montant_ht),
            float(montant_tva),
            float(montant_ttc),
            bool(verifiee),
            int(op_id),
            int(id_note_frais),
        ),
    )
    return {"ok": True, "id_note_frais": str(id_note_frais)}


def soft_delete_note(id_note_frais: int, op_id: int) -> dict:
    """Btn poubelle : soft delete."""
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_note_frais SET
              modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_note_frais = ?""",
        (int(op_id), int(id_note_frais)),
    )
    return {"ok": True}


def get_photo(id_note_frais: int) -> tuple[bytes, str] | None:
    """Bytea + mime de la photo ticket. None si pas de photo."""
    db = get_pg_connection("rh")
    r = db.query_one(
        "SELECT photo_ticket FROM rh.pgt_note_frais WHERE id_note_frais = ?",
        (int(id_note_frais),),
    )
    if not r:
        return None
    blob = r.get("photo_ticket")
    if not blob:
        return None
    if isinstance(blob, memoryview):
        blob = blob.tobytes()
    if not isinstance(blob, (bytes, bytearray)):
        return None
    data = bytes(blob)
    if not data:
        return None
    # Detection mime simple sur les magic bytes
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    elif data[:3] == b"\xff\xd8\xff":
        mime = "image/jpeg"
    elif data[:6] in (b"GIF87a", b"GIF89a"):
        mime = "image/gif"
    elif data[:4] == b"%PDF":
        mime = "application/pdf"
    else:
        mime = "application/octet-stream"
    return data, mime
