"""
Service Fen_RechUlease (ADM Ulease -> Recherche Vehicule / Conducteur).

2 recherches independantes :
  - Vehicules : filtres Modele / Immat / NbCV / Etat / Marque (tous LIKE
    sauf etat/marque qui sont des id exacts).
  - Conducteurs : filtres Nom / Prenom / NumPermis / Societe / Tel / Mob.

Tri par defaut : immat ASC pour vehicules, nom ASC pour conducteurs.
"""

from __future__ import annotations

import base64
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
    else:
        mime = "image/png"
    return f"data:{mime};base64,{base64.b64encode(bytes(v)).decode('ascii')}"


# ---------------------------------------------------------------------------
# Combos
# ---------------------------------------------------------------------------


def list_lookups() -> dict:
    """Combos : etats vehicule + marques + societes (FDV Interne)."""
    db_ul = get_pg_connection("ulease")
    etats = db_ul.query(
        """SELECT id_vehicule_etat, lib_etat FROM ulease.pgt_vehicule_etat
            WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
         ORDER BY id_vehicule_etat""",
    ) or []
    marques = db_ul.query(
        """SELECT id_vehicule_marque, nom FROM ulease.pgt_vehicule_marque
            WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
         ORDER BY nom ASC""",
    ) or []
    db_rh = get_pg_connection("rh")
    societes = db_rh.query(
        """SELECT id_ste, raison_sociale, rs_interne FROM rh.pgt_societe
            WHERE COALESCE(is_actif, FALSE) = TRUE
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY raison_sociale""",
    ) or []
    return {
        "etats": [{
            "id_vehicule_etat": _int(r.get("id_vehicule_etat")),
            "lib": _str(r.get("lib_etat")),
        } for r in etats],
        "marques": [{
            "id_vehicule_marque": str(_int(r.get("id_vehicule_marque"))),
            "nom": _str(r.get("nom")),
        } for r in marques],
        "societes": [{
            "id_ste": str(_int(r.get("id_ste"))),
            "raison_sociale": _str(r.get("raison_sociale")),
            "rs_interne": _str(r.get("rs_interne")),
        } for r in societes],
    }


# ---------------------------------------------------------------------------
# Recherche Vehicule
# ---------------------------------------------------------------------------


def search_vehicules(
    modele: str = "", chevaux: str = "", immat: str = "",
    id_etat: int = 0, id_marque: int = 0,
) -> list[dict]:
    """ReqChercheVehicule : LIKE sur modele/immat/chevaux + filtre exact
    sur etat et marque (si 0 -> pas de filtre)."""
    db = get_pg_connection("ulease")
    where = ["(vf.modif_elem IS NULL OR vf.modif_elem NOT LIKE '%suppr%')"]
    params: list = []
    if modele:
        where.append("LOWER(vf.modele) LIKE ?")
        params.append(f"{modele.lower()}%")
    if chevaux:
        where.append("CAST(vf.chevaux_fiscaux AS TEXT) LIKE ?")
        params.append(f"{chevaux}%")
    if immat:
        where.append("UPPER(vf.immat) LIKE ?")
        params.append(f"{immat.upper()}%")
    if id_etat:
        where.append("vf.id_vehicule_etat = ?")
        params.append(int(id_etat))
    if id_marque:
        where.append("vf.id_vehicule_marque = ?")
        params.append(int(id_marque))

    sql = f"""SELECT vf.id_vehicule, vf.modele, vf.immat,
                     vf.chevaux_fiscaux, vf.forfait_km,
                     vf.k_mdepart, vf.km_actuel,
                     vf.id_ste_proprio, vf.id_ste_reseau,
                     vm.nom AS marque_nom, vm.logo AS marque_logo,
                     ve.lib_etat
                FROM ulease.pgt_vehicule_fiche vf
          INNER JOIN ulease.pgt_vehicule_marque vm
                  ON vm.id_vehicule_marque = vf.id_vehicule_marque
          INNER JOIN ulease.pgt_vehicule_etat ve
                  ON ve.id_vehicule_etat = vf.id_vehicule_etat
               WHERE {' AND '.join(where)}
            ORDER BY vf.immat ASC
               LIMIT 500"""
    rows = db.query(sql, tuple(params)) or []
    return [{
        "id_vehicule": str(_int(r.get("id_vehicule"))),
        "modele": _str(r.get("modele")),
        "immat": _str(r.get("immat")),
        "chevaux_fiscaux": _int(r.get("chevaux_fiscaux")),
        "forfait_km": _int(r.get("forfait_km")),
        "k_mdepart": _int(r.get("k_mdepart")),
        "km_actuel": _int(r.get("km_actuel")),
        "marque_nom": _str(r.get("marque_nom")),
        "marque_logo": _img_b64(r.get("marque_logo")),
        "lib_etat": _str(r.get("lib_etat")),
    } for r in rows]


