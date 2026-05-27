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
import math
import os
import tempfile

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
# Cache disque des photos (perf) : la lecture d'un mémo binaire via le
# bridge HFSQL est lente (~1.5 s/photo de 2.5 Mo). On extrait chaque
# photo UNE fois (réduite Pillow) sur le disque serveur ; le PDF et les
# ré-affichages lisent ensuite le cache local. Le cache se remplit
# naturellement quand l'opérateur affiche les photos pour les noter.
# --------------------------------------------------------------------

def _cache_dir(id_ticket: int) -> str:
    d = os.path.join(tempfile.gettempdir(), "omaya_pv_cache", str(int(id_ticket)))
    os.makedirs(d, exist_ok=True)
    return d


def _photo_cached(id_ticket: int, id_photo: int) -> str | None:
    """Chemin de la photo (réduite) en cache disque. L'extrait du mémo
    binaire (bridge) si absente. None si pas de photo."""
    path = os.path.join(_cache_dir(id_ticket), f"{int(id_photo)}.jpg")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    data = _memo_img("ticket_rh", "TK_DemandeSignPV_Photo",
                     "IDTK_DemandeSignPV_Photo", int(id_photo), "Photo")
    small = _shrink_image(data)
    if not small:
        return None
    try:
        with open(path, "wb") as f:
            f.write(small)
    except Exception:
        return None
    return path


def _photo_cache_invalide(id_ticket: int, id_photo: int) -> None:
    try:
        path = os.path.join(_cache_dir(id_ticket), f"{int(id_photo)}.jpg")
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


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


def _photos(id_ticket: int) -> list[dict]:
    """Photos du PV (TK_DemandeSignPV_Photo, ticket_rh). Le binaire n'est
    pas chargé (flag a_photo) — accès via get_file. DatePhoto = « Prise le »
    et OpPhoto = « par » (opérateur, ID salarié) pour le PDF."""
    try:
        rows = get_connection("ticket_rh").query(
            "SELECT IDTK_DemandeSignPV_Photo, IDTypeCapacite_Photo, NoteEtat, "
            "DatePhoto, OpPhoto FROM TK_DemandeSignPV_Photo "
            "WHERE IDdemandeSignUleaseAuto = ? AND ModifElem <> 'suppr'",
            (int(id_ticket),),
        )
    except Exception:
        return []
    rows = rows or []
    # Libellés en UNE requête (sinon 1 requête bridge par photo = très lent)
    ids_type = {_to_int(r.get("IDTypeCapacite_Photo")) for r in rows}
    ids_type = {i for i in ids_type if i}
    libs: dict[int, str] = {}
    if ids_type:
        try:
            for t in get_connection("ulease").query(
                "SELECT IDTypeCapacite_Photo, LibPhoto FROM TypeCapacite_Photo "
                "WHERE IDTypeCapacite_Photo IN ("
                + ",".join(str(i) for i in ids_type) + ")"
            ):
                libs[_to_int(t.get("IDTypeCapacite_Photo"))] = (
                    t.get("LibPhoto") or ""
                ).strip()
        except Exception:
            pass
    # Noms des opérateurs (= salariés) en UNE requête batch
    ids_op = {_clean_id(_to_int(r.get("OpPhoto"))) for r in rows}
    ids_op = {i for i in ids_op if i}
    ops = load_salaries_minimal(ids_op) if ids_op else {}

    def _op_nom(i: int) -> str:
        info = ops.get(i, {})
        p = (info.get("prenom") or "")
        return (
            f"{info.get('nom', '')} {p[:1].upper() + p[1:].lower() if p else ''}"
        ).strip()

    out = []
    for r in rows:
        idp = _clean_id(_to_int(r.get("IDTK_DemandeSignPV_Photo")))
        if not idp:
            continue
        id_type = _to_int(r.get("IDTypeCapacite_Photo"))
        out.append({
            "id": str(idp),
            # id_type_photo à 17 chiffres > 2^53 → exposé en str sinon
            # JavaScript perd en précision (cf. feedback_ids_8octets_string)
            "id_type_photo": str(id_type),
            "lib_photo": libs.get(id_type, ""),
            "note": _to_int(r.get("NoteEtat")),
            "date_photo": _fmt_dt(r.get("DatePhoto")),
            "op_nom": _op_nom(_clean_id(_to_int(r.get("OpPhoto")))),
        })
    out.sort(key=lambda p: p["lib_photo"])
    return out


