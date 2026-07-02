"""
Service Fen_FicheVehicule Plan 5 (Accidents).

Table : ulease.pgt_vehicule_accident.
Au save : met aussi a jour vehicule_fiche.id_vehicule_etat selon :
  - repare=True -> 1 (EN CIRCULATION)
  - sinon si reparable=True :
      - si deb_rep <= today -> 3 (EN REPARATION)
      - sinon                -> 2 (ACCIDENTE)
  - sinon -> 4 (EPAVE)
"""

from __future__ import annotations

from datetime import date as _date, datetime
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


def _float(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _iso_date(v: Any) -> str:
    if v is None or v == "" or is_sentinel(v):
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    return s[:10] if len(s) >= 10 and s[4] == "-" else s


def _iso_datetime(v: Any) -> str:
    if v is None or v == "" or is_sentinel(v):
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%dT%H:%M")
    s = str(v)
    return s[:16] if len(s) >= 16 else s


def _new_id() -> int:
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


def list_accidents(id_vehicule: int) -> list[dict]:
    """Liste des accidents du vehicule + nom du conducteur."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT va.id_vehicule_acc, va.id_vehicule_pc, va.vehicule_acc_date,
                  va.resp, va.prix_rep, va.prix_fran, va.reparable,
                  va.deb_rep, va.fin_rep, va.repare, va.desc_,
                  c.nom_conducteur, c.prenom_conducteur
             FROM ulease.pgt_vehicule_accident va
        LEFT JOIN ulease.pgt_vehicule_conducteur vc
               ON vc.id_vehicule_pc = va.id_vehicule_pc
        LEFT JOIN ulease.pgt_conducteur c
               ON c.id_conducteur = vc.id_conducteur
            WHERE va.id_vehicule = ?
              AND (va.modif_elem IS NULL OR va.modif_elem NOT LIKE '%suppr%')
         ORDER BY va.vehicule_acc_date DESC""",
        (int(id_vehicule),),
    ) or []
    out = []
    for r in rows:
        nom = _str(r.get("nom_conducteur"))
        prenom = _str(r.get("prenom_conducteur")).strip().capitalize()
        out.append({
            "id_vehicule_acc": str(_int(r.get("id_vehicule_acc"))),
            "id_vehicule_pc": str(_int(r.get("id_vehicule_pc"))),
            "conducteur": f"{nom} {prenom}".strip(),
            "vehicule_acc_date": _iso_datetime(r.get("vehicule_acc_date")),
            "resp": _int(r.get("resp")),
            "prix_rep": _float(r.get("prix_rep")),
            "prix_fran": _float(r.get("prix_fran")),
            "reparable": bool(r.get("reparable")),
            "deb_rep": _iso_date(r.get("deb_rep")),
            "fin_rep": _iso_date(r.get("fin_rep")),
            "repare": bool(r.get("repare")),
            "desc_": _str(r.get("desc_")),
        })
    return out


def get_accident(id_vehicule_acc: int) -> dict | None:
    db = get_pg_connection("ulease")
    r = db.query_one(
        """SELECT id_vehicule_acc, id_vehicule, id_vehicule_pc,
                  vehicule_acc_date, resp, prix_rep, prix_fran,
                  reparable, deb_rep, fin_rep, repare, desc_
             FROM ulease.pgt_vehicule_accident
            WHERE id_vehicule_acc = ? LIMIT 1""",
        (int(id_vehicule_acc),),
    )
    if not r:
        return None
    return {
        "id_vehicule_acc": str(_int(r.get("id_vehicule_acc"))),
        "id_vehicule": str(_int(r.get("id_vehicule"))),
        "id_vehicule_pc": str(_int(r.get("id_vehicule_pc"))),
        "vehicule_acc_date": _iso_datetime(r.get("vehicule_acc_date")),
        "resp": _int(r.get("resp")),
        "prix_rep": _float(r.get("prix_rep")),
        "prix_fran": _float(r.get("prix_fran")),
        "reparable": bool(r.get("reparable")),
        "deb_rep": _iso_date(r.get("deb_rep")),
        "fin_rep": _iso_date(r.get("fin_rep")),
        "repare": bool(r.get("repare")),
        "desc_": _str(r.get("desc_")),
    }


