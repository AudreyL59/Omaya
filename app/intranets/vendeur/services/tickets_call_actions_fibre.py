"""
Actions ecriture ticket Call Fibre (cote Vendeur, PG).

Portage direct des fonctions save/verrou/annuler/valider/renvoyer du
service call/fibre/services/fiche.py, avec get_pg_connection au lieu
de get_connection (HFSQL).

Cf. memoire feedback_fiche_ticket_modal_sync.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection
from app.intranets.vendeur.services.tickets_call_fiche_fibre import (
    _bool, _capitalize, _iso_date, _mask_phone, _to_int,
)


logger = logging.getLogger(__name__)


# --- Helpers -------------------------------------------------------------

def _sql_now_wd() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")


def _dates_to_compact(s: str | None) -> str:
    if not s:
        return ""
    s = str(s).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:4] + s[5:7] + s[8:10]
    if len(s) == 8 and s.isdigit():
        return s
    return ""


def _parse_dt(v: Any):
    if v is None:
        return None
    if hasattr(v, "year"):
        return v
    s = str(v).strip()
    if not s or s.startswith("0000") or s.startswith("1900"):
        return None
    for fmt in ("%Y%m%d%H%M%S%f", "%Y%m%d%H%M%S",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:len(fmt)], fmt)
        except ValueError:
            continue
    return None


def _format_nom_client_sms(nom: str, nom_marital: str, prenom: str) -> str:
    parts = [(nom or "").strip()]
    if (nom_marital or "").strip():
        parts.append(f"ep {nom_marital.strip()}")
    parts.append(_capitalize((prenom or "").strip()))
    return " ".join(p for p in parts if p)


def _get_gsm_vendeur(id_vendeur: int) -> str:
    if not id_vendeur:
        return ""
    rh = get_pg_connection("rh")
    try:
        r = rh.query_one(
            "SELECT tel_mob FROM rh.pgt_salarie_coordonnees WHERE id_salarie = ?",
            (int(id_vendeur),),
        )
    except Exception:
        return ""
    gsm = ((r or {}).get("tel_mob") or "").strip()
    return "".join(c for c in gsm if c.isdigit() or c == "+")


# --- Save --------------------------------------------------------------

def save_vente_infos(id_tk_liste: int, payload: dict) -> dict:
    """UPDATE pgt_tk_call_sfr : infos client + vente.

    Note : mob_propo_vend + anomalie_mobile + id_tk_call_sfr_type_anomalie
    + info_cplt_anomalie absents du schema PG interne (existent cote HFSQL
    OVH), ces champs du payload sont ignores silencieusement.
    """
    db = get_pg_connection("ticket_bo")
    c = payload.get("client", {}) or {}
    v = payload.get("vente", {}) or {}
    now = _sql_now_wd()
    db.query(
        """UPDATE ticket_bo.pgt_tk_call_sfr SET
              civilite_client = ?, nom_client = ?, nom_marital_client = ?,
              prenom_client = ?, date_naiss = ?, dep_naiss = ?,
              type_logement = ?, adresse1 = ?, adresse2 = ?, cp = ?,
              ville = ?, adr_mail = ?, info_vente = ?, ref_appel = ?,
              intervention_vend = ?, modif_date = ?
            WHERE id_tk_liste = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (
            _to_int(c.get("civilite")),
            (c.get("nom") or ""),
            (c.get("nom_marital") or ""),
            (c.get("prenom") or ""),
            _dates_to_compact(c.get("date_naiss")),
            _to_int(c.get("dep_naiss")),
            _to_int(c.get("type_logement")),
            (c.get("adresse1") or ""),
            (c.get("adresse2") or ""),
            (c.get("cp") or ""),
            (c.get("ville") or ""),
            (c.get("email") or ""),
            (v.get("info_vente") or ""),
            (v.get("ref_appel") or ""),
            1 if _bool(v.get("intervention_vendeur")) else 2,
            now,
            int(id_tk_liste),
        ),
    )
    return {"ok": True}


