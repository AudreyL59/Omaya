"""FI_UleasePVLivRest (type 35 — PV Livraison/Restitution ULEASE).

PV photographique d'un véhicule (livraison ou restitution) :
  - Plan 1 : grille de photos (modèle attendu / photo fournie), notation
    par étoiles (NoteEtat 1-5), observation. « Passer à l'étape suivante »
    actif quand toutes les photos sont notées → génère le PDF.
  - Plan 2 : aperçu du PDF généré (EtatUleasePVLivRest) + « Ce document
    est valide » (upload FTP dossier véhicule + salarie_docUlease + SMS +
    mail + clôture).

Tables :
  - TK_DemandeSignPVUlease / TK_DemandeSignPV_Photo : base ticket_rh
  - vehicule_Conducteur / vehicule_Fiche / Vehicule_TypeCapacité /
    conducteur / TypeCapacite_Photo : base **ulease** (module véhicules)
  - salarie / salarie_embauche / societe : base rh
  - salarie_docUlease : base rh ; TK_Liste : base ticket

Note : TK_DemandeSignPV_Photo.IDdemandeSignUleaseAuto contient en réalité
l'IDTK_Liste (cf. code WinDev). Photos = mémos binaires.
"""

import base64
import io

from app.core.config import FTP_HOST, FTP_PASSWORD, FTP_USER
from app.core.database import get_connection

from ..service import (
    _clean_id,
    _now_windev,
    _to_int,
    ajout_histo_tk,
    load_salaries_minimal,
    maj_op_traitement_ticket,
)


# --------------------------------------------------------------------
# Lecture mémos binaires (photos)
# --------------------------------------------------------------------

def _memo_img(db_key: str, table: str, key_field: str, key_value: int,
              field: str) -> bytes | None:
    try:
        r = get_connection(db_key).query_one(
            f"SELECT {key_field}, {field} FROM {table} WHERE {key_field} = ?",
            (int(key_value),),
        )
        v = r.get(field) if r else None
        if not v:
            return None
        return v if isinstance(v, bytes) else base64.b64decode(v)
    except Exception:
        return None


# --------------------------------------------------------------------
# Chaînage module véhicules (base ulease)
# --------------------------------------------------------------------

def _infos_pc(id_pc: int) -> dict:
    """IdPC (IDvehiculePC) → infos véhicule + conducteur (chaînage ulease
    + salarie rh)."""
    out = {
        "id_vehicule": 0, "modele": "", "immat": "", "lib_type": "",
        "id_salarie": 0, "nom_salarie": "",
    }
    if not id_pc:
        return out
    u = get_connection("ulease")
    try:
        pc = u.query_one(
            "SELECT IDvehiculePC, IDvehicule, IDConducteur FROM "
            "vehicule_Conducteur WHERE IDvehiculePC = ?",
            (int(id_pc),),
        )
    except Exception:
        pc = None
    if not pc:
        return out
    out["id_vehicule"] = _clean_id(_to_int(pc.get("IDvehicule")))
    id_cond = _clean_id(_to_int(pc.get("IDConducteur")))
    # Fiche véhicule
    try:
        f = u.query_one(
            "SELECT IDvehicule, MODELE, IMMAT, IDVehicule_TypeCapacité "
            "FROM vehicule_Fiche WHERE IDvehicule = ?",
            (int(out["id_vehicule"]),),
        )
        if f:
            out["modele"] = (f.get("MODELE") or "").strip()
            out["immat"] = (f.get("IMMAT") or "").strip()
            id_type = _to_int(f.get("IDVehicule_TypeCapacité"))
            if id_type:
                t = u.query_one(
                    "SELECT IDVehicule_TypeCapacité, Lib_Type FROM "
                    "Vehicule_TypeCapacité WHERE IDVehicule_TypeCapacité = ?",
                    (int(id_type),),
                )
                out["lib_type"] = ((t.get("Lib_Type") if t else "") or "").strip()
    except Exception:
        pass
    # Conducteur → salarié
    try:
        c = u.query_one(
            "SELECT IDconducteur, IDSalarie FROM conducteur "
            "WHERE IDconducteur = ?",
            (int(id_cond),),
        )
        out["id_salarie"] = _clean_id(_to_int(c.get("IDSalarie"))) if c else 0
    except Exception:
        pass
    if out["id_salarie"]:
        i = load_salaries_minimal({out["id_salarie"]}).get(out["id_salarie"], {})
        p = (i.get("prenom") or "")
        out["nom_salarie"] = (
            f"{i.get('nom', '')} {p[:1].upper() + p[1:].lower() if p else ''}"
        ).strip()
    return out


