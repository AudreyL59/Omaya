"""FI_DemandeCodeVendeur (types 38 Demande Code Vendeur + 39 Désactivation
Code Vendeur).

Même fenêtre WinDev, comportement piloté par TypeDem :
  - 38 → bouton « Enregistrer » (UPDATE TK_DemandeCodeVendeur)
  - 39 → bouton « Désactivation des accès » (UPDATE + cascade
    salarie_partenaire si TypeOri = 'DPAE' : vide MDP, propage Code/LOGIN)

Tables :
  - TK_DemandeCodeVendeur            : base ticket_bo
  - TK_DemandeCodeVendeur_Fichier    : base ticket_bo (HFSQL nom :
        tk_demandecodevendeur_fichier, PG : pgt_tk_demandecodevendeur_fichier)
  - TK_TypePhotoDPAE                 : base ticket_dpae (combo type doc)
  - salarie_partenaire               : base rh (cascade cas 39 DPAE)
  - Partenaire                       : base adv (libellé)
  - TK_Liste                         : base ticket (renvoi traitement)

Fichiers : FTP /OMAYA/PhotoDPAE/<NomFichier> (cf. WinDev).

NB : l'id_type (38 vs 39) est récupéré côté handler via load_ticket_raw,
le router générique ne le transmet pas. Le flag `is_desactivation`
exposé côté front pilote l'UI (libellé bouton + cascade).
"""

import ftplib
import io
import os
import unicodedata

from app.core.config import (
    FTP_HOST,
    FTP_PASSWORD,
    FTP_PHOTO_DPAE_PATH,
    FTP_USER,
)
from app.core.database import get_connection
from app.core.database.pg import get_pg_connection

from ..service import (
    _clean_id,
    _now_windev,
    _to_int,
    load_ticket_raw,
)

_MIMES = {
    "pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "png": "image/png", "gif": "image/gif", "webp": "image/webp",
    "doc": "application/msword", "txt": "text/plain",
    "docx": "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document",
}


def _mime_for(name: str) -> str:
    ext = (name.rsplit(".", 1)[-1] if "." in name else "").lower()
    return _MIMES.get(ext, "application/octet-stream")


def _ftp_connect() -> ftplib.FTP:
    ftp = ftplib.FTP(timeout=30)
    ftp.encoding = "latin-1"
    ftp.connect(FTP_HOST, 21)
    ftp.login(FTP_USER, FTP_PASSWORD)
    return ftp


def _ftp_download(nom_fichier: str) -> bytes | None:
    """Télécharge /OMAYA/PhotoDPAE/<nom_fichier> depuis le FTP."""
    if not nom_fichier:
        return None
    try:
        ftp = _ftp_connect()
        buf = io.BytesIO()
        ftp.retrbinary(
            f"RETR {FTP_PHOTO_DPAE_PATH.rstrip('/')}/{nom_fichier.lstrip('/')}",
            buf.write,
        )
        ftp.quit()
        return buf.getvalue()
    except Exception:
        return None


def _ftp_upload(remote_dir: str, filename: str, data: bytes) -> None:
    ftp = _ftp_connect()
    try:
        ftp.cwd("/")
        for part in [p for p in remote_dir.split("/") if p]:
            try:
                ftp.cwd(part)
            except ftplib.error_perm:
                ftp.mkd(part)
                ftp.cwd(part)
        ftp.storbinary(f"STOR {filename}", io.BytesIO(data))
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def _sanitize_filename(filename: str) -> str:
    """cf. WinDev btn Ajouter : espaces -> '_', sans accents ni
    ponctuation/espaces, extension conservée."""
    base, ext = os.path.splitext(filename or "")
    base = base.replace(" ", "_")
    base = "".join(
        c for c in unicodedata.normalize("NFKD", base)
        if not unicodedata.combining(c)
    )
    base = "".join(c for c in base if c.isalnum() or c in ("_", "-"))
    ext = "".join(
        c for c in unicodedata.normalize("NFKD", ext)
        if not unicodedata.combining(c)
    )
    ext = "".join(c for c in ext if c.isalnum() or c == ".")
    return (base or "fichier") + ext


