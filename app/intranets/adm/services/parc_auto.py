"""
Service Fen_TdbUlease (Ulease -> Suivi du Parc Auto).

Liste des vehicules actifs (IDvehiculeEtat NOT BETWEEN 4 AND 5) avec
alertes Controle Technique (4 ans) et Revision annuelle (1 an), ainsi
que carte grise manquante.

Cf. WinDev MaFenetre / AfficherTDB.
"""

from __future__ import annotations

import base64
from datetime import date, datetime, timedelta
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


def _date(v: Any) -> date | None:
    if isinstance(v, date):
        return v
    if not v:
        return None
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return date(int(s[:4]), int(s[5:7]), int(s[8:10]))
        except Exception:
            return None
    return None


def _date_fr(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else ""


def _img_b64(v: Any) -> str:
    """Convertit bytea -> data:image/png;base64,... pour le frontend."""
    if v is None:
        return ""
    if isinstance(v, memoryview):
        v = bytes(v)
    if not isinstance(v, (bytes, bytearray)):
        return ""
    # Detection rapide du type
    sig = bytes(v[:8])
    if sig.startswith(b"\x89PNG"):
        mime = "image/png"
    elif sig.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif sig[:6] in (b"GIF87a", b"GIF89a"):
        mime = "image/gif"
    elif sig.startswith(b"BM"):
        mime = "image/bmp"
    else:
        # WebP, autres : on essaye image/png par defaut
        mime = "image/png"
    return f"data:{mime};base64,{base64.b64encode(bytes(v)).decode('ascii')}"


def _alerte_dates(
    derniere_realisation: date | None,
    date_mise_circ: date | None,
    annees: int,
    label: str,
) -> str:
    """Calcule l'alerte CT/Revision selon WinDev."""
    today = date.today()
    if derniere_realisation:
        prochain = date(
            derniere_realisation.year + annees,
            derniere_realisation.month,
            derniere_realisation.day,
        )
    elif date_mise_circ:
        prochain = date(
            date_mise_circ.year + annees,
            date_mise_circ.month,
            date_mise_circ.day,
        )
    else:
        return f"Date de mise en circulation non renseignée"
    if prochain < today:
        return f"ATTENTION date de {label} dépassée ({_date_fr(prochain)})"
    delta = (prochain - today).days
    if delta < 90:
        return f"{label.capitalize()} à faire avant le {_date_fr(prochain)}"
    return ""


def list_vehicules_actifs() -> list[dict]:
    """Tableau de bord Ulease : liste des vehicules en circulation avec
    alertes. Tri raison_sociale ASC, immat ASC."""
    db_ul = get_pg_connection("ulease")
    db_rh = get_pg_connection("rh")

    # 1. Vehicules + etat + marque + type capacite (meme schema ulease).
    # INNER JOIN strict (cf. WinDev) : un vehicule sans marque, etat ou
    # type capacite est exclu. La societe (proprio) est en LEFT pour
    # garder les vehicules sans proprio defini.
    vehs = db_ul.query(
        """SELECT vf.id_vehicule, vf.modele, vf.immat, vf.carte_grise,
                  vf.date_mise_circulation, vf.id_vehicule_etat,
                  vf.id_ste_proprio, vf.id_vehicule_marque,
                  vf.id_vehicule_type_capacite,
                  ve.lib_etat, ve.logo AS etat_logo,
                  vm.nom AS marque_nom, vm.logo AS marque_logo,
                  vtc.lib_type
             FROM ulease.pgt_vehicule_fiche vf
       INNER JOIN ulease.pgt_vehicule_etat ve
               ON ve.id_vehicule_etat = vf.id_vehicule_etat
       INNER JOIN ulease.pgt_vehicule_marque vm
               ON vm.id_vehicule_marque = vf.id_vehicule_marque
       INNER JOIN ulease.pgt_vehicule_typecapacite vtc
               ON vtc.id_vehicule_type_capacite = vf.id_vehicule_type_capacite
            WHERE (vf.modif_elem IS NULL OR vf.modif_elem NOT LIKE '%suppr%')
              AND vf.id_vehicule_etat NOT BETWEEN 4 AND 5
         ORDER BY vf.immat ASC""",
    ) or []
    if not vehs:
        return []

    ids = [_int(v.get("id_vehicule")) for v in vehs if _int(v.get("id_vehicule"))]

    # 2. Societes (cross-schema rh) - on charge tout en 1 query
    stes_ids = sorted({_int(v.get("id_ste_proprio")) for v in vehs if _int(v.get("id_ste_proprio"))})
    ste_by_id: dict[int, dict] = {}
    if stes_ids:
        placeholders = ",".join(["?"] * len(stes_ids))
        rows = db_rh.query(
            f"""SELECT id_ste, raison_sociale, rs_interne, guimmick
                  FROM rh.pgt_societe WHERE id_ste IN ({placeholders})""",
            tuple(stes_ids),
        ) or []
        ste_by_id = {_int(r.get("id_ste")): r for r in rows}

    # 3. Dernier entretien type 1 (revision) et type 2 (CT) par vehicule
    last_by_veh_type: dict[tuple[int, int], date] = {}
    if ids:
        placeholders = ",".join(["?"] * len(ids))
        ents = db_ul.query(
            f"""SELECT id_vehicule, type_entretien, MAX(realise_le) AS last_date
                  FROM ulease.pgt_vehicule_entretien
                 WHERE id_vehicule IN ({placeholders})
                   AND type_entretien IN (1, 2)
                   AND realise_le IS NOT NULL
              GROUP BY id_vehicule, type_entretien""",
            tuple(ids),
        ) or []
        for e in ents:
            iv = _int(e.get("id_vehicule"))
            tp = _int(e.get("type_entretien"))
            d = _date(e.get("last_date"))
            if d:
                last_by_veh_type[(iv, tp)] = d

    out = []
    for v in vehs:
        id_v = _int(v.get("id_vehicule"))
        id_ste = _int(v.get("id_ste_proprio"))
        ste = ste_by_id.get(id_ste, {})
        dmc = _date(v.get("date_mise_circulation"))

        alertes = []
        if not v.get("carte_grise"):
            alertes.append("Carte Grise Manquante")

        # CT (4 ans)
        ct = _alerte_dates(
            last_by_veh_type.get((id_v, 2)), dmc, 4, "contrôle technique"
        )
        if ct:
            alertes.append(ct)
        # Revision (1 an)
        rev = _alerte_dates(
            last_by_veh_type.get((id_v, 1)), dmc, 1, "révision"
        )
        if rev:
            alertes.append(rev)

        type_lib = _str(v.get("lib_type"))
        modele_full = _str(v.get("modele"))
        if type_lib:
            modele_full = f"{modele_full} - {type_lib}"

        out.append({
            "id_vehicule": str(id_v),
            "immat": _str(v.get("immat")),
            "modele": modele_full,
            "marque_logo": _img_b64(v.get("marque_logo")),
            "marque_nom": _str(v.get("marque_nom")),
            "etat_logo": _img_b64(v.get("etat_logo")),
            "lib_etat": _str(v.get("lib_etat")),
            "id_vehicule_etat": _int(v.get("id_vehicule_etat")),
            "raison_sociale": _str(ste.get("rs_interne") or ste.get("raison_sociale")),
            "ste_logo": _img_b64(ste.get("guimmick")),
            "alertes": alertes,
            "has_alerte": bool(alertes),
        })
    # Tri final : raison_sociale ASC, immat ASC (comme WinDev)
    out.sort(key=lambda x: (x.get("raison_sociale", ""), x.get("immat", "")))
    return out
