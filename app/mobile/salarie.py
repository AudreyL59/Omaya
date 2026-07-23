"""Endpoints mobile Salarie (WebRest_Omayapp/Salarie/*).

Portage iso-URL des 8 WS Salarie mobile WinDev :

  Info :
    - Info/AttUlease         : liste des fiches Ulease d'un vehicule
                                (via FTP OVH ou local)
    - Info/FichesADF         : liste des PDF ADF d'un salarie
                                (via FTP OVH ou local)
    - Info/IdentiteCoord     : ST_INFOSALARIE identite + coordonnees

  NoteFrais :
    - NoteFrais/Type         : types de note de frais actifs
    - NoteFrais/Liste        : notes du salarie pour un mois+annee
    - NoteFrais/Contenu      : detail d'une note + photo base64
    - NoteFrais/Save         : create/update d'une note de frais
    - NoteFrais/Delete       : soft delete
"""

from __future__ import annotations

import base64
import ftplib
import logging
import os
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends

from app.core.config import (
    FTP_GESTION_RH_PATH, FTP_HOST, FTP_PASSWORD, FTP_USER,
)
from app.core.database.pg import get_pg_connection
from app.mobile.agcial import _new_id_wd, _parse_jour, _to_int
from app.mobile.deps import mobile_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mobile-salarie"],
                    dependencies=[Depends(mobile_auth)])


def _iso_dt(v) -> str:
    if not v:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    return str(v)


def _to_num(v) -> float:
    try:
        return float(v) if v not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0


def _last_day_of_month(d: date) -> date:
    """Dernier jour du mois de d."""
    y, m = d.year, d.month
    if m == 12:
        return date(y, 12, 31)
    return date(y + (1 if m == 12 else 0), (m % 12) + 1, 1) - \
           (date(y, m, 1) - date(y, m, 1))  # noqa - simplifie ci-dessous


def _list_ftp_files(remote_dir: str) -> list[str]:
    """Liste les fichiers d'un repertoire FTP. Renvoie [] si erreur.
    Portage FTPListeFichier WinDev.
    """
    if not FTP_HOST or not FTP_USER:
        return []
    try:
        with ftplib.FTP(FTP_HOST, timeout=15) as ftp:
            ftp.login(FTP_USER, FTP_PASSWORD)
            try:
                ftp.cwd(remote_dir)
            except ftplib.error_perm:
                return []
            try:
                return list(ftp.nlst())
            except ftplib.error_perm:
                return []
    except Exception:
        logger.exception("_list_ftp_files dir=%s", remote_dir)
        return []


def _list_local_files(path: str) -> list[str]:
    """Liste les fichiers d'un repertoire local. Fallback pour
    environnement non FTP."""
    try:
        return [f for f in os.listdir(path)
                if os.path.isfile(os.path.join(path, f))]
    except Exception:
        return []


# ===========================================================================
#  Info
# ===========================================================================

