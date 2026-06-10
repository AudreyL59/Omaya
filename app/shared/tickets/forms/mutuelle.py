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
from app.core.database.pg import get_pg_connection

from ..service import (
    _clean_id,
    _to_int,
    date_only_to_iso,
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
        r = get_pg_connection("ticket_rh").query_one(
            "SELECT id_tk_liste, id_salarie FROM pgt_tk_demande_mutuelle "
            "WHERE id_tk_liste = ?",
            (int(id_ticket),),
        )
        return _clean_id(_to_int(r.get("id_salarie"))) if r else 0
    except Exception:
        return 0


def _salarie_header(id_salarie: int) -> dict:
    """En-tête salarié : nom / nom marital / prénom / activité / date début."""
    if not id_salarie:
        return {}
    rh = get_pg_connection("rh")
    out = {
        "nom": "", "nom_marital": "", "prenom": "",
        "en_activite": False, "date_debut": "",
    }
    try:
        s = rh.query_one(
            "SELECT id_salarie, nom, nom_marital, prenom FROM pgt_salarie "
            "WHERE id_salarie = ?",
            (int(id_salarie),),
        )
        if s:
            out["nom"] = (s.get("nom") or "").strip()
            out["nom_marital"] = (s.get("nom_marital") or "").strip()
            out["prenom"] = (s.get("prenom") or "").strip()
    except Exception:
        pass
    try:
        e = rh.query_one(
            "SELECT id_salarie, date_debut, en_activite FROM pgt_salarie_embauche "
            "WHERE id_salarie = ? ORDER BY date_debut DESC LIMIT 1",
            (int(id_salarie),),
        )
        if e:
            out["en_activite"] = bool(e.get("en_activite"))
            out["date_debut"] = date_only_to_iso(e.get("date_debut"))
    except Exception:
        pass
    return out


def _info_cplt(id_ticket: int) -> str:
    """Mémo texte info_cplt (PG)."""
    try:
        r = get_pg_connection("ticket_rh").query_one(
            "SELECT id_tk_liste, info_cplt FROM pgt_tk_demande_mutuelle "
            "WHERE id_tk_liste = ?",
            (int(id_ticket),),
        )
        return ((r.get("info_cplt") if r else "") or "").strip()
    except Exception:
        return ""


def _pieces(id_ticket: int) -> list[dict]:
    """Pièces jointes (TK_DemandeMutuelle_FIC). NomFichier = mémo (isolé)."""
    rh = get_pg_connection("ticket_rh")
    try:
        rows = rh.query(
            "SELECT id_tk_demande_mutuelle_fic, chemin_fic FROM "
            "pgt_tk_demande_mutuelle_fic WHERE id_tk_liste = ? "
            "AND modif_elem NOT LIKE '%suppr%'",
            (int(id_ticket),),
        )
    except Exception:
        return []
    out = []
    for r in rows or []:
        idf = _clean_id(_to_int(r.get("id_tk_demande_mutuelle_fic")))
        if not idf:
            continue
        chemin = (r.get("chemin_fic") or "").strip()
        nom = ""
        try:
            f = rh.query_one(
                "SELECT id_tk_demande_mutuelle_fic, nom_fichier FROM "
                "pgt_tk_demande_mutuelle_fic WHERE id_tk_demande_mutuelle_fic = ?",
                (int(idf),),
            )
            nom = ((f.get("nom_fichier") if f else "") or "").strip()
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
    db = get_pg_connection("ticket_rh")
    r = db.query_one(
        "SELECT id_tk_liste, id_tk_demande_mutuelle, id_salarie, "
        "demande_affiliation, demande_affiliation_date FROM pgt_tk_demande_mutuelle "
        "WHERE id_tk_liste = ?",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}
    id_salarie = _clean_id(_to_int(r.get("id_salarie")))
    header = _salarie_header(id_salarie)
    return {
        "found": True,
        "id_salarie": str(id_salarie) if id_salarie else "",
        "nom": header.get("nom", ""),
        "nom_marital": header.get("nom_marital", ""),
        "prenom": header.get("prenom", ""),
        "en_activite": header.get("en_activite", False),
        "date_debut": header.get("date_debut", ""),
        "demande_affiliation": bool(r.get("demande_affiliation")),
        "demande_affiliation_date": date_only_to_iso(
            r.get("demande_affiliation_date")
        ),
        "info_cplt": _info_cplt(id_ticket),
        "pieces": _pieces(id_ticket),
    }


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    action = str(payload.get("action") or "")
    rh = get_pg_connection("ticket_rh")

    # --- Enregistrer : demande affiliation + date ---
    if action == "enregistrer":
        affiliation = bool(payload.get("demande_affiliation"))
        d_aff = payload.get("demande_affiliation_date") or None
        try:
            rh.query(
                """UPDATE pgt_tk_demande_mutuelle SET demande_affiliation = ?,
                    demande_affiliation_date = ?, modif_date = NOW(),
                    modif_op = ?, modif_elem = 'modif'
                WHERE id_tk_liste = ?""",
                (affiliation, d_aff, int(user_id), int(id_ticket)),
            )
        except Exception as e:
            return {"ok": False, "error": f"enregistrer : {e}"}
        return {"ok": True}

    # --- Ajouter une observation (journal info_cplt horodaté) ---
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
                """UPDATE pgt_tk_demande_mutuelle SET info_cplt = ?,
                    modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
                WHERE id_tk_liste = ?""",
                (nouveau, int(user_id), int(id_ticket)),
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
