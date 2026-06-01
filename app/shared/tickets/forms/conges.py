"""FI_Congés (type 13 — Demande de congés).

Transposition de la fenêtre interne WinDev FI_Congés.

  - TK_DemandeConges (ticket_rh) : TypeCongés, IDTypeAbsence,
    PériodeCongés ("Période"/"Journée"/"AM"/"PM"), DateDébut, DateFin,
    Motifs (mémo texte), SignatureDemandeur (mémo binaire), SignatureResp
    (mémo binaire, stocke le b64 de la signature manuscrite).
  - TypeAbsence (rh) pour le combo « Absence pour Omaya ».
  - absence (rh) : insertion lors de la validation finale
    (IdAbsence, IDSalarie, dates, NBJ, NBJ_OUVRES, nbSamedi,
    IDTypeAbsence, Période texte « AAAA-AAAA+1 »).

« Validation finale » : enregistre la signature, génère un PDF
récapitulatif (équivalent EtatDemandeCongé), upload FTP dossier
salarié, crée la ligne absence, envoie un SMS si demandé, clôture le
ticket (statut 4).
"""

import base64
import io
from datetime import date, datetime, timedelta

from app.core.config import FTP_GESTION_RH_PATH
from app.core.database import get_connection
from app.core.database.pg import get_pg_connection
from app.shared.notifications.sms import envoi_sms

from ..service import (
    _clean_id,
    _icone_to_data_url,
    _now_windev,
    _to_int,
    ajout_histo_tk,
    date_only_to_iso,
    iso_to_date_only,
    load_salaries_minimal,
    maj_op_traitement_ticket,
)

# cf. init WinDev : mapping TypeCongés -> IDTypeAbsence par défaut
_DEFAULT_TYPE_ABS = {
    "Maladie": 2,
    "Congés payés": 4,
    "Congés sans solde": 5,
}
_DEFAULT_TYPE_ABS_AUTRE = 14


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _types_absence() -> list[dict]:
    try:
        db = get_pg_connection("rh")
        return [
            {
                "id": _to_int(r.get("id_type_absence")),
                "lib": (r.get("lib_absence") or "").strip(),
            }
            for r in db.query(
                "SELECT id_type_absence, lib_absence FROM pgt_type_absence "
                "ORDER BY lib_absence"
            )
        ]
    except Exception:
        return []


