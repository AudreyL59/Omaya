"""
Onglet 'Ulease' de la fiche salarie ADM.

Transposition de FI_SalarieUlease : 4 sous-onglets :
  1. Fichier Conducteur     : listing/upload/delete FTP /ulease/Conducteurs/{idcond}/
  2. Historique Attribution : vehicule_conducteur JOIN vehicule_fiche
  3. Edition documents      : salarie_doc_ulease JOIN doc_ulease_type
  4. Attribution Carte Carb : carteattribution JOIN cartecarburant

Prerequis : une fiche conducteur (ulease.pgt_conducteur) doit exister.
Sinon le frontend propose le bouton 'Creer une fiche conducteur' qui
appelle create_conducteur (copie depuis pgt_salarie).
"""

from __future__ import annotations

import ftplib
import io
import re
from datetime import datetime
from typing import Any

from app.core.config import FTP_HOST, FTP_PASSWORD, FTP_USER
from app.core.database.pg import get_pg_connection
from app.core.utils.sentinel_dates import is_sentinel


_INVALID_NAME_RE = re.compile(r"[<>:\"/\\|?*\x00-\x1f]")


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _iso(v: Any) -> str:
    if v is None or is_sentinel(v):
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _iso_dt(v: Any) -> str:
    if v is None or is_sentinel(v):
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    return str(v)


def _ftp_connect() -> ftplib.FTP | None:
    try:
        ftp = ftplib.FTP(timeout=15)
        ftp.encoding = "latin-1"
        ftp.connect(FTP_HOST, 21)
        ftp.login(FTP_USER, FTP_PASSWORD)
        return ftp
    except Exception:
        return None


def _sanitize_filename(name: str) -> str:
    base = (name or "").replace("/", "_").replace("\\", "_").strip()
    base = _INVALID_NAME_RE.sub("_", base)
    return base[:200] or "sans_nom"


def _ftp_makedirs(ftp: ftplib.FTP, abs_path: str) -> None:
    parts = [p for p in abs_path.split("/") if p]
    cur = "/"
    for p in parts:
        cur = (cur.rstrip("/") + "/" + p)
        try:
            ftp.mkd(cur)
        except ftplib.error_perm:
            pass


# ===========================================================================
# Conducteur (existence + creation + maj permis)
# ===========================================================================