# --------------------------------------------------------------------
# Helpers de lecture
# --------------------------------------------------------------------

def _demande(id_ticket: int) -> dict | None:
    """Lit la demande (1 row par IDTK_Liste). Lecture PG."""
    try:
        return get_pg_connection("ticket_bo").query_one(
            """SELECT id_tk_demande_code_vendeur, id_tk_liste, type_ori,
                id_elem, id_partenaire, id_salarie_id_partenaire,
                code, login, mdp
            FROM pgt_tk_demande_code_vendeur
            WHERE id_tk_liste = ? AND modif_elem <> 'suppr'""",
            (int(id_ticket),),
        )
    except Exception:
        return None


def _lib_partenaire(id_partenaire: int) -> str:
    if not id_partenaire:
        return ""
    try:
        r = get_pg_connection("adv").query_one(
            "SELECT id_partenaire, lib_partenaire FROM pgt_partenaire "
            "WHERE id_partenaire = ?",
            (int(id_partenaire),),
        )
        return ((r.get("lib_partenaire") if r else "") or "").strip()
    except Exception:
        return ""


def _documents(id_ticket: int) -> list[dict]:
    """Liste des PJ liées au ticket (TK_DemandeCodeVendeur_Fichier,
    filtrées modif_elem != suppr)."""
    try:
        rows = get_pg_connection("ticket_bo").query(
            """SELECT id_tk_demande_code_vendeur_fichier, nom_fichier,
                lien_fichier
            FROM pgt_tk_demandecodevendeur_fichier
            WHERE id_tk_liste = ? AND modif_elem <> 'suppr'
            ORDER BY nom_fichier ASC""",
            (int(id_ticket),),
        )
    except Exception:
        return []
    out = []
    for r in rows or []:
        idd = _clean_id(_to_int(r.get("id_tk_demande_code_vendeur_fichier")))
        if not idd:
            continue
        out.append({
            "id": str(idd),
            "nom_fichier": (r.get("nom_fichier") or "").strip(),
            "lien_fichier": (r.get("lien_fichier") or "").strip(),
        })
    return out


def _types_photo_dpae() -> list[dict]:
    """Combo « Type Document » : TK_TypePhotoDPAE actifs."""
    try:
        rows = get_pg_connection("ticket_dpae").query(
            """SELECT id_tk_type_photo_dpae, code_type_doc, lib_type_doc
            FROM pgt_tk_type_photo_dpae
            WHERE desactiver = FALSE
              AND modif_elem <> 'suppr'
            ORDER BY lib_type_doc ASC"""
        )
    except Exception:
        return []
    out = []
    for r in rows or []:
        idt = _clean_id(_to_int(r.get("id_tk_type_photo_dpae")))
        if not idt:
            continue
        out.append({
            "id": str(idt),
            "code": (r.get("code_type_doc") or "").strip(),
            "lib": (r.get("lib_type_doc") or "").strip(),
        })
    return out


def _id_type_demande(id_ticket: int) -> int:
    """Récupère IDTK_TypeDemande du ticket (38 ou 39 attendu)."""
    raw = load_ticket_raw(int(id_ticket))
    if not raw:
        return 0
    s = raw.get("id_type_demande") or ""
    return int(s) if s.isdigit() else 0


# --------------------------------------------------------------------
# load / save
# --------------------------------------------------------------------

