"""Service Fen_EditionDocCourtage - edition d'un template doc courtage.

Cf Fen_EditionDocRH (equivalent RH) : formulaire de metadonnees +
upload/telechargement du contenu DOCX + 'Tester mise en page' via
publipostage.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection


def _date_str(v: Any) -> str:
    if v is None: return ""
    if isinstance(v, (date, datetime)): return v.strftime("%Y-%m-%d %H:%M:%S")
    return str(v)


def _new_id() -> int:
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


class DocCourtageDetail(BaseModel):
    id_doc_courtage: str = "0"
    titre: str = ""
    info_cpl: str = ""
    id_groupe_operateur: int = 0
    lib_groupe_operateur: str = ""
    id_ste: str = "0"
    rs_interne_ste: str = ""
    doc_actif: bool = True
    prioritaire: bool = False
    datecrea: str = ""
    modif_date: str = ""
    has_contenu: bool = False
    taille_contenu: int = 0


class DocCourtagePayload(BaseModel):
    titre: str = ""
    info_cpl: str = ""
    id_groupe_operateur: int = 0
    id_ste: int = 0
    doc_actif: bool = True
    prioritaire: bool = False


class SocieteInterneItem(BaseModel):
    id_ste: str
    rs_interne: str
    raison_sociale: str = ""


def list_societes_interne() -> list[SocieteInterneItem]:
    """Combo 'Societe' (cf reqDistrib WinDev - reciproquement, ici on
    a besoin des internes id_type_orga=1)."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_ste, rs_interne, raison_sociale
             FROM rh.pgt_societe
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
              AND id_type_orga = 1
              AND is_actif = TRUE
            ORDER BY rs_interne""",
    ) or []
    return [SocieteInterneItem(
        id_ste=str(r["id_ste"]),
        rs_interne=r.get("rs_interne") or "",
        raison_sociale=r.get("raison_sociale") or "",
    ) for r in rows]


def get_doc_courtage(id_doc: int) -> DocCourtageDetail | None:
    db_rh = get_pg_connection("rh")
    db_adv = get_pg_connection("adv")
    r = db_rh.query_one(
        """SELECT id_doc_courtage, titre, info_cpl, id_groupe_operateur,
                  id_ste, doc_actif, prioritaire, datecrea, modif_date,
                  (contenu IS NOT NULL AND octet_length(contenu) > 0)
                    AS has_contenu,
                  COALESCE(octet_length(contenu), 0) AS taille_contenu
             FROM rh.pgt_doc_courtage
            WHERE id_doc_courtage = ? LIMIT 1""",
        (int(id_doc),),
    )
    if not r: return None
    lib_grp = ""
    if r.get("id_groupe_operateur"):
        g = db_adv.query_one(
            "SELECT lib_groupe FROM adv.pgt_groupe_operateur WHERE id_groupe_operateur = ? LIMIT 1",
            (int(r["id_groupe_operateur"]),),
        )
        lib_grp = (g or {}).get("lib_groupe") or ""
    rs_ste = ""
    if r.get("id_ste"):
        s = db_rh.query_one(
            "SELECT rs_interne FROM rh.pgt_societe WHERE id_ste = ? LIMIT 1",
            (int(r["id_ste"]),),
        )
        rs_ste = (s or {}).get("rs_interne") or ""
    return DocCourtageDetail(
        id_doc_courtage=str(r["id_doc_courtage"]),
        titre=r.get("titre") or "",
        info_cpl=r.get("info_cpl") or "",
        id_groupe_operateur=int(r.get("id_groupe_operateur") or 0),
        lib_groupe_operateur=lib_grp,
        id_ste=str(r.get("id_ste") or 0),
        rs_interne_ste=rs_ste,
        doc_actif=bool(r.get("doc_actif")),
        prioritaire=bool(r.get("prioritaire")),
        datecrea=_date_str(r.get("datecrea")),
        modif_date=_date_str(r.get("modif_date")),
        has_contenu=bool(r.get("has_contenu")),
        taille_contenu=int(r.get("taille_contenu") or 0),
    )


def create_doc_courtage(p: DocCourtagePayload, op_id: int) -> int:
    """Cree un doc vide (contenu NULL). Le user pourra uploader le
    DOCX ensuite."""
    db = get_pg_connection("rh")
    id_new = _new_id()
    db.query(
        """INSERT INTO rh.pgt_doc_courtage
              (id_doc_courtage, titre, info_cpl, id_groupe_operateur,
               id_ste, doc_actif, prioritaire, datecrea,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), NOW(), ?, 'new')""",
        (id_new, p.titre or "Nouveau document", p.info_cpl,
         int(p.id_groupe_operateur or 0), int(p.id_ste or 0),
         bool(p.doc_actif), bool(p.prioritaire), int(op_id)),
    )
    return id_new


def update_doc_courtage(id_doc: int, p: DocCourtagePayload, op_id: int) -> bool:
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_doc_courtage
              SET titre=?, info_cpl=?, id_groupe_operateur=?, id_ste=?,
                  doc_actif=?, prioritaire=?,
                  modif_date=NOW(), modif_op=?, modif_elem='modif'
            WHERE id_doc_courtage=?""",
        (p.titre, p.info_cpl, int(p.id_groupe_operateur or 0),
         int(p.id_ste or 0), bool(p.doc_actif), bool(p.prioritaire),
         int(op_id), int(id_doc)),
    )
    return True


