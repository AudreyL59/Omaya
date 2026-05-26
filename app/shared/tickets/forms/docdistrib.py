"""FI_DocDistrib (type 31 — Réclamation Documents distributeur).

Validation / refus d'un document fourni par un distributeur (gérant
d'une société partenaire).

Tables :
  - TK_DemandeDocDistrib : base ticket_bo (IDDoc_Distrib, LienFichier,
    MotifRefus)
  - Doc_Distrib : base rh (IdSte, IdGérant, IDTypeDocDistributeur,
    NomFichier, DateDépot)
  - TypeDocDistributeur : base rh (LibDoc)
  - societe / salarie : base rh (libellés société + gérant)
  - TK_Liste : base ticket (statut + clôture)

Fichiers : le document fourni est sur FTP /OMAYA/DocTicket/<idticket>/.
À la validation il est déplacé vers
/OMAYA/gestionRH/<IdGérant>/Fiches_Salaires/.

Statuts : 32 = conforme (clôture), 33 = non conforme (refus).
"""

import ftplib
import io
from datetime import datetime

from app.core.config import (
    FTP_DOC_TICKET_PATH,
    FTP_GESTION_RH_PATH,
    FTP_HOST,
    FTP_PASSWORD,
    FTP_USER,
    MAIL_BO,
)
from app.core.database import get_connection
from app.shared.notifications.mail import envoi_mail_rh
from app.shared.notifications.sms import envoi_sms

from ..service import (
    _clean_id,
    _now_windev,
    _to_int,
    load_salaries_minimal,
)

STATUT_CONFORME = 32
STATUT_NON_CONFORME = 33

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