def load_conducteur_info(id_salarie: int) -> dict:
    """Retourne {exists, id_conducteur, num_permis, type_permis, date_obtention}.

    Si exists=False, le frontend affichera le bouton 'Creer une fiche
    conducteur'.
    """
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT id_conducteur, num_permis, type_permis, date_obtention
             FROM ulease.pgt_conducteur
            WHERE id_salarie = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            LIMIT 1""",
        (int(id_salarie),),
    )
    if not rows:
        return {
            "exists": False,
            "id_conducteur": "",
            "num_permis": "",
            "type_permis": "",
            "date_obtention": "",
        }
    r = rows[0]
    return {
        "exists": True,
        "id_conducteur": _str(r.get("id_conducteur")),
        "num_permis": _str(r.get("num_permis")),
        "type_permis": _str(r.get("type_permis")),
        "date_obtention": _iso(r.get("date_obtention")),
    }


def _sexe_to_int(v: Any) -> int:
    """pgt_salarie.sexe est varchar(1) ('H'/'F'/'M'),
    ulease.pgt_conducteur.sexe_conducteur est smallint.
    On suit le mapping WinDev : H/M -> 1, F -> 2, autre -> 0.
    """
    s = (str(v or "") or "").upper().strip()
    if s in ("H", "M"):
        return 1
    if s == "F":
        return 2
    return 0


def create_conducteur(id_salarie: int, op_id: int) -> dict:
    """Cree la fiche conducteur en copiant les infos salarie
    (pgt_salarie + pgt_salarie_coordonnees + dernier rattachement)."""
    db_rh = get_pg_connection("rh")
    rows = db_rh.query(
        """SELECT s.sexe, s.nom, s.nom_marital, s.prenom, s.date_naiss,
                  s.photo, s.nationalite, s.lieu_naiss, s.dep_naiss,
                  c.tel_fixe, c.tel_mob, c.adresse1, c.adresse2,
                  c.cp, c.ville,
                  (SELECT so.id_ste
                     FROM rh.pgt_salarie_organigramme so
                    WHERE so.id_salarie = s.id_salarie
                      AND (so.modif_elem IS NULL OR so.modif_elem NOT LIKE '%suppr%')
                    ORDER BY so.date_debut DESC NULLS LAST
                    LIMIT 1) AS id_ste
             FROM rh.pgt_salarie s
             LEFT JOIN rh.pgt_salarie_coordonnees c
               ON c.id_salarie = s.id_salarie
            WHERE s.id_salarie = ?
            LIMIT 1""",
        (int(id_salarie),),
    )
    if not rows:
        return {"ok": False, "error": "Salarie introuvable"}
    s = rows[0]

    db_u = get_pg_connection("ulease")
    # Cf. WinDev : conducteur.IDconducteur = idSalarie
    id_cond = int(id_salarie)
    db_u.query(
        """INSERT INTO ulease.pgt_conducteur
              (id_conducteur, id_salarie,
               num_permis, type_permis, date_obtention,
               sexe_conducteur, nom_conducteur, nom_marital,
               prenom_conducteur, date_naiss, photo_conducteur,
               id_ste, tel, mobile, adresse1, adresse2,
               cp, ville, pays, lieu_naiss, dep_naiss,
               login, mdp_user,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?,
                   '', '', NULL,
                   ?, ?, ?,
                   ?, ?, ?,
                   ?, ?, ?, ?, ?,
                   ?, ?, ?, ?, ?,
                   '', '',
                   NOW(), ?, 'new')""",
        (
            id_cond, int(id_salarie),
            _sexe_to_int(s.get("sexe")), s.get("nom"), s.get("nom_marital"),
            s.get("prenom"), s.get("date_naiss"), s.get("photo"),
            s.get("id_ste"), s.get("tel_fixe"), s.get("tel_mob"),
            s.get("adresse1"), s.get("adresse2"),
            s.get("cp"), s.get("ville"), s.get("nationalite"),
            s.get("lieu_naiss"), s.get("dep_naiss"),
            int(op_id),
        ),
    )
    return {"ok": True, "id_conducteur": str(id_cond)}


def update_conducteur_permis(
    id_conducteur: int,
    num_permis: str,
    type_permis: str,
    date_obtention: str,
    op_id: int,
) -> dict:
    """Met a jour les 3 champs Permis (saisis directement dans l'onglet)."""
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_conducteur
              SET num_permis = ?,
                  type_permis = ?,
                  date_obtention = ?::date,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_conducteur = ?""",
        (
            (num_permis or "")[:25],
            (type_permis or "")[:3],
            date_obtention or None,
            int(op_id),
            int(id_conducteur),
        ),
    )
    return {"ok": True}


# ===========================================================================
# Onglet 1 : Fichier Conducteur (FTP)
# ===========================================================================


def _rep_ftp_ulease(id_conducteur: int) -> str:
    return f"/ulease/Conducteurs/{int(id_conducteur)}"


def list_files_ulease(id_conducteur: int) -> dict:
    """Liste les fichiers du conducteur sur le FTP."""
    rep_ftp = _rep_ftp_ulease(id_conducteur)
    out = {"ok": False, "srv": FTP_HOST, "etat": "", "files": []}
    ftp = _ftp_connect()
    if not ftp:
        out["etat"] = "Connexion FTP impossible"
        return out
    try:
        try:
            ftp.cwd(rep_ftp)
        except ftplib.error_perm:
            out["ok"] = True
            out["etat"] = "OK (dossier vide)"
            return out

        files: list[dict] = []
        try:
            entries = list(ftp.mlsd())
            for name, facts in entries:
                if name in (".", "..") or facts.get("type", "file") != "file":
                    continue
                size = int(facts.get("size", "0") or 0)
                modify = facts.get("modify", "")
                date_iso = (
                    f"{modify[0:4]}-{modify[4:6]}-{modify[6:8]} "
                    f"{modify[8:10]}:{modify[10:12]}:{modify[12:14]}"
                    if len(modify) >= 14 else ""
                )
                files.append({
                    "nom": name,
                    "taille_mo": round(size / 1024 / 1024, 2),
                    "date_iso": date_iso,
                })
        except Exception:
            # Fallback LIST
            lines: list[str] = []
            try:
                ftp.retrlines("LIST", lines.append)
            except Exception:
                lines = []
            for line in lines:
                parts = line.split(maxsplit=8)
                if not parts:
                    continue
                if parts[0].startswith("d") or "<DIR>" in line:
                    continue
                nom = parts[-1] if parts else ""
                if nom in (".", ".."):
                    continue
                size = 0
                try:
                    size = ftp.size(nom) or 0
                except Exception:
                    pass
                files.append({
                    "nom": nom,
                    "taille_mo": round(size / 1024 / 1024, 2),
                    "date_iso": "",
                })

        files.sort(key=lambda f: f["date_iso"] or f["nom"], reverse=True)
        out["ok"] = True
        out["etat"] = "OK"
        out["files"] = files
    finally:
        try:
            ftp.quit()
        except Exception:
            pass
    return out


def upload_file_ulease(id_conducteur: int, filename: str, content: bytes) -> dict:
    if not content:
        return {"ok": False, "error": "Contenu vide"}
    safe_name = _sanitize_filename(filename)
    rep_ftp = _rep_ftp_ulease(id_conducteur)
    ftp = _ftp_connect()
    if not ftp:
        return {"ok": False, "error": "Connexion FTP impossible"}
    try:
        try:
            ftp.cwd(rep_ftp)
        except ftplib.error_perm:
            _ftp_makedirs(ftp, rep_ftp)
            ftp.cwd(rep_ftp)
        ftp.storbinary(f"STOR {safe_name}", io.BytesIO(content))
        return {"ok": True, "filename": safe_name}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def download_file_ulease(id_conducteur: int, filename: str) -> bytes | None:
    """Retourne le contenu binaire d'un fichier conducteur (None si KO)."""
    safe_name = _sanitize_filename(filename)
    rep_ftp = _rep_ftp_ulease(id_conducteur)
    ftp = _ftp_connect()
    if not ftp:
        return None
    try:
        try:
            ftp.cwd(rep_ftp)
        except ftplib.error_perm:
            return None
        buf = io.BytesIO()
        try:
            ftp.retrbinary(f"RETR {safe_name}", buf.write)
        except Exception:
            return None
        return buf.getvalue()
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def delete_file_ulease(id_conducteur: int, filename: str) -> dict:
    safe_name = _sanitize_filename(filename)
    rep_ftp = _rep_ftp_ulease(id_conducteur)
    ftp = _ftp_connect()
    if not ftp:
        return {"ok": False, "error": "Connexion FTP impossible"}
    try:
        try:
            ftp.cwd(rep_ftp)
        except ftplib.error_perm:
            return {"ok": False, "error": "Dossier inexistant"}
        try:
            ftp.delete(safe_name)
        except ftplib.error_perm as e:
            return {"ok": False, "error": f"Suppression refusee : {e}"}
        return {"ok": True, "filename": safe_name}
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


# ===========================================================================
# Onglet 2 : Historique Attribution (vehicule)
# ===========================================================================


def load_histo_attribution(id_conducteur: int) -> list[dict]:
    """Historique des attributions vehicule_conducteur JOIN vehicule_fiche."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT vc.id_vehicule_pc, vc.id_vehicule, vc.temporaire,
                  vc.perception_date, vc.perception_heure,
                  vc.restitution_date, vc.restitution_heure,
                  vf.immat
             FROM ulease.pgt_vehicule_conducteur vc
             INNER JOIN ulease.pgt_vehicule_fiche vf
               ON vf.id_vehicule = vc.id_vehicule
            WHERE vc.id_conducteur = ?
            ORDER BY vc.perception_date DESC NULLS LAST""",
        (int(id_conducteur),),
    )
    out = []
    for r in rows or []:
        out.append({
            "id_vehicule_pc": _str(r.get("id_vehicule_pc")),
            "id_vehicule": _str(r.get("id_vehicule")),
            "immat": _str(r.get("immat")),
            "temporaire": bool(r.get("temporaire")),
            "perception_date": _iso(r.get("perception_date")),
            "perception_heure": _str(r.get("perception_heure")),
            "restitution_date": _iso(r.get("restitution_date")),
            "restitution_heure": _str(r.get("restitution_heure")),
        })
    return out