def delete_doc_courtage(id_doc: int, op_id: int) -> bool:
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_doc_courtage
              SET modif_elem='suppr', modif_date=NOW(), modif_op=?
            WHERE id_doc_courtage=?""",
        (int(op_id), int(id_doc)),
    )
    return True


def get_contenu(id_doc: int) -> bytes | None:
    db = get_pg_connection("rh")
    r = db.query_one(
        "SELECT contenu FROM rh.pgt_doc_courtage WHERE id_doc_courtage = ? LIMIT 1",
        (int(id_doc),),
    )
    if not r or not r.get("contenu"): return None
    raw = r["contenu"]
    if isinstance(raw, memoryview): raw = bytes(raw)
    return raw


def update_contenu(id_doc: int, raw: bytes, op_id: int) -> bool:
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_doc_courtage
              SET contenu=?, modif_date=NOW(), modif_op=?, modif_elem='modif'
            WHERE id_doc_courtage=?""",
        (raw, int(op_id), int(id_doc)),
    )
    return True


class DocCourtageListItem(BaseModel):
    id_doc_courtage: str
    id_groupe_operateur: int
    lib_groupe_operateur: str = ""
    titre: str = ""
    info_cpl: str = ""
    id_ste: str = "0"
    rs_interne_ste: str = ""
    doc_actif: bool = True
    prioritaire: bool = False
    modif_date: str = ""


