"""FI_Mutuelle (type 27 — Demande Mutuelle).

Suivi de l'affiliation mutuelle d'un salarié + journal d'observations
et pièces jointes (documents sur le FTP gestionRH).

Tables (base ticket_rh) :
  - TK_DemandeMutuelle : la demande (DemandeAffiliation + date, InfoCplt)
  - TK_DemandeMutuelle_FIC : pièces jointes (CheminFic / NomFichier)
Salarié (base rh) :
  - salarie (Nom, Nom_Marital, Prenom)
  - salarie_embauche (DateDebut, EnActivité)

Fichiers : FTP /OMAYA/gestionRH/<IDSalarie>/<NomFichier>.

Fonctionnalités :
  - En-tête salarié (lecture)
  - Demande Affiliation faite (+ date) → Enregistrer
  - Journal d'observations horodatées (InfoCplt) → Ajouter une observation
  - Pièces jointes : aperçu / téléchargement (get_file)
"""

import ftplib
import io
from datetime import datetime

from app.core.config import (
    FTP_GESTION_RH_PATH,
    FTP_HOST,
    FTP_PASSWORD,
    FTP_USER,
)
from app.core.database import get_connection
from app.core.database.pg import get_pg_connection  # noqa: F401  # phase 1 hybride : tout reste HFSQL (read-modify-write critiques)

