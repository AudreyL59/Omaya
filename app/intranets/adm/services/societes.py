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


# Colonnes bytea de pgt_societe qui acceptent une image (cf boutons
# Logo/Guimmick/Cachet Cial/Paraphe/Signature WinDev)
IMAGE_COLS: set[str] = {
    "logo", "guimmick", "cachet_cial",
    "gerant_paraphe", "gerant_signature",
}


def _detect_mime(raw: bytes) -> str:
    """Detecte le MIME depuis la signature du fichier."""
    if raw.startswith(b"\x89PNG\r\n\x1a\n"): return "image/png"
    if raw.startswith(b"\xff\xd8\xff"):       return "image/jpeg"
    if raw.startswith(b"GIF87a") or raw.startswith(b"GIF89a"): return "image/gif"
    if raw.startswith(b"RIFF") and len(raw) > 12 and raw[8:12] == b"WEBP":
        return "image/webp"
    if raw.startswith(b"<svg") or raw.startswith(b"<?xml"): return "image/svg+xml"
    return "application/octet-stream"


def get_societe_image(id_societe_auto: int, champ: str) -> tuple[bytes, str] | None:
    """Retourne (bytes, mime) ou None si absent / champ invalide."""
    if champ not in IMAGE_COLS: return None
    db = get_pg_connection("rh")
    r = db.query_one(
        f"SELECT {champ} AS img FROM rh.pgt_societe WHERE id_societe_auto = ? LIMIT 1",
        (int(id_societe_auto),),
    )
    if not r or not r.get("img"): return None
    raw = r["img"]
    if isinstance(raw, memoryview): raw = bytes(raw)
    return raw, _detect_mime(raw)


def update_societe_image(
    id_societe_auto: int, champ: str, raw: bytes, op_id: int,
) -> bool:
    """Update une des 5 colonnes bytea. Cf boutons Logo/Guimmick/etc.
    WinDev : societe.<champ> = image + modif_elem='modif'."""
    if champ not in IMAGE_COLS:
        raise ValueError(f"Champ image invalide : {champ}")
    db = get_pg_connection("rh")
    db.query(
        f"""UPDATE rh.pgt_societe
              SET {champ}=?, modif_date=NOW(), modif_op=?, modif_elem='modif'
            WHERE id_societe_auto=?""",
        (raw, int(op_id), int(id_societe_auto)),
    )
    return True


class FormeJuri(BaseModel):
    id_societe_form_juri: int
    lib_form_juri: str = ""


class SocieteDetail(BaseModel):
    id_societe_auto: str = "0"
    id_ste: str = "0"
    id_type_orga: int = 1
    is_actif: bool = True
    raison_sociale: str = ""
    rs_interne: str = ""
    forme_juri: str = ""
    date_creation: str = ""
    siren: str = ""
    siret: str = ""
    num_orias: str = ""
    rcs: str = ""
    code_ape: str = ""
    capital: float = 0.0
    num_tva: str = ""
    id_gerant: int = 0
    gerant_nom: str = ""
    gerant_type: str = ""
    adresse1: str = ""
    adresse2: str = ""
    cp: str = ""
    ville: str = ""
    tel: str = ""
    mail: str = ""
    url: str = ""
    iban: str = ""
    bic: str = ""
    idorganigramme: int = 0
    orga_lib: str = ""                # libelle de l'organigramme
    gerant_display: str = ""          # nom + prenom du salarie gerant
    # Flags de presence des images (les blobs sont recuperes via
    # GET /societes/{id}/image/{champ}) :
    has_logo: bool = False
    has_guimmick: bool = False
    has_cachet_cial: bool = False
    has_gerant_paraphe: bool = False
    has_gerant_signature: bool = False


