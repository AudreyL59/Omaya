"""
Service Fen_FicheVehicule Plan 4 (PV / Amendes).

Table : ulease.pgt_vehicule_amende.
Documents : FTP /OMAYA/Vehicules/{id_vehicule}/PV_{id_vehicule_pv}/
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


def _float(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _iso_date(v: Any) -> str:
    if v is None or v == "":
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    return s[:10] if len(s) >= 10 and s[4] == "-" else s


def _iso_datetime(v: Any) -> str:
    if v is None or v == "":
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%dT%H:%M")
    s = str(v)
    return s[:16] if len(s) >= 16 else s


def _new_id() -> int:
    """idEntierDateHeureSys WinDev."""
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


def list_pv(id_vehicule: int) -> list[dict]:
    """Liste les PV/Amendes d'un vehicule + nom du conducteur."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT va.id_vehicule_pv, va.id_vehicule_pc, va.vehicule_pv_date,
                  va.montant, va.num_pv, va.frais, va.nb_pts,
                  va.paye_employeur, va.paye_employeur_date,
                  va.prel_salarie, va.prel_salarie_date, va.comment,
                  c.nom_conducteur, c.prenom_conducteur
             FROM ulease.pgt_vehicule_amende va
        LEFT JOIN ulease.pgt_vehicule_conducteur vc
               ON vc.id_vehicule_pc = va.id_vehicule_pc
        LEFT JOIN ulease.pgt_conducteur c
               ON c.id_conducteur = vc.id_conducteur
            WHERE va.id_vehicule = ?
              AND (va.modif_elem IS NULL OR va.modif_elem NOT LIKE '%suppr%')
         ORDER BY va.vehicule_pv_date DESC""",
        (int(id_vehicule),),
    ) or []
    out = []
    for r in rows:
        nom = _str(r.get("nom_conducteur"))
        prenom = _str(r.get("prenom_conducteur")).strip().capitalize()
        out.append({
            "id_vehicule_pv": str(_int(r.get("id_vehicule_pv"))),
            "id_vehicule_pc": str(_int(r.get("id_vehicule_pc"))),
            "conducteur": f"{nom} {prenom}".strip(),
            "vehicule_pv_date": _iso_datetime(r.get("vehicule_pv_date")),
            "montant": _float(r.get("montant")),
            "num_pv": _str(r.get("num_pv")),
            "frais": _float(r.get("frais")),
            "nb_pts": _int(r.get("nb_pts")),
            "paye_employeur": bool(r.get("paye_employeur")),
            "paye_employeur_date": _iso_date(r.get("paye_employeur_date")),
            "prel_salarie": bool(r.get("prel_salarie")),
            "prel_salarie_date": _str(r.get("prel_salarie_date")),
            "comment": _str(r.get("comment")),
        })
    return out


def get_pv(id_vehicule_pv: int) -> dict | None:
    """Detail d'un PV pour edition (form)."""
    db = get_pg_connection("ulease")
    r = db.query_one(
        """SELECT id_vehicule_pv, id_vehicule, id_vehicule_pc,
                  vehicule_pv_date, montant, num_pv, frais, nb_pts,
                  paye_employeur, paye_employeur_date,
                  prel_salarie, prel_salarie_date, comment
             FROM ulease.pgt_vehicule_amende
            WHERE id_vehicule_pv = ? LIMIT 1""",
        (int(id_vehicule_pv),),
    )
    if not r:
        return None
    return {
        "id_vehicule_pv": str(_int(r.get("id_vehicule_pv"))),
        "id_vehicule": str(_int(r.get("id_vehicule"))),
        "id_vehicule_pc": str(_int(r.get("id_vehicule_pc"))),
        "vehicule_pv_date": _iso_datetime(r.get("vehicule_pv_date")),
        "montant": _float(r.get("montant")),
        "num_pv": _str(r.get("num_pv")),
        "frais": _float(r.get("frais")),
        "nb_pts": _int(r.get("nb_pts")),
        "paye_employeur": bool(r.get("paye_employeur")),
        "paye_employeur_date": _iso_date(r.get("paye_employeur_date")),
        "prel_salarie": bool(r.get("prel_salarie")),
        "prel_salarie_date": _str(r.get("prel_salarie_date")),
        "comment": _str(r.get("comment")),
    }


def save_pv(payload: dict, op_id: int) -> dict:
    """Btn Enregistrer le PV : create (id=0) ou update."""
    db = get_pg_connection("ulease")
    id_pv = _int(payload.get("id_vehicule_pv"))
    # Si paye_employeur=False, on vide la date associee (cf. WinDev)
    paye_employeur = bool(payload.get("paye_employeur"))
    paye_date = payload.get("paye_employeur_date") if paye_employeur else None
    if paye_date == "":
        paye_date = None
    prel_salarie = bool(payload.get("prel_salarie"))
    prel_date = payload.get("prel_salarie_date") if prel_salarie else ""

    if id_pv == 0:
        new_id = _new_id()
        db.query(
            """INSERT INTO ulease.pgt_vehicule_amende
                 (id_vehicule_pv, id_vehicule, id_vehicule_pc,
                  vehicule_pv_date, montant, num_pv, frais, nb_pts,
                  paye_employeur, paye_employeur_date,
                  prel_salarie, prel_salarie_date, comment,
                  modif_op, modif_date, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, NOW(), 'new')""",
            (
                new_id,
                _int(payload.get("id_vehicule")),
                _int(payload.get("id_vehicule_pc")),
                payload.get("vehicule_pv_date") or None,
                _float(payload.get("montant")),
                _str(payload.get("num_pv")),
                _float(payload.get("frais")) or 15.0,
                _int(payload.get("nb_pts")),
                paye_employeur,
                paye_date,
                prel_salarie,
                prel_date,
                _str(payload.get("comment")),
                int(op_id),
            ),
        )
        return {"ok": True, "id_vehicule_pv": str(new_id)}
    db.query(
        """UPDATE ulease.pgt_vehicule_amende
              SET id_vehicule_pc = ?, vehicule_pv_date = ?,
                  montant = ?, num_pv = ?, frais = ?, nb_pts = ?,
                  paye_employeur = ?, paye_employeur_date = ?,
                  prel_salarie = ?, prel_salarie_date = ?,
                  comment = ?,
                  modif_op = ?, modif_date = NOW(), modif_elem = 'modif'
            WHERE id_vehicule_pv = ?""",
        (
            _int(payload.get("id_vehicule_pc")),
            payload.get("vehicule_pv_date") or None,
            _float(payload.get("montant")),
            _str(payload.get("num_pv")),
            _float(payload.get("frais")) or 15.0,
            _int(payload.get("nb_pts")),
            paye_employeur,
            paye_date,
            prel_salarie,
            prel_date,
            _str(payload.get("comment")),
            int(op_id),
            id_pv,
        ),
    )
    return {"ok": True, "id_vehicule_pv": str(id_pv)}


def delete_pv(id_vehicule_pv: int, op_id: int) -> dict:
    """Btn Poubelle : soft delete."""
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_vehicule_amende
              SET modif_op = ?, modif_date = NOW(), modif_elem = 'suppr'
            WHERE id_vehicule_pv = ?""",
        (int(op_id), int(id_vehicule_pv)),
    )
    return {"ok": True}