def _fmt_dt(v: object) -> str:
    """Date HFSQL/ISO → « JJ/MM/AAAA HH:MM » (ou « JJ/MM/AAAA »)."""
    s = str(v or "").strip()
    if not s:
        return ""
    if "T" in s or "-" in s:
        from datetime import datetime
        s2 = s.replace("T", " ").split(".")[0]
        try:
            if len(s2) >= 19:
                return datetime.strptime(s2[:19], "%Y-%m-%d %H:%M:%S").strftime(
                    "%d/%m/%Y %H:%M"
                )
            return datetime.strptime(s2[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return s
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) >= 12:
        return (f"{digits[6:8]}/{digits[4:6]}/{digits[0:4]} "
                f"{digits[8:10]}:{digits[10:12]}")
    if len(digits) >= 8:
        return f"{digits[6:8]}/{digits[4:6]}/{digits[0:4]}"
    return s


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
        _photo_cache_invalide(int(id_ticket), int(id_photo))
        return {"ok": True}

    # --- Pré-chargement du cache photos (avant génération PDF) ---
    if action == "prepare":
        for p in _photos(id_ticket):
            if p["note"] > 0:
                _photo_cached(int(id_ticket), int(p["id"]))
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
        # photo fournie : sert (et alimente) le cache disque réduit
        path = _photo_cached(int(id_ticket), _to_int(raw))
        if path:
            try:
                with open(path, "rb") as fh:
                    return fh.read(), "image/jpeg"
            except Exception:
                pass
        data = None
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
        # Aplatir la transparence sur fond BLANC : convert('RGB') seul la
        # poserait sur du NOIR → signatures/paraphes/logo sur fond noir
        # dans le PDF. (Les photos JPEG sans alpha ne sont pas concernées.)
        if im.mode in ("RGBA", "LA") or (
            im.mode == "P" and "transparency" in im.info
        ):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        elif im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        im.thumbnail((max_px, max_px))
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=quality, optimize=True)
        return out.getvalue()
    except Exception:
        return data


