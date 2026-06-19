"""
Service Fen_FicheVehicule Plan 3 (Carnet d'entretien).

Type entretien :
- 1 : Revision annuelle
- 2 : Controle technique
- 3 : Remplacement pneus
- 4 : Releve kilometrique (table vehicule_releve, pas vehicule_entretien)

Cf. WinDev PageInterneEntretien.init(id, type).
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


def _new_id() -> int:
    """idEntierDateHeureSys (cf. WinDev)."""
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


# ---------------------------------------------------------------------------
# Types 1/2/3 - vehicule_entretien
# ---------------------------------------------------------------------------


def list_entretiens(id_vehicule: int, type_entretien: int) -> list[dict]:
    """Liste les entretiens d'un type donne pour un vehicule."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT id_vehicule_entretien, type_entretien, realise_le,
                  montant_ht, montant_ttc, c_rentretien
             FROM ulease.pgt_vehicule_entretien
            WHERE id_vehicule = ?
              AND type_entretien = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY realise_le DESC""",
        (int(id_vehicule), int(type_entretien)),
    ) or []
    return [
        {
            "id_vehicule_entretien": str(_int(r.get("id_vehicule_entretien"))),
            "type_entretien": _int(r.get("type_entretien")),
            "realise_le": _iso_date(r.get("realise_le")),
            "montant_ht": _float(r.get("montant_ht")),
            "montant_ttc": _float(r.get("montant_ttc")),
            "c_rentretien": _str(r.get("c_rentretien")),
        }
        for r in rows
    ]


def save_entretien(payload: dict, op_id: int) -> dict:
    """Btn Enregistrer : create si id=0 sinon update."""
    db = get_pg_connection("ulease")
    id_ent = _int(payload.get("id_vehicule_entretien"))
    if id_ent == 0:
        new_id = _new_id()
        db.query(
            """INSERT INTO ulease.pgt_vehicule_entretien
                 (id_vehicule_entretien, id_vehicule, type_entretien,
                  realise_le, montant_ht, montant_ttc, c_rentretien,
                  modif_op, modif_date, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, NOW(), 'new')""",
            (
                new_id,
                _int(payload.get("id_vehicule")),
                _int(payload.get("type_entretien")),
                payload.get("realise_le") or None,
                _float(payload.get("montant_ht")),
                _float(payload.get("montant_ttc")),
                _str(payload.get("c_rentretien")),
                int(op_id),
            ),
        )
        return {"ok": True, "id_vehicule_entretien": str(new_id)}
    db.query(
        """UPDATE ulease.pgt_vehicule_entretien
              SET type_entretien = ?, realise_le = ?, montant_ht = ?,
                  montant_ttc = ?, c_rentretien = ?,
                  modif_op = ?, modif_date = NOW(), modif_elem = 'modif'
            WHERE id_vehicule_entretien = ?""",
        (
            _int(payload.get("type_entretien")),
            payload.get("realise_le") or None,
            _float(payload.get("montant_ht")),
            _float(payload.get("montant_ttc")),
            _str(payload.get("c_rentretien")),
            int(op_id),
            id_ent,
        ),
    )
    return {"ok": True, "id_vehicule_entretien": str(id_ent)}


def delete_entretien(id_vehicule_entretien: int, op_id: int) -> dict:
    """Btn Poubelle entretien : soft delete."""
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_vehicule_entretien
              SET modif_op = ?, modif_date = NOW(), modif_elem = 'suppr'
            WHERE id_vehicule_entretien = ?""",
        (int(op_id), int(id_vehicule_entretien)),
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Type 4 - Releves kilometriques (vehicule_releve)
# ---------------------------------------------------------------------------


def list_releves(id_vehicule: int) -> list[dict]:
    """Liste les releves d'un vehicule."""
    db = get_pg_connection("ulease")
    db_rh = get_pg_connection("rh")
    rows = db.query(
        """SELECT vr.id_vehicule_releve, vr.id_vehicule_pc, vr.km,
                  vr.km_parcouru, vr.km_restant, vr.date_releve,
                  vr.alerte, vr.commentaire, vr.op_releve,
                  c.nom_conducteur, c.prenom_conducteur
             FROM ulease.pgt_vehicule_releve vr
        LEFT JOIN ulease.pgt_vehicule_conducteur vc
               ON vc.id_vehicule_pc = vr.id_vehicule_pc
        LEFT JOIN ulease.pgt_conducteur c
               ON c.id_conducteur = vc.id_conducteur
            WHERE vr.id_vehicule = ?
              AND (vr.modif_elem IS NULL OR vr.modif_elem NOT LIKE '%suppr%')
         ORDER BY vr.date_releve DESC""",
        (int(id_vehicule),),
    ) or []
    # Recuperer le prenom de l'op_releve
    op_ids = sorted({_int(r.get("op_releve")) for r in rows if _int(r.get("op_releve"))})
    op_by_id: dict[int, str] = {}
    if op_ids:
        ph = ",".join(["?"] * len(op_ids))
        sals = db_rh.query(
            f"""SELECT id_salarie, nom, prenom FROM rh.pgt_salarie
                 WHERE id_salarie IN ({ph})""",
            tuple(op_ids),
        ) or []
        op_by_id = {
            _int(s.get("id_salarie")):
                f"{_str(s.get('prenom'))} {_str(s.get('nom'))}".strip()
            for s in sals
        }
    out = []
    for r in rows:
        nom = _str(r.get("nom_conducteur"))
        prenom = _str(r.get("prenom_conducteur")).strip().capitalize()
        out.append({
            "id_vehicule_releve": str(_int(r.get("id_vehicule_releve"))),
            "id_vehicule_pc": str(_int(r.get("id_vehicule_pc"))),
            "conducteur": f"{nom} {prenom}".strip(),
            "km": _int(r.get("km")),
            "km_parcouru": _int(r.get("km_parcouru")),
            "km_restant": _int(r.get("km_restant")),
            "date_releve": _iso_date(r.get("date_releve")),
            "alerte": bool(r.get("alerte")),
            "commentaire": _str(r.get("commentaire")),
            "op_lib": op_by_id.get(_int(r.get("op_releve")), ""),
        })
    return out


