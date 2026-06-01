"""FI_DPAE (type 3 — DPAE) et type 21 (DPAE à venir).

Formulaire principal TK_DemandeDPAE (base ticket_dpae) : 1 enregistrement
par ticket (clé IDTK_Liste). État civil + coordonnées + contact urgence
+ embauche.

Lot 1 : formulaire principal uniquement. La sous-table DOCUMENTS
(TK_DemandeDPAEPhoto, photos via FTP) et les boutons métier (Démarrer
la DPAE / Attest Info / Régénérer) sont traités dans un lot ultérieur.
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
from app.core.database.pg import get_pg_connection

from ..service import (
    _clean_id,
    _now_windev,
    _str_id,
    _to_int,
    date_only_to_iso,
    get_organigramme_lib,
    iso_to_date_only,
    load_salaries_minimal,
)


def _ftp_download(nom_fichier: str) -> bytes | None:
    """Télécharge /OMAYA/PhotoDPAE/<nom_fichier> depuis le FTP en mémoire."""
    if not nom_fichier:
        return None
    try:
        ftp = ftplib.FTP(timeout=15)
        ftp.encoding = "latin-1"
        ftp.connect(FTP_HOST, 21)
        ftp.login(FTP_USER, FTP_PASSWORD)
        buf = io.BytesIO()
        ftp.retrbinary(
            f"RETR {FTP_PHOTO_DPAE_PATH.rstrip('/')}/{nom_fichier}",
            buf.write,
        )
        ftp.quit()
        return buf.getvalue()
    except Exception:
        return None


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
    """Retourne (octets, mime) d'un document DPAE (FTP)."""
    data = _ftp_download(name)
    if data is None:
        raise FileNotFoundError("Document introuvable sur le FTP")
    return data, _mime_for(name)

# Combos statiques (cf. SituationFam.Ajoute / Civilité WinDev)
SITUATION_FAM = {
    0: "---------",
    1: "Célibataire",
    2: "Marié(e)",
    3: "Veuf(ve)",
    4: "Pacsé(e)",
    5: "Divorcé(e)",
}