from ..service import (
    _clean_id,
    _now_windev,
    _to_int,
    date_only_to_iso,
    iso_to_date_only,
    load_salaries_minimal,
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


def _ftp_download(path: str) -> bytes | None:
    """Télécharge un fichier (chemin FTP absolu) en mémoire."""
    if not path:
        return None
    try:
        ftp = ftplib.FTP(timeout=15)
        ftp.encoding = "latin-1"
        ftp.connect(FTP_HOST, 21)
        ftp.login(FTP_USER, FTP_PASSWORD)
        buf = io.BytesIO()
        ftp.retrbinary(f"RETR {path}", buf.write)
        ftp.quit()
        return buf.getvalue()
    except Exception:
        return None


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _id_salarie(id_ticket: int) -> int:
    try:
        r = get_connection("ticket_rh").query_one(
            "SELECT IDTK_Liste, IDSalarie FROM TK_DemandeMutuelle "
            "WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        return _clean_id(_to_int(r.get("IDSalarie"))) if r else 0
    except Exception:
        return 0


def _salarie_header(id_salarie: int) -> dict:
    """En-tête salarié : nom / nom marital / prénom / activité / date début."""
    if not id_salarie:
        return {}
    rh = get_connection("rh")
    out = {
        "nom": "", "nom_marital": "", "prenom": "",
        "en_activite": False, "date_debut": "",
    }
    try:
        s = rh.query_one(
            "SELECT IDSalarie, Nom, Nom_Marital, Prenom FROM salarie "
            "WHERE IDSalarie = ?",
            (int(id_salarie),),
        )
        if s:
            out["nom"] = (s.get("Nom") or "").strip()
            out["nom_marital"] = (s.get("Nom_Marital") or "").strip()
            out["prenom"] = (s.get("Prenom") or "").strip()
    except Exception:
        pass
    try:
        e = rh.query_one(
            "SELECT TOP 1 IDSalarie, DateDebut, EnActivité FROM salarie_embauche "
            "WHERE IDSalarie = ? ORDER BY DateDebut DESC",
            (int(id_salarie),),
        )
        if e:
            out["en_activite"] = bool(e.get("EnActivité"))
            out["date_debut"] = date_only_to_iso(e.get("DateDebut"))
    except Exception:
        pass
    return out


def _info_cplt(id_ticket: int) -> str:
    """Mémo texte InfoCplt (lecture isolée — cf. bridge HFSQL)."""
    try:
        r = get_connection("ticket_rh").query_one(
            "SELECT IDTK_Liste, InfoCplt FROM TK_DemandeMutuelle "
            "WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        return ((r.get("InfoCplt") if r else "") or "").strip()
    except Exception:
        return ""


def _pieces(id_ticket: int) -> list[dict]:
    """Pièces jointes (TK_DemandeMutuelle_FIC). NomFichier = mémo (isolé)."""
    rh = get_connection("ticket_rh")
    try:
        rows = rh.query(
            "SELECT IDTK_DemandeMutuelle_FIC, CheminFic FROM "
            "TK_DemandeMutuelle_FIC WHERE IDTK_Liste = ? "
            "AND ModifElem NOT LIKE '%suppr%'",
            (int(id_ticket),),
        )
    except Exception:
        return []
    out = []
    for r in rows or []:
        idf = _clean_id(_to_int(r.get("IDTK_DemandeMutuelle_FIC")))
        if not idf:
            continue
        chemin = (r.get("CheminFic") or "").strip()
        nom = ""
        try:
            f = rh.query_one(
                "SELECT IDTK_DemandeMutuelle_FIC, NomFichier FROM "
                "TK_DemandeMutuelle_FIC WHERE IDTK_DemandeMutuelle_FIC = ?",
                (int(idf),),
            )
            nom = ((f.get("NomFichier") if f else "") or "").strip()
        except Exception:
            pass
        if not nom:
            nom = chemin.lstrip("/")
        out.append({"id": str(idf), "chemin": chemin, "nom": nom})
    return out


# --------------------------------------------------------------------
# load / save / get_file
# --------------------------------------------------------------------

def load(id_ticket: int) -> dict:
    db = get_connection("ticket_rh")
    r = db.query_one(
        "SELECT IDTK_Liste, IDTK_DemandeMutuelle, IDSalarie, "
        "DemandeAffiliation, DemandeAffiliationDate FROM TK_DemandeMutuelle "
        "WHERE IDTK_Liste = ?",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}
    id_salarie = _clean_id(_to_int(r.get("IDSalarie")))
    header = _salarie_header(id_salarie)
    return {
        "found": True,
        "id_salarie": str(id_salarie) if id_salarie else "",
        "nom": header.get("nom", ""),
        "nom_marital": header.get("nom_marital", ""),
        "prenom": header.get("prenom", ""),
        "en_activite": header.get("en_activite", False),
        "date_debut": header.get("date_debut", ""),
        "demande_affiliation": bool(r.get("DemandeAffiliation")),
        "demande_affiliation_date": date_only_to_iso(
            r.get("DemandeAffiliationDate")
        ),
        "info_cplt": _info_cplt(id_ticket),
        "pieces": _pieces(id_ticket),
    }


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    action = str(payload.get("action") or "")
    now = _now_windev()
    rh = get_connection("ticket_rh")

    # --- Enregistrer : demande affiliation + date ---
    if action == "enregistrer":
        affiliation = 1 if payload.get("demande_affiliation") else 0
        d_aff = iso_to_date_only(payload.get("demande_affiliation_date"))
        try:
            rh.query(
                """UPDATE TK_DemandeMutuelle SET DemandeAffiliation = ?,
                    DemandeAffiliationDate = ?, ModifDate = ?, ModifOp = ?,
                    ModifElem = 'new'
                WHERE IDTK_Liste = ?""",
                (affiliation, d_aff, now, int(user_id), int(id_ticket)),
            )
        except Exception as e:
            return {"ok": False, "error": f"enregistrer : {e}"}
        return {"ok": True}

    # --- Ajouter une observation (journal InfoCplt horodaté) ---
    if action == "add_obser":
        obser = str(payload.get("observation") or "").strip()
        if not obser:
            return {"ok": False, "error": "Observation vide"}
        prenom = ""
        i = load_salaries_minimal({int(user_id)}).get(int(user_id), {})
        p = (i.get("prenom") or "")
        prenom = p[:1].upper() + p[1:] if p else ""
        horodatage = datetime.now().strftime("%d/%m/%Y %H:%M")
        ligne = f"{horodatage} par {prenom} : {obser}"
        ancien = _info_cplt(id_ticket)
        nouveau = (ancien + "\r\n" + ligne) if ancien else ligne
        try:
            rh.query(
                """UPDATE TK_DemandeMutuelle SET InfoCplt = ?,
                    ModifDate = ?, ModifOp = ?, ModifElem = 'new'
                WHERE IDTK_Liste = ?""",
                (nouveau, now, int(user_id), int(id_ticket)),
            )
        except Exception as e:
            return {"ok": False, "error": f"add_obser : {e}"}
        return {"ok": True, "info_cplt": nouveau}

    return {"ok": False, "error": "Action non disponible"}


def get_file(id_ticket: int, name: str) -> tuple[bytes, str]:
    """Retourne (octets, mime) d'une pièce jointe mutuelle (FTP gestionRH).

    `name` = NomFichier (ou CheminFic) de la pièce ; le chemin FTP est
    /OMAYA/gestionRH/<IDSalarie>/<nom>.
    """
    id_salarie = _id_salarie(id_ticket)
    if not id_salarie:
        raise FileNotFoundError("Salarié introuvable pour ce ticket")
    fic = name.lstrip("/")
    path = f"{FTP_GESTION_RH_PATH.rstrip('/')}/{id_salarie}/{fic}"
    data = _ftp_download(path)
    if data is None:
        raise FileNotFoundError("Document introuvable sur le FTP")
    return data, _mime_for(name)