def list_conducteurs_all(id_vehicule: int) -> list[dict]:
    """Combo conducteur Plan 4 (releve). Tous les conducteurs (meme
    historiques)."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT vc.id_vehicule_pc, vc.perception_date, vc.restitution_date,
                  vc.k_mdepart, vc.temporaire, vc.id_conducteur,
                  c.nom_conducteur, c.prenom_conducteur, c.id_salarie,
                  c.mobile, c.tel
             FROM ulease.pgt_vehicule_conducteur vc
        LEFT JOIN ulease.pgt_conducteur c
               ON c.id_conducteur = vc.id_conducteur
            WHERE vc.id_vehicule = ?
              AND (vc.modif_elem IS NULL OR vc.modif_elem NOT LIKE '%suppr%')
         ORDER BY vc.perception_date DESC""",
        (int(id_vehicule),),
    ) or []
    out = []
    for r in rows:
        nom = _str(r.get("nom_conducteur"))
        deb = _iso_date(r.get("perception_date"))
        fin = _iso_date(r.get("restitution_date"))
        temp = ", Temp" if r.get("temporaire") else ""
        deb_fr = f"{deb[8:10]}/{deb[5:7]}/{deb[0:4]}" if len(deb) >= 10 else ""
        fin_fr = f"{fin[8:10]}/{fin[5:7]}/{fin[0:4]}" if len(fin) >= 10 else ""
        titre = f"{nom}{temp} ( Début : {deb_fr} - Fin : {fin_fr} )"
        out.append({
            "id_vehicule_pc": str(_int(r.get("id_vehicule_pc"))),
            "id_salarie": str(_int(r.get("id_salarie"))),
            "k_mdepart": _int(r.get("k_mdepart")),
            "mobile": _str(r.get("mobile")) or _str(r.get("tel")),
            "titre": titre,
        })
    return out


def save_releve(payload: dict, op_id: int) -> dict:
    """Btn Enregistrer la releve : INSERT vehicule_releve + UPDATE
    vehicule_fiche (km_actuel, date_releve)."""
    db = get_pg_connection("ulease")
    new_id = _new_id()
    id_vehicule = _int(payload.get("id_vehicule"))
    nouvelle_releve = _int(payload.get("km"))
    db.query(
        """INSERT INTO ulease.pgt_vehicule_releve
             (id_vehicule_releve, id_vehicule, date_releve, km,
              km_parcouru, km_restant, op_releve, id_vehicule_pc,
              alerte, commentaire,
              modif_op, modif_date, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), 'new')""",
        (
            new_id,
            id_vehicule,
            payload.get("date_releve") or None,
            nouvelle_releve,
            _int(payload.get("km_parcouru")),
            _int(payload.get("km_restant")),
            int(op_id),
            _int(payload.get("id_vehicule_pc")),
            bool(payload.get("alerte")),
            _str(payload.get("commentaire")),
            int(op_id),
        ),
    )
    # Update vehicule_fiche
    db.query(
        """UPDATE ulease.pgt_vehicule_fiche
              SET date_releve = ?, km_actuel = ?, alerte_rel = ?,
                  modif_op = ?, modif_date = NOW(), modif_elem = 'modif'
            WHERE id_vehicule = ?""",
        (
            payload.get("date_releve") or None,
            nouvelle_releve,
            bool(payload.get("alerte")),
            int(op_id),
            id_vehicule,
        ),
    )
    return {"ok": True, "id_vehicule_releve": str(new_id)}


def delete_releve(id_vehicule_releve: int, op_id: int) -> dict:
    """Btn Poubelle releve : soft delete."""
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_vehicule_releve
              SET modif_op = ?, modif_date = NOW(), modif_elem = 'suppr'
            WHERE id_vehicule_releve = ?""",
        (int(op_id), int(id_vehicule_releve)),
    )
    return {"ok": True}