def _lib_photo(id_type_photo: int) -> str:
    if not id_type_photo:
        return ""
    try:
        r = get_connection("ulease").query_one(
            "SELECT IDTypeCapacite_Photo, LibPhoto FROM TypeCapacite_Photo "
            "WHERE IDTypeCapacite_Photo = ?",
            (int(id_type_photo),),
        )
        return ((r.get("LibPhoto") if r else "") or "").strip()
    except Exception:
        return ""


def _photos(id_ticket: int) -> list[dict]:
    """Photos du PV (TK_DemandeSignPV_Photo, ticket_rh). Le binaire n'est
    pas chargé (flag a_photo) — accès via get_file."""
    try:
        rows = get_connection("ticket_rh").query(
            "SELECT IDTK_DemandeSignPV_Photo, IDTypeCapacite_Photo, NoteEtat "
            "FROM TK_DemandeSignPV_Photo WHERE IDdemandeSignUleaseAuto = ? "
            "AND ModifElem <> 'suppr'",
            (int(id_ticket),),
        )
    except Exception:
        return []
    out = []
    for r in rows or []:
        idp = _clean_id(_to_int(r.get("IDTK_DemandeSignPV_Photo")))
        if not idp:
            continue
        id_type = _to_int(r.get("IDTypeCapacite_Photo"))
        out.append({
            "id": str(idp),
            "id_type_photo": id_type,
            "lib_photo": _lib_photo(id_type),
            "note": _to_int(r.get("NoteEtat")),
        })
    out.sort(key=lambda p: p["lib_photo"])
    return out


# --------------------------------------------------------------------
# load / save / get_file / print_pdf
# --------------------------------------------------------------------

def load(id_ticket: int) -> dict:
    db = get_connection("ticket_rh")
    r = db.query_one(
        "SELECT IDTK_Liste, IDdemandeSignPVUlease, IDSalarie, idDA, IdPC, "
        "contratValidé, contratSigné, IDSalarie_Ulease "
        "FROM TK_DemandeSignPVUlease WHERE IDTK_Liste = ?",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}
    titre = _memo_text(id_ticket, "TitreContrat")
    observations = _memo_text(id_ticket, "Observations")
    id_pc = _clean_id(_to_int(r.get("IdPC")))
    infos = _infos_pc(id_pc)
    photos = _photos(id_ticket)
    # NB : on ne charge PAS les binaires ici (lourd) — le front récupère
    # chaque image en lazy via get_file (404 = photo non recevable/vide).
    notees = sum(1 for p in photos if p["note"] > 0)

    is_livraison = "livraison" in titre.lower()
    return {
        "found": True,
        "titre_contrat": titre,
        "lib_pv": "PV Livraison" if is_livraison else "PV Restitution",
        "vehicule": " ".join(
            x for x in [infos["modele"], infos["immat"]] if x
        ) + (f" // {infos['lib_type']}" if infos["lib_type"] else ""),
        "conducteur": infos["nom_salarie"],
        "observations": observations,
        "photos": photos,
        "nb_notees": notees,
        "nb_total": len(photos),
        "toutes_notees": len(photos) > 0 and notees == len(photos),
        "contrat_valide": bool(r.get("contratValidé")),
        "contrat_signe": bool(r.get("contratSigné")),
    }