class SocietePayload(BaseModel):
    id_type_orga: int = 1
    is_actif: bool = True
    raison_sociale: str = ""
    rs_interne: str = ""
    forme_juri: str = ""
    date_creation: str | None = None
    siren: str = ""
    siret: str = ""
    num_orias: str = ""
    rcs: str = ""
    code_ape: str = ""
    capital: float = 0.0
    num_tva: str = ""
    id_gerant: int = 0
    gerant_nom: str = ""
    gerant_type: str = ""
    adresse1: str = ""
    adresse2: str = ""
    cp: str = ""
    ville: str = ""
    tel: str = ""
    mail: str = ""
    url: str = ""
    iban: str = ""
    bic: str = ""
    idorganigramme: int = 0


def list_formes_juri() -> list[FormeJuri]:
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_societe_form_juri, lib_form_juri
             FROM rh.pgt_societe_formjuri
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            ORDER BY lib_form_juri""",
    ) or []
    return [FormeJuri(
        id_societe_form_juri=int(r["id_societe_form_juri"]),
        lib_form_juri=r.get("lib_form_juri") or "",
    ) for r in rows]


def get_societe(id_societe_auto: int) -> SocieteDetail | None:
    db = get_pg_connection("rh")
    r = db.query_one(
        """SELECT id_societe_auto, id_ste, id_type_orga, is_actif,
                  raison_sociale, rs_interne, forme_juri, date_creation,
                  siren, siret, num_orias, rcs, code_ape, capital, num_tva,
                  id_gerant, gerant_nom, gerant_type,
                  adresse1, adresse2, cp, ville, tel, mail, url,
                  iban, bic, idorganigramme,
                  (logo IS NOT NULL AND octet_length(logo) > 0) AS has_logo,
                  (guimmick IS NOT NULL AND octet_length(guimmick) > 0) AS has_guimmick,
                  (cachet_cial IS NOT NULL AND octet_length(cachet_cial) > 0) AS has_cachet_cial,
                  (gerant_paraphe IS NOT NULL AND octet_length(gerant_paraphe) > 0) AS has_gerant_paraphe,
                  (gerant_signature IS NOT NULL AND octet_length(gerant_signature) > 0) AS has_gerant_signature
             FROM rh.pgt_societe
            WHERE id_societe_auto = ? LIMIT 1""",
        (int(id_societe_auto),),
    )
    if not r:
        return None

    # Resolution libelle organigramme + nom du gerant
    orga_lib = ""
    if r.get("idorganigramme"):
        orow = db.query_one(
            "SELECT lib_orga FROM rh.pgt_organigramme WHERE idorganigramme = ? LIMIT 1",
            (int(r["idorganigramme"]),),
        )
        orga_lib = (orow or {}).get("lib_orga") or ""
    gerant_display = ""
    id_g = int(r.get("id_gerant") or 0)
    if id_g:
        srow = db.query_one(
            "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
            (id_g,),
        )
        if srow:
            nom = (srow.get("nom") or "").upper()
            prenom = (srow.get("prenom") or "").lower()
            prenom = prenom[:1].upper() + prenom[1:] if prenom else ""
            gerant_display = f"{nom} {prenom}".strip()

    return SocieteDetail(
        id_societe_auto=str(r["id_societe_auto"]),
        id_ste=str(r.get("id_ste") or 0),
        id_type_orga=int(r.get("id_type_orga") or 1),
        is_actif=bool(r.get("is_actif")),
        raison_sociale=r.get("raison_sociale") or "",
        rs_interne=r.get("rs_interne") or "",
        forme_juri=str(r.get("forme_juri") or ""),
        date_creation=_date_str(r.get("date_creation")),
        siren=r.get("siren") or "",
        siret=r.get("siret") or "",
        num_orias=r.get("num_orias") or "",
        rcs=r.get("rcs") or "",
        code_ape=r.get("code_ape") or "",
        capital=float(r.get("capital") or 0),
        num_tva=r.get("num_tva") or "",
        id_gerant=int(r.get("id_gerant") or 0),
        gerant_nom=r.get("gerant_nom") or "",
        gerant_type=r.get("gerant_type") or "",
        adresse1=r.get("adresse1") or "",
        adresse2=r.get("adresse2") or "",
        cp=r.get("cp") or "",
        ville=r.get("ville") or "",
        tel=r.get("tel") or "",
        mail=r.get("mail") or "",
        url=r.get("url") or "",
        iban=r.get("iban") or "",
        bic=r.get("bic") or "",
        idorganigramme=int(r.get("idorganigramme") or 0),
        orga_lib=orga_lib,
        gerant_display=gerant_display,
        has_logo=bool(r.get("has_logo")),
        has_guimmick=bool(r.get("has_guimmick")),
        has_cachet_cial=bool(r.get("has_cachet_cial")),
        has_gerant_paraphe=bool(r.get("has_gerant_paraphe")),
        has_gerant_signature=bool(r.get("has_gerant_signature")),
    )


def create_societe(p: SocietePayload, op_id: int) -> int:
    """Cree une societe. IdSte selon type_orga :
      - Interne (1) : 300 + count des internes actives (WinDev)
      - Distrib (3) : timestamp"""
    db = get_pg_connection("rh")
    if int(p.id_type_orga) == TYPE_ORGA_INTERNE:
        cnt = db.query_one(
            """SELECT COUNT(*) AS n FROM rh.pgt_societe
                WHERE id_type_orga = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
            (TYPE_ORGA_INTERNE,),
        )
        id_ste = 300 + int((cnt or {}).get("n") or 0)
    else:
        id_ste = _new_id()

    auto = db.query_one(
        "SELECT COALESCE(MAX(id_societe_auto), 0) + 1 AS n FROM rh.pgt_societe"
    )
    new_auto = int((auto or {}).get("n") or 1)
    cle_composite = f"{id_ste}{int(p.id_type_orga)}"

    db.query(
        """INSERT INTO rh.pgt_societe
              (id_societe_auto, id_ste, id_type_orga, is_actif,
               raison_sociale, rs_interne, forme_juri, date_creation,
               siren, siret, num_orias, rcs, code_ape, capital, num_tva,
               id_gerant, gerant_nom, gerant_type,
               adresse1, adresse2, cp, ville, tel, mail, url,
               iban, bic, idorganigramme,
               id_ste_id_type_orga,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                   ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (new_auto, id_ste, int(p.id_type_orga), bool(p.is_actif),
         p.raison_sociale, p.rs_interne, p.forme_juri or "",
         p.date_creation if p.date_creation else None,
         p.siren, p.siret, p.num_orias, p.rcs, p.code_ape,
         float(p.capital or 0), p.num_tva,
         int(p.id_gerant or 0), p.gerant_nom, p.gerant_type,
         p.adresse1, p.adresse2, p.cp, p.ville, p.tel, p.mail, p.url,
         p.iban, p.bic, int(p.idorganigramme or 0),
         cle_composite, int(op_id)),
    )
    return new_auto


def update_societe(id_societe_auto: int, p: SocietePayload, op_id: int) -> bool:
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_societe
              SET id_type_orga=?, is_actif=?, raison_sociale=?, rs_interne=?,
                  forme_juri=?, date_creation=?,
                  siren=?, siret=?, num_orias=?, rcs=?, code_ape=?,
                  capital=?, num_tva=?,
                  id_gerant=?, gerant_nom=?, gerant_type=?,
                  adresse1=?, adresse2=?, cp=?, ville=?, tel=?, mail=?, url=?,
                  iban=?, bic=?, idorganigramme=?,
                  modif_date=NOW(), modif_op=?, modif_elem='modif'
            WHERE id_societe_auto=?""",
        (int(p.id_type_orga), bool(p.is_actif),
         p.raison_sociale, p.rs_interne, p.forme_juri or "",
         p.date_creation if p.date_creation else None,
         p.siren, p.siret, p.num_orias, p.rcs, p.code_ape,
         float(p.capital or 0), p.num_tva,
         int(p.id_gerant or 0), p.gerant_nom, p.gerant_type,
         p.adresse1, p.adresse2, p.cp, p.ville, p.tel, p.mail, p.url,
         p.iban, p.bic, int(p.idorganigramme or 0),
         int(op_id), int(id_societe_auto)),
    )
    return True


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