def save_offre(id_panier: int, payload: dict) -> dict:
    """UPDATE pgt_tk_call_sfr_panier : modifs d'une ligne d'offre."""
    db = get_pg_connection("ticket_bo")
    now = _sql_now_wd()
    db.query(
        """UPDATE ticket_bo.pgt_tk_call_sfr_panier SET
              portabilite = ?, num_portabilite = ?, num_prise_rio = ?,
              type_vente = ?, statut_prod = ?, num_prise_optique = ?,
              opt_choisies = ?, modif_date = ?
            WHERE id_tk_call_sfr_panier = ?""",
        (
            _bool(payload.get("portabilite")),
            (payload.get("num_portabilite") or ""),
            (payload.get("num_rio") or ""),
            _to_int(payload.get("type_vente")),
            _to_int(payload.get("statut_prod")),
            (payload.get("num_prise_optique") or ""),
            (payload.get("opt_choisies") or ""),
            now,
            int(id_panier),
        ),
    )
    return {"ok": True}


# --- Verrou ------------------------------------------------------------

def peek_verrou(id_tk_liste: int) -> dict:
    """Etat du verrou ope : qui, depuis quand + duree."""
    db_bo = get_pg_connection("ticket_bo")
    db_rh = get_pg_connection("rh")
    r = db_bo.query_one(
        """SELECT id_tk_call_sfr, appel_en_cours, ope_appel, date_h_appel
             FROM ticket_bo.pgt_tk_call_sfr
            WHERE id_tk_liste = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_tk_liste),),
    )
    if not r:
        return {"error": "Ticket introuvable"}
    appel_en_cours = _bool(r.get("appel_en_cours"))
    ope_appel_id = _to_int(r.get("ope_appel"))
    date_h_appel_iso = str(r.get("date_h_appel") or "")
    nom_ope = ""
    if ope_appel_id:
        rs = db_rh.query_one(
            "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ?",
            (ope_appel_id,),
        )
        if rs:
            nom_ope = (
                f"{(rs.get('nom') or '').strip()} "
                f"{_capitalize((rs.get('prenom') or '').strip())}"
            ).strip()
    minutes = 0
    seconds = 0
    dt = _parse_dt(r.get("date_h_appel"))
    if dt is not None:
        total = max(0, int((datetime.now() - dt).total_seconds()))
        minutes = total // 60
        seconds = total % 60
    return {
        "appel_en_cours": appel_en_cours,
        "ope_appel_id": ope_appel_id,
        "ope_appel_nom": nom_ope,
        "date_h_appel": date_h_appel_iso,
        "duree_minutes": minutes,
        "duree_secondes": seconds,
    }


def prendre_appel(id_tk_liste: int, user_id: int, force: bool = False) -> dict:
    """Pose le verrou ope. Confirmation si un autre a deja le verrou."""
    db_bo = get_pg_connection("ticket_bo")
    r = db_bo.query_one(
        """SELECT id_tk_call_sfr, id_salarie, appel_en_cours, ope_appel,
                  date_h_appel, date_deb_prise_en_charge,
                  nom_client, nom_marital_client, prenom_client
             FROM ticket_bo.pgt_tk_call_sfr
            WHERE id_tk_liste = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_tk_liste),),
    )
    if not r:
        return {"error": "Ticket introuvable"}
    id_call_sfr = _to_int(r.get("id_tk_call_sfr"))
    id_salarie = _to_int(r.get("id_salarie"))

    if not force:
        appel_en_cours = _bool(r.get("appel_en_cours"))
        ope_appel_id = _to_int(r.get("ope_appel"))
        date_h_appel = _parse_dt(r.get("date_h_appel"))
        if (appel_en_cours and ope_appel_id and ope_appel_id != user_id) or (
            not appel_en_cours and date_h_appel is not None
            and ope_appel_id != user_id
        ):
            return {"needs_confirm": True, "peek": peek_verrou(id_tk_liste)}

    now = _sql_now_wd()
    db_bo.query(
        """UPDATE ticket_bo.pgt_tk_call_sfr SET
              appel_en_cours = TRUE, ope_appel = ?,
              date_h_appel = ?, modif_date = ?
            WHERE id_tk_call_sfr = ?""",
        (int(user_id), now, now, id_call_sfr),
    )
    if not _parse_dt(r.get("date_deb_prise_en_charge")):
        db_bo.query(
            """UPDATE ticket_bo.pgt_tk_call_sfr SET
                  date_deb_prise_en_charge = ?, modif_date = ?
                WHERE id_tk_call_sfr = ?""",
            (now, now, id_call_sfr),
        )

    sms_result = _envoyer_sms_prise_appel(
        id_salarie, user_id,
        r.get("nom_client"), r.get("nom_marital_client"),
        r.get("prenom_client"),
    )
    return {"ok": True, "sms": sms_result}