def load(id_ticket: int) -> dict:
    id_type = _id_type_demande(id_ticket)
    r = _demande(id_ticket)
    if not r:
        return {
            "found": False,
            "id_type_demande": id_type,
            "is_desactivation": id_type == 39,
            "types_doc": _types_photo_dpae(),
            "documents": [],
        }
    id_partenaire = _clean_id(_to_int(r.get("id_partenaire")))
    return {
        "found": True,
        "id_type_demande": id_type,
        "is_desactivation": id_type == 39,
        "id_demande": str(_clean_id(_to_int(
            r.get("id_tk_demande_code_vendeur")
        ))),
        "type_ori": (r.get("type_ori") or "").strip(),
        "id_elem": str(_clean_id(_to_int(r.get("id_elem")))),
        "id_partenaire": str(id_partenaire),
        "lib_partenaire": _lib_partenaire(id_partenaire),
        "id_salarie_id_partenaire": (
            r.get("id_salarie_id_partenaire") or ""
        ).strip(),
        "code": (r.get("code") or "").strip(),
        "login": (r.get("login") or "").strip(),
        "mdp": (r.get("mdp") or "").strip(),
        "documents": _documents(id_ticket),
        "types_doc": _types_photo_dpae(),
    }


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    """Dispatch sur payload.action :
      - 'enregistrer'           : UPDATE TK_DemandeCodeVendeur (cas 38)
      - 'desactivation'         : UPDATE + cascade salarie_partenaire (cas 39)
      - 'renvoyer_traitement'   : TK_Liste.IDTK_Statut = 1
      - 'delete_document'       : soft-delete TK_DemandeCodeVendeur_Fichier
    """
    action = str(payload.get("action") or "")
    now = _now_windev()
    bo = get_connection("ticket_bo")

    if action == "enregistrer":
        r = _demande(id_ticket)
        if not r:
            return {"ok": False, "error": "Demande introuvable"}
        code = str(payload.get("code") or "").strip()
        login = str(payload.get("login") or "").strip()
        mdp = str(payload.get("mdp") or "").strip()
        try:
            bo.query(
                """UPDATE TK_DemandeCodeVendeur
                SET Code = ?, LOGIN = ?, MDP = ?,
                    ModifDate = ?, ModifOp = ?, ModifElem = 'modif'
                WHERE IDTK_Liste = ?""",
                (code, login, mdp, now, int(user_id), int(id_ticket)),
            )
        except Exception as e:
            return {"ok": False, "error": f"Enregistrement : {e}"}
        return {"ok": True}

    if action == "desactivation":
        r = _demande(id_ticket)
        if not r:
            return {"ok": False, "error": "Demande introuvable"}
        code = str(payload.get("code") or "").strip()
        login = str(payload.get("login") or "").strip()
        mdp = str(payload.get("mdp") or "").strip()
        # On enregistre l'état courant du form puis on cascade
        try:
            bo.query(
                """UPDATE TK_DemandeCodeVendeur
                SET Code = ?, LOGIN = ?, MDP = ?,
                    ModifDate = ?, ModifOp = ?, ModifElem = 'modif'
                WHERE IDTK_Liste = ?""",
                (code, login, mdp, now, int(user_id), int(id_ticket)),
            )
        except Exception as e:
            return {"ok": False, "error": f"Désactivation : {e}"}

        # Cascade salarie_partenaire si origine DPAE
        cascade = False
        type_ori = (r.get("type_ori") or "").strip().upper()
        id_sal_id_part = (r.get("id_salarie_id_partenaire") or "").strip()
        if type_ori == "DPAE" and id_sal_id_part:
            try:
                get_connection("rh").query(
                    """UPDATE salarie_partenaire
                    SET Code = ?, LOGIN = ?, MDP = '',
                        ModifDate = ?, ModifOp = ?, ModifElem = 'modif'
                    WHERE IDSalarieIDPartenaire = ?""",
                    (code, login, now, int(user_id), id_sal_id_part),
                )
                cascade = True
            except Exception as e:
                return {"ok": False, "error": f"salarie_partenaire : {e}"}
        return {"ok": True, "cascade": cascade}

    if action == "renvoyer_traitement":
        try:
            get_connection("ticket").query(
                """UPDATE TK_Liste
                SET IDTK_Statut = 1, ModifDate = ?, ModifOp = ?,
                    ModifElem = 'modif'
                WHERE IDTK_Liste = ?""",
                (now, int(user_id), int(id_ticket)),
            )
        except Exception as e:
            return {"ok": False, "error": f"Renvoi traitement : {e}"}
        return {"ok": True}

    if action == "delete_document":
        id_doc = _to_int(payload.get("id_doc"))
        if not id_doc:
            return {"ok": False, "error": "Document manquant"}
        try:
            bo.query(
                """UPDATE tk_demandecodevendeur_fichier
                SET ModifDate = ?, ModifOp = ?, ModifElem = 'suppr'
                WHERE IDTK_DemandeCodeVendeur_Fichier = ?""",
                (now, int(user_id), int(id_doc)),
            )
        except Exception as e:
            return {"ok": False, "error": f"Suppression doc : {e}"}
        return {"ok": True, "documents": _documents(id_ticket)}

    return {"ok": False, "error": "Action non disponible"}