# ---------------------------------------------------------------------------
# Recherche Conducteur
# ---------------------------------------------------------------------------


def search_conducteurs(
    nom: str = "", prenom: str = "", num_permis: str = "",
    id_ste: int = 0, tel: str = "", mobile: str = "",
) -> list[dict]:
    """ReqChercheConducteur : LIKE sur nom/prenom/numpermis/tel/mobile +
    filtre exact id_ste (si 0 -> pas de filtre).

    JOIN : conducteur + salarie (rh, cross-schema) + salarie_coordonnees
    + salarie_embauche. Cross-schema OK car meme DB."""
    db = get_pg_connection("ulease")
    where = [
        "(c.modif_elem IS NULL OR c.modif_elem NOT LIKE '%suppr%')",
        "(s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')",
    ]
    params: list = []
    if nom:
        where.append("UPPER(s.nom) LIKE ?")
        params.append(f"{nom.upper()}%")
    if prenom:
        where.append("LOWER(s.prenom) LIKE ?")
        params.append(f"{prenom.lower()}%")
    if num_permis:
        where.append("c.num_permis LIKE ?")
        params.append(f"{num_permis}%")
    if id_ste:
        where.append("e.id_ste = ?")
        params.append(int(id_ste))
    if tel:
        where.append("co.tel_fixe LIKE ?")
        params.append(f"{tel}%")
    if mobile:
        where.append("co.tel_mob LIKE ?")
        params.append(f"{mobile}%")

    sql = f"""SELECT c.id_conducteur, c.id_salarie, c.num_permis,
                     s.nom, s.nom_marital, s.prenom,
                     co.tel_fixe, co.tel_mob,
                     e.id_ste
                FROM ulease.pgt_conducteur c
          INNER JOIN rh.pgt_salarie s
                  ON s.id_salarie = c.id_salarie
           LEFT JOIN rh.pgt_salarie_coordonnees co
                  ON co.id_salarie = s.id_salarie
           LEFT JOIN rh.pgt_salarie_embauche e
                  ON e.id_salarie = s.id_salarie
                 AND (e.modif_elem IS NULL OR e.modif_elem NOT LIKE '%suppr%')
                 AND (e.en_activite IS NULL OR e.en_activite = TRUE)
               WHERE {' AND '.join(where)}
            ORDER BY s.nom ASC, s.prenom ASC
               LIMIT 500"""
    rows = db.query(sql, tuple(params)) or []
    out = []
    for r in rows:
        prenom_norm = _str(r.get("prenom")).strip()
        if prenom_norm:
            prenom_norm = prenom_norm[:1].upper() + prenom_norm[1:].lower()
        out.append({
            "id_conducteur": str(_int(r.get("id_conducteur"))),
            "id_salarie": str(_int(r.get("id_salarie"))),
            "nom": _str(r.get("nom")),
            "nom_marital": _str(r.get("nom_marital")),
            "prenom": prenom_norm,
            "num_permis": _str(r.get("num_permis")),
            "tel": _str(r.get("tel_fixe")),
            "mobile": _str(r.get("tel_mob")),
            "id_ste": str(_int(r.get("id_ste"))),
        })
    return out
