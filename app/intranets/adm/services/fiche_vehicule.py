"""
Service Fen_FicheVehicule (ADM Ulease).

5 plans :
1. Info Vehicule    : marque/modele/immat/cheveaux/km/societe/etat + docs
2. Conducteurs      : liste des conducteurs successifs + attribution
3. Carnet entretien : Revision / Controle technique / Pneus / Releve km
4. PV / Amendes
5. Accidents

V1.1 (ce commit) : Plan 1 + boutons communs (delete, header info).
Les autres plans suivront commit par commit selon le code WinDev.
"""

from __future__ import annotations

import base64
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


def _iso_date(v: Any) -> str:
    if v is None or v == "":
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _img_b64(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, memoryview):
        v = bytes(v)
    if not isinstance(v, (bytes, bytearray)):
        return ""
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
        mime = "image/png"
    return f"data:{mime};base64,{base64.b64encode(bytes(v)).decode('ascii')}"


def get_vehicule(id_vehicule: int) -> dict | None:
    """Charge toutes les infos du vehicule pour le header + plan 1."""
    db_ul = get_pg_connection("ulease")
    db_rh = get_pg_connection("rh")

    v = db_ul.query_one(
        """SELECT vf.id_vehicule, vf.id_vehicule_marque, vf.modele, vf.immat,
                  vf.forfait_km, vf.date_deb, vf.date_fin, vf.carte_grise,
                  vf.info_vehicule, vf.k_mdepart, vf.km_actuel,
                  vf.date_releve, vf.id_vehicule_etat, vf.chevaux_fiscaux,
                  vf.km_mensuel, vf.id_ste_proprio, vf.lien_carte_grise,
                  vf.achat_loc, vf.date_mise_circulation, vf.id_ste_reseau,
                  vf.id_vehicule_type_capacite,
                  vm.nom AS marque_nom, vm.logo AS marque_logo,
                  ve.lib_etat, ve.logo AS etat_logo,
                  vtc.lib_type, vtc.nb_place
             FROM ulease.pgt_vehicule_fiche vf
        LEFT JOIN ulease.pgt_vehicule_marque vm
               ON vm.id_vehicule_marque = vf.id_vehicule_marque
        LEFT JOIN ulease.pgt_vehicule_etat ve
               ON ve.id_vehicule_etat = vf.id_vehicule_etat
        LEFT JOIN ulease.pgt_vehicule_typecapacite vtc
               ON vtc.id_vehicule_type_capacite = vf.id_vehicule_type_capacite
            WHERE vf.id_vehicule = ? LIMIT 1""",
        (int(id_vehicule),),
    )
    if not v:
        return None

    # Societes proprio + reseau (cross-schema)
    ste_proprio = ste_reseau = None
    if _int(v.get("id_ste_proprio")):
        ste_proprio = db_rh.query_one(
            """SELECT id_ste, raison_sociale, rs_interne
                 FROM rh.pgt_societe WHERE id_ste = ? LIMIT 1""",
            (_int(v.get("id_ste_proprio")),),
        )
    if _int(v.get("id_ste_reseau")):
        ste_reseau = db_rh.query_one(
            """SELECT id_ste, raison_sociale, rs_interne
                 FROM rh.pgt_societe WHERE id_ste = ? LIMIT 1""",
            (_int(v.get("id_ste_reseau")),),
        )

    return {
        "id_vehicule": str(_int(v.get("id_vehicule"))),
        "immat": _str(v.get("immat")),
        "modele": _str(v.get("modele")),
        "id_vehicule_marque": str(_int(v.get("id_vehicule_marque"))),
        "marque_nom": _str(v.get("marque_nom")),
        "marque_logo": _img_b64(v.get("marque_logo")),
        "id_vehicule_etat": _int(v.get("id_vehicule_etat")),
        "lib_etat": _str(v.get("lib_etat")),
        "etat_logo": _img_b64(v.get("etat_logo")),
        "id_vehicule_type_capacite": str(_int(v.get("id_vehicule_type_capacite"))),
        "lib_type": _str(v.get("lib_type")),
        "nb_place": _int(v.get("nb_place")),
        "chevaux_fiscaux": _int(v.get("chevaux_fiscaux")),
        "date_mise_circulation": _iso_date(v.get("date_mise_circulation")),
        "date_deb": _iso_date(v.get("date_deb")),
        "date_fin": _iso_date(v.get("date_fin")),
        "k_mdepart": _int(v.get("k_mdepart")),
        "km_actuel": _int(v.get("km_actuel")),
        "km_mensuel": _int(v.get("km_mensuel")),
        "forfait_km": _int(v.get("forfait_km")),
        "date_releve": _iso_date(v.get("date_releve")),
        "id_ste_proprio": str(_int(v.get("id_ste_proprio"))),
        "ste_proprio_lib": _str(
            (ste_proprio or {}).get("rs_interne")
            or (ste_proprio or {}).get("raison_sociale"),
        ),
        "id_ste_reseau": str(_int(v.get("id_ste_reseau"))),
        "ste_reseau_lib": _str(
            (ste_reseau or {}).get("rs_interne")
            or (ste_reseau or {}).get("raison_sociale"),
        ),
        "carte_grise": bool(v.get("carte_grise")),
        "lien_carte_grise": _str(v.get("lien_carte_grise")),
        "achat_loc": _str(v.get("achat_loc")),
        "info_vehicule": _str(v.get("info_vehicule")),
    }