@router.post("/Salarie/Info/IdentiteCoord")
def info_identite_coord(payload: dict = Body(...)):
    """Portage InfoSalarié_IdentCoord. Identite + coordonnees d'un salarie.

    Payload : { idSalarié: int } (ou IDSalarie, id).
    """
    id_sal = _to_int(payload.get("idSalarié") or payload.get("idSalarie")
                      or payload.get("IDSalarie") or payload.get("id"))
    empty = {
        "ID": 0, "NOM": "", "NOM_MARITAL": "", "PRENOM": "",
        "DNAISS": "", "LNAISS": "", "DEPNAISS": 0, "NUMSS": "",
        "ADRESSE1": "", "ADRESSE2": "", "Cp": "", "VILLE": "",
        "TEL": "", "GSM": "", "MAIL": "",
        "URGNOM": "", "URGLIEN": "", "URGTEL": "",
        "IBAN": "", "BIC": "",
    }
    if not id_sal:
        return empty

    db = get_pg_connection("rh")
    try:
        row = db.query_one(
            """SELECT s.id_salarie, s.nom, s.nom_marital, s.prenom,
                      s.date_naiss, s.lieu_naiss, s.dep_naiss, s.num_ss,
                      c.adresse1, c.adresse2, c.cp, c.ville,
                      c.tel_fixe, c.tel_mob, c.mail,
                      c.urg_nom, c.urg_lien, c.urg_tel,
                      c.iban, c.bic
                 FROM rh.pgt_salarie s
                 LEFT JOIN rh.pgt_salarie_coordonnees c
                        ON c.id_salarie = s.id_salarie
                WHERE s.id_salarie = ? LIMIT 1""",
            (id_sal,),
        )
    except Exception:
        logger.exception("info_identite_coord id=%s", id_sal)
        return empty
    if not row:
        return empty
    return {
        "ID": int(row.get("id_salarie") or 0),
        "NOM": (row.get("nom") or "").strip(),
        "NOM_MARITAL": (row.get("nom_marital") or "").strip(),
        "PRENOM": (row.get("prenom") or "").strip(),
        "DNAISS": _iso_dt(row.get("date_naiss")),
        "LNAISS": (row.get("lieu_naiss") or "").strip(),
        "DEPNAISS": _to_int(row.get("dep_naiss")),
        "NUMSS": (row.get("num_ss") or "").strip(),
        "ADRESSE1": (row.get("adresse1") or "").strip(),
        "ADRESSE2": (row.get("adresse2") or "").strip(),
        "Cp": (row.get("cp") or "").strip(),
        "VILLE": (row.get("ville") or "").strip(),
        "TEL": (row.get("tel_fixe") or "").strip(),
        "GSM": (row.get("tel_mob") or "").strip(),
        "MAIL": (row.get("mail") or "").strip(),
        "URGNOM": (row.get("urg_nom") or "").strip(),
        "URGLIEN": (row.get("urg_lien") or "").strip(),
        "URGTEL": (row.get("urg_tel") or "").strip(),
        "IBAN": (row.get("iban") or "").strip(),
        "BIC": (row.get("bic") or "").strip(),
    }


@router.post("/Salarie/Info/FichesADF")
def info_fiches_adf(payload: dict = Body(...),
                     id_auth: int = Depends(mobile_auth)):
    """Portage FichesADF. Liste des noms de fichiers PDF ADF d'un
    salarie sur le FTP OVH (ou fallback local).

    Payload : { idCial } (fallback = user auth).
    """
    id_cial = _to_int(payload.get("idCial") or payload.get("IDSalarie")
                       or id_auth)
    if not id_cial:
        return []

    # Chemin FTP WinDev : /OMAYA/gestionRH/{idCial}/ADF/
    ftp_dir = f"{FTP_GESTION_RH_PATH}/{id_cial}/ADF/"
    files = _list_ftp_files(ftp_dir)
    if not files:
        # Fallback local (au cas ou pas de FTP configure)
        local_dir = os.path.join(r"D:\OMAYA\gestionRH",
                                  str(id_cial), "ADF")
        files = _list_local_files(local_dir)
    return files


@router.post("/Salarie/Info/AttUlease")
def info_att_ulease(payload: dict = Body(...)):
    """Portage FichesAttUlease. Liste des fichiers Ulease pour un
    vehicule_Conducteur donne.

    Payload : { idAtt: id_vehicule_pc }
    """
    id_att = _to_int(payload.get("idAtt") or payload.get("IDvehiculePC"))
    if not id_att:
        return []

    db = get_pg_connection("ulease")
    try:
        row = db.query_one(
            """SELECT id_vehicule
                 FROM ulease.pgt_vehicule_conducteur
                WHERE id_vehicule_pc = ? LIMIT 1""",
            (id_att,),
        )
    except Exception:
        logger.exception("info_att_ulease id=%s", id_att)
        return []
    if not row:
        return []

    id_veh = int(row.get("id_vehicule") or 0)
    # Chemin WinDev : /OMAYA/Vehicules/{idvehicule}/{idvehiculePC}/
    ftp_dir = f"/OMAYA/Vehicules/{id_veh}/{id_att}/"
    files = _list_ftp_files(ftp_dir)
    if not files:
        local_dir = os.path.join(r"D:\OMAYA\Vehicules",
                                  str(id_veh), str(id_att))
        files = _list_local_files(local_dir)
    return files


# ===========================================================================
#  NoteFrais
# ===========================================================================

