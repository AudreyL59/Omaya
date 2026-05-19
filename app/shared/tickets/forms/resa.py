"""FI_Resa (type 9 — Réservation).

Transposition de la fenêtre interne WinDev FI_Resa.

Données : TK_DemandeResa (1 enr/ticket, clé IDTK_Liste), TK_TypeResa
(catégorie : 1=Hébergement, 2=Transport, 3=Salle de réunion),
TK_TypeResaSSFam (sous-famille, reliée à TK_TypeResa) — base
**ticket_bo**. TK_Liste (base ticket) pour le demandeur (OPCREA).
Salariés (nom/GSM/mail) : base rh (salarie + salarie_coordonnées).

PJ : FTP /OMAYA/DocTicket/<idTicket>/ (liste / aperçu / ajout /
suppression). Lien SMS : DOCS_URL + DocTicket/<idTicket>/<fichier>.
"""

import ftplib
import io
import urllib.parse

from app.core.config import (
    DOCS_URL,
    FTP_DOC_TICKET_PATH,
    FTP_HOST,
    FTP_PASSWORD,
    FTP_USER,
)
from app.core.database import get_connection
from app.shared.notifications.sms import envoi_sms

from ..service import (
    _clean_id,
    _now_windev,
    _to_int,
    date_only_to_iso,
    iso_to_date_only,
    maj_op_traitement_ticket,
)

# idTypeResa connus (cf. afficherTypeResa WinDev)
HEBERGEMENT, TRANSPORT, SALLE = 1, 2, 3


# --------------------------------------------------------------------
# Heures HFSQL (rubrique 'Heure') <-> 'HH:MM'
# --------------------------------------------------------------------

def _heure_to_hhmm(v) -> str:
    d = "".join(c for c in str(v or "") if c.isdigit())
    if len(d) < 4 or d[:4] == "0000":
        return ""
    return f"{d[0:2]}:{d[2:4]}"


def _hhmm_to_heure(v) -> str:
    """'HH:MM' -> 'HHMMSSCC' (8 chiffres, sec/centièmes à 0)."""
    d = "".join(c for c in str(v or "") if c.isdigit())
    return (d[:4] + "0000") if len(d) >= 4 else ""


# --------------------------------------------------------------------
# Salariés (DonneInfoSalarié -> ST_SALARIE : Nom, Prénom, GSM, Mail)
# --------------------------------------------------------------------

def _salaries_full(ids: set[int]) -> dict[int, dict]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    rh = get_connection("rh")
    ids_sql = ",".join(str(i) for i in ids)
    base: dict[int, dict] = {}
    for r in rh.query(
        f"SELECT IDSalarie, NOM, PRENOM FROM salarie "
        f"WHERE IDSalarie IN ({ids_sql})"
    ):
        sid = _clean_id(_to_int(r.get("IDSalarie")))
        if sid:
            base[sid] = {
                "nom": (r.get("NOM") or "").strip(),
                "prenom": (r.get("PRENOM") or "").strip(),
                "gsm": "",
                "mail": "",
            }
    try:
        for r in rh.query(
            f"SELECT IDSalarie, TélMob, MAIL FROM salarie_coordonnées "
            f"WHERE IDSalarie IN ({ids_sql})"
        ):
            sid = _clean_id(_to_int(r.get("IDSalarie")))
            if sid in base:
                base[sid]["gsm"] = (r.get("TélMob") or "").strip()
                base[sid]["mail"] = (r.get("MAIL") or "").strip()
    except Exception:
        pass
    return base


def _nom_complet(info: dict) -> str:
    p = info.get("prenom", "")
    return f"{info.get('nom', '')} {p[:1].upper() + p[1:].lower() if p else ''}".strip()


