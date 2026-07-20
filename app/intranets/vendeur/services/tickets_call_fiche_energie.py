"""
Fiche ticket Call Energie (cote Vendeur, PG).

Portage direct de app/intranets/call/energie/services/fiche.py mais en
PG. Reutilise les helpers du service Fibre Vendeur (partages).

Cf. memoire feedback_fiche_ticket_modal_sync : cette copie doit rester
en sync avec le service source cote /call/energie.
"""
from __future__ import annotations

import logging
import time as _time
from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection
from app.intranets.vendeur.services.tickets_call_fiche_fibre import (
    _bool, _capitalize, _civilite_to_prefix, _format_nom_client,
    _format_ville, _iso_date, _mask_phone, _str_id, _to_int,
)


logger = logging.getLogger(__name__)


# Constantes
ID_ORGA_POWER_OHM = 20260324120238233


def _load_partenaires_prefix_to_lib() -> dict[str, str]:
    """Charge {prefix: lib} depuis adv.pgt_partenaire."""
    db = get_pg_connection("adv")
    try:
        rows = db.query(
            """SELECT prefixe_bdd, lib_partenaire
                 FROM adv.pgt_partenaire
                WHERE is_actif = TRUE
                  AND (modif_elem IS NULL
                       OR modif_elem NOT LIKE '%suppr%')""",
        ) or []
    except Exception:
        return {}
    return {
        (r.get("prefixe_bdd") or "").strip():
            (r.get("lib_partenaire") or "").strip()
        for r in rows
        if (r.get("prefixe_bdd") or "").strip()
    }


def _orga_descendants_set(id_orga: int) -> set[int]:
    """Descendants de id_orga (CTE recursive PG)."""
    if not id_orga:
        return set()
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """WITH RECURSIVE tree AS (
                   SELECT idorganigramme AS id FROM pgt_organigramme
                    WHERE idorganigramme = ?
                   UNION ALL
                   SELECT o.idorganigramme
                     FROM pgt_organigramme o
                     JOIN tree t ON o.id_parent = t.id
                    WHERE (o.modif_elem IS NULL
                           OR o.modif_elem NOT LIKE '%suppr%')
               )
               SELECT id FROM tree""",
            (int(id_orga),),
        ) or []
    except Exception:
        return set()
    return {_to_int(r.get("id")) for r in rows} - {0}


