"""FI_FactDistrib (type 28 — Facturation Distrib).

Traitement ADM d'une demande de facturation distributeur : montant +
date de virement, ouverture de la facture, chargement de la preuve de
virement (→ clôture du ticket), et suivi ADM (mémos + notification mail).

Tables :
  - TK_DemandeFacturationDistrib : base ticket_bo (FicFacture,
    FicPreuveVirement, IdGérant, IdSte, Montant, DateVirement)
  - salarie_suiviADM : base rh (journal de suivi ADM)
  - societe (RaisonSociale) / salarie : base rh (libellés)
  - TK_Liste : base ticket (clôture)

Fichiers : FTP /OMAYA/gestionRH/<IdGérant>/Factures/<nom>.
"""

import ftplib
import io
from datetime import datetime

from app.core.config import (
    FTP_GESTION_RH_PATH,
    FTP_HOST,
    FTP_PASSWORD,
    FTP_USER,
    MAIL_BO,
    MAIL_JURISTE_1,
    MAIL_RESP_JURISTE,
)
from app.core.database import get_connection
from app.core.database.pg import get_pg_connection
from app.shared.notifications.mail import envoi_mail_rh

from ..service import (
    _clean_id,
    _now_windev,
    _to_int,
    _windev_to_iso,
    date_only_to_iso,
    iso_to_date_only,
    load_salaries_minimal,
    rtf_to_text,
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

def _demande(id_ticket: int) -> dict | None:
    """Ligne TK_DemandeFacturationDistrib (sans les mémos texte)."""
    try:
        return get_connection("ticket_bo").query_one(
            "SELECT IDTK_Liste, IdGérant, IdSte, Montant, DateVirement "
            "FROM TK_DemandeFacturationDistrib WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
    except Exception:
        return None


def _memo_fic(id_ticket: int, field: str) -> str:
    """Mémo texte FicFacture / FicPreuveVirement (lecture isolée)."""
    try:
        r = get_connection("ticket_bo").query_one(
            f"SELECT IDTK_Liste, {field} FROM TK_DemandeFacturationDistrib "
            "WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        return ((r.get(field) if r else "") or "").strip()
    except Exception:
        return ""


def _lib_ste(id_ste: int) -> str:
    if not id_ste:
        return ""
    try:
        r = get_pg_connection("rh").query_one(
            "SELECT id_ste, raison_sociale FROM pgt_societe WHERE id_ste = ?",
            (int(id_ste),),
        )
        return ((r.get("raison_sociale") if r else "") or "").strip()
    except Exception:
        return ""


def _lib_gerant(id_gerant: int) -> str:
    if not id_gerant:
        return ""
    i = load_salaries_minimal({int(id_gerant)}).get(int(id_gerant), {})
    p = (i.get("prenom") or "")
    return f"{i.get('nom', '')} {p[:1].upper() + p[1:].lower() if p else ''}".strip()


def _suivi_adm(id_gerant: int) -> list[dict]:
    """Journal salarie_suiviADM (schema rh) pour le gerant. Description =
    memo texte -> lecture isolee. Lecture pure PG (lag tolere)."""
    if not id_gerant:
        return []
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            "SELECT id_salarie_suivi_adm, op_crea, date_crea FROM pgt_salarie_suivi_adm "
            "WHERE id_salarie = ? AND modif_elem NOT LIKE '%suppr%' "
            "ORDER BY date_crea DESC",
            (int(id_gerant),),
        )
    except Exception:
        return []
    rows = rows or []
    ops = {_clean_id(_to_int(r.get("op_crea"))) for r in rows}
    noms = load_salaries_minimal(ops)
    out = []
    for r in rows:
        idm = _clean_id(_to_int(r.get("id_salarie_suivi_adm")))
        if not idm:
            continue
        op = _clean_id(_to_int(r.get("op_crea")))
        ni = noms.get(op, {})
        np = (ni.get("prenom") or "")
        par = f"{ni.get('nom', '')} {np[:1].upper() + np[1:].lower() if np else ''}".strip()
        desc = ""
        try:
            d = rh.query_one(
                "SELECT id_salarie_suivi_adm, description FROM pgt_salarie_suivi_adm "
                "WHERE id_salarie_suivi_adm = ?",
                (int(idm),),
            )
            desc = rtf_to_text((d.get("description") if d else "") or "")
        except Exception:
            pass
        out.append({
            "id": str(idm),
            "depose_le": _windev_to_iso(r.get("date_crea")),
            "par": par,
            "message": desc,
        })
    return out


# --------------------------------------------------------------------
# load / save / get_file / upload_file
# --------------------------------------------------------------------

def load(id_ticket: int) -> dict:
    r = _demande(id_ticket)
    if not r:
        return {"found": False}
    id_gerant = _clean_id(_to_int(r.get("IdGérant")))
    id_ste = _clean_id(_to_int(r.get("IdSte")))
    fic_preuve = _memo_fic(id_ticket, "FicPreuveVirement")
    return {
        "found": True,
        "id_gerant": str(id_gerant) if id_gerant else "",
        "id_ste": str(id_ste) if id_ste else "",
        "lib_ste": _lib_ste(id_ste),
        "lib_gerant": _lib_gerant(id_gerant),
        "montant": float(r.get("Montant") or 0),
        "date_virement": date_only_to_iso(r.get("DateVirement")),
        "fic_facture": _memo_fic(id_ticket, "FicFacture"),
        "fic_preuve": fic_preuve,
        "a_preuve": bool(fic_preuve),
        "suivi_adm": _suivi_adm(id_gerant),
    }


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    action = str(payload.get("action") or "")
    now = _now_windev()
    bo = get_connection("ticket_bo")

    # --- Enregistrer les infos ticket (montant + date de virement) ---
    if action == "enregistrer":
        montant = float(payload.get("montant") or 0)
        d_vir = iso_to_date_only(payload.get("date_virement"))
        try:
            bo.query(
                """UPDATE TK_DemandeFacturationDistrib SET Montant = ?,
                    DateVirement = ?, ModifDate = ?, ModifOp = ?,
                    ModifElem = 'modif'
                WHERE IDTK_Liste = ?""",
                (montant, d_vir, now, int(user_id), int(id_ticket)),
            )
        except Exception as e:
            return {"ok": False, "error": f"enregistrer : {e}"}
        return {"ok": True}

    # --- Ajouter un mémo (suivi ADM) + notification mail ---
    if action == "add_memo":
        desc = str(payload.get("message") or "").strip()
        if not desc:
            return {"ok": False, "error": "Mémo vide"}
        r = _demande(id_ticket)
        id_gerant = _clean_id(_to_int(r.get("IdGérant"))) if r else 0
        id_ste = _clean_id(_to_int(r.get("IdSte"))) if r else 0
        lib_ste = _lib_ste(id_ste)
        try:
            get_connection("rh").query(
                """INSERT INTO salarie_suiviADM
                (IDsalarie_suiviADM, IDSalarie, OPCREA, DESCRIPTION,
                 DATECREA, ModifDate, ModifOP, ModifELEM)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'new')""",
                (
                    int(now), int(id_gerant), int(user_id), desc,
                    now, now, int(user_id),
                ),
            )
        except Exception as e:
            return {"ok": False, "error": f"add_memo : {e}"}

        # Notification mail (juristes + BO)
        mail_result = ""
        try:
            i = load_salaries_minimal({int(user_id)}).get(int(user_id), {})
            p = (i.get("prenom") or "")
            prenom = p[:1].upper() + p[1:].lower() if p else ""
            dest = [m for m in (MAIL_RESP_JURISTE, MAIL_JURISTE_1, MAIL_BO) if m]
            html = (
                "<font face='arial' style='font-size:10pt;'>"
                "<p>Bonjour,</p>"
                f"<p>Un mémo vient d'être déposé par {prenom} concernant le "
                f"ticket de demande de facturation pour la société "
                f"{lib_ste}.</p><br/>---Cdt.<br/>"
                "<p><i>PS : Ceci est un mail automatique, ne pas répondre. "
                "Merci.</i></p></font>"
            )
            if dest:
                ok = envoi_mail_rh(
                    f"Ajout Mémo Distrib - {lib_ste}", html, dest,
                    cci=["intranet@omaya.fr"],
                )
                mail_result = "Mail envoyé" if ok else "Mail non envoyé"
        except Exception as e:
            mail_result = f"Mail non envoyé : {e}"

        return {"ok": True, "mail_result": mail_result,
                "suivi_adm": _suivi_adm(id_gerant)}

    return {"ok": False, "error": "Action non disponible"}


def get_file(id_ticket: int, name: str) -> tuple[bytes, str]:
    """Facture ou preuve de virement (FTP gestionRH/<IdGérant>/Factures)."""
    r = _demande(id_ticket)
    id_gerant = _clean_id(_to_int(r.get("IdGérant"))) if r else 0
    if not id_gerant:
        raise FileNotFoundError("Gérant introuvable pour ce ticket")
    fic = name.lstrip("/")
    path = f"{FTP_GESTION_RH_PATH.rstrip('/')}/{id_gerant}/Factures/{fic}"
    data = _ftp_download(path)
    if data is None:
        raise FileNotFoundError("Document introuvable sur le FTP")
    return data, _mime_for(name)


def upload_file(id_ticket: int, filename: str, content: bytes) -> dict:
    """« Charger la preuve de virement » : upload FTP + clôture du ticket.

    Le montant et la date de virement doivent être enregistrés au
    préalable (action `enregistrer`). On refuse si DateVirement absente.
    """
    if not content:
        return {"ok": False, "error": "Fichier vide"}
    r = _demande(id_ticket)
    if not r:
        return {"ok": False, "error": "Demande introuvable"}
    id_gerant = _clean_id(_to_int(r.get("IdGérant")))
    if not id_gerant:
        return {"ok": False, "error": "Gérant introuvable"}
    if not date_only_to_iso(r.get("DateVirement")):
        return {"ok": False,
                "error": "Date de virement obligatoire avant le chargement"}

    # Nom : <baseFacture>_PreuveVirement.<ext> (cf. WinDev)
    fic_facture = _memo_fic(id_ticket, "FicFacture")
    base = fic_facture.rsplit("/", 1)[-1]
    base = base.rsplit(".", 1)[0] if "." in base else base
    if not base:
        base = str(id_ticket)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    fic_preuve = f"{base}_PreuveVirement.{ext}"

    now = _now_windev()
    try:
        from .cttw_pdf import ftp_upload

        ftp_upload(
            f"{FTP_GESTION_RH_PATH.rstrip('/')}/{id_gerant}/Factures",
            fic_preuve, content,
        )
    except Exception as e:
        return {"ok": False, "error": f"Upload FTP : {e}"}

    bo = get_connection("ticket_bo")
    try:
        bo.query(
            """UPDATE TK_DemandeFacturationDistrib SET FicPreuveVirement = ?,
                ModifDate = ?, ModifElem = 'modif'
            WHERE IDTK_Liste = ?""",
            (fic_preuve, now, int(id_ticket)),
        )
    except Exception as e:
        return {"ok": False, "error": f"MAJ preuve : {e}"}

    # Clôture du ticket (cf. WinDev : TK_Liste.Cloturée + DateCloture)
    try:
        get_connection("ticket").query(
            """UPDATE TK_Liste SET Cloturée = 1, DateCloture = ?,
                ModifDate = ? WHERE IDTK_Liste = ?""",
            (now, now, int(id_ticket)),
        )
    except Exception:
        pass
    return {"ok": True, "fic_preuve": fic_preuve, "cloture": True}
