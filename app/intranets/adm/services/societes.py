"""Service Fen_ListeSociete (Sociétés - icône building du header).

Cf code WinDev Fen_ListeSociete :
  - Tableau des societes filtre par IsActif (glissiere 'Afficher les STE
    archivees') et IDTypeOrga (selecteur Interne=1 / Distributeur=3)
  - Colonnes : Societe (RS_Interne), Type Orga, Raison Sociale,
    Raison Sociale Interne, SIRET, Visible (IsActif), ModifDate
  - Boutons : Nouveau, Dupliquer, Supprimer, Modifier, Archiver
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection


TYPE_ORGA_INTERNE = 1
TYPE_ORGA_DISTRIBUTEUR = 3


def _date_str(v: Any) -> str:
    if v is None: return ""
    if isinstance(v, datetime): return v.strftime("%Y-%m-%d %H:%M:%S")
    return str(v)


class SocieteItem(BaseModel):
    id_societe_auto: str
    id_ste: str
    id_type_orga: int
    raison_sociale: str = ""
    rs_interne: str = ""
    siret: str = ""
    is_actif: bool = True
    modif_date: str = ""
    id_gerant: int = 0
    num_orias: str = ""
    date_creation: str = ""


def list_societes(
    id_type_orga: int = TYPE_ORGA_INTERNE,
    archivees: bool = False,
) -> list[SocieteItem]:
    """cf reqSql WinDev :
      IsActif = archivees ? False : True
      IDTypeOrga = 1 (interne) ou 3 (distributeur)
    ORDER BY RS_Interne ASC."""
    db = get_pg_connection("rh")
    is_actif = not archivees
    rows = db.query(
        """SELECT id_societe_auto, id_ste, id_type_orga,
                  raison_sociale, rs_interne, siret,
                  is_actif, modif_date, id_gerant, num_orias, date_creation
             FROM rh.pgt_societe
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
              AND is_actif = ?
              AND id_type_orga = ?
            ORDER BY rs_interne ASC""",
        (bool(is_actif), int(id_type_orga)),
    ) or []
    return [SocieteItem(
        id_societe_auto=str(r["id_societe_auto"]),
        id_ste=str(r["id_ste"]),
        id_type_orga=int(r.get("id_type_orga") or 0),
        raison_sociale=r.get("raison_sociale") or "",
        rs_interne=r.get("rs_interne") or "",
        siret=r.get("siret") or "",
        is_actif=bool(r.get("is_actif")),
        modif_date=_date_str(r.get("modif_date")),
        id_gerant=int(r.get("id_gerant") or 0),
        num_orias=r.get("num_orias") or "",
        date_creation=_date_str(r.get("date_creation")),
    ) for r in rows]
