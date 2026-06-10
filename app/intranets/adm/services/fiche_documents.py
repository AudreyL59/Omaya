"""
Onglet 'Documents' de la fiche salarie ADM.

Transposition de la fenetre WinDev FI_SalarieDocuments :
  - Listing FTP des fichiers du salarie dans /OMAYA/gestionRH/{id}/<sous_rep>
  - 5 sous-onglets : Docs internes ('/'), Espace salarié ('/Fiches_Salaires/'),
    ADF ('/Suivi_ADF/'), Bilans d'évolution ('/BilanEvo/'), Facture ('/Factures/')
  - Actions : upload, telechargement (selection), suppression (selection),
    'Voir le doc' (apercu), 'Envoyer la selection par mail', 'Tk Mutuelle
    avec la selection'

Ce module ne fait que le LISTING + URL HTTP pour le bouton 'Voir le doc'.
Les autres actions (upload/delete/mail/tk) viendront dans des commits dedies.
"""

from __future__ import annotations

import ftplib
import io
import re
from urllib.parse import quote

from app.core.config import DOCS_URL, FTP_HOST, FTP_PASSWORD, FTP_USER


# Mapping ssRep WinDev -> chemin relatif (sans slash initial ni final)
SOUS_REPS = {
    "internes": "",
    "espace_salarie": "Fiches_Salaires",
    "adf": "Suivi_ADF",
    "bilan_evo": "BilanEvo",
    "factures": "Factures",
}


def _ftp_connect() -> ftplib.FTP | None:
    """Connexion FTP. Retourne None en cas d'echec."""
    try:
        ftp = ftplib.FTP(timeout=15)
        ftp.encoding = "latin-1"
        ftp.connect(FTP_HOST, 21)
        ftp.login(FTP_USER, FTP_PASSWORD)
        return ftp
    except Exception:
        return None


def _parse_mlsd_entry(entry: tuple) -> dict:
    """Convertit une entree MLSD (name, facts) en dict {nom, taille, date}.

    facts : {'modify': 'YYYYMMDDHHMMSS', 'size': '12345', 'type': 'file', ...}
    """
    name, facts = entry
    size = int(facts.get("size", "0") or 0)
    modify = facts.get("modify", "")
    date_iso = ""
    if len(modify) >= 14:
        date_iso = (
            f"{modify[0:4]}-{modify[4:6]}-{modify[6:8]}"
            f" {modify[8:10]}:{modify[10:12]}:{modify[12:14]}"
        )
    return {"nom": name, "taille": size, "date_iso": date_iso}


def list_files(id_salarie: int, sous_rep_key: str = "internes") -> dict:
    """Liste les fichiers du salarie sur le FTP.

    Retourne :
      {
        ok: bool,
        srv: str (ipFTP),
        etat: str (Etat Connexion),
        sous_rep: str (relatif, sans slash),
        files: list[{nom, taille_mo, date_iso, url}]
      }
    """
    sous_rep = SOUS_REPS.get(sous_rep_key, "")
    base_rel = f"gestionRH/{int(id_salarie)}"
    rep_rel = f"{base_rel}/{sous_rep}".rstrip("/")
    rep_ftp = f"/OMAYA/{rep_rel}"

    out_base = {
        "ok": False,
        "srv": FTP_HOST,
        "etat": "",
        "sous_rep": sous_rep,
        "files": [],
    }

    ftp = _ftp_connect()
    if not ftp:
        out_base["etat"] = "Connexion FTP impossible"
        return out_base

    files: list[dict] = []
    try:
        try:
            ftp.cwd(rep_ftp)
        except ftplib.error_perm:
            # Dossier inexistant -> liste vide mais OK
            out_base["ok"] = True
            out_base["etat"] = "OK (dossier vide)"
            return out_base

        entries: list[tuple] = []
        try:
            # MLSD donne directement taille + date
            entries = list(ftp.mlsd())
        except Exception:
            # Fallback NLST + SIZE
            try:
                noms = ftp.nlst()
                for nom in noms:
                    if nom in (".", ".."):
                        continue
                    size = 0
                    try:
                        size = ftp.size(nom) or 0
                    except Exception:
                        pass
                    entries.append((nom, {"size": str(size), "type": "file"}))
            except Exception:
                entries = []

        for entry in entries:
            name, facts = entry
            if name in (".", "..") or facts.get("type") == "dir":
                continue
            info = _parse_mlsd_entry(entry)
            nom = info["nom"]
            files.append({
                "nom": nom,
                "taille_mo": round(info["taille"] / 1024 / 1024, 2),
                "date_iso": info["date_iso"],
                "url": (
                    f"{DOCS_URL.rstrip('/')}/{base_rel}"
                    + (f"/{sous_rep}" if sous_rep else "")
                    + f"/{quote(nom)}"
                ),
            })

        files.sort(key=lambda f: f["date_iso"] or f["nom"], reverse=True)
        out_base["ok"] = True
        out_base["etat"] = "OK"
        out_base["files"] = files
    finally:
        try:
            ftp.quit()
        except Exception:
            pass

    return out_base


