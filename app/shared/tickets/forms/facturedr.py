"""FI_FactureDR (type 33 — Facture BO).

Demande de facture / remboursement de frais d'un vendeur, avec transfert
vers le module de gestion des factures (Commande / Commande_facture).

Tables :
  - TK_DemandeFacturation : base ticket_bo (LibFacture=Enseigne,
    NumCommande, Montant, DateAchat, Descriptif, FicFacture,
    FicPreuveVirement, IDCommande)
  - Commande / Commande_facture : base divers (module factures)
  - salarie / salarie_embauche / societe : base rh (vendeur + société)
  - TK_Liste : base ticket (OPCREA = vendeur)

Fichiers : FTP /OMAYA/factures/<NomFic> (puis /OMAYA/factures/<IDCommande>/
après transfert) et /OMAYA/factures/PreuvesPaiements/<idTicket>/<preuve>.

NB : « Voir la fiche Facture » (Fen_FactureFiche, module factures) est en
TODO. « Transférer dans le module facture » crée bien la Commande.
"""

import ftplib
import io

from app.core.config import FTP_HOST, FTP_PASSWORD, FTP_USER
from app.core.database import get_connection

from ..service import (
    _clean_id,
    _now_windev,
    _to_int,
    date_only_to_iso,
    iso_to_date_only,
    load_salaries_minimal,
    maj_op_traitement_ticket,
)

# Base FTP factures (sous la racine /OMAYA)
_FTP_FACTURES = "/OMAYA/factures"
MODES_PAIEMENT = ["CB", "CH", "PRLV", "ESP", "VIR"]