def _memo_text(id_ticket: int, field: str) -> str:
    try:
        r = get_connection("ticket_rh").query_one(
            f"SELECT IDTK_Liste, {field} FROM TK_DemandeSignPVUlease "
            "WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        return ((r.get(field) if r else "") or "").strip()
    except Exception:
        return ""


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    action = str(payload.get("action") or "")
    now = _now_windev()
    rh_tk = get_connection("ticket_rh")

    # --- Notation d'une photo ---
    if action == "note_photo":
        id_photo = _to_int(payload.get("id_photo"))
        note = max(0, min(5, _to_int(payload.get("note"))))
        if not id_photo:
            return {"ok": False, "error": "Photo manquante"}
        try:
            rh_tk.query(
                "UPDATE TK_DemandeSignPV_Photo SET NoteEtat = ?, "
                "ModifDate = ?, ModifOP = ?, ModifELEM = 'modif' "
                "WHERE IDTK_DemandeSignPV_Photo = ?",
                (note, now, int(user_id), int(id_photo)),
            )
        except Exception as e:
            return {"ok": False, "error": f"note_photo : {e}"}
        return {"ok": True}

    # --- Photo non recevable (vide la photo + la note) ---
    if action == "del_photo":
        id_photo = _to_int(payload.get("id_photo"))
        if not id_photo:
            return {"ok": False, "error": "Photo manquante"}
        try:
            rh_tk.query(
                "UPDATE TK_DemandeSignPV_Photo SET Photo = '', NoteEtat = 0, "
                "ModifDate = ?, ModifOP = ?, ModifELEM = 'modif' "
                "WHERE IDTK_DemandeSignPV_Photo = ?",
                (now, int(user_id), int(id_photo)),
            )
        except Exception as e:
            return {"ok": False, "error": f"del_photo : {e}"}
        return {"ok": True}

    # --- Sauvegarde de l'observation (avant génération PDF) ---
    if action == "save_obs":
        obs = str(payload.get("observations") or "")
        try:
            rh_tk.query(
                "UPDATE TK_DemandeSignPVUlease SET Observations = ?, "
                "ModifDate = ?, ModifOP = ?, ModifELEM = 'modif' "
                "WHERE IDTK_Liste = ?",
                (obs, now, int(user_id), int(id_ticket)),
            )
        except Exception as e:
            return {"ok": False, "error": f"save_obs : {e}"}
        return {"ok": True}

    # --- Ce document est valide : upload PDF + salarie_docUlease + clôture ---
    if action == "valider_signe":
        from app.shared.notifications.mail import envoi_mail_rh
        from app.shared.notifications.sms import envoi_sms

        from .cttw_pdf import ftp_upload

        cloturer = bool(payload.get("cloturer"))
        r = rh_tk.query_one(
            "SELECT IDTK_Liste, IDdemandeSignPVUlease, IDSalarie, idDA, IdPC, "
            "IDSalarie_Ulease FROM TK_DemandeSignPVUlease WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        if not r:
            return {"ok": False, "error": "PV introuvable"}
        id_pc = _clean_id(_to_int(r.get("IdPC")))
        id_da = _clean_id(_to_int(r.get("idDA")))
        id_demande = _clean_id(_to_int(r.get("IDdemandeSignPVUlease")))
        id_doc_ulease = _clean_id(_to_int(r.get("IDSalarie_Ulease")))
        infos = _infos_pc(id_pc)
        id_salarie = infos["id_salarie"]
        id_vehicule = infos["id_vehicule"]
        titre = _memo_text(id_ticket, "TitreContrat")
        type_cttw = 2 if "livraison" in titre.lower() else 3
        lib_pv = "PV_Livraison" if type_cttw == 2 else "PV_Restitution"
        nom_pdf = f"{id_ticket}_{lib_pv}.pdf"

        try:
            pdf = _generate_pv_pdf(int(id_ticket))
        except Exception as e:
            return {"ok": False, "error": f"Génération PDF : {e}"}
        try:
            ftp_upload(
                f"/OMAYA/Vehicules/{id_vehicule}/{id_pc}", nom_pdf, pdf
            )
        except Exception as e:
            return {"ok": False, "error": f"Upload FTP : {e}"}

        # salarie_docUlease (base rh)
        rh = get_connection("rh")
        try:
            target = id_doc_ulease or None
            if not target:
                ex = rh.query_one(
                    "SELECT IDsalarie_docUlease FROM salarie_docUlease "
                    "WHERE IDSalarie = ? AND RECU = 0 AND IDdocUleaseTYPE = ?",
                    (int(id_salarie), type_cttw),
                )
                if ex:
                    target = _clean_id(_to_int(ex.get("IDsalarie_docUlease")))
            if target:
                rh.query(
                    "UPDATE salarie_docUlease SET RECU = 1, RECUDATE = ?, "
                    "ModifOP = ?, ModifDate = ?, ModifELEM = 'modif' "
                    "WHERE IDsalarie_docUlease = ?",
                    (now, int(user_id), now, int(target)),
                )
            else:
                new_id = int(now)
                rh.query(
                    """INSERT INTO salarie_docUlease
                    (IDsalarie_docUlease, IDdocUleaseTYPE, IDSalarie, ID_DA,
                     DATE_Edition, RECU, RECUDATE, ModifOP, ModifDate,
                     ModifELEM)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, 'new')""",
                    (new_id, type_cttw, int(id_salarie), int(id_da),
                     str(id_demande), now, int(user_id), now),
                )
                rh_tk.query(
                    "UPDATE TK_DemandeSignPVUlease SET IDSalarie_Ulease = ?, "
                    "ModifDate = ?, ModifOP = ?, ModifELEM = 'modif' "
                    "WHERE IDTK_Liste = ?",
                    (new_id, now, int(user_id), int(id_ticket)),
                )
        except Exception as e:
            return {"ok": False, "error": f"salarie_docUlease : {e}"}

        # SMS + mail au salarié
        sms_result = ""
        try:
            c = rh.query_one(
                "SELECT IDSalarie, MAIL, TélMob FROM salarie_coordonnées "
                "WHERE IDSalarie = ?",
                (int(id_salarie),),
            )
            mail = (c.get("MAIL") or "").strip() if c else ""
            gsm = (c.get("TélMob") or "") if c else ""
            for ch in (".", " ", "/", "-"):
                gsm = gsm.replace(ch, "")
            if gsm:
                sms_result = envoi_sms(
                    "Votre document ULEASE est disponible sur votre espace "
                    "salarié (intranet ou appli Omaya).\nUne copie est "
                    f"envoyée sur votre email : {mail}",
                    gsm, "", "OMAYA-Info",
                )
            if mail:
                html = (
                    "<p>Bonjour,</p><p>Voici votre document ULEASE signé.</p>"
                    "<p>Cdt</p><p>Service RH</p>"
                )
                envoi_mail_rh(
                    "Document ULEASE Signé", html, [mail],
                    cci=["intranet@omaya.fr"], expediteur="intranet@omaya.fr",
                    attachments=[(nom_pdf, pdf)],
                )
        except Exception as e:
            sms_result = f"SMS/mail : {e}"

        if cloturer:
            try:
                get_connection("ticket").query(
                    """UPDATE TK_Liste SET Cloturée = 1, DateCloture = ?,
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
        return {"ok": True, "closed": cloturer, "sms_result": sms_result}

    return {"ok": False, "error": "Action non disponible"}


def get_file(id_ticket: int, name: str) -> tuple[bytes, str]:
    """Photos : name = 'f<id>' (photo fournie, TK_DemandeSignPV_Photo) ou
    'm<id>' (photo modèle, TypeCapacite_Photo)."""
    kind, _, raw = name.partition(":") if ":" in name else (name[:1], "", name[1:])
    if kind == "f":
        data = _memo_img("ticket_rh", "TK_DemandeSignPV_Photo",
                         "IDTK_DemandeSignPV_Photo", _to_int(raw), "Photo")
    elif kind == "m":
        data = _memo_img("ulease", "TypeCapacite_Photo",
                         "IDTypeCapacite_Photo", _to_int(raw), "Photo")
    else:
        data = None
    if data is None:
        raise FileNotFoundError("Photo introuvable")
    # détection sommaire du type image
    mime = "image/jpeg"
    if data[:8].startswith(b"\x89PNG"):
        mime = "image/png"
    return data, mime


def print_pdf(id_ticket: int, payload: dict) -> bytes:
    """Génère le PDF EtatUleasePVLivRest (Plan 2)."""
    return _generate_pv_pdf(int(id_ticket))


# --------------------------------------------------------------------
# Génération PDF (reportlab)
# --------------------------------------------------------------------

def _societe_salarie(id_salarie: int) -> dict:
    out = {"raison": "", "adresse": "", "cp": "", "ville": "",
           "siren": "", "guimmick": None}
    if not id_salarie:
        return out
    rh = get_connection("rh")
    try:
        e = rh.query_one(
            "SELECT TOP 1 IDSalarie, IdSte FROM salarie_embauche "
            "WHERE IDSalarie = ? ORDER BY DateDebut DESC",
            (int(id_salarie),),
        )
        id_ste = _clean_id(_to_int(e.get("IdSte"))) if e else 0
        if not id_ste:
            return out
        s = rh.query_one(
            "SELECT IdSte, RaisonSociale, SIREN, ADRESSE1, Cp, VILLE "
            "FROM societe WHERE IdSte = ?",
            (int(id_ste),),
        )
        if s:
            out["raison"] = (s.get("RaisonSociale") or "").strip()
            out["siren"] = (s.get("SIREN") or "").strip()
            out["adresse"] = (s.get("ADRESSE1") or "").strip()
            out["cp"] = (s.get("Cp") or "").strip()
            out["ville"] = (s.get("VILLE") or "").strip()
        out["guimmick"] = _memo_img("rh", "societe", "IdSte", id_ste, "GUIMMICK")
    except Exception:
        pass
    return out


def _shrink_image(data: bytes | None, max_px: int = 1000,
                  quality: int = 72) -> bytes | None:
    """Redimensionne + recompresse une image (JPEG) pour alléger le PDF."""
    if not data:
        return None
    try:
        from PIL import Image

        im = Image.open(io.BytesIO(data))
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        im.thumbnail((max_px, max_px))
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=quality, optimize=True)
        return out.getvalue()
    except Exception:
        return data


def _generate_pv_pdf(id_ticket: int) -> bytes:
    """PDF récap du PV : société, véhicule, conducteur, photos notées,
    observation, signatures. Images réduites (Pillow) pour la taille."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    d = load(id_ticket)
    if not d.get("found"):
        raise ValueError("PV introuvable")
    db = get_connection("ticket_rh")
    r = db.query_one(
        "SELECT IDTK_Liste, IDSalarie, IdPC FROM TK_DemandeSignPVUlease "
        "WHERE IDTK_Liste = ?",
        (int(id_ticket),),
    )
    id_pc = _clean_id(_to_int(r.get("IdPC"))) if r else 0
    infos = _infos_pc(id_pc)
    ste = _societe_salarie(infos["id_salarie"])

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    def reader(data, shrink=True):
        d2 = _shrink_image(data) if shrink else data
        try:
            return ImageReader(io.BytesIO(d2)) if d2 else None
        except Exception:
            return None

    y = H - 18 * mm
    # En-tête société
    g = reader(ste["guimmick"], shrink=True)
    if g:
        try:
            c.drawImage(g, 18 * mm, y - 12 * mm, width=32 * mm, height=16 * mm,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(W - 18 * mm, y, ste["raison"] or "")
    c.setFont("Helvetica", 8)
    c.drawRightString(W - 18 * mm, y - 5 * mm, ste["adresse"])
    c.drawRightString(W - 18 * mm, y - 9 * mm,
                      f"{ste['cp']} {ste['ville']}".strip())
    if ste["siren"]:
        c.drawRightString(W - 18 * mm, y - 13 * mm, f"Siren : {ste['siren']}")
    y -= 22 * mm

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W / 2, y, d["lib_pv"])
    y -= 8 * mm
    c.setFont("Helvetica", 10)
    c.drawString(18 * mm, y, f"Contrat : {d['titre_contrat']}")
    y -= 5 * mm
    c.drawString(18 * mm, y, f"Véhicule : {d['vehicule']}")
    y -= 5 * mm
    c.drawString(18 * mm, y, f"Conducteur : {d['conducteur']}")
    y -= 9 * mm

    # Grille photos (2 colonnes)
    col_w = (W - 36 * mm) / 2
    ph_h = 42 * mm
    cols = [18 * mm, 18 * mm + col_w]
    col = 0
    for p in d["photos"]:
        if col == 0 and y < 60 * mm:
            c.showPage()
            y = H - 18 * mm
        cx = cols[col]
        c.setFont("Helvetica-Bold", 7.5)
        note = "★" * p["note"] + "☆" * (5 - p["note"])
        c.drawString(cx, y, f"{p['lib_photo'][:42]}")
        c.setFont("Helvetica", 7.5)
        c.drawRightString(cx + col_w - 4 * mm, y, f"{p['note']}/5")
        data = _memo_img("ticket_rh", "TK_DemandeSignPV_Photo",
                         "IDTK_DemandeSignPV_Photo", int(p["id"]), "Photo")
        ir = reader(data, shrink=True)
        if ir:
            try:
                c.drawImage(ir, cx, y - ph_h - 2 * mm, width=col_w - 6 * mm,
                            height=ph_h, preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
        else:
            c.setFont("Helvetica-Oblique", 7)
            c.drawString(cx, y - 6 * mm, "(photo non recevable)")
        col += 1
        if col == 2:
            col = 0
            y -= ph_h + 9 * mm
    if col == 1:
        y -= ph_h + 9 * mm

    # Observations
    if d["observations"]:
        if y < 45 * mm:
            c.showPage()
            y = H - 18 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(18 * mm, y, "Observation générale :")
        y -= 5 * mm
        c.setFont("Helvetica", 9)
        for line in (d["observations"].splitlines() or [""]):
            c.drawString(20 * mm, y, line[:115])
            y -= 4.5 * mm
        y -= 4 * mm

    # Signatures (nouvelle page si peu de place)
    if y < 45 * mm:
        c.showPage()
        y = H - 18 * mm
    sigs = [
        ("Signature", "Signature", 45 * mm, 22 * mm),
        ("Paraphe", "paraphe", 30 * mm, 18 * mm),
        ("Lu et approuvé", "luApp", 55 * mm, 18 * mm),
        ("Photo salarié", "PhotoSalarié", 28 * mm, 28 * mm),
    ]
    sx = 18 * mm
    for label, field, w, h in sigs:
        c.setFont("Helvetica", 8)
        c.drawString(sx, y, label)
        data = _memo_img("ticket_rh", "TK_DemandeSignPVUlease", "IDTK_Liste",
                         int(id_ticket), field)
        ir = reader(data, shrink=True)
        if ir:
            try:
                c.drawImage(ir, sx, y - h - 2 * mm, width=w, height=h,
                            preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
        sx += w + 6 * mm
        if sx > W - 30 * mm:
            sx = 18 * mm
            y -= 34 * mm

    c.showPage()
    c.save()
    return buf.getvalue()