def lacher_appel(id_tk_liste: int) -> dict:
    db_bo = get_pg_connection("ticket_bo")
    r = db_bo.query_one(
        """SELECT id_tk_call_sfr, date_fin_prise_en_charge
             FROM ticket_bo.pgt_tk_call_sfr WHERE id_tk_liste = ?""",
        (int(id_tk_liste),),
    )
    if not r:
        return {"error": "Ticket introuvable"}
    id_call_sfr = _to_int(r.get("id_tk_call_sfr"))
    now = _sql_now_wd()
    if not _parse_dt(r.get("date_fin_prise_en_charge")):
        db_bo.query(
            """UPDATE ticket_bo.pgt_tk_call_sfr SET
                  appel_en_cours = FALSE,
                  date_fin_prise_en_charge = ?, modif_date = ?
                WHERE id_tk_call_sfr = ?""",
            (now, now, id_call_sfr),
        )
    else:
        db_bo.query(
            """UPDATE ticket_bo.pgt_tk_call_sfr SET
                  appel_en_cours = FALSE, modif_date = ?
                WHERE id_tk_call_sfr = ?""",
            (now, id_call_sfr),
        )
    return {"ok": True}


# --- SMS ---------------------------------------------------------------

def _envoyer_sms_prise_appel(id_vendeur, id_ope,
                              nom_client, nom_marital, prenom_client) -> str:
    from app.shared.notifications.sms import envoi_sms
    gsm = _get_gsm_vendeur(id_vendeur)
    if not gsm:
        return "Pas de GSM vendeur (SMS non envoye)"
    nom_clt = _format_nom_client_sms(nom_client, nom_marital, prenom_client)
    texte = (
        f"Attention, vous allez bientot recevoir un appel du CALL "
        f"pour votre client {nom_clt}."
    )
    return envoi_sms(texte, gsm, emetteur="Omaya-Call")


def _envoyer_sms_renvoi_complement(id_vendeur, nom, nom_marital, prenom) -> str:
    from app.shared.notifications.sms import envoi_sms
    gsm = _get_gsm_vendeur(id_vendeur)
    if not gsm:
        return "Pas de GSM vendeur"
    nom_clt = _format_nom_client_sms(nom, nom_marital, prenom)
    texte = f"Attention, votre panier pour le client {nom_clt} est renvoye pour complement."
    return envoi_sms(texte, gsm, emetteur="Omaya-Call")


def _envoyer_sms_renvoi_lettre_resil(id_vendeur, nom, nom_marital, prenom) -> str:
    from app.shared.notifications.sms import envoi_sms
    gsm = _get_gsm_vendeur(id_vendeur)
    if not gsm:
        return "Pas de GSM vendeur"
    nom_clt = _format_nom_client_sms(nom, nom_marital, prenom)
    texte = f"Attention, votre panier pour le client {nom_clt} est renvoye car il manque la lettre de resiliation."
    return envoi_sms(texte, gsm, emetteur="Omaya-Call")


def _envoyer_sms_validation_degroupage(id_vendeur, nom, nom_marital, prenom) -> str:
    from app.shared.notifications.sms import envoi_sms
    gsm = _get_gsm_vendeur(id_vendeur)
    if not gsm:
        return "Pas de GSM vendeur"
    nom_clt = _format_nom_client_sms(nom, nom_marital, prenom)
    texte = f"Le CALL vient d'envoyer le panier degroupe SFR pour votre client {nom_clt}."
    return envoi_sms(texte, gsm, emetteur="Omaya-Call")


# --- Actions panier ----------------------------------------------------