def _compute_etat(reparable: bool, deb_rep: str, repare: bool) -> int:
    """Calcule l'etat du vehicule selon les valeurs de l'accident."""
    if repare:
        return 1  # EN CIRCULATION
    if reparable:
        try:
            if deb_rep:
                d = _date.fromisoformat(deb_rep)
                if d <= _date.today():
                    return 3  # EN REPARATION
        except Exception:
            pass
        return 2  # ACCIDENTE
    return 4  # EPAVE


def save_accident(payload: dict, op_id: int) -> dict:
    """Btn Enregistrer Accident : create/update + maj vehicule_fiche.etat."""
    db = get_pg_connection("ulease")
    id_acc = _int(payload.get("id_vehicule_acc"))
    id_vehicule = _int(payload.get("id_vehicule"))

    deb = payload.get("deb_rep") or None
    fin = payload.get("fin_rep") or None
    reparable = bool(payload.get("reparable"))
    repare = bool(payload.get("repare"))

    if id_acc == 0:
        new_id = _new_id()
        db.query(
            """INSERT INTO ulease.pgt_vehicule_accident
                 (id_vehicule_acc, id_vehicule, id_vehicule_pc,
                  vehicule_acc_date, resp, prix_rep, prix_fran,
                  reparable, deb_rep, fin_rep, repare, desc_,
                  modif_op, modif_date, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, NOW(), 'new')""",
            (
                new_id, id_vehicule,
                _int(payload.get("id_vehicule_pc")),
                payload.get("vehicule_acc_date") or None,
                _int(payload.get("resp")),
                _float(payload.get("prix_rep")),
                _float(payload.get("prix_fran")),
                reparable, deb, fin, repare,
                _str(payload.get("desc_")),
                int(op_id),
            ),
        )
        id_acc = new_id
    else:
        db.query(
            """UPDATE ulease.pgt_vehicule_accident
                  SET id_vehicule_pc = ?, vehicule_acc_date = ?,
                      resp = ?, prix_rep = ?, prix_fran = ?,
                      reparable = ?, deb_rep = ?, fin_rep = ?,
                      repare = ?, desc_ = ?,
                      modif_op = ?, modif_date = NOW(), modif_elem = 'modif'
                WHERE id_vehicule_acc = ?""",
            (
                _int(payload.get("id_vehicule_pc")),
                payload.get("vehicule_acc_date") or None,
                _int(payload.get("resp")),
                _float(payload.get("prix_rep")),
                _float(payload.get("prix_fran")),
                reparable, deb, fin, repare,
                _str(payload.get("desc_")),
                int(op_id), id_acc,
            ),
        )

    # Maj vehicule_fiche.id_vehicule_etat
    nouvel_etat = _compute_etat(reparable, _str(deb) if deb else "", repare)
    db.query(
        """UPDATE ulease.pgt_vehicule_fiche
              SET id_vehicule_etat = ?, modif_op = ?, modif_date = NOW(),
                  modif_elem = 'modif'
            WHERE id_vehicule = ?""",
        (nouvel_etat, int(op_id), id_vehicule),
    )

    return {
        "ok": True,
        "id_vehicule_acc": str(id_acc),
        "id_vehicule_etat": nouvel_etat,
    }


def delete_accident(id_vehicule_acc: int, op_id: int) -> dict:
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_vehicule_accident
              SET modif_op = ?, modif_date = NOW(), modif_elem = 'suppr'
            WHERE id_vehicule_acc = ?""",
        (int(op_id), int(id_vehicule_acc)),
    )
    return {"ok": True}
