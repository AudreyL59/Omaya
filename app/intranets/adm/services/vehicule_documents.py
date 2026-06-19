"""
Documents FTP d'un vehicule (Fen_FicheVehicule Plan 1).

Repertoire FTP : /OMAYA/Vehicules/{id_vehicule}/  (cf. WinDev
listerFichierVehicule qui fait FTPListeFichier sur ce chemin).

Actions :
- list_files     : FTPListeFichier (MLSD + fallback LIST + MDTM pour la date)
- upload_file    : STOR
- download_file  : RETR
- delete_file    : DELE
- set_as_carte_grise : UPDATE vehicule_fiche.carte_grise + lien_carte_grise
"""

from __future__ import annotations

import ftplib
import io
import re
from datetime import datetime
from typing import Any

from app.core.config import FTP_HOST, FTP_PASSWORD, FTP_USER
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


def _ftp_connect() -> ftplib.FTP | None:
    try:
        ftp = ftplib.FTP(timeout=15)
        ftp.encoding = "latin-1"
        ftp.connect(FTP_HOST, 21)
        ftp.login(FTP_USER, FTP_PASSWORD)
        return ftp
    except Exception:
        return None


def _ftp_makedirs(ftp: ftplib.FTP, path: str) -> None:
    """Cree recursivement un chemin (split par /)."""
    parts = [p for p in path.split("/") if p]
    current = "/"
    for p in parts:
        current = current.rstrip("/") + "/" + p
        try:
            ftp.cwd(current)
        except ftplib.error_perm:
            try:
                ftp.mkd(current)
            except Exception:
                pass
            try:
                ftp.cwd(current)
            except Exception:
                pass


def _rep_ftp(id_vehicule: int) -> str:
    return f"/OMAYA/Vehicules/{int(id_vehicule)}"


def _sanitize_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._\- ]+", "_", name).strip()


def _parse_mlsd_entry(entry: tuple) -> dict:
    name, facts = entry
    size = _int(facts.get("size"))
    modify = facts.get("modify", "")
    date_iso = ""
    if len(modify) >= 14:
        date_iso = (
            f"{modify[0:4]}-{modify[4:6]}-{modify[6:8]}"
            f" {modify[8:10]}:{modify[10:12]}:{modify[12:14]}"
        )
    return {"nom": name, "taille": size, "date_iso": date_iso}


def list_files(id_vehicule: int) -> dict:
    """Liste les fichiers FTP du vehicule. Retourne {ok, files: [{nom,
    taille_mo, date_iso}]}."""
    rep = _rep_ftp(id_vehicule)
    out = {"ok": False, "files": []}
    ftp = _ftp_connect()
    if not ftp:
        return out
    try:
        try:
            ftp.cwd(rep)
        except ftplib.error_perm:
            # Dossier inexistant -> on le cree
            _ftp_makedirs(ftp, rep)
            ftp.cwd(rep)

        entries: list[tuple] = []
        try:
            entries = list(ftp.mlsd())
        except Exception:
            # Fallback LIST + MDTM
            try:
                lines: list[str] = []
                ftp.retrlines("LIST", lines.append)
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
                    modify = ""
                    try:
                        resp = ftp.sendcmd(f"MDTM {nom}")
                        ps = resp.split()
                        if len(ps) >= 2 and ps[0] == "213":
                            modify = ps[1][:14]
                    except Exception:
                        pass
                    entries.append((nom, {"size": str(size), "type": "file", "modify": modify}))
            except Exception:
                entries = []

        files = []
        for entry in entries:
            name, facts = entry
            if name in (".", "..") or facts.get("type", "file") != "file":
                continue
            info = _parse_mlsd_entry(entry)
            files.append({
                "nom": info["nom"],
                "taille_mo": round(info["taille"] / 1024 / 1024, 2),
                "date_iso": info["date_iso"],
            })
        files.sort(key=lambda x: x["nom"])
        return {"ok": True, "files": files}
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def upload_file(id_vehicule: int, filename: str, content: bytes) -> dict:
    """STOR du fichier dans /OMAYA/Vehicules/{id}/."""
    if not content:
        return {"ok": False, "error": "Contenu vide"}
    rep = _rep_ftp(id_vehicule)
    safe = _sanitize_filename(filename)
    ftp = _ftp_connect()
    if not ftp:
        return {"ok": False, "error": "Connexion FTP impossible"}
    try:
        try:
            ftp.cwd(rep)
        except ftplib.error_perm:
            _ftp_makedirs(ftp, rep)
            ftp.cwd(rep)
        ftp.storbinary(f"STOR {safe}", io.BytesIO(content))
        return {"ok": True, "filename": safe, "taille": len(content)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def download_file(id_vehicule: int, filename: str) -> bytes | None:
    """RETR depuis FTP."""
    rep = _rep_ftp(id_vehicule)
    ftp = _ftp_connect()
    if not ftp:
        return None
    try:
        ftp.cwd(rep)
        buf = io.BytesIO()
        ftp.retrbinary(f"RETR {filename}", buf.write)
        return buf.getvalue()
    except Exception:
        return None
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def delete_file(id_vehicule: int, filename: str) -> dict:
    """DELE FTP."""
    rep = _rep_ftp(id_vehicule)
    ftp = _ftp_connect()
    if not ftp:
        return {"ok": False, "error": "Connexion FTP impossible"}
    try:
        ftp.cwd(rep)
        ftp.delete(filename)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def set_as_carte_grise(id_vehicule: int, filename: str, op_id: int) -> dict:
    """Marque un fichier comme carte grise du vehicule (cf. WinDev btn
    'Definir comme Carte grise')."""
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_vehicule_fiche
              SET carte_grise = TRUE,
                  lien_carte_grise = ?,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_vehicule = ?""",
        (filename, int(op_id), int(id_vehicule)),
    )
    return {"ok": True, "lien_carte_grise": filename}