def _memo(db, id_ticket: int, field: str) -> str:
    try:
        r = db.query_one(
            f"SELECT IDTK_Liste, {field} FROM TK_DemandeConges "
            f"WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        return ((r.get(field) if r else "") or "").strip()
    except Exception:
        return ""


def _signature_img_url(id_ticket: int, field: str) -> str:
    """Mémo binaire (jpg/png) -> data URL. Le bridge encode en base64.
    WinDev stocke parfois aussi le b64 de l'image (Encode + assignation
    à un mémo binaire) -> on tente d'abord la lecture brute, puis un
    décodage si le payload re-décodé démarre par /9j/ (JPEG) ou iVBOR."""
    try:
        db = get_connection("ticket_rh")
        r = db.query_one(
            f"SELECT IDTK_Liste, {field} FROM TK_DemandeConges "
            f"WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        v = r.get(field) if r else None
        if not v:
            return ""
        url = _icone_to_data_url(v)
        if url:
            return url
        # WinDev stocke parfois directement le b64 dans le mémo binaire
        s = v.decode("latin-1", "ignore") if isinstance(v, bytes) else str(v)
        s = s.strip()
        if s.startswith("/9j/"):
            return f"data:image/jpeg;base64,{s}"
        if s.startswith("iVBOR"):
            return f"data:image/png;base64,{s}"
        return ""
    except Exception:
        return ""


def _salarie_info(id_salarie: int) -> dict:
    """nom/prénom (rh.salarie), gsm (rh.salarie_coordonnées),
    activite (rh.salarie_embauche.EnActivité)."""
    if not id_salarie:
        return {}
    i = load_salaries_minimal({id_salarie}).get(id_salarie, {})
    out: dict = {
        "nom": i.get("nom", ""),
        "prenom": i.get("prenom", ""),
        "gsm": "",
        "activite": False,
    }
    rh = get_connection("rh")
    try:
        c = rh.query_one(
            "SELECT IDSalarie, TélMob FROM salarie_coordonnées "
            "WHERE IDSalarie = ?",
            (int(id_salarie),),
        )
        out["gsm"] = ((c.get("TélMob") if c else "") or "").strip()
    except Exception:
        pass
    try:
        e = rh.query_one(
            "SELECT IDSalarie, EnActivité FROM salarie_embauche "
            "WHERE IDSalarie = ?",
            (int(id_salarie),),
        )
        out["activite"] = bool(e.get("EnActivité")) if e else False
    except Exception:
        pass
    return out


def _nom_complet(info: dict) -> str:
    p = info.get("prenom", "")
    return (
        f"{info.get('nom', '')} {p[:1].upper() + p[1:].lower() if p else ''}"
        .strip()
    )


def _parse_iso_date(s: str) -> date | None:
    try:
        return datetime.fromisoformat((s or "")[:10]).date()
    except Exception:
        return None


def _periode_scolaire(d: date) -> str:
    """cf. WinDev : avant juillet -> AAAA-1/AAAA, sinon AAAA/AAAA+1."""
    if d.month <= 6:
        return f"{d.year - 1}-{d.year}"
    return f"{d.year}-{d.year + 1}"


def _nb_ouvres(deb: date, fin: date) -> int:
    n = 0
    d = deb
    while d <= fin:
        if d.weekday() < 5:
            n += 1
        d += timedelta(days=1)
    return n


def _nb_samedi(deb: date, fin: date) -> int:
    n = 0
    d = deb
    while d <= fin:
        if d.weekday() == 5:
            n += 1
        d += timedelta(days=1)
    return n


def _periode_text(periode_conges: str, deb: date | None, fin: date | None) -> str:
    p = (periode_conges or "").strip()
    df = deb.strftime("%d/%m/%Y") if deb else ""
    ff = fin.strftime("%d/%m/%Y") if fin else ""
    if p == "Période":
        return f" du {df} au {ff}"
    suf = ""
    if p == "AM":
        suf = " (matin)"
    elif p == "PM":
        suf = " (après-midi)"
    else:
        suf = " (journée entière)"
    return f" pour le {df}{suf}"


def _poste_lib(id_salarie: int) -> str:
    """Fonction = '<Catégorie> - <Lib_Poste>' via salarie_embauche +
    TypePoste (base rh)."""
    if not id_salarie:
        return ""
    try:
        rh = get_connection("rh")
        e = rh.query_one(
            "SELECT IDSalarie, IdTypePoste FROM salarie_embauche "
            "WHERE IDSalarie = ?",
            (int(id_salarie),),
        )
        idp = _to_int(e.get("IdTypePoste")) if e else 0
        if not idp:
            return ""
        t = rh.query_one(
            "SELECT IdTypePoste, Catégorie, Lib_Poste FROM TypePoste "
            "WHERE IdTypePoste = ?",
            (int(idp),),
        )
        if not t:
            return ""
        cat = (t.get("Catégorie") or "").strip()
        lib = (t.get("Lib_Poste") or "").strip()
        return f"{cat} - {lib}" if (cat and lib) else (lib or cat)
    except Exception:
        return ""


def _service_lib(id_salarie: int) -> str:
    """Service = 1ʳᵉ organigramme du salarié (salarie_organigramme +
    organigramme.Lib_ORGA, base rh)."""
    if not id_salarie:
        return ""
    try:
        rh = get_connection("rh")
        so = rh.query_one(
            "SELECT IDSalarie, idorganigramme FROM salarie_organigramme "
            "WHERE IDSalarie = ?",
            (int(id_salarie),),
        )
        ido = _to_int(so.get("idorganigramme")) if so else 0
        if not ido:
            return ""
        o = rh.query_one(
            "SELECT idorganigramme, Lib_ORGA FROM organigramme "
            "WHERE idorganigramme = ?",
            (int(ido),),
        )
        return (o.get("Lib_ORGA") or "").strip() if o else ""
    except Exception:
        return ""


def _societe_info(id_salarie: int) -> dict:
    """RaisonSociale + LOGO (mémo binaire) de la société du salarié,
    via salarie_embauche.IdSte -> societe (base rh). Le LOGO est lu en
    SELECT isolé (clé + mémo binaire) pour éviter le bug bridge JSON."""
    if not id_salarie:
        return {"name": "", "logo": None}
    rh = get_connection("rh")
    id_ste = 0
    try:
        e = rh.query_one(
            "SELECT IDSalarie, IdSte FROM salarie_embauche "
            "WHERE IDSalarie = ?",
            (int(id_salarie),),
        )
        id_ste = _to_int(e.get("IdSte")) if e else 0
    except Exception:
        return {"name": "", "logo": None}
    if not id_ste:
        return {"name": "", "logo": None}
    name = ""
    try:
        s = rh.query_one(
            "SELECT IdSte, RaisonSociale FROM societe WHERE IdSte = ?",
            (int(id_ste),),
        )
        name = (s.get("RaisonSociale") or "").strip() if s else ""
    except Exception:
        pass
    logo_bytes: bytes | None = None
    try:
        sl = rh.query_one(
            "SELECT IdSte, LOGO FROM societe WHERE IdSte = ?",
            (int(id_ste),),
        )
        v = sl.get("LOGO") if sl else None
        if v:
            if isinstance(v, bytes):
                logo_bytes = v
            else:
                s = str(v).strip()
                if s.startswith("data:"):
                    s = s.split(",", 1)[1]
                try:
                    logo_bytes = base64.b64decode(s)
                except Exception:
                    logo_bytes = None
    except Exception:
        pass
    return {"name": name, "logo": logo_bytes}


def _responsable_nom(id_ticket: int, fallback_user_id: int) -> str:
    """TK_Liste.OPDEST -> salarié, sinon l'utilisateur courant."""
    try:
        tk = get_connection("ticket").query_one(
            "SELECT IDTK_Liste, OPDEST FROM TK_Liste WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        op = _clean_id(_to_int(tk.get("OPDEST"))) if tk else 0
    except Exception:
        op = 0
    sid = op or _clean_id(_to_int(fallback_user_id))
    return _nom_complet(load_salaries_minimal({sid}).get(sid, {})) if sid else ""


def _fmt_windev_dt(s) -> str:
    """WinDev compact AAAAMMJJHHMMSS[mmm] -> 'JJ/MM/AAAA HH:MM:SS'."""
    d = "".join(c for c in str(s or "") if c.isdigit())
    if len(d) >= 14:
        return f"{d[6:8]}/{d[4:6]}/{d[0:4]} {d[8:10]}:{d[10:12]}:{d[12:14]}"
    if len(d) >= 8:
        return f"{d[6:8]}/{d[4:6]}/{d[0:4]}"
    return ""


def _fmt_iso_date(iso: str) -> str:
    if not iso or len(iso) < 10:
        return ""
    return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"


# --------------------------------------------------------------------
# PDF récapitulatif (équivalent EtatDemandeCongé)
# --------------------------------------------------------------------

def _build_pdf(
    salarie_nom: str, fonction: str, service: str, responsable: str,
    type_conges: str, date_debut: str, date_fin: str, motif: str,
    date_fait_salarie: str, signature_demandeur_url: str,
    date_fait_resp: str, signature_resp_bytes: bytes | None,
    societe_nom: str = "", societe_logo: bytes | None = None,
) -> bytes:
    """Reproduit le gabarit EtatDemandeCongé (PDF de référence) :
    titre, bandeau noir « Détails de la demande », champs avec
    soulignement, blocs Motifs, signature salarié, bandeau noir
    « Décision du responsable : Accordé », signature responsable."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # Header : logo + nom société (societe.LOGO + RaisonSociale) + titre
    from reportlab.lib.utils import ImageReader  # noqa: F811  (déjà importé)

    head_y = h - 18 * mm
    if societe_logo:
        try:
            c.drawImage(
                ImageReader(io.BytesIO(societe_logo)),
                25 * mm, head_y - 8 * mm, 16 * mm, 16 * mm,
                preserveAspectRatio=True, mask="auto",
            )
        except Exception:
            pass
    if societe_nom:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(45 * mm, head_y, societe_nom.upper())
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, head_y, "Demande de congé")

    def band(y_mm: float, label: str):
        c.setFillColorRGB(0, 0, 0)
        c.rect(20 * mm, y_mm * mm - 5, (w - 40 * mm), 8 * mm, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(w / 2, y_mm * mm - 1, label)
        c.setFillColorRGB(0, 0, 0)

    band(h / mm - 35, "Détails de la demande")

    def field(y_mm: float, label: str, val: str):
        c.setFont("Helvetica", 10)
        c.drawRightString(60 * mm, y_mm * mm, label)
        c.setFont("Helvetica", 10)
        c.drawString(63 * mm, y_mm * mm, val or "")
        c.setLineWidth(0.4)
        c.line(63 * mm, y_mm * mm - 1.5, w - 25 * mm, y_mm * mm - 1.5)

    yhdr = h / mm - 48
    field(yhdr, "Nom de l'employé :", salarie_nom)
    field(yhdr - 8, "Fonction :", fonction)
    field(yhdr - 16, "Service :", service)
    field(yhdr - 24, "Responsable :", responsable)

    # Type de congé + dates
    y2 = yhdr - 44
    field(y2, "Type de congé :", type_conges)
    c.setFont("Helvetica", 10)
    range_txt = f"Du {_fmt_iso_date(date_debut)} au {_fmt_iso_date(date_fin)}"
    c.drawString(63 * mm, (y2 - 8) * mm, range_txt)
    c.line(63 * mm, (y2 - 8) * mm - 1.5, w - 25 * mm, (y2 - 8) * mm - 1.5)

    # Motifs ou commentaires
    y3 = y2 - 22
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y3 * mm, "Motifs ou commentaires :")
    y_motif = y3 - 4
    for ln in (motif or "").splitlines()[:5]:
        c.drawString(20 * mm, y_motif * mm, ln[:120])
        y_motif -= 5
    c.setLineWidth(0.4)
    c.line(20 * mm, (y3 - 25) * mm, w - 20 * mm, (y3 - 25) * mm)

    # Signature salarié
    y_sig1 = y3 - 30
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(25 * mm, y_sig1 * mm, f"Fait le {date_fait_salarie}")
    c.drawRightString(w - 30 * mm, y_sig1 * mm, "Signature du salarié")
    if signature_demandeur_url:
        try:
            b64 = signature_demandeur_url.split(",", 1)[-1]
            img = ImageReader(io.BytesIO(base64.b64decode(b64)))
            c.drawImage(
                img, w - 80 * mm, (y_sig1 - 30) * mm, 55 * mm, 22 * mm,
                preserveAspectRatio=True, mask="auto",
            )
        except Exception:
            pass

    # Bandeau décision
    band(y_sig1 - 38, "Décision du responsable : Accordé")

    # Signature responsable
    y_sig2 = y_sig1 - 46
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(25 * mm, y_sig2 * mm, f"Fait le {date_fait_resp}")
    c.drawRightString(w - 30 * mm, y_sig2 * mm, "Signature du responsable")
    if signature_resp_bytes:
        try:
            img = ImageReader(io.BytesIO(signature_resp_bytes))
            c.drawImage(
                img, w - 80 * mm, (y_sig2 - 30) * mm, 55 * mm, 22 * mm,
                preserveAspectRatio=True, mask="auto",
            )
        except Exception:
            pass

    c.save()
    return buf.getvalue()


# --------------------------------------------------------------------
# load / save
# --------------------------------------------------------------------

def load(id_ticket: int) -> dict:
    db = get_connection("ticket_rh")
    r = db.query_one(
        """SELECT IDTK_Liste, IDTK_DemandeCongés, IDSalarie, PériodeCongés,
            DateDébut, DateFin, IDTypeAbsence
        FROM TK_DemandeConges WHERE IDTK_Liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}

    id_demande = _clean_id(_to_int(r.get("IDTK_DemandeCongés")))
    id_salarie = _clean_id(_to_int(r.get("IDSalarie")))
    type_conges = _memo(db, id_ticket, "TypeCongés")
    motif = _memo(db, id_ticket, "Motifs")
    id_type = _to_int(r.get("IDTypeAbsence"))

    # cf. init WinDev : si IDTypeAbsence=0, on dérive depuis TypeCongés
    if not id_type:
        id_type = _DEFAULT_TYPE_ABS.get(type_conges, _DEFAULT_TYPE_ABS_AUTRE)
        try:
            db.query(
                "UPDATE TK_DemandeConges SET IDTypeAbsence = ?, "
                "ModifDate = ?, ModifELEM = 'modif' WHERE IDTK_Liste = ?",
                (int(id_type), _now_windev(), int(id_ticket)),
            )
        except Exception:
            pass

    sal = _salarie_info(id_salarie)
    return {
        "found": True,
        "id_demande": str(id_demande) if id_demande else "",
        "id_salarie": str(id_salarie) if id_salarie else "",
        "salarie_nom": _nom_complet(sal),
        "type_conges": type_conges,
        "id_type_absence": id_type,
        "types_absence": _types_absence(),
        "periode_conges": (r.get("PériodeCongés") or "").strip(),
        "date_debut": date_only_to_iso(r.get("DateDébut")),
        "date_fin": date_only_to_iso(r.get("DateFin")),
        "motif": motif,
        "signature_demandeur_url": _signature_img_url(
            id_ticket, "SignatureDemandeur"
        ),
        "signature_resp_url": _signature_img_url(id_ticket, "SignatureResp"),
        "activite_salarie": sal.get("activite", False),
        "gsm_salarie": sal.get("gsm", ""),
    }


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    if str(payload.get("action") or "valider") != "valider":
        return {"ok": False, "error": "Action non disponible"}
    now = _now_windev()

    db = get_connection("ticket_rh")
    cur = db.query_one(
        """SELECT IDTK_Liste, IDTK_DemandeCongés, IDSalarie
        FROM TK_DemandeConges WHERE IDTK_Liste = ?""",
        (int(id_ticket),),
    )
    if not cur:
        return {"ok": False, "error": "Demande de congé introuvable"}
    id_demande = _clean_id(_to_int(cur.get("IDTK_DemandeCongés")))
    id_salarie = _clean_id(_to_int(cur.get("IDSalarie")))

    type_conges = str(payload.get("type_conges") or "").strip()
    id_type_abs = _to_int(payload.get("id_type_absence"))
    periode_conges = str(payload.get("periode_conges") or "").strip()
    motif = str(payload.get("motif") or "")
    date_debut = str(payload.get("date_debut") or "")
    date_fin = str(payload.get("date_fin") or "")
    envoyer_sms = bool(payload.get("envoyer_sms"))

    sig_b64 = str(payload.get("signature_b64") or "").strip()
    if sig_b64.startswith("data:"):
        sig_b64 = sig_b64.split(",", 1)[1]
    if not sig_b64:
        return {"ok": False, "error": "Signature manquante"}
    try:
        sig_bytes = base64.b64decode(sig_b64)
    except Exception:
        return {"ok": False, "error": "Signature invalide"}

    # Si IDTypeAbsence=0, on tente la résolution via TypeAbsence.Lib_Absence
    if not id_type_abs:
        try:
            tt = get_connection("rh").query_one(
                "SELECT IDTypeAbsence FROM TypeAbsence "
                "WHERE Lib_Absence = ?",
                (type_conges,),
            )
            id_type_abs = _to_int(tt.get("IDTypeAbsence")) if tt else _DEFAULT_TYPE_ABS_AUTRE
        except Exception:
            id_type_abs = _DEFAULT_TYPE_ABS_AUTRE

    # 1. Update TK_DemandeConges (champs + SignatureResp = b64 string,
    # comme WinDev qui assigne Encode(...,encodeBASE64) au mémo binaire).
    db.query(
        """UPDATE TK_DemandeConges SET
            TypeCongés = ?, IDTypeAbsence = ?, PériodeCongés = ?,
            DateDébut = ?, DateFin = ?, Motifs = ?, SignatureResp = ?,
            ModifDate = ?, ModifOP = ?, ModifELEM = 'modif'
        WHERE IDTK_Liste = ?""",
        (
            type_conges, int(id_type_abs), periode_conges,
            iso_to_date_only(date_debut), iso_to_date_only(date_fin),
            motif, sig_b64, now, int(user_id), int(id_ticket),
        ),
    )

    # 2. PDF récap + upload FTP dossier salarié (gabarit EtatDemandeCongé)
    sig_dem = _signature_img_url(int(id_ticket), "SignatureDemandeur")
    salarie_nom = _nom_complet(_salarie_info(id_salarie))
    fonction = _poste_lib(id_salarie)
    service = _service_lib(id_salarie)
    responsable = _responsable_nom(int(id_ticket), int(user_id))
    societe = _societe_info(id_salarie)
    # Date « Fait le » du salarié = création du ticket (TK_Liste.DATECREA)
    date_fait_sal = ""
    try:
        tkl = get_connection("ticket").query_one(
            "SELECT IDTK_Liste, DATECREA FROM TK_Liste WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        date_fait_sal = _fmt_windev_dt(tkl.get("DATECREA")) if tkl else ""
    except Exception:
        pass
    date_fait_resp = _fmt_windev_dt(now)
    try:
        pdf = _build_pdf(
            salarie_nom.upper(), fonction, service, responsable,
            type_conges, date_debut, date_fin, motif,
            date_fait_sal, sig_dem, date_fait_resp, sig_bytes,
            societe_nom=societe.get("name") or "",
            societe_logo=societe.get("logo"),
        )
        from .cttw_pdf import ftp_upload

        ftp_upload(
            f"{FTP_GESTION_RH_PATH}/{id_salarie}/Fiches_Salaires",
            f"{id_ticket}_DemandeConges.pdf", pdf,
        )
    except Exception:
        pass

    # 3. Insertion absence (rh)
    deb = _parse_iso_date(date_debut)
    fin = _parse_iso_date(date_fin)
    if deb and fin and deb <= fin:
        nbj = (fin - deb).days + 1
        try:
            get_connection("rh").query(
                """INSERT INTO absence
                (IdAbsence, IDSalarie, IDTypeAbsence, DateDEBUT, DateFIN,
                 NBJ, NBJ_OUVRES, nbSamedi, Période, ModifOP, ModifDate,
                 ModifELEM)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                (
                    int(now), int(id_salarie), int(id_type_abs),
                    iso_to_date_only(date_debut),
                    iso_to_date_only(date_fin),
                    nbj, _nb_ouvres(deb, fin), _nb_samedi(deb, fin),
                    _periode_scolaire(deb), int(user_id), now,
                ),
            )
        except Exception as e:
            return {"ok": False, "error": f"absence : {e}"}

    # 4. SMS au salarié si demandé + actif
    sms_result = ""
    if envoyer_sms:
        sal = _salarie_info(id_salarie)
        gsm = sal.get("gsm", "")
        for c in (".", " ", "/", "-"):
            gsm = gsm.replace(c, "")
        if sal.get("activite") and gsm:
            txt = (
                "Votre demande de congés,"
                + _periode_text(periode_conges, deb, fin)
                + ", a été acceptée."
            )
            try:
                sms_result = envoi_sms(txt, gsm, "", "OMAYA-Info")
            except Exception as e:
                sms_result = f"erreur : {e}"

    # 5. Clôture du ticket (statut 4)
    try:
        get_connection("ticket").query(
            """UPDATE TK_Liste SET
                Cloturée = 1, DateCloture = ?, IDTK_Statut = 4,
                modification = 1, opModif = ?, idModif = 0,
                TypeModif = 'TKSTATUT', ModifDate = ?, ModifOP = ?,
                ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (now, int(user_id), now, int(user_id), int(id_ticket)),
        )
        ajout_histo_tk(int(id_ticket), 4, int(user_id))
    except Exception:
        pass

    maj_op_traitement_ticket(int(id_ticket), int(user_id))
    return {"ok": True, "closed": True, "sms_result": sms_result}