def annuler_ligne_panier(id_panier: int, motifs: list[str],
                          precisions: str) -> dict:
    if not motifs and not (precisions or "").strip():
        return {"error": "Merci d'ajouter un motif ou des informations complementaires"}
    parts = []
    if motifs:
        parts.append("Motif(s) d'annulation :\n" + "\n".join(f"  - {m}" for m in motifs))
    if (precisions or "").strip():
        parts.append(f"Informations complementaires:\n{precisions.strip()}")
    motif_str = "\n".join(parts)
    db_bo = get_pg_connection("ticket_bo")
    now = _sql_now_wd()
    db_bo.query(
        """UPDATE ticket_bo.pgt_tk_call_sfr_panier SET
              statut_prod = 2, motif_annulation = ?, modif_date = ?
            WHERE id_tk_call_sfr_panier = ?""",
        (motif_str, now, int(id_panier)),
    )
    return {"ok": True}


def _action_vente_finale(
    id_tk_liste: int, payload: dict, new_statut: int,
    send_sms_renvoi: bool = False, send_sms_si_degroupage: bool = False,
    send_sms_lettre_resil: bool = False, extra_info_vente: str = "",
) -> dict:
    """Logique commune AnnulVente / ValideVente / RenvoiPanier / RenvoiLettreResil."""
    db_bo = get_pg_connection("ticket_bo")
    db_ticket = get_pg_connection("ticket")
    now = _sql_now_wd()

    if payload:
        save_vente_infos(id_tk_liste, payload)

    r_call = db_bo.query_one(
        """SELECT id_tk_call_sfr, id_salarie, appel_en_cours, info_vente,
                  nom_client, nom_marital_client, prenom_client
             FROM ticket_bo.pgt_tk_call_sfr WHERE id_tk_liste = ?""",
        (int(id_tk_liste),),
    )
    if not r_call:
        return {"error": "Ticket introuvable"}
    id_call_sfr = _to_int(r_call.get("id_tk_call_sfr"))
    id_salarie = _to_int(r_call.get("id_salarie"))
    appel_en_cours = _bool(r_call.get("appel_en_cours"))
    nom_client = r_call.get("nom_client") or ""
    nom_marital = r_call.get("nom_marital_client") or ""
    prenom_client = r_call.get("prenom_client") or ""

    r_liste = db_ticket.query_one(
        """SELECT id_tk_statut FROM ticket.pgt_tk_liste
            WHERE id_tk_liste = ?""",
        (int(id_tk_liste),),
    )
    statut_avant = _to_int((r_liste or {}).get("id_tk_statut"))

    db_ticket.query(
        """UPDATE ticket.pgt_tk_liste SET
              id_tk_statut = ?, modif_date = ?
            WHERE id_tk_liste = ?""",
        (int(new_statut), now, int(id_tk_liste)),
    )

    if extra_info_vente:
        cur_info = (r_call.get("info_vente") or "").strip()
        new_info = f"{cur_info}\n{extra_info_vente}".strip() if cur_info else extra_info_vente
        db_bo.query(
            """UPDATE ticket_bo.pgt_tk_call_sfr SET
                  info_vente = ?, modif_date = ?
                WHERE id_tk_call_sfr = ?""",
            (new_info, now, id_call_sfr),
        )

    if appel_en_cours:
        db_bo.query(
            """UPDATE ticket_bo.pgt_tk_call_sfr SET
                  appel_en_cours = FALSE,
                  date_fin_prise_en_charge = ?, modif_date = ?
                WHERE id_tk_call_sfr = ?""",
            (now, now, id_call_sfr),
        )

    sms_result = ""
    if send_sms_renvoi:
        sms_result = _envoyer_sms_renvoi_complement(
            id_salarie, nom_client, nom_marital, prenom_client,
        )
    elif send_sms_lettre_resil:
        sms_result = _envoyer_sms_renvoi_lettre_resil(
            id_salarie, nom_client, nom_marital, prenom_client,
        )
    elif send_sms_si_degroupage and statut_avant == 34:
        sms_result = _envoyer_sms_validation_degroupage(
            id_salarie, nom_client, nom_marital, prenom_client,
        )

    return {"ok": True, "sms": sms_result}