def _ftp_move(src_path: str, dst_dir: str, dst_name: str) -> bool:
    """Déplace src_path → dst_dir/dst_name (crée l'arbo cible). Chemins
    FTP absolus. Renvoie True si OK."""
    ftp = _ftp_connect()
    try:
        ftp.cwd("/")
        for part in [p for p in dst_dir.split("/") if p]:
            try:
                ftp.cwd(part)
            except ftplib.error_perm:
                ftp.mkd(part)
                ftp.cwd(part)
        ftp.rename(src_path, f"{dst_dir.rstrip('/')}/{dst_name}")
        return True
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _demande(id_ticket: int) -> dict | None:
    try:
        return get_connection("ticket_bo").query_one(
            "SELECT IDTK_Liste, IDDoc_Distrib, LienFichier, MotifRefus "
            "FROM TK_DemandeDocDistrib WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
    except Exception:
        return None


def _infos_doc(id_doc: int) -> dict:
    """Cross-DB sur rh : Doc_Distrib → TypeDocDistributeur (LibDoc) +
    societe (RaisonSociale, IdGérant) + salarie (gérant)."""
    out = {
        "lib_doc": "", "lib_ste": "", "lib_gerant": "",
        "id_gerant": 0, "id_ste": 0,
    }
    if not id_doc:
        return out
    rh = get_connection("rh")
    try:
        d = rh.query_one(
            "SELECT IDDoc_Distrib, IdSte, IDTypeDocDistributeur "
            "FROM Doc_Distrib WHERE IDDoc_Distrib = ?",
            (int(id_doc),),
        )
    except Exception:
        d = None
    if not d:
        return out
    id_ste = _clean_id(_to_int(d.get("IdSte")))
    id_type = _to_int(d.get("IDTypeDocDistributeur"))
    out["id_ste"] = id_ste
    # LibDoc
    try:
        t = rh.query_one(
            "SELECT IDTypeDocDistributeur, LibDoc FROM TypeDocDistributeur "
            "WHERE IDTypeDocDistributeur = ?",
            (int(id_type),),
        )
        out["lib_doc"] = ((t.get("LibDoc") if t else "") or "").strip()
    except Exception:
        pass
    # Société + gérant
    try:
        s = rh.query_one(
            "SELECT IdSte, RaisonSociale, IdGérant FROM societe "
            "WHERE IdSte = ?",
            (int(id_ste),),
        )
        if s:
            out["lib_ste"] = (s.get("RaisonSociale") or "").strip()
            out["id_gerant"] = _clean_id(_to_int(s.get("IdGérant")))
    except Exception:
        pass
    if out["id_gerant"]:
        i = load_salaries_minimal({out["id_gerant"]}).get(out["id_gerant"], {})
        p = (i.get("prenom") or "")
        out["lib_gerant"] = (
            f"{i.get('nom', '')} {p[:1].upper() + p[1:].lower() if p else ''}"
        ).strip()
    return out


def _gsm_gerant(id_gerant: int) -> str:
    if not id_gerant:
        return ""
    try:
        c = get_connection("rh").query_one(
            "SELECT IDSalarie, TélMob FROM salarie_coordonnées "
            "WHERE IDSalarie = ?",
            (int(id_gerant),),
        )
        gsm = ((c.get("TélMob") if c else "") or "")
        for ch in (".", " ", "/", "-"):
            gsm = gsm.replace(ch, "")
        return gsm
    except Exception:
        return ""


# --------------------------------------------------------------------
# load / save / get_file
# --------------------------------------------------------------------

def load(id_ticket: int) -> dict:
    r = _demande(id_ticket)
    if not r:
        return {"found": False}
    id_doc = _clean_id(_to_int(r.get("IDDoc_Distrib")))
    lien = (r.get("LienFichier") or "").strip()
    infos = _infos_doc(id_doc)
    return {
        "found": True,
        "id_doc": str(id_doc) if id_doc else "",
        "lib_doc": infos["lib_doc"],
        "lib_ste": infos["lib_ste"],
        "lib_gerant": infos["lib_gerant"],
        "id_gerant": str(infos["id_gerant"]) if infos["id_gerant"] else "",
        "id_ste": str(infos["id_ste"]) if infos["id_ste"] else "",
        "lien_fichier": lien,
        "a_fichier": bool(lien),
        "motif_refus": (r.get("MotifRefus") or "").strip(),
    }


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    action = str(payload.get("action") or "")
    now = _now_windev()
    bo = get_connection("ticket_bo")

    r = _demande(id_ticket)
    if not r:
        return {"ok": False, "error": "Demande introuvable"}
    id_doc = _clean_id(_to_int(r.get("IDDoc_Distrib")))
    lien = (r.get("LienFichier") or "").strip()
    infos = _infos_doc(id_doc)
    id_gerant = infos["id_gerant"]
    id_ste = infos["id_ste"]
    lib_doc = infos["lib_doc"]
    lib_ste = infos["lib_ste"]
    lib_gerant = infos["lib_gerant"]

    # --- Le document est conforme ---
    if action == "conforme":
        if not lien:
            return {"ok": False, "error": "Aucun fichier à valider"}
        ext = ("." + lien.rsplit(".", 1)[-1]) if "." in lien else ""
        date_j = datetime.now().strftime("%Y%m%d")
        nom_doc = f"{date_j}_{id_ste}_{lib_doc}{ext}"
        src = f"{FTP_DOC_TICKET_PATH.rstrip('/')}/{id_ticket}/{lien}"
        dst_dir = f"{FTP_GESTION_RH_PATH.rstrip('/')}/{id_gerant}/Fiches_Salaires"
        try:
            if not _ftp_move(src, dst_dir, nom_doc):
                return {"ok": False, "error": "Déplacement FTP échoué"}
        except Exception as e:
            return {"ok": False, "error": f"FTP : {e}"}

        # Doc_Distrib (rh) : NomFichier + DateDépot
        try:
            get_connection("rh").query(
                """UPDATE Doc_Distrib SET NomFichier = ?, DateDépot = ?,
                    IdGérant = ?, ModifDate = ?, ModifOp = ?,
                    ModifElem = 'modif'
                WHERE IDDoc_Distrib = ?""",
                (
                    nom_doc, date_j, int(id_gerant), now, int(user_id),
                    int(id_doc),
                ),
            )
        except Exception as e:
            return {"ok": False, "error": f"Doc_Distrib : {e}"}

        # Mail BO
        mail_result = ""
        try:
            i = load_salaries_minimal({int(user_id)}).get(int(user_id), {})
            op_nom = i.get("nom", "")
            dest = [MAIL_BO or "bo@exosphere.fr"]
            html = (
                "<font face='arial' style='font-size:10pt;'><p>Bonjour,</p>"
                f"<p>Le fichier '{lib_doc}' pour {lib_gerant} société "
                f"{lib_ste} a été validé ce jour par {op_nom}.</p><br/>---"
                "Cdt.<br/><p><i>PS : Ceci est un mail automatique, ne pas "
                "répondre. Merci.</i></p></font>"
            )
            ok = envoi_mail_rh(
                f"Validation DOC DISTRIB - {lib_ste}", html, dest,
                cci=["intranet@omaya.fr"],
            )
            mail_result = "Mail envoyé" if ok else "Mail non envoyé"
        except Exception as e:
            mail_result = f"Mail non envoyé : {e}"

        # TK_Liste : statut 32 + clôture
        try:
            get_connection("ticket").query(
                """UPDATE TK_Liste SET IDTK_Statut = ?, Cloturée = 1,
                    DateCloture = ?, ModifDate = ? WHERE IDTK_Liste = ?""",
                (STATUT_CONFORME, now, now, int(id_ticket)),
            )
        except Exception:
            pass
        return {"ok": True, "mail_result": mail_result, "cloture": True}

    # --- Le document n'est pas conforme ---
    if action == "non_conforme":
        motif = str(payload.get("motif_refus") or "").strip()
        if not motif:
            return {"ok": False, "error": "Merci de saisir un motif de refus"}
        # Persiste le motif (champ MotifRefus prévu à cet effet)
        try:
            bo.query(
                """UPDATE TK_DemandeDocDistrib SET MotifRefus = ?,
                    ModifDate = ?, ModifOp = ?, ModifElem = 'modif'
                WHERE IDTK_Liste = ?""",
                (motif, now, int(user_id), int(id_ticket)),
            )
        except Exception as e:
            return {"ok": False, "error": f"MotifRefus : {e}"}
        # TK_Liste statut 33
        try:
            get_connection("ticket").query(
                "UPDATE TK_Liste SET IDTK_Statut = ?, ModifDate = ? "
                "WHERE IDTK_Liste = ?",
                (STATUT_NON_CONFORME, now, int(id_ticket)),
            )
        except Exception:
            pass
        # SMS au gérant
        sms_result = ""
        gsm = _gsm_gerant(id_gerant)
        if gsm:
            texte = (
                f"Bonjour, vous devez impérativement fournir à nouveau votre "
                f"{lib_doc}.\nCelui-ci a été refusé par le service juridique.\n"
                "Merci de vous rendre sur l'intranet ou sur l'appli mobile "
                "Omayapp pour renvoyer ce document.\nCdt"
            )
            sms_result = envoi_sms(texte, gsm, "", "OMAYA-Info")
        return {"ok": True, "sms_result": sms_result, "cloture": True}

    # --- Relance SMS ---
    if action == "relance_sms":
        gsm = _gsm_gerant(id_gerant)
        if not gsm:
            return {"ok": False, "error": "Pas de mobile pour le gérant"}
        texte = (
            f"Bonjour, vous devez impérativement fournir votre {lib_doc}.\n"
            "Merci de vous rendre sur l'intranet ou sur l'appli mobile "
            "Omayapp pour envoyer ce document.\nCdt"
        )
        res = envoi_sms(texte, gsm, "", "OMAYA-Info")
        return {"ok": True, "sms_result": res}

    return {"ok": False, "error": "Action non disponible"}


def get_file(id_ticket: int, name: str) -> tuple[bytes, str]:
    """Document fourni (FTP /OMAYA/DocTicket/<idticket>/<name>)."""
    path = f"{FTP_DOC_TICKET_PATH.rstrip('/')}/{id_ticket}/{name.lstrip('/')}"
    try:
        ftp = _ftp_connect()
        buf = io.BytesIO()
        ftp.retrbinary(f"RETR {path}", buf.write)
        ftp.quit()
        data = buf.getvalue()
    except Exception:
        raise FileNotFoundError("Document introuvable sur le FTP")
    return data, _mime_for(name)