def _generate_pv_pdf(id_ticket: int) -> bytes:
    """PDF du PV (modèle WinDev EtatUleasePVLivRest) : une photo par page
    avec libellé / note / prise le / opérateur, en-tête véhicule courant,
    pied de page société (logo + raison + adresse + Siren + paraphe + n°
    de page). Dernière page = récap (nb photos, moyenne, observation,
    signatures + photo salarié). Images réduites (Pillow) pour la taille."""
    from datetime import datetime

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

    is_liv = "livraison" in (d["lib_pv"] or "").lower()
    titre_doc = "PV de livraison" if is_liv else "PV de restitution"
    veh_line = (
        f"{(d['conducteur'] or '').upper()} : {d['vehicule']}"
    ).strip(" :")
    date_doc = datetime.now().strftime("%d/%m/%Y")

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    ML = 18 * mm  # marge gauche/droite

    def reader(data, shrink=True):
        d2 = _shrink_image(data) if shrink else data
        try:
            return ImageReader(io.BytesIO(d2)) if d2 else None
        except Exception:
            return None

    def reader_path(path):
        try:
            with open(path, "rb") as fh:
                return ImageReader(io.BytesIO(fh.read()))
        except Exception:
            return None

    # Photos réellement présentes (cache disque rempli) + note
    photos = []
    for p in d["photos"]:
        path = _photo_cached(int(id_ticket), int(p["id"]))
        if path:
            photos.append((p, path))
    nb = len(photos)
    moyenne = (sum(p["note"] for p, _ in photos) / nb) if nb else 0.0
    total_pages = nb + 1

    # Paraphe (répété en pied de page) + logo société, lus une fois
    logo = reader(ste["guimmick"], shrink=True)
    paraphe = reader(
        _memo_img("ticket_rh", "TK_DemandeSignPVUlease", "IDTK_Liste",
                  int(id_ticket), "paraphe"),
        shrink=True,
    )

    def footer(page_no: int) -> None:
        if logo:
            try:
                c.drawImage(logo, ML, 6 * mm, width=18 * mm, height=14 * mm,
                            preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
        c.setFont("Helvetica", 7)
        c.drawCentredString(W / 2, 14 * mm, ste["raison"] or "")
        c.drawCentredString(
            W / 2, 10.5 * mm,
            f"{ste['adresse']} {ste['cp']} {ste['ville']}".strip(),
        )
        if ste["siren"]:
            c.drawCentredString(W / 2, 7 * mm, f"Siren : {ste['siren']}")
        if paraphe:
            try:
                c.drawImage(paraphe, W - 58 * mm, 6 * mm, width=16 * mm,
                            height=10 * mm, preserveAspectRatio=True,
                            mask="auto")
            except Exception:
                pass
        c.setFont("Helvetica", 8)
        c.drawRightString(W - ML, 15 * mm, f"{page_no}/{total_pages}")

    def draw_stars(right_x: float, y_base: float, note: int) -> float:
        """Dessine 5 étoiles vectorielles alignées à droite (bord droit =
        right_x). `note` remplies (ambre), le reste en contour gris.
        Retourne le bord gauche du groupe (pour poser le libellé)."""
        R = 1.5 * mm
        gap = 1.0 * mm
        step = 2 * R + gap
        left_x = right_x - (10 * R + 4 * gap)
        cy = y_base + 1.0 * mm
        for i in range(5):
            cx = left_x + R + i * step
            path = c.beginPath()
            for k in range(10):
                ang = math.pi / 2 + k * math.pi / 5
                rad = R if k % 2 == 0 else R * 0.4
                px, py = cx + rad * math.cos(ang), cy + rad * math.sin(ang)
                path.moveTo(px, py) if k == 0 else path.lineTo(px, py)
            path.close()
            if i < note:
                c.setFillColorRGB(0.98, 0.74, 0.18)
                c.setStrokeColorRGB(0.90, 0.62, 0.05)
                c.drawPath(path, fill=1, stroke=1)
            else:
                c.setFillColorRGB(1, 1, 1)
                c.setStrokeColorRGB(0.75, 0.75, 0.78)
                c.drawPath(path, fill=0, stroke=1)
        c.setFillColorRGB(0, 0, 0)
        c.setStrokeColorRGB(0, 0, 0)
        return left_x

    # --- Pages photos (une par photo) ---
    page_no = 0
    for idx, (p, path) in enumerate(photos):
        page_no += 1
        if idx == 0:
            c.setFont("Helvetica-Bold", 18)
            c.drawCentredString(W / 2, H - 22 * mm, titre_doc)
            c.setFont("Helvetica", 9)
            c.drawRightString(W - ML, H - 20 * mm, date_doc)
            y = H - 36 * mm
        else:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(ML, H - 18 * mm, veh_line)
            y = H - 30 * mm
        c.setFont("Helvetica", 9.5)
        c.drawString(ML, y, f"Lib Photo :   {p['lib_photo']}")
        star_left = draw_stars(W - ML, y, p["note"])
        c.setFont("Helvetica", 9.5)
        c.drawRightString(star_left - 2.5 * mm, y, "Note donnée :")
        y -= 6 * mm
        meta = f"Prise le :   {p.get('date_photo', '')}"
        if p.get("op_nom"):
            meta += f"        par :   {p['op_nom']}"
        c.drawString(ML, y, meta)
        y -= 5 * mm
        # Photo : occupe la place restante jusqu'au pied de page
        box_top = y
        box_bottom = 24 * mm
        ir = reader_path(path)
        if ir:
            try:
                c.drawImage(ir, ML, box_bottom, width=W - 2 * ML,
                            height=box_top - box_bottom,
                            preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
        footer(page_no)
        c.showPage()

    # --- Page récapitulative ---
    page_no += 1
    c.setFont("Helvetica-Bold", 12)
    c.drawString(ML, H - 18 * mm, veh_line)
    y = H - 32 * mm
    c.setFont("Helvetica", 10)
    c.drawString(ML, y, f"Nombre de Photos :    {nb}")
    y -= 7 * mm
    moy_str = f"{moyenne:.2f}".replace(".", ",")
    c.drawString(ML, y, f"Moyenne globale :    {moy_str} / 5")
    y -= 10 * mm
    c.drawString(ML, y, "Observation :")
    y -= 3 * mm
    box_h = 70 * mm
    box_w = W - 2 * ML
    box_bottom = y - box_h
    c.roundRect(ML, box_bottom, box_w, box_h, 4 * mm)
    # Texte de l'observation (retour à la ligne simple)
    c.setFont("Helvetica", 9)
    ty = y - 6 * mm
    max_chars = 110
    for raw in (d["observations"] or "").splitlines():
        chunk = raw
        while chunk:
            c.drawString(ML + 3 * mm, ty, chunk[:max_chars])
            chunk = chunk[max_chars:]
            ty -= 4.5 * mm
            if ty < box_bottom + 3 * mm:
                break
        if not raw:
            ty -= 4.5 * mm
        if ty < box_bottom + 3 * mm:
            break
    # Signatures (empilées à gauche) + photo salarié (à droite)
    sy = box_bottom - 8 * mm
    for field in ("Signature", "paraphe", "luApp"):
        data = _memo_img("ticket_rh", "TK_DemandeSignPVUlease", "IDTK_Liste",
                         int(id_ticket), field)
        ir = reader(data, shrink=True)
        if ir:
            try:
                c.drawImage(ir, ML, sy - 18 * mm, width=55 * mm, height=18 * mm,
                            preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
            sy -= 22 * mm
    photo_sal = reader(
        _memo_img("ticket_rh", "TK_DemandeSignPVUlease", "IDTK_Liste",
                  int(id_ticket), "PhotoSalarié"),
        shrink=True,
    )
    if photo_sal:
        try:
            c.drawImage(photo_sal, W - ML - 32 * mm, box_bottom - 38 * mm,
                        width=32 * mm, height=32 * mm,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    footer(page_no)
    c.showPage()
    c.save()
    return buf.getvalue()