def annuler_vente(id_tk_liste: int, payload: dict) -> dict:
    return _action_vente_finale(id_tk_liste, payload, new_statut=14)


def valider_vente(id_tk_liste: int, payload: dict) -> dict:
    return _action_vente_finale(
        id_tk_liste, payload, new_statut=15, send_sms_si_degroupage=True,
    )


def renvoyer_complement(id_tk_liste: int) -> dict:
    return _action_vente_finale(
        id_tk_liste, payload={}, new_statut=28, send_sms_renvoi=True,
    )


def renvoyer_lettre_resil(id_tk_liste: int, user_nom: str,
                            user_prenom: str) -> dict:
    note = (
        f"Ticket renvoye pour lettre de resil le "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')} "
        f"par {user_nom} {_capitalize(user_prenom)}"
    )
    return _action_vente_finale(
        id_tk_liste, payload={}, new_statut=28,
        send_sms_lettre_resil=True, extra_info_vente=note,
    )


# --- Documents + Lettre resil + Test eligibilite -----------------------

DOC_BASE_URL = "https://rest.omaya.fr/DocOmaya"


def _url_exists(url: str, timeout: float = 1.5) -> bool:
    """HEAD HTTP : True si le fichier existe."""
    import urllib.request
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def _first_existing(*urls: str) -> tuple[str, str]:
    """Retourne (url, kind) du 1er URL existant, kind = 'pdf' | 'image' | ''."""
    for url in urls:
        if _url_exists(url):
            low = url.lower()
            kind = "pdf" if low.endswith(".pdf") else "image"
            return url, kind
    return "", ""


def load_documents(id_tk_liste: int, client_pro: bool = False) -> dict:
    cin_url, cin_kind = _first_existing(
        f"{DOC_BASE_URL}/{id_tk_liste}_PieceIdentite.pdf",
        f"{DOC_BASE_URL}/{id_tk_liste}_PieceIdentite.png",
        f"{DOC_BASE_URL}/{id_tk_liste}_PieceIdentite.jpg",
        f"{DOC_BASE_URL}/{id_tk_liste}_CIN.jpg",
    )
    kbis_url, kbis_kind = ("", "")
    if client_pro:
        kbis_url, kbis_kind = _first_existing(
            f"{DOC_BASE_URL}/{id_tk_liste}_KBIS.pdf",
            f"{DOC_BASE_URL}/{id_tk_liste}_KBIS.png",
            f"{DOC_BASE_URL}/{id_tk_liste}_KBIS.jpg",
        )
    return {
        "cin": {"url": cin_url, "kind": cin_kind},
        "kbis": {"url": kbis_url, "kind": kbis_kind},
    }


def load_lettre_resil(id_tk_liste: int, id_panier: int) -> dict:
    url, kind = _first_existing(
        f"{DOC_BASE_URL}/{id_tk_liste}_{id_panier}_LettreResil.pdf",
        f"{DOC_BASE_URL}/{id_tk_liste}_{id_panier}_LettreResil.png",
        f"{DOC_BASE_URL}/{id_tk_liste}_LettreResil.pdf",
        f"{DOC_BASE_URL}/{id_tk_liste}_LettreResil.png",
    )
    return {"url": url, "kind": kind}


def load_panier_ligne_image(id_panier: int) -> str:
    """Charge l'image TestEligibilite d'une ligne (FIBRE only). data-URL b64."""
    db_bo = get_pg_connection("ticket_bo")
    r = db_bo.query_one(
        """SELECT type, test_eligibilite
             FROM ticket_bo.pgt_tk_call_sfr_panier
            WHERE id_tk_call_sfr_panier = ?""",
        (int(id_panier),),
    )
    if not r:
        return ""
    if (r.get("type") or "").strip().upper() != "FIBRE":
        return ""
    raw = r.get("test_eligibilite")
    if not raw:
        return ""
    import base64
    if isinstance(raw, (bytes, bytearray)):
        b64 = base64.b64encode(raw).decode("ascii")
    else:
        try:
            b64 = base64.b64encode(bytes(raw)).decode("ascii")
        except Exception:
            return ""
    return f"data:image/png;base64,{b64}"
