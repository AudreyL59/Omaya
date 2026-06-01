"""FI_DPAEDistrib (types 29 Nouveau Vendeur Distrib + 30 Intégration
Nouveau Distrib).

Formulaire d'intégration d'un distributeur : état civil, coordonnées,
produits proposés (champ LNAISS détourné en code 0/1), équipe
(organigramme), documents DPAE et demandes de code vendeur.

Tables :
  - TK_DemandeDPAE_Distrib : base ticket_bo (état civil + coordonnées,
    LNAISS = code produits, idorganigramme)
  - TK_DemandeDPAE_DistribPhoto : base ticket_bo (documents, FTP PhotoDPAE)
  - TK_DemandeCodeVendeur : base ticket_bo (demandes de code générées)
  - Partenaire : base adv (libellés partenaires)
  - organigramme : base rh (équipe)
  - TK_Liste / TK_Statut : base ticket (statut des demandes de code)

Fichiers : FTP /OMAYA/PhotoDPAE/<NomFichier>.

NB : « Générer Tk Demande de Code » (création ticket type 38) et
« Convertir en fiche salarié » sont en TODO (modules dépendants).
"""

import ftplib
import io

from app.core.config import (
    FTP_HOST,
    FTP_PASSWORD,
    FTP_PHOTO_DPAE_PATH,
    FTP_USER,
)
from app.core.database import get_connection
from app.core.database.pg import get_pg_connection  # noqa: F401  # phase 1 hybride : tout reste HFSQL (read-modify-write critiques)
from app.shared.notifications.sms import envoi_sms

from ..service import (
    _clean_id,
    _now_windev,
    _to_int,
    _windev_to_iso,
    date_only_to_iso,
    iso_to_date_only,
    list_statuts,
)

CIVILITE = {1: "M.", 2: "Mme"}
# Ordre = position du caractère dans LNAISS (cf. ZoneRépétée WinDev)
PRODUITS = ["ENI", "SFR", "ASSU", "PRESSE", "OHM Énergie"]

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


def _ftp_download(nom_fichier: str) -> bytes | None:
    """Télécharge /OMAYA/PhotoDPAE/<nom_fichier> depuis le FTP."""
    if not nom_fichier:
        return None
    try:
        ftp = ftplib.FTP(timeout=15)
        ftp.encoding = "latin-1"
        ftp.connect(FTP_HOST, 21)
        ftp.login(FTP_USER, FTP_PASSWORD)
        buf = io.BytesIO()
        ftp.retrbinary(
            f"RETR {FTP_PHOTO_DPAE_PATH.rstrip('/')}/{nom_fichier.lstrip('/')}",
            buf.write,
        )
        ftp.quit()
        return buf.getvalue()
    except Exception:
        return None


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _decode_produits(lnaiss) -> list[dict]:
    """LNAISS (détourné) → liste des produits avec leur état coché.

    Seulement si LNAISS est une chaîne de 0/1 (sinon = lieu de
    naissance des anciens enregistrements → tout décoché)."""
    s = (lnaiss or "").strip()
    is_code = bool(s) and all(c in "01" for c in s) and len(s) <= len(PRODUITS)
    return [
        {
            "nom": PRODUITS[i],
            "actif": bool(is_code and i < len(s) and s[i] == "1"),
        }
        for i in range(len(PRODUITS))
    ]


def _encode_produits(actifs: list[bool]) -> str:
    """Liste de booléens (ordre PRODUITS) → chaîne 0/1 pour LNAISS."""
    return "".join(
        "1" if (i < len(actifs) and actifs[i]) else "0"
        for i in range(len(PRODUITS))
    )


def _equipe_label(id_orga: int) -> str:
    if not id_orga:
        return ""
    try:
        r = get_connection("rh").query_one(
            "SELECT idorganigramme, Lib_ORGA FROM organigramme "
            "WHERE idorganigramme = ?",
            (int(id_orga),),
        )
        return ((r.get("Lib_ORGA") if r else "") or "").strip()
    except Exception:
        return ""


def _doc_nom(id_doc: int) -> str:
    """NOM (mémo texte) d'un document (lecture isolée)."""
    try:
        r = get_connection("ticket_bo").query_one(
            "SELECT IDTK_DemandeDPAEPhoto, NOM FROM TK_DemandeDPAE_DistribPhoto "
            "WHERE IDTK_DemandeDPAEPhoto = ?",
            (int(id_doc),),
        )
        return ((r.get("NOM") if r else "") or "").strip()
    except Exception:
        return ""