def load(id_ticket: int) -> dict:
    db = get_connection("ticket_dpae")
    r = db.query_one(
        """SELECT IDTK_Liste, Civilité, idorganigramme, NOM, NOM_MARITAL,
            PRENOM, NUMSS, CPAM, LNAISS, DEPNAISS, NUMCIN, NATIONALITE,
            DNAISS, Coopté, Coopteur, JOdirecte, JOCoopteur,
            ADRESSE1, VILLE, Cp, GSM, MAIL,
            URGNOM, URGLIEN, URGTEL,
            DateDébut, MUTUELLE, MUTDATE, TravailleurHandi,
            SituationFam, AvecEnfant, NbEnfants
        FROM TK_DemandeDPAE
        WHERE IDTK_Liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}

    civilite = _to_int(r.get("Civilité"))
    numss = (r.get("NUMSS") or "").strip()
    # Civilité auto (cf. WinDev) : 0 → déduite du 1er chiffre du NUMSS
    if civilite == 0 and numss:
        civilite = 1 if numss[:1] == "1" else 2
        try:
            db.query(
                "UPDATE TK_DemandeDPAE SET Civilité = ? WHERE IDTK_Liste = ?",
                (civilite, int(id_ticket)),
            )
        except Exception:
            pass

    id_equipe = _clean_id(_to_int(r.get("idorganigramme")))
    coopteur = _clean_id(_to_int(r.get("Coopteur")))
    jocoopteur = _clean_id(_to_int(r.get("JOCoopteur")))
    sal = load_salaries_minimal({coopteur, jocoopteur})

    def _nom(sid: int) -> str:
        i = sal.get(sid, {})
        p = i.get("prenom", "")
        return (
            f"{i.get('nom', '')} {p[:1].upper() + p[1:].lower() if p else ''}"
            .strip()
        )

    # Sous-table DOCUMENTS (TK_DemandeDPAEPhoto, fichiers sur le FTP).
    # Lecture pure (PG) ; les uploads de docs vont sur HFSQL via d'autres
    # routes -> lag tolere pour l'affichage.
    documents: list[dict] = []
    try:
        for d in get_pg_connection("ticket_dpae").query(
            """SELECT id_tk_demande_dpae_photo, nom, nom_fichier,
                id_tk_type_photo_dpae
            FROM pgt_tk_demande_dpae_photo
            WHERE id_tk_liste = ?
              AND modif_elem NOT LIKE '%suppr%'
            ORDER BY nom""",
            (int(id_ticket),),
        ):
            did = _clean_id(_to_int(d.get("id_tk_demande_dpae_photo")))
            if did:
                documents.append({
                    "id": str(did),
                    "nom": (d.get("nom") or "").strip(),
                    "nom_fichier": (d.get("nom_fichier") or "").strip(),
                    "id_type_photo": _to_int(d.get("id_tk_type_photo_dpae")),
                })
    except Exception:
        documents = []

    return {
        "found": True,
        "civilite": civilite,
        "id_equipe": str(id_equipe) if id_equipe else "",
        "lib_equipe": get_organigramme_lib(id_equipe) if id_equipe else "",
        "nom": (r.get("NOM") or "").strip(),
        "nom_marital": (r.get("NOM_MARITAL") or "").strip(),
        "prenom": (r.get("PRENOM") or "").strip(),
        "numss": numss,
        "cpam": (r.get("CPAM") or "").strip(),
        "lnaiss": (r.get("LNAISS") or "").strip(),
        "depnaiss": _to_int(r.get("DEPNAISS")),
        "numcin": (r.get("NUMCIN") or "").strip(),
        "nationalite": (r.get("NATIONALITE") or "").strip(),
        "dnaiss": date_only_to_iso(r.get("DNAISS")),
        "coopte": bool(r.get("Coopté")),
        "coopteur": str(coopteur) if coopteur else "",
        "coopteur_nom": _nom(coopteur),
        "jodirecte": bool(r.get("JOdirecte")),
        "jocoopteur": str(jocoopteur) if jocoopteur else "",
        "jocoopteur_nom": _nom(jocoopteur),
        "adresse1": (r.get("ADRESSE1") or "").strip(),
        "ville": (r.get("VILLE") or "").strip(),
        "cp": (r.get("Cp") or "").strip(),
        "gsm": (r.get("GSM") or "").strip(),
        "mail": (r.get("MAIL") or "").strip(),
        "urgnom": (r.get("URGNOM") or "").strip(),
        "urglien": (r.get("URGLIEN") or "").strip(),
        "urgtel": (r.get("URGTEL") or "").strip(),
        "date_debut": date_only_to_iso(r.get("DateDébut")),
        "mutuelle": bool(r.get("MUTUELLE")),
        "mutdate": date_only_to_iso(r.get("MUTDATE")),
        "travailleur_handi": bool(r.get("TravailleurHandi")),
        "situation_fam": _to_int(r.get("SituationFam")),
        "avec_enfant": bool(r.get("AvecEnfant")),
        "nb_enfants": _to_int(r.get("NbEnfants")),
        "situation_fam_options": SITUATION_FAM,
        "documents": documents,
    }


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    """ÉcranVersFichier : UPDATE TK_DemandeDPAE (tous champs éditables)
    + ModifOP/ModifDate/ModifELEM='modif'.
    """
    db = get_connection("ticket_dpae")
    exists = db.query_one(
        "SELECT IDTK_Liste FROM TK_DemandeDPAE WHERE IDTK_Liste = ?",
        (int(id_ticket),),
    )
    if not exists:
        return {"ok": False, "error": "DPAE introuvable pour ce ticket"}

    def s(k: str) -> str:
        return str(payload.get(k) or "").strip()

    def b(k: str) -> int:
        return 1 if payload.get(k) else 0

    def i(k: str) -> int:
        return _to_int(payload.get(k))

    now = _now_windev()
    db.query(
        """UPDATE TK_DemandeDPAE SET
            Civilité = ?, idorganigramme = ?, NOM = ?, NOM_MARITAL = ?,
            PRENOM = ?, NUMSS = ?, CPAM = ?, LNAISS = ?, DEPNAISS = ?,
            NUMCIN = ?, NATIONALITE = ?, DNAISS = ?,
            Coopté = ?, Coopteur = ?, JOdirecte = ?, JOCoopteur = ?,
            ADRESSE1 = ?, VILLE = ?, Cp = ?, GSM = ?, MAIL = ?,
            URGNOM = ?, URGLIEN = ?, URGTEL = ?,
            DateDébut = ?, MUTUELLE = ?, MUTDATE = ?, TravailleurHandi = ?,
            SituationFam = ?, AvecEnfant = ?, NbEnfants = ?,
            ModifOP = ?, ModifDate = ?, ModifELEM = 'modif'
        WHERE IDTK_Liste = ?""",
        (
            i("civilite"), i("id_equipe"), s("nom"), s("nom_marital"),
            s("prenom"), s("numss"), s("cpam"), s("lnaiss"), i("depnaiss"),
            s("numcin"), s("nationalite"), iso_to_date_only(payload.get("dnaiss")),
            b("coopte"), i("coopteur"), b("jodirecte"), i("jocoopteur"),
            s("adresse1"), s("ville"), s("cp"), s("gsm"), s("mail"),
            s("urgnom"), s("urglien"), s("urgtel"),
            iso_to_date_only(payload.get("date_debut")), b("mutuelle"),
            iso_to_date_only(payload.get("mutdate")), b("travailleur_handi"),
            i("situation_fam"), b("avec_enfant"), i("nb_enfants"),
            int(user_id), now, int(id_ticket),
        ),
    )
    return {"ok": True}