@router.post("/Salarie/NoteFrais/Type")
def note_frais_type(_payload: Any = Body(default=None)):
    """Portage NoteFrais_Type. Types actifs."""
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT id_note_frais_type, lib_type_note_frais
                 FROM rh.pgt_note_frais_type
                WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY lib_type_note_frais ASC""",
        ) or []
    except Exception:
        logger.exception("note_frais_type")
        return []
    return [
        {"IDNoteFraisType": str(int(r.get("id_note_frais_type") or 0)),
         "LibTypeNoteFrais": (r.get("lib_type_note_frais") or "").strip()}
        for r in rows
    ]


@router.post("/Salarie/NoteFrais/Liste")
def note_frais_liste(payload: dict = Body(...)):
    """Portage NoteFrais_Lister. Notes d'un salarie pour un mois+annee.

    Payload : { idSalarie, mois, annee }
    """
    id_sal = _to_int(payload.get("idSalarie") or payload.get("IDSalarie"))
    mois = _to_int(payload.get("mois"))
    annee = _to_int(payload.get("annee"))
    if not id_sal or not mois or not annee:
        return []
    try:
        deb = date(annee, mois, 1)
    except ValueError:
        return []

    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT nf.id_note_frais, nf.id_salarie, nf.id_note_frais_type,
                      nf.date, nf.description, nf.montant_ttc, nf.montant_ht,
                      nf.montant_tva,
                      nft.lib_type_note_frais
                 FROM rh.pgt_note_frais nf
                 LEFT JOIN rh.pgt_note_frais_type nft
                        ON nft.id_note_frais_type = nf.id_note_frais_type
                WHERE (nf.modif_elem IS NULL OR nf.modif_elem NOT LIKE '%suppr%')
                  AND nf.id_salarie = ?
                  AND nf.periode_note::date = ?::date
                ORDER BY nf.date ASC""",
            (id_sal, deb.isoformat()),
        ) or []
    except Exception:
        logger.exception("note_frais_liste id=%s m=%s a=%s", id_sal, mois, annee)
        return []
    return [
        {"IDNoteFrais": str(int(r.get("id_note_frais") or 0)),
         "IDNoteFraisType": str(int(r.get("id_note_frais_type") or 0)),
         "LibTypeNoteFrais": (r.get("lib_type_note_frais") or "").strip(),
         "MontantHT": _to_num(r.get("montant_ht")),
         "MontantTTC": _to_num(r.get("montant_ttc")),
         "MontantTVA": _to_num(r.get("montant_tva")),
         "Date": _iso_dt(r.get("date")),
         "Description": r.get("description") or ""}
        for r in rows
    ]


@router.post("/Salarie/NoteFrais/Contenu")
def note_frais_contenu(payload: dict = Body(...)):
    """Portage NoteFrais_Contenu. Detail d'une note avec photo base64."""
    id_note = _to_int(payload.get("idNote") or payload.get("IDNoteFrais"))
    empty = {
        "IDNoteFrais": "0", "IDNoteFraisType": "0",
        "MontantHT": 0.0, "MontantTTC": 0.0, "MontantTVA": 0.0,
        "Date": "", "Description": "", "PhotoTicket": "",
    }
    if not id_note:
        return empty

    db = get_pg_connection("rh")
    try:
        row = db.query_one(
            """SELECT id_note_frais, id_note_frais_type, date, description,
                      montant_ttc, montant_ht, montant_tva, photo_ticket
                 FROM rh.pgt_note_frais
                WHERE id_note_frais = ? LIMIT 1""",
            (id_note,),
        )
    except Exception:
        logger.exception("note_frais_contenu id=%s", id_note)
        return empty
    if not row:
        return empty

    photo = row.get("photo_ticket")
    photo_b64 = ""
    if photo:
        if isinstance(photo, memoryview):
            photo = photo.tobytes()
        try:
            photo_b64 = base64.b64encode(photo).decode("ascii")
        except Exception:
            photo_b64 = ""

    return {
        "IDNoteFrais": str(int(row.get("id_note_frais") or 0)),
        "IDNoteFraisType": str(int(row.get("id_note_frais_type") or 0)),
        "MontantHT": _to_num(row.get("montant_ht")),
        "MontantTTC": _to_num(row.get("montant_ttc")),
        "MontantTVA": _to_num(row.get("montant_tva")),
        "Date": _iso_dt(row.get("date")),
        "Description": row.get("description") or "",
        "PhotoTicket": photo_b64,
    }