def _documents(id_ticket: int) -> list[dict]:
    """Documents TK_DemandeDPAE_DistribPhoto (base ticket_bo)."""
    bo = get_connection("ticket_bo")
    try:
        rows = bo.query(
            "SELECT IDTK_DemandeDPAEPhoto, NomFichier, IDTK_TypePhotoDPAE "
            "FROM TK_DemandeDPAE_DistribPhoto WHERE IDTK_Liste = ? "
            "AND ModifElem NOT LIKE '%suppr%' ORDER BY NomFichier ASC",
            (int(id_ticket),),
        )
    except Exception:
        return []
    out = []
    for r in rows or []:
        idp = _clean_id(_to_int(r.get("IDTK_DemandeDPAEPhoto")))
        if not idp:
            continue
        out.append({
            "id": str(idp),
            "nom_fichier": (r.get("NomFichier") or "").strip(),
            "nom": _doc_nom(idp),
        })
    return out


def _partenaires_map() -> dict[int, str]:
    try:
        rows = get_connection("adv").query(
            "SELECT IDPartenaire, Lib_Partenaire FROM Partenaire"
        )
    except Exception:
        return {}
    return {
        _to_int(r.get("IDPartenaire")): (r.get("Lib_Partenaire") or "").strip()
        for r in rows or []
    }


def _partenaires_portail() -> list[dict]:
    """Combo « Choisir un partenaire » : partenaires ayant un portail
    partenaire actif. Cross-DB : PortailPartenaire (base recrutement) →
    Lib_Partenaire (base adv). Le JOIN WinDev n'est pas faisable via le
    bridge (bases différentes)."""
    try:
        rows = get_connection("recrutement").query(
            "SELECT IDPartenaire FROM PortailPartenaire "
            "WHERE ModifElem NOT LIKE '%suppr%' AND IsActif = 1"
        )
    except Exception:
        return []
    ids = {_to_int(r.get("IDPartenaire")) for r in rows or []}
    ids = {i for i in ids if i}
    if not ids:
        return []
    parts = _partenaires_map()
    out = [
        {"id": str(i), "lib": parts.get(i, "")}
        for i in ids if parts.get(i)
    ]
    out.sort(key=lambda p: p["lib"])
    return out


def _demandes_code(id_ticket: int) -> list[dict]:
    """Demandes de code vendeur liées à ce ticket (TK_DemandeCodeVendeur
    base ticket_bo) + libellé partenaire (adv) + statut (ticket)."""
    bo = get_connection("ticket_bo")
    try:
        rows = bo.query(
            "SELECT IDTK_Liste, IDPartenaire, ModifDate FROM "
            "TK_DemandeCodeVendeur WHERE IdElem = ? "
            "AND ModifElem NOT LIKE '%suppr%'",
            (int(id_ticket),),
        )
    except Exception:
        return []
    rows = rows or []
    if not rows:
        return []
    parts = _partenaires_map()
    statuts = {s["id_statut"]: s["lib_statut"] for s in list_statuts()}
    tk = get_connection("ticket")
    out = []
    for r in rows:
        id_liste = _clean_id(_to_int(r.get("IDTK_Liste")))
        id_part = _to_int(r.get("IDPartenaire"))
        id_statut = 0
        try:
            st = tk.query_one(
                "SELECT IDTK_Liste, IDTK_Statut FROM TK_Liste "
                "WHERE IDTK_Liste = ?",
                (int(id_liste),),
            )
            id_statut = _to_int(st.get("IDTK_Statut")) if st else 0
        except Exception:
            pass
        out.append({
            "partenaire": parts.get(id_part, ""),
            "statut": statuts.get(id_statut, ""),
            "date": _windev_to_iso(r.get("ModifDate")),
        })
    return out


# --------------------------------------------------------------------
# load / save / get_file
# --------------------------------------------------------------------

