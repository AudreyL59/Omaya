"""Service Fen_LieuRDV + Fen_LieuRDV_AjoutModif (shared : ADM + Vendeur).

Gestion CRUD des lieux de RDV pour les entretiens de recrutement.
Inclut la geolocalisation via API gouv.fr.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection
from app.shared.notifications.mail import envoi_mail
from app.shared.recrutement.services.recherche_cv import _int, _str


def _new_id() -> int:
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S")) * 1000 + n.microsecond // 1000


def _next_auto(db, schema: str, table: str, auto_col: str) -> int:
    r = db.query(f"SELECT COALESCE(MAX({auto_col}),0)+1 AS n FROM {schema}.{table}")
    return _int(r[0]["n"]) if r else 1


# ---------------------------------------------------------------------------
# Schemas inline
# ---------------------------------------------------------------------------


class LieuRDV(BaseModel):
    id_cv_lieu_rdv: str = ""
    lib_lieu: str = ""
    adresse1: str = ""
    adresse2: str = ""
    id_communes_france: str = ""
    code_postal: str = ""
    nom_ville: str = ""
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    is_actif: bool = True
    is_in_annuaire: bool = False


class LieuRdvPayload(BaseModel):
    id_cv_lieu_rdv: str = "0"        # 0 = create, sinon update
    lib_lieu: str = ""
    adresse1: str = ""
    adresse2: str = ""
    id_communes_france: str = ""
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    is_actif: bool = True


class GeocodePayload(BaseModel):
    adresse: str = ""
    code_postal: str = ""
    nom_ville: str = ""


class GeocodeResponse(BaseModel):
    found: bool = False
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    code_postal_corrige: str = ""


# ---------------------------------------------------------------------------
# Liste / get
# ---------------------------------------------------------------------------


def list_lieux(is_actif: Optional[bool] = None) -> list[LieuRDV]:
    """Liste des lieux avec resolveur ville + flag is_in_annuaire."""
    db = get_pg_connection("recrutement")
    where = ["(l.modif_elem IS NULL OR l.modif_elem NOT LIKE '%suppr%')"]
    params: list = []
    if is_actif is not None:
        where.append("l.is_actif = ?")
        params.append(bool(is_actif))
    sql = f"""
        SELECT l.id_cv_lieu_rdv, l.lib_lieu, l.adresse1, l.adresse2,
               l.id_communes_france, l.latitude_deg, l.longitude_deg,
               l.is_actif,
               c.code_postal, c.nom_ville,
               EXISTS (SELECT 1 FROM recrutement.pgt_annuaire a
                        WHERE a.id_cv_lieu_rdv = l.id_cv_lieu_rdv
                          AND (a.modif_elem IS NULL OR a.modif_elem NOT LIKE '%suppr%')
               ) AS is_in_annuaire
          FROM recrutement.pgt_cv_lieu_rdv l
          LEFT JOIN divers.pgt_communes_france c
                 ON c.id_communes_france = l.id_communes_france
         WHERE {" AND ".join(where)}
      ORDER BY l.lib_lieu ASC
    """
    rows = db.query(sql, tuple(params)) or []
    return [LieuRDV(
        id_cv_lieu_rdv=str(_int(r["id_cv_lieu_rdv"])),
        lib_lieu=_str(r["lib_lieu"]),
        adresse1=_str(r["adresse1"]),
        adresse2=_str(r["adresse2"]),
        id_communes_france=str(_int(r.get("id_communes_france"))) if _int(r.get("id_communes_france")) else "",
        code_postal=_str(r["code_postal"]),
        nom_ville=_str(r["nom_ville"]),
        latitude_deg=r["latitude_deg"],
        longitude_deg=r["longitude_deg"],
        is_actif=bool(r["is_actif"]),
        is_in_annuaire=bool(r["is_in_annuaire"]),
    ) for r in rows]


def get_lieu(id_lieu: int) -> Optional[LieuRDV]:
    db = get_pg_connection("recrutement")
    r = db.query_one(
        """SELECT l.id_cv_lieu_rdv, l.lib_lieu, l.adresse1, l.adresse2,
                  l.id_communes_france, l.latitude_deg, l.longitude_deg,
                  l.is_actif,
                  c.code_postal, c.nom_ville
             FROM recrutement.pgt_cv_lieu_rdv l
             LEFT JOIN divers.pgt_communes_france c
                    ON c.id_communes_france = l.id_communes_france
            WHERE l.id_cv_lieu_rdv = ?""",
        (int(id_lieu),),
    )
    if not r:
        return None
    return LieuRDV(
        id_cv_lieu_rdv=str(_int(r["id_cv_lieu_rdv"])),
        lib_lieu=_str(r["lib_lieu"]),
        adresse1=_str(r["adresse1"]),
        adresse2=_str(r["adresse2"]),
        id_communes_france=str(_int(r.get("id_communes_france"))) if _int(r.get("id_communes_france")) else "",
        code_postal=_str(r["code_postal"]),
        nom_ville=_str(r["nom_ville"]),
        latitude_deg=r["latitude_deg"],
        longitude_deg=r["longitude_deg"],
        is_actif=bool(r["is_actif"]),
    )


# ---------------------------------------------------------------------------
# Save / delete / duplicate
# ---------------------------------------------------------------------------


def save_lieu(p: LieuRdvPayload, op_id: int) -> dict:
    """INSERT si id=0, UPDATE sinon. Si INSERT : envoi mail d'alerte."""
    db = get_pg_connection("recrutement")
    id_v = _int(p.id_cv_lieu_rdv)
    fields = (
        p.lib_lieu.strip(),
        p.adresse1.strip(),
        p.adresse2.strip(),
        _int(p.id_communes_france),
        p.latitude_deg,
        p.longitude_deg,
        bool(p.is_actif),
    )

    if id_v == 0:
        # CREATE
        id_v = _new_id()
        auto = _next_auto(db, "recrutement", "pgt_cv_lieu_rdv", "id_cv_lieu_rdv_auto")
        db.query(
            """INSERT INTO recrutement.pgt_cv_lieu_rdv
                 (id_cv_lieu_rdv_auto, id_cv_lieu_rdv,
                  lib_lieu, adresse1, adresse2, id_communes_france,
                  latitude_deg, longitude_deg, is_actif,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
            (auto, id_v, *fields, int(op_id)),
        )
        # Mail d'alerte (best-effort, ne bloque pas)
        try:
            _envoi_mail_nouveau_lieu(id_v, p)
        except Exception:
            pass
    else:
        # UPDATE
        db.query(
            """UPDATE recrutement.pgt_cv_lieu_rdv
                  SET lib_lieu = ?, adresse1 = ?, adresse2 = ?,
                      id_communes_france = ?,
                      latitude_deg = ?, longitude_deg = ?, is_actif = ?,
                      modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
                WHERE id_cv_lieu_rdv = ?""",
            (*fields, int(op_id), id_v),
        )
    return {"ok": True, "id_cv_lieu_rdv": str(id_v)}


def delete_lieu(id_lieu: int, op_id: int) -> dict:
    """Soft-delete (modif_elem = 'suppr')."""
    db = get_pg_connection("recrutement")
    db.query(
        """UPDATE recrutement.pgt_cv_lieu_rdv
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_cv_lieu_rdv = ?""",
        (int(op_id), int(id_lieu)),
    )
    return {"ok": True}


def duplicate_lieu(id_lieu: int, op_id: int) -> dict:
    """Copie un lieu existant avec un nouvel id."""
    src = get_lieu(id_lieu)
    if not src:
        return {"ok": False, "error": "lieu_inconnu"}
    payload = LieuRdvPayload(
        id_cv_lieu_rdv="0",
        lib_lieu=src.lib_lieu + " (copie)",
        adresse1=src.adresse1,
        adresse2=src.adresse2,
        id_communes_france=src.id_communes_france,
        latitude_deg=src.latitude_deg,
        longitude_deg=src.longitude_deg,
        is_actif=src.is_actif,
    )
    return save_lieu(payload, op_id)


# ---------------------------------------------------------------------------
# Geocoding API gouv.fr
# ---------------------------------------------------------------------------


_API_GOUV = "https://api-adresse.data.gouv.fr/search/"


def _api_gouv_call(query_url: str) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            query_url, headers={"User-Agent": "OmayaERP/1.0"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def geocode_adresse(p: GeocodePayload) -> GeocodeResponse:
    """Geocode une adresse via API gouv.fr (cascade de fallbacks comme WinDev)."""
    adr = (p.adresse or p.nom_ville).strip()
    cp = p.code_postal.strip()
    ville = p.nom_ville.strip()

    # Encode URL
    adr_q = urllib.parse.quote(adr)
    ville_q = urllib.parse.quote(ville)

    # 1) q=adresse + postcode + city
    url = f"{_API_GOUV}?q={adr_q}&postcode={cp}&city={ville_q}"
    data = _api_gouv_call(url)
    if data and data.get("features"):
        f0 = data["features"][0]
        coords = f0.get("geometry", {}).get("coordinates") or []
        if len(coords) >= 2:
            return GeocodeResponse(
                found=True, longitude_deg=coords[0], latitude_deg=coords[1],
            )

    # 2) q=adresse city (sans postcode)
    url = f"{_API_GOUV}?q={adr_q}%20{ville_q}"
    data = _api_gouv_call(url)
    if data and data.get("features"):
        f0 = data["features"][0]
        coords = f0.get("geometry", {}).get("coordinates") or []
        if len(coords) >= 2:
            cp_corr = (f0.get("properties") or {}).get("postcode", "")
            return GeocodeResponse(
                found=True, longitude_deg=coords[0], latitude_deg=coords[1],
                code_postal_corrige=cp_corr,
            )

    # 3) fallback ville seule
    url = f"{_API_GOUV}?q={ville_q}"
    data = _api_gouv_call(url)
    if data and data.get("features"):
        f0 = data["features"][0]
        coords = f0.get("geometry", {}).get("coordinates") or []
        if len(coords) >= 2:
            return GeocodeResponse(
                found=True, longitude_deg=coords[0], latitude_deg=coords[1],
            )

    return GeocodeResponse(found=False)


# ---------------------------------------------------------------------------
# Mail d'alerte au nouveau lieu
# ---------------------------------------------------------------------------


def _envoi_mail_nouveau_lieu(id_lieu: int, p: LieuRdvPayload) -> None:
    cp_ville = ""
    if p.id_communes_france and _int(p.id_communes_france):
        db = get_pg_connection("divers")
        com = db.query_one(
            "SELECT code_postal, nom_ville FROM divers.pgt_communes_france "
            "WHERE id_communes_france = ?",
            (_int(p.id_communes_france),),
        )
        if com:
            cp_ville = f"{_str(com['code_postal'])} {_str(com['nom_ville'])}"
    maps_url = ""
    if p.latitude_deg and p.longitude_deg:
        maps_url = (
            f"https://www.google.com/maps/?q={p.latitude_deg},{p.longitude_deg}"
        )
    html = (
        f"<h3>Nouveau lieu de RDV</h3>"
        f"<ul>"
        f"<li><strong>ID</strong> : {id_lieu}</li>"
        f"<li><strong>Intitulé</strong> : {p.lib_lieu}</li>"
        f"<li><strong>Adresse</strong> : {p.adresse1}</li>"
        f"<li><strong>Ville</strong> : {cp_ville}</li>"
        + (f"<li><strong>Maps</strong> : <a href='{maps_url}'>{maps_url}</a></li>"
           if maps_url else "")
        + f"</ul>"
    )
    envoi_mail(
        sujet="Ajout nouveau lieu de RDV",
        html=html,
        destinataires=["a.loudieux@exosphere.fr"],
    )