# --- Sanitize + write actions --------------------------------------------

_INVALID_NAME_RE = re.compile(r"[<>:\"/\\|?*\x00-\x1f]")


def _sanitize_filename(name: str) -> str:
    """Nettoie un nom de fichier (transposition WinDev
    ccSansPonctuationNiEspace+ccSansAccent+ccSansEspace de Btn '+').

    On retire seulement les caracteres interdits pour le FTP/IIS,
    sans tout ecraser (l'operateur garde un nom lisible)."""
    base = (name or "").replace("/", "_").replace("\\", "_").strip()
    base = _INVALID_NAME_RE.sub("_", base)
    return base[:200] or "sans_nom"


def _resolve_rep_ftp(id_salarie: int, sous_rep_key: str) -> tuple[str, str]:
    """Retourne (rep_ftp_absolu, sous_rep_lib).

    rep_ftp_absolu : '/OMAYA/gestionRH/<id>[/<sous>]'
    sous_rep_lib : '' | 'Fiches_Salaires' | ...
    """
    sous_rep = SOUS_REPS.get(sous_rep_key, "")
    base_rel = f"gestionRH/{int(id_salarie)}"
    if sous_rep:
        return (f"/OMAYA/{base_rel}/{sous_rep}", sous_rep)
    return (f"/OMAYA/{base_rel}", "")


def _ftp_makedirs(ftp: ftplib.FTP, abs_path: str) -> None:
    """Crée l'arbo si necessaire (best effort)."""
    parts = [p for p in abs_path.split("/") if p]
    cur = "/"
    for p in parts:
        cur = (cur.rstrip("/") + "/" + p)
        try:
            ftp.mkd(cur)
        except ftplib.error_perm:
            pass  # existe deja


def upload_file(id_salarie: int, sous_rep_key: str, filename: str, content: bytes) -> dict:
    """STOR le fichier sur le FTP (transposition Btn '+').

    Retourne {ok, filename (final, sanitize), path}.
    """
    if not content:
        return {"ok": False, "error": "Contenu vide"}

    safe_name = _sanitize_filename(filename)
    rep_ftp, _sous = _resolve_rep_ftp(id_salarie, sous_rep_key)

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
        return {"ok": True, "filename": safe_name, "path": f"{rep_ftp}/{safe_name}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def delete_file(id_salarie: int, sous_rep_key: str, filename: str) -> dict:
    """DELE le fichier sur le FTP (transposition Btn 'Suppression')."""
    safe_name = _sanitize_filename(filename)
    rep_ftp, _ = _resolve_rep_ftp(id_salarie, sous_rep_key)

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
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    finally:
        try:
            ftp.quit()
        except Exception:
            pass