def list_docs(archives: bool = False) -> list[DocCourtageListItem]:
    """cf reqTableau Fen_ListeDocCourtage : RIGHT OUTER JOIN sur
    GroupeOperateur (docs sans groupe conserves) + filtre doc_actif."""
    db_rh = get_pg_connection("rh")
    db_adv = get_pg_connection("adv")
    # doc_actif = True (visibles) OU False (archives)
    doc_actif = not archives
    rows = db_rh.query(
        """SELECT d.id_doc_courtage, d.id_groupe_operateur, d.titre,
                  d.info_cpl, d.id_ste, d.doc_actif, d.prioritaire,
                  d.modif_date
             FROM rh.pgt_doc_courtage d
            WHERE (d.modif_elem IS NULL OR d.modif_elem NOT LIKE '%suppr%')
              AND d.doc_actif = ?
            ORDER BY d.id_groupe_operateur, d.prioritaire DESC, d.titre""",
        (bool(doc_actif),),
    ) or []
    # Resolution batch lib_groupe + rs_interne
    id_gops = list({int(r["id_groupe_operateur"]) for r in rows if r.get("id_groupe_operateur")})
    id_stes = list({int(r["id_ste"]) for r in rows if r.get("id_ste")})
    gop_map: dict[int, str] = {}
    if id_gops:
        ids = ",".join(str(i) for i in id_gops)
        g = db_adv.query(
            f"SELECT id_groupe_operateur, lib_groupe FROM adv.pgt_groupe_operateur WHERE id_groupe_operateur IN ({ids})",
        ) or []
        gop_map = {int(x["id_groupe_operateur"]): x.get("lib_groupe") or "" for x in g}
    ste_map: dict[int, str] = {}
    if id_stes:
        ids = ",".join(str(i) for i in id_stes)
        s = db_rh.query(
            f"SELECT id_ste, rs_interne FROM rh.pgt_societe WHERE id_ste IN ({ids})",
        ) or []
        ste_map = {int(x["id_ste"]): x.get("rs_interne") or "" for x in s}
    return [DocCourtageListItem(
        id_doc_courtage=str(r["id_doc_courtage"]),
        id_groupe_operateur=int(r.get("id_groupe_operateur") or 0),
        lib_groupe_operateur=gop_map.get(int(r.get("id_groupe_operateur") or 0), ""),
        titre=r.get("titre") or "",
        info_cpl=r.get("info_cpl") or "",
        id_ste=str(r.get("id_ste") or 0),
        rs_interne_ste=ste_map.get(int(r.get("id_ste") or 0), ""),
        doc_actif=bool(r.get("doc_actif")),
        prioritaire=bool(r.get("prioritaire")),
        modif_date=_date_str(r.get("modif_date")),
    ) for r in rows]


def duplicate_doc(id_doc: int, op_id: int) -> int:
    """Duplique le doc (metadata + contenu bytea)."""
    db = get_pg_connection("rh")
    src = db.query_one(
        "SELECT * FROM rh.pgt_doc_courtage WHERE id_doc_courtage = ? LIMIT 1",
        (int(id_doc),),
    )
    if not src:
        raise ValueError("Document introuvable")
    id_new = _new_id()
    db.query(
        """INSERT INTO rh.pgt_doc_courtage
              (id_doc_courtage, titre, info_cpl, id_groupe_operateur,
               contenu, id_ste, doc_actif, prioritaire, datecrea,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, NOW(), NOW(), ?, 'new')""",
        (id_new,
         (src.get("titre") or "") + " (copie)",
         src.get("info_cpl") or "",
         int(src.get("id_groupe_operateur") or 0),
         src.get("contenu"),
         int(src.get("id_ste") or 0),
         bool(src.get("doc_actif")),
         bool(src.get("prioritaire")),
         int(op_id)),
    )
    return id_new


def archive_doc(id_doc: int, op_id: int) -> bool:
    """Met doc_actif=False (cf btn Archiver WinDev)."""
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_doc_courtage
              SET doc_actif=FALSE, modif_elem='modif',
                  modif_date=NOW(), modif_op=?
            WHERE id_doc_courtage=?""",
        (int(op_id), int(id_doc)),
    )
    return True


class DistribTestItem(BaseModel):
    id_ste: str
    rs_interne: str
    id_gerant: int = 0


def list_distribs_test() -> list[DistribTestItem]:
    """Combo 'Test avec' : liste des distributeurs actifs pour tester
    le publipostage (id_type_orga=3, is_actif=true)."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_ste, rs_interne, id_gerant
             FROM rh.pgt_societe
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
              AND id_type_orga = 3
              AND is_actif = TRUE
            ORDER BY rs_interne""",
    ) or []
    return [DistribTestItem(
        id_ste=str(r["id_ste"]),
        rs_interne=r.get("rs_interne") or "",
        id_gerant=int(r.get("id_gerant") or 0),
    ) for r in rows]
