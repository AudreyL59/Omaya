"""FI_CttW_Demande (type 40 — Contrat W : Demande).

Transposition de la fenêtre interne WinDev FI_CttW_Demande :

  - « Type de Contrat demandé »  = TK_DemandeCttW.TitreContrat (lecture)
  - « Casier judiciaire »        = salarie_embauche.CJ_envoyé (lecture)
  - Bloc « Documents Fournis »   = infos mutuelle (salarie_mutuelle,
    base rh) — strictement la même logique que le Plan 1 de FI_CttW,
    on réutilise donc cttw._load_mutuelle / cttw.save (action mutuelle).
  - « Documents à Fournir »      = ReqListeDocàFournir : tk_demandecttw_doc
    (base ticket_rh), aperçu via FTP /OMAYA/gestionRH/<IDSalarie>/<nom>.
  - « Générer le contrat de travail » : ouvre Fen_SalariéDocRH côté
    WinDev (génération du document + ReqOrgaCourantetParentByVendeur).
    Cette fenêtre n'a pas été fournie et dépend du futur module
    « Ajout d'un salarié » -> bouton désactivé (note côté UI).
"""

import ftplib
import io

from app.core.config import (
    FTP_GESTION_RH_PATH,
    FTP_HOST,
    FTP_PASSWORD,
    FTP_USER,
)
from app.core.database.pg import get_pg_connection

from ..service import _clean_id, _to_int
from . import cttw  # réutilisation du bloc mutuelle (load + save)


def _casier_judiciaire(id_salarie: int) -> bool:
    """salarie_embauche.cj_envoye (base rh) — lecture seule."""
    if not id_salarie:
        return False
    try:
        db = get_pg_connection("rh")
        r = db.query_one(
            "SELECT id_salarie, cj_envoye FROM pgt_salarie_embauche "
            "WHERE id_salarie = ?",
            (int(id_salarie),),
        )
        return bool(r.get("cj_envoye")) if r else False
    except Exception:
        return False


def _documents(id_ticket: int) -> list[dict]:
    """Liste des documents a fournir (pgt_tk_demandecttw_doc, base ticket_rh PG)."""
    try:
        db = get_pg_connection("ticket_rh")
        rows = db.query(
            """SELECT id_tk_demande_ctt_w_doc, doc_present, type_doc, nom_fichier
            FROM pgt_tk_demandecttw_doc
            WHERE modif_elem NOT LIKE '%suppr%' AND id_tk_liste = ?""",
            (int(id_ticket),),
        )
    except Exception:
        return []
    out = []
    for r in rows or []:
        out.append({
            "id": str(_clean_id(_to_int(r.get("id_tk_demande_ctt_w_doc")))),
            "present": bool(r.get("doc_present")),
            "type_doc": (r.get("type_doc") or "").strip(),
            "nom_fichier": (r.get("nom_fichier") or "").strip(),
        })
    return out


def load(id_ticket: int) -> dict:
    db = get_pg_connection("ticket_rh")
    r = db.query_one(
        "SELECT id_tk_liste, id_salarie, titre_contrat, type_ctt_w "
        "FROM pgt_tk_demande_ctt_w WHERE id_tk_liste = ?",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}

    id_salarie = _clean_id(_to_int(r.get("id_salarie")))
    base = {
        "found": True,
        "id_salarie": str(id_salarie) if id_salarie else "",
        "type_contrat": (r.get("titre_contrat") or "").strip(),
        "casier_judiciaire": _casier_judiciaire(id_salarie),
        "documents": _documents(int(id_ticket)),
        # Fen_SalariéDocRH branchee depuis fiche-salarie ADM
        "generer_disabled": True,
    }
    base.update(cttw._load_mutuelle(id_salarie))
    base["mutuelles"] = cttw._list_mutuelles()
    return base


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    """Action 'mutuelle' : même sauvegarde salarie_mutuelle que FI_CttW
    (WLangage : ÉcranVersFichier salarie_mutuelle + HModifie)."""
    action = str(payload.get("action") or "mutuelle")
    if action == "mutuelle":
        return cttw.save(
            int(id_ticket), {**payload, "action": "mutuelle"}, int(user_id)
        )
    return {"ok": False, "error": "Action non disponible"}


def _mime_for(name: str) -> str:
    n = (name or "").lower()
    if n.endswith(".pdf"):
        return "application/pdf"
    if n.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if n.endswith(".png"):
        return "image/png"
    if n.endswith(".gif"):
        return "image/gif"
    if n.endswith((".tif", ".tiff")):
        return "image/tiff"
    return "application/octet-stream"


def get_file(id_ticket: int, name: str) -> tuple[bytes, str]:
    """Aperçu d'un document fourni : FTP
    /OMAYA/gestionRH/<IDSalarie>/<name> (cf. WinDev OuvreSoeur(
    Fen_AperçuFichier, TypeDoc, lienDoc+gestionRH/IDSalarie/NomFichier))."""
    if not name:
        raise FileNotFoundError("Nom de fichier manquant")
    db = get_pg_connection("ticket_rh")
    r = db.query_one(
        "SELECT id_tk_liste, id_salarie FROM pgt_tk_demande_ctt_w "
        "WHERE id_tk_liste = ?",
        (int(id_ticket),),
    )
    id_salarie = _clean_id(_to_int(r.get("id_salarie"))) if r else 0
    if not id_salarie:
        raise FileNotFoundError("Salarié introuvable")
    try:
        ftp = ftplib.FTP(timeout=15)
        ftp.encoding = "latin-1"
        ftp.connect(FTP_HOST, 21)
        ftp.login(FTP_USER, FTP_PASSWORD)
        buf = io.BytesIO()
        ftp.retrbinary(
            f"RETR {FTP_GESTION_RH_PATH.rstrip('/')}/{id_salarie}/{name}",
            buf.write,
        )
        ftp.quit()
        data = buf.getvalue()
    except Exception:
        raise FileNotFoundError("Document introuvable sur le FTP")
    if not data:
        raise FileNotFoundError("Document vide")
    return data, _mime_for(name)
