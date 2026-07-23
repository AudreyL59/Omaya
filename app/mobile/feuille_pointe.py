"""Endpoints mobile FeuillePointe (WebRest_Omayapp/FeuillePointe/*).

Portage iso-URL des 6 WS FeuillePointe (feuille de pointage FDV) :
  - Ajout            : cree une nouvelle feuille pour un vendeur+date+commune
  - Feuille/Suppr    : soft delete d'une feuille
  - Liste            : contenu complet des feuilles d'un vendeur pour une date
  - Pointage/Liste   : types de pointages actifs (avec icone base64)
  - Porte/Suppr      : soft delete d'une porte
  - Rue/Suppr        : soft delete d'une rue

La feuille inclut rues et portes imbriquees (recursive JOIN).
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends

from app.core.database.pg import get_pg_connection
from app.mobile.agcial import _new_id_wd, _parse_jour, _to_int
from app.mobile.deps import mobile_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mobile-feuille-pointe"],
                    dependencies=[Depends(mobile_auth)])


def _bytea_to_b64(v) -> str:
    if not v:
        return ""
    if isinstance(v, memoryview):
        v = v.tobytes()
    if isinstance(v, str):
        return v
    try:
        return base64.b64encode(v).decode("ascii")
    except Exception:
        return ""


def _iso_dt(v) -> str:
    if not v:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    return str(v)


# ---------------------------------------------------------------------------
#  FeuillePointe/Ajout
# ---------------------------------------------------------------------------

@router.post("/FeuillePointe/Ajout")
def feuille_ajout(payload: dict = Body(...),
                   id_vend: int = Depends(mobile_auth)):
    """Portage FeuillePointe_Ajoute.

    Payload ST_FeuillePointe : { ID (=id_communes_france), Date }
    Retour : { nIdDemande: id_feuille_pointe }
    """
    id_commune = _to_int(payload.get("ID") or payload.get("IDCommunesFrance"))
    jour = _parse_jour(payload.get("Date"))
    if not id_commune or not jour:
        return {"nIdDemande": "0"}

    id_new = _new_id_wd()
    now = datetime.now()
    db = get_pg_connection("divers")
    try:
        db.query(
            """INSERT INTO divers.pgt_feuille_pointe
                 (id_feuille_pointe, id_communes_france, id_salarie,
                  date, date_crea, modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'new')""",
            (id_new, id_commune, int(id_vend), jour, now, now, int(id_vend)),
        )
        return {"nIdDemande": str(id_new)}
    except Exception as e:
        logger.exception("feuille_ajout")
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ---------------------------------------------------------------------------
#  FeuillePointe/Liste
# ---------------------------------------------------------------------------

@router.post("/FeuillePointe/Liste")
def feuille_liste(payload: dict = Body(...),
                   id_auth: int = Depends(mobile_auth)):
    """Portage FeuillePointe_Liste + FeuillePointe_Contenu.

    Payload : { IdSa, DateF }
    Retour : [ST_FeuillePointe] avec MesRues[] et MesPortes[] imbriques.
    """
    id_sa = _to_int(payload.get("IdSa") or payload.get("IDSalarie") or id_auth)
    jour = _parse_jour(payload.get("DateF") or payload.get("dateF")
                        or payload.get("Date"))
    if not id_sa or not jour:
        return []

    db = get_pg_connection("divers")
    dbrh = get_pg_connection("rh")

    # 1. Feuilles du jour
    try:
        feuilles = db.query(
            """SELECT id_feuille_pointe, id_communes_france, date_crea
                 FROM divers.pgt_feuille_pointe
                WHERE id_salarie = ?
                  AND date::date = ?::date
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')""",
            (int(id_sa), jour.isoformat()),
        ) or []
    except Exception:
        logger.exception("feuille_liste feuilles id=%s j=%s", id_sa, jour)
        return []

    if not feuilles:
        return []

    # Prefetch pointages
    pointages_map: dict[int, dict] = {}
    try:
        pts = db.query(
            """SELECT id_pointage, type_pointage, icone
                 FROM divers.pgt_feuille_pointe_pointage""",
        ) or []
        pointages_map = {int(p.get("id_pointage") or 0): p for p in pts}
    except Exception:
        logger.exception("feuille_liste pointages")

    result = []
    for f in feuilles:
        id_feuille = int(f.get("id_feuille_pointe") or 0)
        id_commune = int(f.get("id_communes_france") or 0)

        # Ville / CP
        nom_ville = cp = ""
        if id_commune:
            try:
                v = db.query_one(
                    """SELECT nom_ville, code_postal
                         FROM divers.pgt_communes_france
                        WHERE id_communes_france = ? LIMIT 1""",
                    (id_commune,),
                )
                if v:
                    nom_ville = (v.get("nom_ville") or "").strip()
                    cp = (v.get("code_postal") or "").strip()
            except Exception:
                logger.exception("feuille_liste commune %s", id_commune)

        # Rues
        try:
            rues = db.query(
                """SELECT id_feuille_pointe_rue, nom_rue
                     FROM divers.pgt_feuille_pointe_rue
                    WHERE id_feuille_pointe = ?
                      AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                    ORDER BY date_crea ASC""",
                (id_feuille,),
            ) or []
        except Exception:
            logger.exception("feuille_liste rues f=%s", id_feuille)
            rues = []

        rues_list = []
        for r in rues:
            id_rue = int(r.get("id_feuille_pointe_rue") or 0)
            # Portes
            try:
                portes = db.query(
                    """SELECT id_feuille_pointe_porte, num_porte, cplt_porte,
                              datecrea, info_cplt, pointage
                         FROM divers.pgt_feuille_pointe_porte
                        WHERE id_feuille_pointe_rue = ?
                          AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                        ORDER BY datecrea ASC""",
                    (id_rue,),
                ) or []
            except Exception:
                logger.exception("feuille_liste portes r=%s", id_rue)
                portes = []
            portes_list = []
            for p in portes:
                pointage_id = int(p.get("pointage") or 0)
                pt = pointages_map.get(pointage_id)
                pointage_obj = {"ID": 0, "LibPointage": "", "IconePointage": ""}
                if pt:
                    pointage_obj = {
                        "ID": int(pt.get("id_pointage") or 0),
                        "LibPointage": (pt.get("type_pointage") or "").strip(),
                        "IconePointage": _bytea_to_b64(pt.get("icone")),
                    }
                portes_list.append({
                    "ID": str(int(p.get("id_feuille_pointe_porte") or 0)),
                    "NumPorte": p.get("num_porte") or "",
                    "CpltPorte": p.get("cplt_porte") or "",
                    "DateCrea": _iso_dt(p.get("datecrea")),
                    "InfoCplt": p.get("info_cplt") or "",
                    "Pointage": pointage_obj,
                })
            rues_list.append({
                "ID": str(id_rue),
                "NomRue": r.get("nom_rue") or "",
                "MesPortes": portes_list,
            })

        result.append({
            "ID": str(id_feuille),
            "DateCrea": _iso_dt(f.get("date_crea")),
            "NomVille": nom_ville,
            "CPVille": cp,
            "MesRues": rues_list,
        })

    return result