# ===========================================================================
# Onglet 3 : Edition documents
# ===========================================================================


def load_doc_edition(id_salarie: int) -> list[dict]:
    """Documents Ulease edites pour le salarie (JOIN type)."""
    db_rh = get_pg_connection("rh")
    rows = db_rh.query(
        """SELECT sdu.id_salarie_doc_ulease, sdu.date_edition,
                  sdu.recu, sdu.recu_date,
                  sdu.id_doc_ulease_type
             FROM rh.pgt_salarie_doc_ulease sdu
            WHERE sdu.id_salarie = ?
              AND (sdu.modif_elem IS NULL OR sdu.modif_elem NOT LIKE '%suppr%')
            ORDER BY sdu.date_edition DESC NULLS LAST""",
        (int(id_salarie),),
    )
    if not rows:
        return []

    # Resolution des libelles type via une 2eme requete (cross-schema KO via JOIN)
    db_u = get_pg_connection("ulease")
    type_ids = list({r.get("id_doc_ulease_type") for r in rows if r.get("id_doc_ulease_type")})
    libs: dict[int, str] = {}
    if type_ids:
        placeholders = ",".join(["?"] * len(type_ids))
        type_rows = db_u.query(
            f"""SELECT id_type_doc, lib_type
                  FROM ulease.pgt_doc_ulease_type
                 WHERE id_type_doc IN ({placeholders})""",
            tuple(int(t) for t in type_ids),
        )
        for tr in type_rows or []:
            libs[int(tr.get("id_type_doc") or 0)] = _str(tr.get("lib_type"))

    out = []
    for r in rows:
        tid = int(r.get("id_doc_ulease_type") or 0)
        out.append({
            "id_salarie_doc_ulease": _str(r.get("id_salarie_doc_ulease")),
            "date_edition": _iso_dt(r.get("date_edition")),
            "lib_type": libs.get(tid, ""),
            "recu": bool(r.get("recu")),
            "recu_date": _iso_dt(r.get("recu_date")),
        })
    return out


