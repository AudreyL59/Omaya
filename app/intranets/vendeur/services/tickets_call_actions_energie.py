"""
Actions ecriture ticket Call Energie (cote Vendeur, PG).

Portage direct du service call/energie/services/fiche.py en PG.
Reutilise les helpers du service Fibre Vendeur (get_gsm, _format_nom_sms,
etc.) via import.

Cf. memoire feedback_fiche_ticket_modal_sync.
"""
from __future__ import annotations

import logging
from datetime import datetime

from app.core.database.pg import get_pg_connection
from app.intranets.vendeur.services.tickets_call_fiche_fibre import (
    _bool, _capitalize, _to_int,
)
from app.intranets.vendeur.services.tickets_call_actions_fibre import (
    _dates_to_compact, _first_existing, _format_nom_client_sms,
    _get_gsm_vendeur, _parse_dt, _sql_now_wd, DOC_BASE_URL,
)


logger = logging.getLogger(__name__)


# --- Save --------------------------------------------------------------

def save_vente_infos(id_tk_liste: int, payload: dict) -> dict:
    """UPDATE pgt_tk_call (Energie) : infos client + vente (sans anomalie
    ni MobPropoVend contrairement a Fibre).
    """
    db = get_pg_connection("ticket_bo")
    c = payload.get("client", {}) or {}
    v = payload.get("vente", {}) or {}
    now = _sql_now_wd()
    db.query(
        """UPDATE ticket_bo.pgt_tk_call SET
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


# Mapping des champs optionnels de save_offre Energie
# (nom_python_snake -> (nom_colonne_pg, transform))
_OFFRE_FIELDS = [
    ("statut_prod", "statut_prod", lambda v: _to_int(v)),
    ("num_bs", "num_bs", lambda v: (v or "")),
    ("opt_mandat", "opt_mandat", lambda v: _bool(v)),
    # opt_maintenance : colonne absente du schema PG interne (existe cote
    # HFSQL OVH), on l'ignore silencieusement dans les save.
    # ("opt_maintenance", "opt_maintenance", lambda v: _bool(v)),
    ("format_numerique", "format_numerique", lambda v: _bool(v)),
    ("opt_accept_com_parte", "opt_accept_com_parte", lambda v: _bool(v)),
    ("opt_consent_consult_distri", "opt_consent_consult_distri", lambda v: _bool(v)),
    ("opt_e_communication", "opt_e_communication", lambda v: _bool(v)),
    ("opt_e_facture", "opt_e_facture", lambda v: _bool(v)),
    ("opt_optin_commercial", "opt_optin_commercial", lambda v: _bool(v)),
    ("opt_energie_verte_elec", "opt_energie_verte_elec", lambda v: _bool(v)),
    ("opt_energie_verte_gaz", "opt_energie_verte_gaz", lambda v: _bool(v)),
    ("opt_reforestation", "opt_reforestation", lambda v: _bool(v)),
    ("opt_mail", "opt_mail", lambda v: _bool(v)),
    ("date_activ", "date_entree", lambda v: _dates_to_compact(v)),
    ("ref_client_oen", "observations", lambda v: (v or "")),
]


def save_offre(id_panier: int, payload: dict) -> dict:
    """UPDATE pgt_tk_call_panier : SET dynamique (seuls les champs
    fournis dans le payload sont modifies). Meme comportement que le
    service source HFSQL.

    Note : la copie de clarif OEN vers Call_OhmEnergie est SKIP cote
    Vendeur (pas d'acces au filesystem partage OVH).
    """
    db = get_pg_connection("ticket_bo")
    now = _sql_now_wd()
    sets: list[str] = ["modif_date = ?"]
    params: list = [now]
    for py_key, pg_col, transform in _OFFRE_FIELDS:
        if py_key in payload:
            sets.append(f"{pg_col} = ?")
            params.append(transform(payload.get(py_key)))
            # Cas NumBS : ecrire aussi la date de saisie
            if py_key == "num_bs" and payload.get("num_bs"):
                sets.append("num_date_saisie = ?")
                params.append(now)
    params.append(int(id_panier))
    sql = (
        "UPDATE ticket_bo.pgt_tk_call_panier SET "
        + ", ".join(sets)
        + " WHERE id_tk_call_panier = ?"
    )
    db.query(sql, tuple(params))
    return {"ok": True}


# --- Verrou ------------------------------------------------------------

def peek_verrou(id_tk_liste: int) -> dict:
    db_bo = get_pg_connection("ticket_bo")
    db_rh = get_pg_connection("rh")
    r = db_bo.query_one(
        """SELECT id_tk_call, appel_en_cours, ope_appel, date_h_appel
             FROM ticket_bo.pgt_tk_call
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
    db_bo = get_pg_connection("ticket_bo")
    r = db_bo.query_one(
        """SELECT id_tk_call, id_salarie, appel_en_cours, ope_appel,
                  date_h_appel, date_deb_prise_en_charge,
                  nom_client, nom_marital_client, prenom_client
             FROM ticket_bo.pgt_tk_call
            WHERE id_tk_liste = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_tk_liste),),
    )
    if not r:
        return {"error": "Ticket introuvable"}
    id_call = _to_int(r.get("id_tk_call"))
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
        """UPDATE ticket_bo.pgt_tk_call SET
              appel_en_cours = TRUE, ope_appel = ?,
              date_h_appel = ?, modif_date = ?
            WHERE id_tk_call = ?""",
        (int(user_id), now, now, id_call),
    )
    if not _parse_dt(r.get("date_deb_prise_en_charge")):
        db_bo.query(
            """UPDATE ticket_bo.pgt_tk_call SET
                  date_deb_prise_en_charge = ?, modif_date = ?
                WHERE id_tk_call = ?""",
            (now, now, id_call),
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
        """SELECT id_tk_call, date_fin_prise_en_charge
             FROM ticket_bo.pgt_tk_call WHERE id_tk_liste = ?""",
        (int(id_tk_liste),),
    )
    if not r:
        return {"error": "Ticket introuvable"}
    id_call = _to_int(r.get("id_tk_call"))
    now = _sql_now_wd()
    if not _parse_dt(r.get("date_fin_prise_en_charge")):
        db_bo.query(
            """UPDATE ticket_bo.pgt_tk_call SET
                  appel_en_cours = FALSE,
                  date_fin_prise_en_charge = ?, modif_date = ?
                WHERE id_tk_call = ?""",
            (now, now, id_call),
        )
    else:
        db_bo.query(
            """UPDATE ticket_bo.pgt_tk_call SET
                  appel_en_cours = FALSE, modif_date = ?
                WHERE id_tk_call = ?""",
            (now, id_call),
        )
    return {"ok": True}


# --- SMS ---------------------------------------------------------------

def _envoyer_sms_prise_appel(id_vendeur, id_ope,
                              nom, nom_marital, prenom) -> str:
    from app.shared.notifications.sms import envoi_sms
    gsm = _get_gsm_vendeur(id_vendeur)
    if not gsm:
        return "Pas de GSM vendeur (SMS non envoye)"
    nom_clt = _format_nom_client_sms(nom, nom_marital, prenom)
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


def _envoyer_sms_renvoi_clarification(id_vendeur, nom, nom_marital, prenom) -> str:
    from app.shared.notifications.sms import envoi_sms
    gsm = _get_gsm_vendeur(id_vendeur)
    if not gsm:
        return "Pas de GSM vendeur"
    nom_clt = _format_nom_client_sms(nom, nom_marital, prenom)
    texte = (
        f"Attention, votre panier pour le client {nom_clt} est renvoye "
        f"car il manque la fiche de clarification."
    )
    return envoi_sms(texte, gsm, emetteur="Omaya-Call")


# --- Actions panier ----------------------------------------------------

def annuler_ligne_panier(id_panier: int, motifs: list[str],
                          precisions: str) -> dict:
    """Cote Energie, un motif est OBLIGATOIRE (pas de fallback
    precisions seule contrairement a Fibre)."""
    if not motifs:
        return {"error": "Merci d'ajouter un motif d'annulation"}
    motif_str = "Motif(s) d'annulation :\n" + "\n".join(f"  - {m}" for m in motifs)
    if (precisions or "").strip():
        motif_str += f"\nInformations complementaires:\n{precisions.strip()}"
    db_bo = get_pg_connection("ticket_bo")
    now = _sql_now_wd()
    db_bo.query(
        """UPDATE ticket_bo.pgt_tk_call_panier SET
              statut_prod = 2, motif_annulation = ?, modif_date = ?
            WHERE id_tk_call_panier = ?""",
        (motif_str, now, int(id_panier)),
    )
    return {"ok": True}


def _action_vente_finale(
    id_tk_liste: int, payload: dict, new_statut: int,
    sms_kind: str = "",
    extra_info_vente: str = "",
) -> dict:
    db_bo = get_pg_connection("ticket_bo")
    db_ticket = get_pg_connection("ticket")
    now = _sql_now_wd()

    if extra_info_vente:
        r_cur = db_bo.query_one(
            "SELECT info_vente FROM ticket_bo.pgt_tk_call WHERE id_tk_liste = ?",
            (int(id_tk_liste),),
        )
        prev = ((r_cur or {}).get("info_vente") or "").strip()
        new_info = (prev + "\n" if prev else "") + extra_info_vente
        if payload:
            v = payload.setdefault("vente", {}) or {}
            v["info_vente"] = new_info
        else:
            db_bo.query(
                """UPDATE ticket_bo.pgt_tk_call SET
                      info_vente = ?, modif_date = ?
                    WHERE id_tk_liste = ?
                      AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
                (new_info, now, int(id_tk_liste)),
            )

    if payload and ("client" in payload or "vente" in payload):
        save_vente_infos(id_tk_liste, payload)

    r_call = db_bo.query_one(
        """SELECT id_tk_call, id_salarie, appel_en_cours,
                  nom_client, nom_marital_client, prenom_client
             FROM ticket_bo.pgt_tk_call WHERE id_tk_liste = ?""",
        (int(id_tk_liste),),
    )
    if not r_call:
        return {"error": "Ticket introuvable"}
    id_call = _to_int(r_call.get("id_tk_call"))
    id_salarie = _to_int(r_call.get("id_salarie"))
    appel_en_cours = _bool(r_call.get("appel_en_cours"))

    db_ticket.query(
        """UPDATE ticket.pgt_tk_liste SET
              id_tk_statut = ?, modif_date = ?
            WHERE id_tk_liste = ?""",
        (int(new_statut), now, int(id_tk_liste)),
    )

    if appel_en_cours:
        db_bo.query(
            """UPDATE ticket_bo.pgt_tk_call SET
                  appel_en_cours = FALSE,
                  date_fin_prise_en_charge = ?, modif_date = ?
                WHERE id_tk_call = ?""",
            (now, now, id_call),
        )

    sms_result = ""
    nom_client = r_call.get("nom_client") or ""
    nom_marital = r_call.get("nom_marital_client") or ""
    prenom_client = r_call.get("prenom_client") or ""
    if sms_kind == "renvoi_complement":
        sms_result = _envoyer_sms_renvoi_complement(
            id_salarie, nom_client, nom_marital, prenom_client,
        )
    elif sms_kind == "renvoi_clarification":
        sms_result = _envoyer_sms_renvoi_clarification(
            id_salarie, nom_client, nom_marital, prenom_client,
        )

    return {"ok": True, "sms": sms_result}


def annuler_vente(id_tk_liste: int, payload: dict) -> dict:
    return _action_vente_finale(id_tk_liste, payload, new_statut=14)


def valider_vente(id_tk_liste: int, payload: dict) -> dict:
    return _action_vente_finale(id_tk_liste, payload, new_statut=15)


def renvoyer_complement(id_tk_liste: int) -> dict:
    return _action_vente_finale(
        id_tk_liste, payload={}, new_statut=28,
        sms_kind="renvoi_complement",
    )


def renvoyer_clarification(id_tk_liste: int, user_nom: str,
                            user_prenom: str) -> dict:
    note = (
        f"Ticket renvoye pour fiche clarification le "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')} "
        f"par {user_nom} {_capitalize(user_prenom)}"
    )
    return _action_vente_finale(
        id_tk_liste, payload={}, new_statut=28,
        sms_kind="renvoi_clarification", extra_info_vente=note,
    )


# --- Documents ---------------------------------------------------------

def load_clarification(id_panier: int) -> dict:
    url, kind = _first_existing(
        f"{DOC_BASE_URL}/{id_panier}_Clarification.pdf",
    )
    return {"url": url, "kind": kind}


def load_documents(id_tk_liste: int, client_pro: bool = False) -> dict:
    """Documents Energie : CIN + KBIS (si Pro) + Justif (specifique)."""
    db_bo = get_pg_connection("ticket_bo")
    r = db_bo.query_one(
        """SELECT id_tk_call FROM ticket_bo.pgt_tk_call
            WHERE id_tk_liste = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_tk_liste),),
    )
    id_call = _to_int((r or {}).get("id_tk_call"))

    cin_url, cin_kind = "", ""
    if id_call:
        cin_url, cin_kind = _first_existing(
            f"{DOC_BASE_URL}/{id_tk_liste}_PieceIdentite.pdf",
            f"{DOC_BASE_URL}/{id_call}_PieceIdentite.png",
            f"{DOC_BASE_URL}/{id_call}_CIN.jpg",
        )

    kbis_url, kbis_kind = "", ""
    if client_pro:
        kbis_url, kbis_kind = _first_existing(
            f"{DOC_BASE_URL}/{id_tk_liste}_KBIS.pdf",
            f"{DOC_BASE_URL}/{id_tk_liste}_KBIS.png",
        )

    justif_url, justif_kind = "", ""
    if id_call:
        justif_url, justif_kind = _first_existing(
            f"{DOC_BASE_URL}/{id_call}_Justif.png",
            f"{DOC_BASE_URL}/{id_call}_Justif.jpg",
        )

    return {
        "cin": {"url": cin_url, "kind": cin_kind},
        "kbis": {"url": kbis_url, "kind": kbis_kind},
        "justif": {"url": justif_url, "kind": justif_kind},
    }