def _parse_supp(liste: str) -> list[int]:
    out: list[int] = []
    for part in str(liste or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        part = part.strip()
        if part.isdigit():
            v = _clean_id(int(part))
            if v:
                out.append(v)
    return out


# --------------------------------------------------------------------
# Mémos isolés (bridge : SELECT clé + mémo)
# --------------------------------------------------------------------

def _memo(db, id_ticket: int, field: str) -> str:
    try:
        r = db.query_one(
            f"SELECT IDTK_Liste, {field} FROM TK_DemandeResa "
            f"WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        return ((r.get(field) if r else "") or "").strip()
    except Exception:
        return ""


# --------------------------------------------------------------------
# FTP PJ : /OMAYA/DocTicket/<idTicket>/
# --------------------------------------------------------------------

def _ftp_dir(id_ticket: int) -> str:
    return f"{FTP_DOC_TICKET_PATH.rstrip('/')}/{int(id_ticket)}"


def _ftp_connect() -> ftplib.FTP:
    ftp = ftplib.FTP(timeout=20)
    ftp.encoding = "latin-1"
    ftp.connect(FTP_HOST, 21)
    ftp.login(FTP_USER, FTP_PASSWORD)
    return ftp


def _list_files(id_ticket: int) -> list[dict]:
    out: list[dict] = []
    try:
        ftp = _ftp_connect()
    except Exception:
        return out
    try:
        d = _ftp_dir(id_ticket)
        lines: list[str] = []
        try:
            ftp.retrlines(f"LIST {d}", lines.append)
        except Exception:
            return out
        for ln in lines:
            parts = ln.split(maxsplit=8)
            if len(parts) < 9 or ln[0] == "d":
                continue
            taille = parts[4]
            date = " ".join(parts[5:8])
            nom = parts[8]
            out.append({
                "nom": nom,
                "taille": taille,
                "date": date,
                "heure": "",
            })
    finally:
        try:
            ftp.quit()
        except Exception:
            pass
    return out


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


# --------------------------------------------------------------------
# Combos catégorie / sous-famille
# --------------------------------------------------------------------

def _categories() -> list[dict]:
    try:
        db = get_connection("ticket_bo")
        return [
            {
                "id": _to_int(r.get("IDTK_TypeResa")),
                "lib": (r.get("Lib_TypeResa") or "").strip(),
            }
            for r in db.query(
                "SELECT IDTK_TypeResa, Lib_TypeResa FROM TK_TypeResa "
                "ORDER BY Lib_TypeResa"
            )
        ]
    except Exception:
        return []


def _sous_familles() -> list[dict]:
    try:
        db = get_connection("ticket_bo")
        return [
            {
                "id": _to_int(r.get("IDTK_TypeResaSSFam")),
                "lib": (r.get("Lib_TypeResaSSFam") or "").strip(),
                "id_type_resa": _to_int(r.get("IDTK_TypeResa")),
            }
            for r in db.query(
                "SELECT IDTK_TypeResaSSFam, Lib_TypeResaSSFam, IDTK_TypeResa "
                "FROM TK_TypeResaSSFam ORDER BY Lib_TypeResaSSFam"
            )
        ]
    except Exception:
        return []


def _id_type_resa_of(id_ss_fam: int) -> int:
    if not id_ss_fam:
        return 0
    try:
        db = get_connection("ticket_bo")
        r = db.query_one(
            "SELECT IDTK_TypeResaSSFam, IDTK_TypeResa FROM TK_TypeResaSSFam "
            "WHERE IDTK_TypeResaSSFam = ?",
            (int(id_ss_fam),),
        )
        return _to_int(r.get("IDTK_TypeResa")) if r else 0
    except Exception:
        return 0


def _libelles(id_type_resa: int, ar: bool) -> dict:
    """cf. afficherTypeResa() : libellés + visibilités selon la
    catégorie (1 Hébergement / 2 Transport / 3 Salle)."""
    if id_type_resa == HEBERGEMENT:
        return {
            "lib_dep": "Début du séjour le", "lib_arr": "Fin du séjour le",
            "show_ville_arr": False, "show_retour": False,
            "lib_ville_dep": "À",
        }
    if id_type_resa == TRANSPORT:
        return {
            "lib_dep": "Aller : Départ le" if ar else "Départ le",
            "lib_arr": "Aller : Arrivée le" if ar else "Arrivée le",
            "show_ville_arr": True, "show_retour": bool(ar),
            "lib_ville_dep": "De :",
        }
    if id_type_resa == SALLE:
        return {
            "lib_dep": "Du", "lib_arr": "Au",
            "show_ville_arr": False, "show_retour": False,
            "lib_ville_dep": "À",
        }
    return {
        "lib_dep": "Départ le", "lib_arr": "Arrivée le",
        "show_ville_arr": True, "show_retour": bool(ar),
        "lib_ville_dep": "À",
    }


# --------------------------------------------------------------------
# load / save
# --------------------------------------------------------------------

def load(id_ticket: int) -> dict:
    db = get_connection("ticket_bo")
    r = db.query_one(
        """SELECT IDTK_Liste, IDTK_TypeResaSSFam, Ville_Dep, Ville_Arr,
            Jour_Dep, Jour_Arr, Heure_Dep, Heure_Arr, Bénéficiaire, AR,
            JourR_Dep, JourR_Arr, HeureR_Dep, HeureR_Arr
        FROM TK_DemandeResa WHERE IDTK_Liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}

    id_ss_fam = _to_int(r.get("IDTK_TypeResaSSFam"))
    id_type_resa = _id_type_resa_of(id_ss_fam)
    ar = bool(r.get("AR"))

    liste_supp = _memo(db, id_ticket, "ListeBénéSupp")
    info_cplt = _memo(db, id_ticket, "InfoCplt")

    benef_id = _clean_id(_to_int(r.get("Bénéficiaire")))
    supp_ids = _parse_supp(liste_supp)

    # Demandeur (TK_Liste.OPCREA, base ticket)
    op_crea = 0
    try:
        tk = get_connection("ticket").query_one(
            "SELECT IDTK_Liste, OPCREA FROM TK_Liste WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        op_crea = _clean_id(_to_int(tk.get("OPCREA"))) if tk else 0
    except Exception:
        op_crea = 0

    sal = _salaries_full(set(supp_ids) | {benef_id, op_crea})

    beneficiaires = []
    if benef_id and benef_id in sal:
        i = sal[benef_id]
        beneficiaires.append({
            "id_salarie": str(benef_id), "nom": _nom_complet(i),
            "mobile": i["gsm"], "mail": i["mail"], "principal": True,
        })
    for sid in supp_ids:
        if sid in sal:
            i = sal[sid]
            beneficiaires.append({
                "id_salarie": str(sid), "nom": _nom_complet(i),
                "mobile": i["gsm"], "mail": i["mail"], "principal": False,
            })

    return {
        "found": True,
        "id_type_resa": id_type_resa,
        "id_ss_fam": id_ss_fam,
        "categories": _categories(),
        "sous_familles": _sous_familles(),
        "ville_dep": (r.get("Ville_Dep") or "").strip(),
        "ville_arr": (r.get("Ville_Arr") or "").strip(),
        "jour_dep": date_only_to_iso(r.get("Jour_Dep")),
        "jour_arr": date_only_to_iso(r.get("Jour_Arr")),
        "heure_dep": _heure_to_hhmm(r.get("Heure_Dep")),
        "heure_arr": _heure_to_hhmm(r.get("Heure_Arr")),
        "ar": ar,
        "jourr_dep": date_only_to_iso(r.get("JourR_Dep")),
        "jourr_arr": date_only_to_iso(r.get("JourR_Arr")),
        "heurer_dep": _heure_to_hhmm(r.get("HeureR_Dep")),
        "heurer_arr": _heure_to_hhmm(r.get("HeureR_Arr")),
        "benef_id": str(benef_id) if benef_id else "",
        "benef_nom": _nom_complet(sal.get(benef_id, {})) if benef_id else "",
        "beneficiaires": beneficiaires,
        "info_cplt": info_cplt,
        "mobile_demandeur": (sal.get(op_crea, {}) or {}).get("gsm", ""),
        "fichiers": _list_files(int(id_ticket)),
        "labels": _libelles(id_type_resa, ar),
    }


def _sms_text(id_ticket: int, d: dict, fichier: str) -> str:
    """cf. envoyerSMS() WinDev."""
    id_type = _to_int(d.get("id_type_resa"))
    ar = bool(d.get("ar"))
    t = "OMAYA - Service réservation\n"
    t += "Une PJ a été ajoutée pour votre réservation "
    if id_type == HEBERGEMENT:
        t += "d'herbergement "
        t += f"du {d.get('jour_dep', '')} au {d.get('jour_arr', '')}"
    elif id_type == TRANSPORT:
        t += "de transport "
        if ar:
            t += "Aller-Retour "
        t += f"entre {d.get('ville_dep', '')} et {d.get('ville_arr', '')}\n"
        t += f"Départ le {d.get('jour_dep', '')} à {d.get('heure_dep', '')}\n"
        if ar:
            t += f"retour le {d.get('jourr_dep', '')} à {d.get('heurer_dep', '')}\n"
    elif id_type == SALLE:
        t += f"de salle de réunion à {d.get('ville_dep', '')} le {d.get('jour_dep', '')}\n"
    url = f"{DOCS_URL.rstrip('/')}/DocTicket/{int(id_ticket)}/{fichier}"
    t += "\n" + urllib.parse.quote(url, safe=":/")
    t += "\nCdt."
    return t


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    action = str(payload.get("action") or "enregistrer")
    now = _now_windev()
    db = get_connection("ticket_bo")

    if action == "enregistrer":
        cur = db.query_one(
            "SELECT IDTK_Liste FROM TK_DemandeResa WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Réservation introuvable"}
        benef = _to_int(payload.get("benef_id"))
        supp = [
            str(_to_int(s)) for s in (payload.get("supp_ids") or [])
            if _to_int(s)
        ]
        db.query(
            """UPDATE TK_DemandeResa SET
                IDTK_TypeResaSSFam = ?, Ville_Dep = ?, Ville_Arr = ?,
                Jour_Dep = ?, Jour_Arr = ?, Heure_Dep = ?, Heure_Arr = ?,
                Bénéficiaire = ?, ListeBénéSupp = ?, InfoCplt = ?, AR = ?,
                JourR_Dep = ?, JourR_Arr = ?, HeureR_Dep = ?, HeureR_Arr = ?,
                ModifDate = ?, ModifOP = ?, ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (
                _to_int(payload.get("id_ss_fam")),
                str(payload.get("ville_dep") or "").strip(),
                str(payload.get("ville_arr") or "").strip(),
                iso_to_date_only(payload.get("jour_dep")),
                iso_to_date_only(payload.get("jour_arr")),
                _hhmm_to_heure(payload.get("heure_dep")),
                _hhmm_to_heure(payload.get("heure_arr")),
                benef,
                "\r\n".join(supp),
                str(payload.get("info_cplt") or ""),
                1 if payload.get("ar") else 0,
                iso_to_date_only(payload.get("jourr_dep")),
                iso_to_date_only(payload.get("jourr_arr")),
                _hhmm_to_heure(payload.get("heurer_dep")),
                _hhmm_to_heure(payload.get("heurer_arr")),
                now, int(user_id), int(id_ticket),
            ),
        )
        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True}

    if action == "delete_pj":
        nom = str(payload.get("nom_fichier") or "").strip()
        if not nom:
            return {"ok": False, "error": "Fichier manquant"}
        try:
            ftp = _ftp_connect()
            try:
                ftp.delete(f"{_ftp_dir(id_ticket)}/{nom}")
            finally:
                ftp.quit()
        except Exception as e:
            return {"ok": False, "error": f"Suppression FTP : {e}"}
        return {"ok": True}

    if action == "sms":
        # « Envoyer le lien (de cette PJ) par SMS à tous les bénéficiaires »
        nom = str(payload.get("nom_fichier") or "").strip()
        if not nom:
            return {"ok": False, "error": "Sélectionne une PJ"}
        d = load(int(id_ticket))
        texte = _sms_text(int(id_ticket), d, nom)
        envois = []
        mob_dem = (d.get("mobile_demandeur") or "").replace(".", "").strip()
        seen: set[str] = set()
        for b in d.get("beneficiaires", []):
            gsm = (b.get("mobile") or "").replace(".", "").strip()
            if gsm and gsm not in seen:
                seen.add(gsm)
                try:
                    res = envoi_sms(texte, gsm, "", "OMAYA-Resa")
                except Exception as e:
                    res = f"erreur : {e}"
                envois.append(f"{b.get('nom')} : {res}")
        if mob_dem and mob_dem not in seen:
            try:
                res = envoi_sms(texte, mob_dem, "", "OMAYA-Resa")
            except Exception as e:
                res = f"erreur : {e}"
            envois.append(f"Demandeur : {res}")
        return {"ok": True, "envois": envois}

    return {"ok": False, "error": "Action non disponible"}


def get_file(id_ticket: int, name: str) -> tuple[bytes, str]:
    """Aperçu d'une PJ : FTP /OMAYA/DocTicket/<idTicket>/<name>."""
    if not name:
        raise FileNotFoundError("Nom de fichier manquant")
    try:
        ftp = _ftp_connect()
        buf = io.BytesIO()
        try:
            ftp.retrbinary(f"RETR {_ftp_dir(id_ticket)}/{name}", buf.write)
        finally:
            ftp.quit()
        data = buf.getvalue()
    except Exception:
        raise FileNotFoundError("Document introuvable sur le FTP")
    if not data:
        raise FileNotFoundError("Document vide")
    return data, _mime_for(name)


def upload_file(id_ticket: int, filename: str, content: bytes) -> dict:
    """Ajout d'une PJ sur le FTP (crée le dossier du ticket au besoin)."""
    if not filename or not content:
        return {"ok": False, "error": "Fichier vide"}
    safe = filename.replace("/", "_").replace("\\", "_").strip()
    try:
        ftp = _ftp_connect()
        try:
            ftp.cwd("/")
            for part in [p for p in _ftp_dir(id_ticket).split("/") if p]:
                try:
                    ftp.cwd(part)
                except ftplib.error_perm:
                    ftp.mkd(part)
                    ftp.cwd(part)
            ftp.storbinary(f"STOR {safe}", io.BytesIO(content))
        finally:
            ftp.quit()
    except Exception as e:
        return {"ok": False, "error": f"Upload FTP : {e}"}
    return {"ok": True, "nom_fichier": safe}