# ---------------------------------------------------------------------------
#  FeuillePointe/Pointage/Liste
# ---------------------------------------------------------------------------

@router.post("/FeuillePointe/Pointage/Liste")
def pointage_liste(_payload: Any = Body(default=None)):
    """Portage FeuillePointe_ListePointage. Types de pointages actifs."""
    db = get_pg_connection("divers")
    try:
        rows = db.query(
            """SELECT id_pointage, type_pointage, icone
                 FROM divers.pgt_feuille_pointe_pointage
                WHERE COALESCE(is_actif, FALSE) = TRUE
                ORDER BY id_pointage ASC""",
        ) or []
    except Exception:
        logger.exception("pointage_liste")
        return []
    return [
        {"ID": int(r.get("id_pointage") or 0),
         "LibPointage": (r.get("type_pointage") or "").strip(),
         "IconePointage": _bytea_to_b64(r.get("icone"))}
        for r in rows
    ]


# ---------------------------------------------------------------------------
#  FeuillePointe/Feuille/Suppr
# ---------------------------------------------------------------------------

@router.post("/FeuillePointe/Feuille/Suppr")
def feuille_suppr(payload: dict = Body(...),
                    id_vend: int = Depends(mobile_auth)):
    """Portage FeuillePointe_Suppr. Payload : { ID }"""
    id_feuille = _to_int(payload.get("ID") or payload.get("IDFeuillePointe"))
    if not id_feuille:
        return {"nIdDemande": "0"}
    db = get_pg_connection("divers")
    now = datetime.now()
    try:
        db.query(
            """UPDATE divers.pgt_feuille_pointe
                  SET modif_elem = 'suppr', modif_date = ?, modif_op = ?
                WHERE id_feuille_pointe = ?""",
            (now, int(id_vend), id_feuille),
        )
        return {"nIdDemande": str(id_feuille)}
    except Exception as e:
        logger.exception("feuille_suppr id=%s", id_feuille)
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ---------------------------------------------------------------------------
#  FeuillePointe/Rue/Suppr
# ---------------------------------------------------------------------------

@router.post("/FeuillePointe/Rue/Suppr")
def rue_suppr(payload: dict = Body(...),
              id_vend: int = Depends(mobile_auth)):
    """Portage FeuillePointe_RueSuppr. Payload : { ID }"""
    id_rue = _to_int(payload.get("ID") or payload.get("IDFeuillePointeRue"))
    if not id_rue:
        return {"nIdDemande": "0"}
    db = get_pg_connection("divers")
    now = datetime.now()
    try:
        db.query(
            """UPDATE divers.pgt_feuille_pointe_rue
                  SET modif_elem = 'suppr', modif_date = ?, modif_op = ?
                WHERE id_feuille_pointe_rue = ?""",
            (now, int(id_vend), id_rue),
        )
        return {"nIdDemande": str(id_rue)}
    except Exception as e:
        logger.exception("rue_suppr id=%s", id_rue)
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ---------------------------------------------------------------------------
#  FeuillePointe/Porte/Suppr
# ---------------------------------------------------------------------------

@router.post("/FeuillePointe/Porte/Suppr")
def porte_suppr(payload: dict = Body(...),
                id_vend: int = Depends(mobile_auth)):
    """Portage FeuillePointe_PorteSuppr. Payload : { ID }"""
    id_porte = _to_int(payload.get("ID") or payload.get("IDFeuillePointePorte"))
    if not id_porte:
        return {"nIdDemande": "0"}
    db = get_pg_connection("divers")
    now = datetime.now()
    try:
        db.query(
            """UPDATE divers.pgt_feuille_pointe_porte
                  SET modif_elem = 'suppr', modif_date = ?, modif_op = ?
                WHERE id_feuille_pointe_porte = ?""",
            (now, int(id_vend), id_porte),
        )
        return {"nIdDemande": str(id_porte)}
    except Exception as e:
        logger.exception("porte_suppr id=%s", id_porte)
        return {"nIdDemande": "0", "sInfoData": str(e)}