# --------------------------------------------------------------------
# Fichiers (FTP /OMAYA/PhotoDPAE/)
# --------------------------------------------------------------------

def get_file(id_ticket: int, name: str) -> tuple[bytes, str]:
    """Document du dossier code vendeur (FTP /OMAYA/PhotoDPAE/<name>)."""
    data = _ftp_download(name)
    if data is None:
        raise FileNotFoundError("Document introuvable sur le FTP")
    return data, _mime_for(name)


def upload_file(
    id_ticket: int,
    filename: str,
    content: bytes,
    extras: dict | None = None,
) -> dict:
    """Ajoute une PJ au ticket.

    extras attendu : {'id_type_photo_dpae': '<id>', 'lib_type_doc': '<lib>'}
      - id_type_photo_dpae : id du type combo (TK_TypePhotoDPAE).
      - lib_type_doc       : libellé du type choisi (pour le nom de fichier).

    Le nom stocké est préfixé par <idTicket>_<libType> pour éviter les
    collisions dans /OMAYA/PhotoDPAE/ (dossier partagé entre tickets).
    """
    if not filename or not content:
        return {"ok": False, "error": "Fichier vide"}
    extras = extras or {}
    r = _demande(id_ticket)
    if not r:
        return {"ok": False, "error": "Demande introuvable"}
    id_demande = _clean_id(_to_int(r.get("id_tk_demande_code_vendeur")))
    id_type_doc = _to_int(extras.get("id_type_photo_dpae"))
    lib_type = str(extras.get("lib_type_doc") or "").strip()
    if not lib_type:
        return {"ok": False, "error": "Type de document obligatoire"}

    base = _sanitize_filename(filename)
    nom_type = _sanitize_filename(lib_type)
    safe = f"{id_ticket}_{nom_type}_{base}"

    try:
        _ftp_upload(FTP_PHOTO_DPAE_PATH, safe, content)
    except Exception as e:
        return {"ok": False, "error": f"Upload FTP : {e}"}

    now = _now_windev()
    bo = get_connection("ticket_bo")
    try:
        # Le PK (IDTK_DemandeCodeVendeur_Fichier) est auto-incrémenté
        # côté HFSQL (cf. dpaedistrib pour le même pattern).
        bo.query(
            """INSERT INTO tk_demandecodevendeur_fichier
                (IDTK_DemandeCodeVendeur, IDTK_Liste, NomFichier,
                 LienFichier, ModifDate, ModifOp, ModifElem)
            VALUES (?, ?, ?, ?, ?, ?, 'modif')""",
            (
                int(id_demande), int(id_ticket), lib_type, safe,
                now, int(extras.get("user_id") or 0),
            ),
        )
    except Exception as e:
        return {"ok": False, "error": f"INSERT fichier : {e}"}
    return {
        "ok": True,
        "nom_fichier": safe,
        "lien_fichier": safe,
        "documents": _documents(id_ticket),
    }
