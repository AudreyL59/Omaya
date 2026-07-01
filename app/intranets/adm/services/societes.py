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


def _new_id() -> int:
    """ID entier 8 octets = timestamp yyyyMMddHHmmssSSS."""
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


def duplicate_societe(id_societe_auto: int, op_id: int) -> int:
    """Duplique la societe : nouvel id_ste selon type_orga :
      - Interne (id_type_orga=1) : id_ste = 300 + nb societes internes
        (equivalent 'ReqListeSTE_Filliale' WinDev)
      - Distrib : id_ste = timestamp (idEntierDateHeureSys)
    Retourne le nouvel id_societe_auto."""
    db = get_pg_connection("rh")
    src = db.query_one(
        "SELECT * FROM rh.pgt_societe WHERE id_societe_auto = ? LIMIT 1",
        (int(id_societe_auto),),
    )
    if not src:
        raise ValueError("Société introuvable")

    id_type_orga = int(src.get("id_type_orga") or 0)
    if id_type_orga == TYPE_ORGA_INTERNE:
        cnt = db.query_one(
            """SELECT COUNT(*) AS n FROM rh.pgt_societe
                WHERE id_type_orga = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
            (TYPE_ORGA_INTERNE,),
        )
        new_id_ste = 300 + int((cnt or {}).get("n") or 0)
    else:
        new_id_ste = _new_id()

    # Nouvel id_societe_auto
    auto = db.query_one(
        "SELECT COALESCE(MAX(id_societe_auto), 0) + 1 AS n FROM rh.pgt_societe"
    )
    new_auto = int((auto or {}).get("n") or 1)

    # INSERT via colonnes dynamiques (copie tout sauf PK/id_ste/composite/modif)
    excluded = {"id_societe_auto", "id_ste", "id_ste_id_type_orga",
                "modif_date", "modif_op", "modif_elem"}
    cols_src = [k for k in src.keys() if k not in excluded]
    cols_dst = ["id_societe_auto", "id_ste", *cols_src,
                "id_ste_id_type_orga", "modif_date", "modif_op", "modif_elem"]
    vals = [new_auto, new_id_ste, *[src[k] for k in cols_src],
             f"{new_id_ste}{id_type_orga}", datetime.now(), int(op_id), "new"]
    ph = ", ".join(["?"] * len(vals))
    db.query(
        f"INSERT INTO rh.pgt_societe ({', '.join(cols_dst)}) VALUES ({ph})",
        tuple(vals),
    )
    return new_auto


def delete_societe(id_societe_auto: int, op_id: int) -> bool:
    """Soft-delete (modif_elem='suppr')."""
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_societe
              SET modif_elem='suppr', modif_date=NOW(), modif_op=?
            WHERE id_societe_auto=?""",
        (int(op_id), int(id_societe_auto)),
    )
    return True


def archive_societe(id_societe_auto: int, op_id: int) -> bool:
    """Archive : is_actif=FALSE."""
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_societe
              SET is_actif=FALSE, modif_elem='modif',
                  modif_date=NOW(), modif_op=?
            WHERE id_societe_auto=?""",
        (int(op_id), int(id_societe_auto)),
    )
    return True


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