@router.post("/Salarie/NoteFrais/Save")
def note_frais_save(payload: dict = Body(...),
                     id_cial: int = Depends(mobile_auth)):
    """Portage NoteFrais_Enr. Create/update d'une note de frais.

    Payload STNoteFrais : { IDNoteFrais (0=create), idSalarie,
                             IDNoteFraisType, Date, Description,
                             MontantHT/TTC/TVA, PhotoTicket (base64) }
    """
    id_note = _to_int(payload.get("IDNoteFrais"))
    id_sal = _to_int(payload.get("idSalarie") or payload.get("IDSalarie"))
    id_type = _to_int(payload.get("IDNoteFraisType"))
    d = _parse_jour(payload.get("Date"))
    desc = payload.get("Description") or ""
    m_ttc = _to_num(payload.get("MontantTTC"))
    m_ht = _to_num(payload.get("MontantHT"))
    m_tva = _to_num(payload.get("MontantTVA"))
    photo_b64 = payload.get("PhotoTicket") or ""

    if not id_sal or not id_type or not d:
        return {"nIdDemande": "0"}

    photo_bytes = None
    if photo_b64:
        try:
            photo_bytes = base64.b64decode(photo_b64)
        except Exception:
            photo_bytes = None

    import psycopg2
    db = get_pg_connection("rh")
    now = datetime.now()
    periode = date(d.year, d.month, 1)

    if not id_note:
        id_note = _new_id_wd()
        try:
            db.query(
                """INSERT INTO rh.pgt_note_frais
                     (id_note_frais_auto, id_note_frais, id_salarie,
                      id_note_frais_type, periode_note, date, description,
                      montant_ttc, montant_ht, montant_tva, photo_ticket,
                      modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                (id_note, id_note, id_sal, id_type, periode, d, desc,
                 m_ttc, m_ht, m_tva,
                 psycopg2.Binary(photo_bytes) if photo_bytes else None,
                 now, id_cial),
            )
            return {"nIdDemande": str(id_note)}
        except Exception as e:
            logger.exception("note_frais_save insert")
            return {"nIdDemande": "0", "sInfoData": str(e)}
    else:
        try:
            # Reconstruit la SQL selon si on update la photo ou non
            if photo_bytes is not None:
                db.query(
                    """UPDATE rh.pgt_note_frais
                          SET id_salarie = ?, id_note_frais_type = ?,
                              date = ?, description = ?,
                              montant_ttc = ?, montant_ht = ?, montant_tva = ?,
                              photo_ticket = ?, modif_date = ?, modif_op = ?,
                              modif_elem = 'new'
                        WHERE id_note_frais = ?""",
                    (id_sal, id_type, d, desc, m_ttc, m_ht, m_tva,
                     psycopg2.Binary(photo_bytes), now, id_cial, id_note),
                )
            else:
                db.query(
                    """UPDATE rh.pgt_note_frais
                          SET id_salarie = ?, id_note_frais_type = ?,
                              date = ?, description = ?,
                              montant_ttc = ?, montant_ht = ?, montant_tva = ?,
                              modif_date = ?, modif_op = ?, modif_elem = 'new'
                        WHERE id_note_frais = ?""",
                    (id_sal, id_type, d, desc, m_ttc, m_ht, m_tva,
                     now, id_cial, id_note),
                )
            return {"nIdDemande": str(id_note)}
        except Exception as e:
            logger.exception("note_frais_save update id=%s", id_note)
            return {"nIdDemande": "0", "sInfoData": str(e)}


@router.post("/Salarie/NoteFrais/Delete")
def note_frais_delete(payload: dict = Body(...),
                       id_cial: int = Depends(mobile_auth)):
    """Portage NoteFrais_Supprimer. Soft delete."""
    id_note = _to_int(payload.get("IDNoteFrais"))
    if not id_note:
        return {"nIdDemande": "0"}
    db = get_pg_connection("rh")
    now = datetime.now()
    try:
        db.query(
            """UPDATE rh.pgt_note_frais
                  SET modif_elem = 'suppr', modif_date = ?, modif_op = ?
                WHERE id_note_frais = ?""",
            (now, id_cial, id_note),
        )
        return {"nIdDemande": str(id_note)}
    except Exception as e:
        logger.exception("note_frais_delete id=%s", id_note)
        return {"nIdDemande": "0", "sInfoData": str(e)}
