"""
Fiche ticket Call Fibre (cote Vendeur, PG).

Portage direct de app/intranets/call/fibre/services/fiche.py mais avec
get_pg_connection au lieu de get_connection (HFSQL).

Cf. memoire feedback_fiche_ticket_modal_sync : cette copie doit rester
en sync avec le service source cote /call/fibre.
"""
from __future__ import annotations

import logging
import time as _time
from typing import Any

from app.core.database.pg import get_pg_connection


logger = logging.getLogger(__name__)


# --- Helpers -------------------------------------------------------------

def _to_int(v, default: int = 0) -> int:
    try:
        return int(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _str_id(v) -> str:
    n = _to_int(v)
    return str(n) if n else ""


def _bool(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    s = str(v).strip().lower()
    return s in ("true", "1", "vrai", "t", "y", "yes")


def _iso_date(v: Any) -> str:
    if v is None:
        return ""
    s = str(v)[:10]
    if s.startswith("1900") or s.startswith("0000"):
        return ""
    return s


def _capitalize(s: str) -> str:
    if not s:
        return ""
    return s[0].upper() + s[1:].lower() if len(s) > 1 else s.upper()


def _civilite_to_prefix(civ: int) -> str:
    return "M." if (civ or 0) <= 1 else "Mme"


def _format_nom_client(civ: int, nom: str, nom_marital: str, prenom: str) -> str:
    parts = [_civilite_to_prefix(civ), (nom or "").strip()]
    if (nom_marital or "").strip():
        parts.append(f"ép {nom_marital.strip()}")
    parts.append(_capitalize((prenom or "").strip()))
    return " ".join(p for p in parts if p)


def _format_ville(ville: str) -> str:
    if not ville:
        return ""
    if "(" in ville:
        return ville.split("(")[0].strip()
    return ville.strip()


def _mask_phone(num: str) -> str:
    if not num:
        return ""
    n = num.strip()
    if len(n) < 2:
        return n
    return n[:-2] + "xx"


# --- Referentiels (cache 10min) ------------------------------------------

_TYPE_ANOMALIE_CACHE: list[dict] | None = None
_TYPE_ANOMALIE_AT: float = 0.0
_TYPE_ANOMALIE_TTL = 600.0

_OFFRES_REF_CACHE: dict[int, str] | None = None
_OFFRES_REF_AT: float = 0.0
_OFFRES_REF_TTL = 600.0


def _load_motifs_anomalie() -> list[dict]:
    """Referentiel pgt_tk_callsfr_typeanomalie (cache 10min).

    Note : le nom PG de la table est 'pgt_tk_callsfr_typeanomalie'
    (sans underscore entre call/sfr et type/anomalie), cf. schema PG
    genere depuis le XLSX HFSQL.
    """
    global _TYPE_ANOMALIE_CACHE, _TYPE_ANOMALIE_AT
    now = _time.monotonic()
    if (_TYPE_ANOMALIE_CACHE is not None
            and now - _TYPE_ANOMALIE_AT < _TYPE_ANOMALIE_TTL):
        return _TYPE_ANOMALIE_CACHE
    db = get_pg_connection("ticket_bo")
    try:
        rows = db.query(
            """SELECT id_tk_call_sfr_type_anomalie, lib_type_anomalie
                 FROM ticket_bo.pgt_tk_callsfr_typeanomalie
                WHERE (modif_elem IS NULL
                       OR modif_elem NOT LIKE '%suppr%')
                ORDER BY id_tk_call_sfr_type_anomalie ASC""",
        ) or []
    except Exception:
        logger.exception("_load_motifs_anomalie")
        rows = []
    out = [
        {
            "id": _to_int(r.get("id_tk_call_sfr_type_anomalie")),
            "label": (r.get("lib_type_anomalie") or "").strip(),
        }
        for r in rows
    ]
    _TYPE_ANOMALIE_CACHE = out
    _TYPE_ANOMALIE_AT = now
    return out


def _load_offres_ref() -> dict[int, str]:
    """Referentiel adv.pgt_sfr_offres_provad (cache 10min)."""
    global _OFFRES_REF_CACHE, _OFFRES_REF_AT
    now = _time.monotonic()
    if (_OFFRES_REF_CACHE is not None
            and now - _OFFRES_REF_AT < _OFFRES_REF_TTL):
        return _OFFRES_REF_CACHE
    db = get_pg_connection("adv")
    try:
        rows = db.query(
            """SELECT id_offres_sfr, lib_offre
                 FROM adv.pgt_sfr_offres_provad""",
        ) or []
    except Exception:
        logger.exception("_load_offres_ref")
        return {}
    _OFFRES_REF_CACHE = {
        _to_int(r.get("id_offres_sfr")): (r.get("lib_offre") or "").strip()
        for r in rows
    }
    _OFFRES_REF_AT = now
    return _OFFRES_REF_CACHE


# --- Point d'entree ------------------------------------------------------

def load_fiche(id_tk_liste: int, current_user_id: int = 0) -> dict:
    """Charge la fiche complete d'un ticket Call Fibre (PG).

    current_user_id : id_salarie du user connecte. Sert au demasquage
    des mobiles quand il a pris l'appel (verrou pose).
    """
    from concurrent.futures import ThreadPoolExecutor
    db_ticket = get_pg_connection("ticket")
    db_bo = get_pg_connection("ticket_bo")
    db_rh = get_pg_connection("rh")

    # Vague 1 : TK_Liste + TK_CallSFR + referentiels en parallele
    with ThreadPoolExecutor(max_workers=4) as pool:
        f_liste = pool.submit(
            db_ticket.query_one,
            """SELECT id_tk_liste, id_tk_statut, op_crea, cloturee, date_cloture
                 FROM ticket.pgt_tk_liste
                WHERE id_tk_liste = ?""",
            (int(id_tk_liste),),
        )
        f_call = pool.submit(
            db_bo.query_one,
            """SELECT id_tk_call_sfr, id_tk_liste, id_salarie,
                      civilite_client, nom_client, nom_marital_client,
                      prenom_client, date_naiss, dep_naiss, type_logement,
                      adresse1, adresse2, cp, ville,
                      adr_mail, mobile1, mobile2,
                      appel_en_cours, date_h_appel, ope_appel, ref_appel,
                      motif_annulation, date_deb_prise_en_charge,
                      date_fin_prise_en_charge,
                      intervention_vend, mob_propo_vend, info_vente,
                      anomalie_mobile, id_tk_call_sfr_type_anomalie,
                      info_cplt_anomalie, opt_rappel, opt_partenaire,
                      client_pro, client_rs, client_siret
                 FROM ticket_bo.pgt_tk_call_sfr
                WHERE id_tk_liste = ?
                  AND (modif_elem IS NULL
                       OR modif_elem NOT LIKE '%suppr%')""",
            (int(id_tk_liste),),
        )
        f_motifs = pool.submit(_load_motifs_anomalie)
        f_offres = pool.submit(_load_offres_ref)
        tk_liste = f_liste.result()
        tc = f_call.result()
        motifs_anomalie = f_motifs.result()
        offre_libs = f_offres.result()

    if not tk_liste:
        return {"error": "Ticket introuvable"}
    if not tc:
        return {"error": "Pas de TK_CallSFR pour ce ticket"}

    id_call_sfr = _to_int(tc.get("id_tk_call_sfr"))
    id_salarie = _to_int(tc.get("id_salarie"))
    id_tk_statut = _to_int(tk_liste.get("id_tk_statut"))
    appel_en_cours = _bool(tc.get("appel_en_cours"))
    ope_appel_id = _to_int(tc.get("ope_appel"))

    is_my_call = appel_en_cours and ope_appel_id == current_user_id
    mobile1_raw = (tc.get("mobile1") or "").strip()
    mobile2_raw = (tc.get("mobile2") or "").strip()
    mobile1 = mobile1_raw if is_my_call else _mask_phone(mobile1_raw)
    mobile2 = mobile2_raw if is_my_call else _mask_phone(mobile2_raw)

    # Vague 2 : Salarie + Salarie_Coordonnees + Panier en parallele
    nom_vend = ""
    prenom_vend = ""
    gsm_vend_raw = ""
    ope_en_cours_nom = ""
    need_ope = appel_en_cours and ope_appel_id and not is_my_call
    with ThreadPoolExecutor(max_workers=4) as pool:
        f_sal = pool.submit(
            db_rh.query_one,
            """SELECT nom, prenom FROM rh.pgt_salarie
                WHERE id_salarie = ?""",
            (id_salarie,),
        ) if id_salarie else None
        f_coord = pool.submit(
            db_rh.query_one,
            """SELECT tel_mob FROM rh.pgt_salarie_coordonnees
                WHERE id_salarie = ?""",
            (id_salarie,),
        ) if id_salarie else None
        f_ope = pool.submit(
            db_rh.query_one,
            """SELECT nom, prenom FROM rh.pgt_salarie
                WHERE id_salarie = ?""",
            (ope_appel_id,),
        ) if need_ope else None
        f_panier = pool.submit(
            db_bo.query,
            """SELECT id_tk_call_sfr_panier, id_offres_sfr, opt_tv, type,
                      portabilite, type_vente, motif_annulation, statut_prod,
                      num_portabilite, num_prise_rio, num_prise_optique,
                      opt_choisies
                 FROM ticket_bo.pgt_tk_call_sfr_panier
                WHERE id_tk_call_sfr = ?
                  AND (modif_elem IS NULL
                       OR modif_elem NOT LIKE '%suppr%')""",
            (id_call_sfr,),
        )
        s = f_sal.result() if f_sal else None
        coord = f_coord.result() if f_coord else None
        ope = f_ope.result() if f_ope else None
        rows_panier = f_panier.result() or []

    if s:
        nom_vend = (s.get("nom") or "").strip()
        prenom_vend = _capitalize((s.get("prenom") or "").strip())
    if coord:
        gsm_vend_raw = (coord.get("tel_mob") or "").strip()
    if ope:
        ope_en_cours_nom = (
            f"{(ope.get('nom') or '').strip()} "
            f"{_capitalize((ope.get('prenom') or '').strip())}"
        ).strip()
    gsm_vend = gsm_vend_raw if is_my_call else _mask_phone(gsm_vend_raw)

    panier = []
    for p in rows_panier:
        id_off = _to_int(p.get("id_offres_sfr"))
        panier.append({
            "id": _str_id(p.get("id_tk_call_sfr_panier")),
            "id_offre": _str_id(p.get("id_offres_sfr")),
            "lib_offre": offre_libs.get(id_off, ""),
            "type": (p.get("type") or "").strip(),
            "opt_tv": _bool(p.get("opt_tv")),
            "portabilite": _bool(p.get("portabilite")),
            "type_vente": _to_int(p.get("type_vente")),
            "statut_prod": _to_int(p.get("statut_prod")),
            "motif_annulation": (p.get("motif_annulation") or "").strip(),
            "num_portabilite": (p.get("num_portabilite") or "").strip(),
            "num_rio": (p.get("num_prise_rio") or "").strip(),
            "num_prise_optique": (p.get("num_prise_optique") or "").strip(),
            "opt_choisies": (p.get("opt_choisies") or "").strip(),
        })

    statuts_vente = [
        {"id": 0, "label": "Non défini"},
        {"id": 1, "label": "Validé"},
        {"id": 2, "label": "Annulé"},
        {"id": 3, "label": "Num BS ajouté"},
    ]
    if id_tk_statut == 15:
        statuts_vente.append({"id": 4, "label": "Validé - Différé"})

    nb_prod_total = len(panier)
    nb_prod_valide = sum(1 for p in panier if p["statut_prod"] == 1)
    nb_prod_annule = sum(1 for p in panier if p["statut_prod"] == 2)
    btn_valider_actif = (
        nb_prod_valide > 0
        and (nb_prod_valide + nb_prod_annule) == nb_prod_total
    )
    btn_annuler_actif = nb_prod_total > 0 and nb_prod_annule == nb_prod_total

    return {
        "id_ticket": _str_id(id_tk_liste),
        "id_call_sfr": _str_id(id_call_sfr),
        "id_tk_statut": id_tk_statut,
        "is_cloture": _bool(tk_liste.get("cloturee")),
        "is_statut_34": id_tk_statut == 34,
        "is_my_call": is_my_call,
        "appel_en_cours": appel_en_cours,
        "ope_en_cours_nom": ope_en_cours_nom,
        "client": {
            "civilite": _to_int(tc.get("civilite_client")),
            "nom": (tc.get("nom_client") or "").strip(),
            "nom_marital": (tc.get("nom_marital_client") or "").strip(),
            "prenom": (tc.get("prenom_client") or "").strip(),
            "nom_format": _format_nom_client(
                _to_int(tc.get("civilite_client")),
                tc.get("nom_client"),
                tc.get("nom_marital_client"),
                tc.get("prenom_client"),
            ),
            "date_naiss": _iso_date(tc.get("date_naiss")),
            "dep_naiss": _to_int(tc.get("dep_naiss")),
            "type_logement": _to_int(tc.get("type_logement")),
            "adresse1": (tc.get("adresse1") or "").strip(),
            "adresse2": (tc.get("adresse2") or "").strip(),
            "cp": (tc.get("cp") or "").strip(),
            "ville": _format_ville(tc.get("ville") or ""),
            "email": (tc.get("adr_mail") or "").strip(),
            "mobile1": mobile1,
            "mobile2": mobile2,
            "opt_rappel": _bool(tc.get("opt_rappel")),
            "opt_partenaire": _bool(tc.get("opt_partenaire")),
            "client_pro": _bool(tc.get("client_pro")),
            "client_rs": (tc.get("client_rs") or "").strip(),
            "client_siret": (tc.get("client_siret") or "").strip(),
        },
        "vendeur": {
            "id_salarie": id_salarie,
            "nom": nom_vend,
            "prenom": prenom_vend,
            "gsm": gsm_vend,
            "lib_affectation": "",
        },
        "vente": {
            "ref_appel": (tc.get("ref_appel") or "").strip(),
            "intervention_vendeur": _bool(tc.get("intervention_vend")),
            "mobile_propose_vendeur": _bool(tc.get("mob_propo_vend")),
            "info_vente": (tc.get("info_vente") or "").strip(),
        },
        "anomalie": {
            "active": _bool(tc.get("anomalie_mobile")),
            "id_type": _to_int(tc.get("id_tk_call_sfr_type_anomalie")),
            "info_cplt": (tc.get("info_cplt_anomalie") or "").strip(),
        },
        "panier": panier,
        "nb_prod_total": nb_prod_total,
        "nb_prod_valide": nb_prod_valide,
        "nb_prod_annule": nb_prod_annule,
        "btn_valider_actif": btn_valider_actif,
        "btn_annuler_actif": btn_annuler_actif,
        "statuts_vente": statuts_vente,
        "motifs_anomalie": motifs_anomalie,
    }