def load_fiche(id_tk_liste: int, current_user_id: int = 0) -> dict:
    """Charge la fiche complete d'un ticket Call Energie (PG)."""
    from concurrent.futures import ThreadPoolExecutor
    db_ticket = get_pg_connection("ticket")
    db_bo = get_pg_connection("ticket_bo")
    db_rh = get_pg_connection("rh")

    # Vague 1 : TK_Liste + TK_Call
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_liste = pool.submit(
            db_ticket.query_one,
            """SELECT id_tk_liste, date_crea, id_tk_statut, op_crea,
                      cloturee, date_cloture
                 FROM ticket.pgt_tk_liste
                WHERE id_tk_liste = ?""",
            (int(id_tk_liste),),
        )
        f_call = pool.submit(
            db_bo.query_one,
            """SELECT id_tk_call, id_tk_liste, id_salarie,
                      civilite_client, nom_client, nom_marital_client,
                      prenom_client, date_naiss, dep_naiss, type_logement,
                      adresse1, adresse2, cp, ville,
                      adr_mail, mobile1,
                      appel_en_cours, date_h_appel, ope_appel, ref_appel,
                      motif_annulation, date_deb_prise_en_charge,
                      date_fin_prise_en_charge,
                      intervention_vend, info_vente,
                      opt_rappel, opt_partenaire,
                      client_pro, client_rs, client_siret
                 FROM ticket_bo.pgt_tk_call
                WHERE id_tk_liste = ?
                  AND (modif_elem IS NULL
                       OR modif_elem NOT LIKE '%suppr%')""",
            (int(id_tk_liste),),
        )
        tk_liste = f_liste.result()
        tc = f_call.result()

    if not tk_liste:
        return {"error": "Ticket introuvable"}
    if not tc:
        return {"error": "Pas de TK_Call pour ce ticket"}

    id_call = _to_int(tc.get("id_tk_call"))
    id_salarie = _to_int(tc.get("id_salarie"))
    id_tk_statut = _to_int(tk_liste.get("id_tk_statut"))
    appel_en_cours = _bool(tc.get("appel_en_cours"))
    ope_appel_id = _to_int(tc.get("ope_appel"))

    is_my_call = appel_en_cours and ope_appel_id == current_user_id
    mobile1_raw = (tc.get("mobile1") or "").strip()
    mobile1 = mobile1_raw if is_my_call else _mask_phone(mobile1_raw)

    # Vague 2
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
            # Note : opt_maintenance existe cote HFSQL OVH mais pas dans
            # le schema PG interne (pas encore repliquee via SymmetricDS).
            # On expose False par defaut cote API.
            """SELECT id_tk_call_panier, id_produit, partenaire,
                      opt_energie_verte_elec, opt_reforestation,
                      opt_energie_verte_gaz, opt_mail, opt_mandat,
                      format_numerique, opt_accept_com_parte,
                      opt_consent_consult_distri,
                      opt_e_communication, opt_e_facture,
                      opt_optin_commercial, date_entree, observations,
                      motif_annulation, statut_prod, num_bs,
                      num_date_saisie
                 FROM ticket_bo.pgt_tk_call_panier
                WHERE id_tk_call = ?
                  AND (modif_elem IS NULL
                       OR modif_elem NOT LIKE '%suppr%')""",
            (id_call,),
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

    # Panier + resolution partenaire lib
    prefix_to_lib = _load_partenaires_prefix_to_lib()
    panier = []
    for p in rows_panier:
        prefix = (p.get("partenaire") or "").strip()
        panier.append({
            "id": _str_id(p.get("id_tk_call_panier")),
            "id_produit": _to_int(p.get("id_produit")),
            "partenaire": prefix,
            "partenaire_lib": prefix_to_lib.get(prefix, prefix),
            "opt_energie_verte_elec": _bool(p.get("opt_energie_verte_elec")),
            "opt_energie_verte_gaz": _bool(p.get("opt_energie_verte_gaz")),
            "opt_reforestation": _bool(p.get("opt_reforestation")),
            "opt_mail": _bool(p.get("opt_mail")),
            "opt_mandat": _bool(p.get("opt_mandat")),
            "format_numerique": _bool(p.get("format_numerique")),
            "opt_maintenance": False,  # colonne absente du schema PG interne
            "opt_accept_com_parte": _bool(p.get("opt_accept_com_parte")),
            "opt_consent_consult_distri": _bool(
                p.get("opt_consent_consult_distri"),
            ),
            "opt_e_communication": _bool(p.get("opt_e_communication")),
            "opt_e_facture": _bool(p.get("opt_e_facture")),
            "opt_optin_commercial": _bool(p.get("opt_optin_commercial")),
            "statut_prod": _to_int(p.get("statut_prod")),
            "motif_annulation": (p.get("motif_annulation") or "").strip(),
            "num_bs": (p.get("num_bs") or "").strip(),
            "num_date_saisie": _iso_date(p.get("num_date_saisie")),
            "date_activ": _iso_date(p.get("date_entree")),
            "ref_client_oen": (p.get("observations") or "").strip(),
        })

    # Credentials portail Ohm Energie (dependant de l'orga du vendeur)
    ohm_login = "Power_distribExo_Sup"
    ohm_mdp = "U8uDym72"
    if id_salarie:
        try:
            row_aff = db_rh.query_one(
                """SELECT idorganigramme
                     FROM rh.pgt_salarie_organigramme
                    WHERE id_salarie = ?
                      AND (modif_elem IS NULL
                           OR modif_elem NOT LIKE '%suppr%')
                      AND COALESCE(aff_actif, FALSE) = TRUE
                    ORDER BY date_debut DESC
                    LIMIT 1""",
                (id_salarie,),
            )
            id_orga_vendeur = _to_int(
                (row_aff or {}).get("idorganigramme"),
            )
            if id_orga_vendeur:
                power_ohm_set = _orga_descendants_set(ID_ORGA_POWER_OHM)
                if id_orga_vendeur in power_ohm_set:
                    ohm_login = "Power_distrib_admin"
                    ohm_mdp = "Jbrk5Q78"
        except Exception:
            pass

    statuts_vente = [
        {"id": 0, "label": "Non défini"},
        {"id": 1, "label": "Validé"},
        {"id": 2, "label": "Annulé"},
        {"id": 3, "label": "Num BS ajouté"},
    ]
    if id_tk_statut == 15:
        statuts_vente.append({"id": 4, "label": "Validé - Différé"})

    nb_prod_total = len(panier)
    nb_prod_valide = sum(
        1 for p in panier if p["statut_prod"] in (1, 3)
    )
    nb_prod_annule = sum(1 for p in panier if p["statut_prod"] == 2)
    btn_valider_actif = (
        nb_prod_valide > 0
        and (nb_prod_valide + nb_prod_annule) == nb_prod_total
    )
    btn_annuler_actif = nb_prod_total > 0 and nb_prod_annule == nb_prod_total

    return {
        "id_ticket": _str_id(id_tk_liste),
        "id_call": _str_id(id_call),
        "id_tk_statut": id_tk_statut,
        "is_cloture": _bool(tk_liste.get("cloturee")),
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
            "info_vente": (tc.get("info_vente") or "").strip(),
        },
        "panier": panier,
        "nb_prod_total": nb_prod_total,
        "nb_prod_valide": nb_prod_valide,
        "nb_prod_annule": nb_prod_annule,
        "btn_valider_actif": btn_valider_actif,
        "btn_annuler_actif": btn_annuler_actif,
        "statuts_vente": statuts_vente,
        "ohm_login": ohm_login,
        "ohm_mdp": ohm_mdp,
    }