def mark_doc_recu(id_salarie_doc_ulease: int, op_id: int) -> dict:
    """Btn 'Doc recu signe' : UPDATE RECU=1 + RECUDATE=NOW."""
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_salarie_doc_ulease
              SET recu = TRUE,
                  recu_date = NOW(),
                  modif_date = NOW(),
                  modif_op = ?
            WHERE id_salarie_doc_ulease = ?""",
        (int(op_id), int(id_salarie_doc_ulease)),
    )
    return {"ok": True}


# ===========================================================================
# Onglet 4 : Attribution Carte Carburant
# ===========================================================================


def load_attribution_carte(id_conducteur: int) -> list[dict]:
    """Liste des attributions de carte carburant (non suppr)."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT ca.id_carte_attribution, ca.du, ca.au,
                  cc.num_carte
             FROM ulease.pgt_carteattribution ca
             INNER JOIN ulease.pgt_cartecarburant cc
               ON cc.id_carte_carburant = ca.id_carte_carburant
            WHERE ca.id_conducteur = ?
              AND ca.modif_elem <> 'suppr'
            ORDER BY ca.du DESC NULLS LAST""",
        (int(id_conducteur),),
    )
    out = []
    for r in rows or []:
        out.append({
            "id_carte_attribution": _str(r.get("id_carte_attribution")),
            "num_carte": _str(r.get("num_carte")),
            "du": _iso(r.get("du")),
            "au": _iso(r.get("au")),
        })
    return out


def soft_delete_attribution_carte(id_carte_attribution: int, op_id: int) -> dict:
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_carteattribution
              SET modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'suppr'
            WHERE id_carte_attribution = ?""",
        (int(op_id), int(id_carte_attribution)),
    )
    return {"ok": True}