_MIMES = {
    "pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "png": "image/png", "gif": "image/gif", "webp": "image/webp",
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


def _ftp_mkdirs(ftp: ftplib.FTP, abs_dir: str) -> None:
    ftp.cwd("/")
    for part in [p for p in abs_dir.split("/") if p]:
        try:
            ftp.cwd(part)
        except ftplib.error_perm:
            ftp.mkd(part)
            ftp.cwd(part)


def _ftp_move(src_abs: str, dst_dir_abs: str, dst_name: str) -> bool:
    ftp = _ftp_connect()
    try:
        _ftp_mkdirs(ftp, dst_dir_abs)
        ftp.rename(src_abs, f"{dst_dir_abs.rstrip('/')}/{dst_name}")
        return True
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def _ftp_download(abs_path: str) -> bytes | None:
    try:
        ftp = _ftp_connect()
        buf = io.BytesIO()
        ftp.retrbinary(f"RETR {abs_path}", buf.write)
        ftp.quit()
        return buf.getvalue()
    except Exception:
        return None


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _demande(id_ticket: int) -> dict | None:
    try:
        return get_connection("ticket_bo").query_one(
            "SELECT IDTK_Liste, IDCommande, FicFacture, FicPreuveVirement, "
            "Montant, LibFacture, DateAchat, NumCommande "
            "FROM TK_DemandeFacturation WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
    except Exception:
        return None


def _descriptif(id_ticket: int) -> str:
    try:
        r = get_connection("ticket_bo").query_one(
            "SELECT IDTK_Liste, Descriptif FROM TK_DemandeFacturation "
            "WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        return ((r.get("Descriptif") if r else "") or "").strip()
    except Exception:
        return ""


def _id_societe_salarie(id_salarie: int) -> int:
    """Société du vendeur (salarie_embauche.IdSte, base rh)."""
    if not id_salarie:
        return 0
    try:
        r = get_connection("rh").query_one(
            "SELECT TOP 1 IDSalarie, IdSte FROM salarie_embauche "
            "WHERE IDSalarie = ? ORDER BY DateDebut DESC",
            (int(id_salarie),),
        )
        return _clean_id(_to_int(r.get("IdSte"))) if r else 0
    except Exception:
        return 0


def _societes() -> list[dict]:
    try:
        rows = get_connection("rh").query(
            "SELECT IdSte, RaisonSociale FROM societe ORDER BY RaisonSociale"
        )
    except Exception:
        return []
    out = []
    for r in rows or []:
        ids = _clean_id(_to_int(r.get("IdSte")))
        lib = (r.get("RaisonSociale") or "").strip()
        if ids and lib:
            out.append({"id": str(ids), "lib": lib})
    return out


# --------------------------------------------------------------------
# load / save / get_file / upload_file
# --------------------------------------------------------------------

def load(id_ticket: int) -> dict:
    r = _demande(id_ticket)
    if not r:
        return {"found": False}
    id_commande = _clean_id(_to_int(r.get("IDCommande")))
    fic_facture = (r.get("FicFacture") or "").strip()
    fic_preuve = (r.get("FicPreuveVirement") or "").strip()

    # Vendeur = TK_Liste.OPCREA
    id_salarie = 0
    vendeur_nom = ""
    try:
        tk = get_connection("ticket").query_one(
            "SELECT IDTK_Liste, OPCREA FROM TK_Liste WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        id_salarie = _clean_id(_to_int(tk.get("OPCREA"))) if tk else 0
    except Exception:
        pass
    if id_salarie:
        i = load_salaries_minimal({id_salarie}).get(id_salarie, {})
        p = (i.get("prenom") or "")
        vendeur_nom = (
            f"{i.get('nom', '')} {p[:1].upper() + p[1:].lower() if p else ''}"
        ).strip()
    id_ste = _id_societe_salarie(id_salarie)

    # Chemins relatifs (sous /OMAYA) pour aperçu via get_file
    chemin_facture = ""
    if fic_facture:
        chemin_facture = (
            f"factures/{id_commande}/{fic_facture}" if id_commande
            else f"factures/{fic_facture}"
        )
    chemin_preuve = (
        f"factures/PreuvesPaiements/{id_ticket}/{fic_preuve}"
        if fic_preuve else ""
    )

    return {
        "found": True,
        "enseigne": (r.get("LibFacture") or "").strip(),
        "num_commande": (r.get("NumCommande") or "").strip(),
        "descriptif": _descriptif(id_ticket),
        "montant": float(r.get("Montant") or 0),
        "date_achat": date_only_to_iso(r.get("DateAchat")),
        "vendeur_nom": vendeur_nom,
        "id_salarie": str(id_salarie) if id_salarie else "",
        "id_ste": str(id_ste) if id_ste else "",
        "fic_facture": fic_facture,
        "fic_preuve": fic_preuve,
        "chemin_facture": chemin_facture,
        "chemin_preuve": chemin_preuve,
        "id_commande": str(id_commande) if id_commande else "",
        "transferee": bool(id_commande),
        "societes": _societes(),
        "modes_paiement": MODES_PAIEMENT,
    }


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    action = str(payload.get("action") or "")
    now = _now_windev()
    bo = get_connection("ticket_bo")

    # --- Enregistrer les champs (Enseigne / N° Cde / Montant / Date / Descr) ---
    if action == "enregistrer":
        try:
            bo.query(
                """UPDATE TK_DemandeFacturation SET LibFacture = ?,
                    NumCommande = ?, Montant = ?, DateAchat = ?,
                    Descriptif = ?, ModifDate = ?, ModifOp = ?,
                    ModifElem = 'modif'
                WHERE IDTK_Liste = ?""",
                (
                    str(payload.get("enseigne") or "").strip(),
                    str(payload.get("num_commande") or "").strip(),
                    float(payload.get("montant") or 0),
                    iso_to_date_only(payload.get("date_achat")),
                    str(payload.get("descriptif") or "").strip(),
                    now, int(user_id), int(id_ticket),
                ),
            )
        except Exception as e:
            return {"ok": False, "error": f"enregistrer : {e}"}
        return {"ok": True}

    # --- Transférer dans le module facture ---
    if action == "transferer":
        r = _demande(id_ticket)
        if not r:
            return {"ok": False, "error": "Demande introuvable"}
        if _clean_id(_to_int(r.get("IDCommande"))):
            return {"ok": False, "error": "Déjà transférée dans les factures"}
        nom_fic = (r.get("FicFacture") or "").strip()
        montant = float(payload.get("montant") or r.get("Montant") or 0)
        enseigne = str(payload.get("enseigne") or r.get("LibFacture") or "").strip()
        num_cde = str(payload.get("num_commande") or r.get("NumCommande") or "").strip()
        descriptif = str(payload.get("descriptif") or _descriptif(id_ticket)).strip()
        date_achat = iso_to_date_only(
            payload.get("date_achat") or date_only_to_iso(r.get("DateAchat"))
        )
        mode_paiement = str(payload.get("mode_paiement") or "").strip()
        # Vendeur (OPCREA) + société
        id_salarie = _to_int(payload.get("id_salarie"))
        id_ste = _to_int(payload.get("id_ste")) or _id_societe_salarie(id_salarie)

        id_cde = int(now)
        div = get_connection("divers")
        # 1. Commande
        try:
            div.query(
                """INSERT INTO Commande
                (IDCommande, DateAchat, OpéAchat, NumCommande, MontantTTC,
                 Enseigne, DESCRIPTION, ModePaiement, BénéService, BénéID,
                 IdSte, ModifDate, ModifOP, ModifELEM)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, 'new')""",
                (
                    id_cde, date_achat, int(id_salarie), num_cde, montant,
                    enseigne, descriptif, mode_paiement, int(id_salarie),
                    int(id_ste), now, int(user_id),
                ),
            )
        except Exception as e:
            return {"ok": False, "error": f"Commande : {e}"}

        # 2. Déplacement FTP de la facture : factures/<nom> -> factures/<idCde>/<nom>
        if nom_fic:
            try:
                _ftp_move(
                    f"{_FTP_FACTURES}/{nom_fic}",
                    f"{_FTP_FACTURES}/{id_cde}", nom_fic,
                )
            except Exception:
                pass  # non bloquant (la facture peut déjà être ailleurs)

        # 3. Commande_facture
        try:
            div.query(
                """INSERT INTO Commande_facture
                (IDCommande_facture, IDCommande, MontantTTC, nom_Fic,
                 DateAjout, ModifDate, ModifOP, ModifELEM)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'new')""",
                (int(now), id_cde, montant, nom_fic, now, now, int(user_id)),
            )
        except Exception as e:
            return {"ok": False, "error": f"Commande_facture : {e}"}

        # 4. TK_DemandeFacturation.IDCommande
        try:
            bo.query(
                """UPDATE TK_DemandeFacturation SET IDCommande = ?,
                    ModifDate = ?, ModifOp = ?, ModifElem = 'modif'
                WHERE IDTK_Liste = ?""",
                (id_cde, now, int(user_id), int(id_ticket)),
            )
        except Exception as e:
            return {"ok": False, "error": f"MAJ demande : {e}"}

        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True, "id_commande": str(id_cde)}

    return {"ok": False, "error": "Action non disponible"}


def get_file(id_ticket: int, name: str) -> tuple[bytes, str]:
    """Télécharge un fichier sous /OMAYA/<name> (chemin relatif transmis
    par le front : factures/... ou factures/PreuvesPaiements/...)."""
    rel = name.lstrip("/")
    data = _ftp_download(f"/OMAYA/{rel}")
    if data is None:
        raise FileNotFoundError("Document introuvable sur le FTP")
    fic = rel.rsplit("/", 1)[-1]
    return data, _mime_for(fic)


def upload_file(id_ticket: int, filename: str, content: bytes) -> dict:
    """« Charger la preuve de virement » : upload image vers
    /OMAYA/factures/PreuvesPaiements/<idTicket>/ + MAJ FicPreuveVirement."""
    if not content:
        return {"ok": False, "error": "Fichier vide"}
    nom = filename.rsplit("/", 1)[-1] or "preuve.jpg"
    now = _now_windev()
    dst_dir = f"{_FTP_FACTURES}/PreuvesPaiements/{id_ticket}"
    try:
        ftp = _ftp_connect()
        try:
            _ftp_mkdirs(ftp, dst_dir)
            ftp.storbinary(f"STOR {nom}", io.BytesIO(content))
        finally:
            ftp.quit()
    except Exception as e:
        return {"ok": False, "error": f"Upload FTP : {e}"}
    try:
        get_connection("ticket_bo").query(
            "UPDATE TK_DemandeFacturation SET FicPreuveVirement = ?, "
            "ModifDate = ? WHERE IDTK_Liste = ?",
            (nom, now, int(id_ticket)),
        )
    except Exception as e:
        return {"ok": False, "error": f"MAJ preuve : {e}"}
    return {"ok": True, "fic_preuve": nom,
            "chemin_preuve": f"factures/PreuvesPaiements/{id_ticket}/{nom}"}