def list_marques() -> list[dict]:
    """Combo Marque."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT id_vehicule_marque, nom FROM ulease.pgt_vehicule_marque
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY nom""",
    ) or []
    return [
        {"id_vehicule_marque": str(_int(r.get("id_vehicule_marque"))),
         "nom": _str(r.get("nom"))}
        for r in rows
    ]


def list_etats() -> list[dict]:
    """Combo Etat."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT id_vehicule_etat, lib_etat FROM ulease.pgt_vehicule_etat
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY lib_etat""",
    ) or []
    return [
        {"id_vehicule_etat": _int(r.get("id_vehicule_etat")),
         "lib_etat": _str(r.get("lib_etat"))}
        for r in rows
    ]


def list_types_capacite() -> list[dict]:
    """Combo Type/Capacite (Lib_Type + nbPlace)."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT id_vehicule_type_capacite, lib_type, nb_place
             FROM ulease.pgt_vehicule_typecapacite
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY lib_type, nb_place""",
    ) or []
    return [
        {
            "id_vehicule_type_capacite": str(_int(r.get("id_vehicule_type_capacite"))),
            "lib_type": _str(r.get("lib_type")),
            "nb_place": _int(r.get("nb_place")),
        }
        for r in rows
    ]


def list_societes() -> list[dict]:
    """Combo Societe (proprio + reseau)."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_ste, raison_sociale, rs_interne FROM rh.pgt_societe
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY raison_sociale""",
    ) or []
    return [
        {
            "id_ste": str(_int(r.get("id_ste"))),
            "lib": _str(r.get("rs_interne") or r.get("raison_sociale")),
        }
        for r in rows
    ]


def get_lookups() -> dict:
    """Tous les lookups pour Fen_FicheVehicule en 1 appel."""
    return {
        "marques": list_marques(),
        "etats": list_etats(),
        "types_capacite": list_types_capacite(),
        "societes": list_societes(),
        # Cf. WinDev ListeAjoute(TypePossession,...)
        "types_possession": [
            {"value": "Achat", "label": "Achat"},
            {"value": "Location", "label": "Location"},
            {"value": "Location CD", "label": "Location courte durée"},
            {"value": "Crédit bail", "label": "Crédit bail"},
        ],
    }


def update_vehicule(id_vehicule: int, payload: dict, op_id: int) -> dict:
    """Btn Enregistrer Plan 1 : UPDATE vehicule_fiche."""
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_vehicule_fiche
              SET id_vehicule_marque = ?,
                  modele = ?,
                  immat = ?,
                  chevaux_fiscaux = ?,
                  date_mise_circulation = ?,
                  id_vehicule_type_capacite = ?,
                  date_deb = ?,
                  date_fin = ?,
                  id_ste_proprio = ?,
                  id_ste_reseau = ?,
                  achat_loc = ?,
                  id_vehicule_etat = ?,
                  forfait_km = ?,
                  k_mdepart = ?,
                  km_actuel = ?,
                  km_mensuel = ?,
                  date_releve = ?,
                  info_vehicule = ?,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_vehicule = ?""",
        (
            _int(payload.get("id_vehicule_marque")),
            _str(payload.get("modele")),
            _str(payload.get("immat")),
            _int(payload.get("chevaux_fiscaux")),
            payload.get("date_mise_circulation") or None,
            _int(payload.get("id_vehicule_type_capacite")),
            payload.get("date_deb") or None,
            payload.get("date_fin") or None,
            _int(payload.get("id_ste_proprio")),
            _int(payload.get("id_ste_reseau")),
            _str(payload.get("achat_loc")),
            _int(payload.get("id_vehicule_etat")),
            _int(payload.get("forfait_km")),
            _int(payload.get("k_mdepart")),
            _int(payload.get("km_actuel")),
            _int(payload.get("km_mensuel")),
            payload.get("date_releve") or None,
            _str(payload.get("info_vehicule")),
            int(op_id),
            int(id_vehicule),
        ),
    )
    return {"ok": True}


def delete_vehicule(id_vehicule: int, op_id: int) -> dict:
    """Btn Supprimer la fiche : soft delete."""
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_vehicule_fiche
              SET modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'suppr'
            WHERE id_vehicule = ?""",
        (int(op_id), int(id_vehicule)),
    )
    return {"ok": True}