def load(id_ticket: int) -> dict:
    bo = get_connection("ticket_bo")
    r = bo.query_one(
        "SELECT IDTK_Liste, IDTK_DemandeDPAE_Distrib, Civilité, NOM, "
        "NOM_MARITAL, PRENOM, DNAISS, ADRESSE1, Cp, VILLE, GSM, MAIL, "
        "LNAISS, idorganigramme FROM TK_DemandeDPAE_Distrib "
        "WHERE IDTK_Liste = ?",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}
    id_orga = _clean_id(_to_int(r.get("idorganigramme")))
    return {
        "found": True,
        "civilite": _to_int(r.get("Civilité")) or 1,
        "nom": (r.get("NOM") or "").strip(),
        "nom_marital": (r.get("NOM_MARITAL") or "").strip(),
        "prenom": (r.get("PRENOM") or "").strip(),
        "date_naiss": date_only_to_iso(r.get("DNAISS")),
        "adresse": (r.get("ADRESSE1") or "").strip(),
        "cp": (r.get("Cp") or "").strip(),
        "ville": (r.get("VILLE") or "").strip(),
        "gsm": (r.get("GSM") or "").strip(),
        "mail": (r.get("MAIL") or "").strip(),
        "produits": _decode_produits(r.get("LNAISS")),
        "id_equipe": str(id_orga) if id_orga else "",
        "equipe_label": _equipe_label(id_orga),
        "documents": _documents(id_ticket),
        "demandes_code": _demandes_code(id_ticket),
        "partenaires": _partenaires_portail(),
    }


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    action = str(payload.get("action") or "")
    now = _now_windev()
    bo = get_connection("ticket_bo")

    # --- Enregistrer le ticket (état civil + coords + produits + équipe) ---
    if action == "enregistrer":
        civilite = _to_int(payload.get("civilite")) or 1
        lnaiss = _encode_produits(
            [bool(x) for x in (payload.get("produits") or [])]
        )
        id_equipe = _to_int(payload.get("id_equipe"))
        try:
            bo.query(
                """UPDATE TK_DemandeDPAE_Distrib SET Civilité = ?, NOM = ?,
                    NOM_MARITAL = ?, PRENOM = ?, DNAISS = ?, ADRESSE1 = ?,
                    Cp = ?, VILLE = ?, GSM = ?, MAIL = ?, LNAISS = ?,
                    idorganigramme = ?, ModifOP = 0, ModifDate = ?,
                    ModifELEM = 'modif'
                WHERE IDTK_Liste = ?""",
                (
                    civilite,
                    str(payload.get("nom") or "").strip(),
                    str(payload.get("nom_marital") or "").strip(),
                    str(payload.get("prenom") or "").strip(),
                    iso_to_date_only(payload.get("date_naiss")),
                    str(payload.get("adresse") or "").strip(),
                    str(payload.get("cp") or "").strip(),
                    str(payload.get("ville") or "").strip(),
                    str(payload.get("gsm") or "").strip(),
                    str(payload.get("mail") or "").strip(),
                    lnaiss, int(id_equipe), now, int(id_ticket),
                ),
            )
        except Exception as e:
            return {"ok": False, "error": f"enregistrer : {e}"}
        return {"ok": True}

    # --- Document non conforme : soft-delete + SMS au candidat ---
    if action == "doc_non_conforme":
        id_doc = _to_int(payload.get("id_doc"))
        if not id_doc:
            return {"ok": False, "error": "Document manquant"}
        nom_doc = _doc_nom(id_doc)
        try:
            bo.query(
                """UPDATE TK_DemandeDPAE_DistribPhoto SET ModifDate = ?,
                    ModifOP = ?, ModifELEM = 'suppr'
                WHERE IDTK_DemandeDPAEPhoto = ?""",
                (now, int(user_id), int(id_doc)),
            )
        except Exception as e:
            return {"ok": False, "error": f"doc_non_conforme : {e}"}

        # SMS au candidat (GSM de la demande)
        sms_result = ""
        try:
            d = bo.query_one(
                "SELECT IDTK_Liste, GSM FROM TK_DemandeDPAE_Distrib "
                "WHERE IDTK_Liste = ?",
                (int(id_ticket),),
            )
            gsm = ((d.get("GSM") if d else "") or "")
            for ch in (".", " ", "/", "-"):
                gsm = gsm.replace(ch, "")
            if gsm:
                texte = (
                    "Bonjour, le document suivant a été jugé non-conforme "
                    "par le service BO, merci de le recharger à nouveau.\n"
                    f"   - {nom_doc}\nMerci"
                )
                sms_result = envoi_sms(texte, gsm, "", "DPAEDistrib")
        except Exception as e:
            sms_result = f"SMS non envoyé : {e}"

        return {"ok": True, "sms_result": sms_result,
                "documents": _documents(id_ticket)}

    return {"ok": False, "error": "Action non disponible"}


def get_file(id_ticket: int, name: str) -> tuple[bytes, str]:
    """Document DPAE distrib (FTP /OMAYA/PhotoDPAE/<name>)."""
    data = _ftp_download(name)
    if data is None:
        raise FileNotFoundError("Document introuvable sur le FTP")
    return data, _mime_for(name)
