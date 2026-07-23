"""Endpoints mobile SFR (WebRest_Omayapp/SFR/*).

Portage iso-URL des 7 WS SFR mobile WinDev :
  - AjoutNumBS         : renseigne le NumBS d'une ligne de panier
  - ContenuCall        : detail complet d'un ticket SFR (client +
                          panier + anomalie mobile)
  - ListeRDVTech       : RDV tech fibre d'un vendeur pour un jour
                          (SFR_contrat + override si TK_RetourRdvTech)
  - ListeTicketDiff    : tickets 'diff' (anomalie mobile) du vendeur
                          pour un jour
  - ListerOffres       : catalogue d'offres SFR (Provad) filtre par
                          type (+ opt TV pour Fibre)
  - StatuerRDV         : statue un RDV tech fibre + cree ticket BO 19
  - StatutsRDV         : categories de statut RDV SFR (couleur RVB)
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Body, Depends

from app.core.database.pg import get_pg_connection
from app.mobile.agcial import _new_id_wd, _parse_jour, _to_int
from app.mobile.auth import _capitalise
from app.mobile.deps import mobile_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mobile-sfr"],
                    dependencies=[Depends(mobile_auth)])


def _to_num(v) -> float:
    try:
        return float(v) if v not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0


def _iso_dt(v) -> str:
    if not v:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    return str(v)


def _rvb(r: Any, v: Any, b: Any) -> int:
    """WinDev RVB = r + v*256 + b*65536."""
    return (_to_int(b) << 16) | (_to_int(v) << 8) | _to_int(r)


def _create_ticket_liste(service: str, id_type_dem: int, id_statut: int,
                          op_crea: int, id_tk_liste: int | None = None) -> int:
    """Portage nouveauTicket : insert TK_Liste avec service/type/statut donnes."""
    db = get_pg_connection("ticket")
    now = datetime.now()
    id_new = id_tk_liste or _new_id_wd()
    try:
        db.query(
            """INSERT INTO ticket.pgt_tk_liste
                 (id_tk_liste_auto, id_tk_liste, date_crea, op_crea, op_dest,
                  service, id_tk_type_demande, id_tk_statut, cloturee,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, FALSE, ?, ?, 'new')""",
            (id_new, id_new, now, int(op_crea), int(op_crea),
             service, id_type_dem, id_statut, now, int(op_crea)),
        )
        return id_new
    except Exception:
        logger.exception("_create_ticket_liste svc=%s type=%s", service, id_type_dem)
        return 0


# ===========================================================================
#  StatutsRDV
# ===========================================================================

@router.post("/SFR/StatutsRDV")
def statuts_rdv(_payload: Any = Body(default=None)):
    """Portage ListeStatutRDVTech."""
    db = get_pg_connection("adv")
    try:
        rows = db.query(
            """SELECT id_sfr_statut_rdv, lib_statut,
                      couleur_r, couleur_v, couleur_b
                 FROM adv.pgt_sfr_statut_rdv
                WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY id_sfr_statut_rdv""",
        ) or []
    except Exception:
        logger.exception("statuts_rdv")
        return []
    return [
        {"IDStatutCV": str(int(r.get("id_sfr_statut_rdv") or 0)),
         "lib": (r.get("lib_statut") or "").strip(),
         "Coul": _rvb(r.get("couleur_r"), r.get("couleur_v"),
                       r.get("couleur_b")),
         "ID": _to_int(r.get("id_sfr_statut_rdv"))}
        for r in rows
    ]


# ===========================================================================
#  ListerOffres
# ===========================================================================

@router.post("/SFR/ListerOffres")
def lister_offres(payload: dict = Body(...)):
    """Portage ListeOffreSFR_ByType.
    Payload : { type: 'FIBRE'|'FIB PRO'|'MOBILE'|...,
                OptTv: bool }
    """
    typ = (payload.get("type") or "").strip()
    opt_tv = bool(payload.get("OptTv"))
    if not typ:
        return []

    db = get_pg_connection("adv")
    try:
        rows = db.query(
            """SELECT id_offres_sfr, type, lib_offre, debit_down, debit_up,
                      prix_offre, recurrence, prix_pro_ttc, engagement,
                      en_promo, info_promo, service_inclus, online
                 FROM adv.pgt_sfr_offres_provad
                WHERE type = ?
                  AND COALESCE(online, FALSE) = TRUE
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY lib_offre""",
            (typ,),
        ) or []
    except Exception:
        logger.exception("lister_offres type=%s", typ)
        return []

    result = []
    for r in rows:
        lib = (r.get("lib_offre") or "").strip()
        # Renommage WinDev
        lib = lib.replace("standard", "STD").replace("Standard", "STD").replace("STANDARD", "STD")
        lib = lib.replace("offre ", "").replace("Offre ", "").replace("OFFRE ", "")
        engagement = (r.get("engagement") or "").strip()
        if "sans engagement" in engagement.lower():
            lib += " SE"
        elif engagement and "engagement" not in engagement.lower():
            engagement = f"Engagement : {engagement}"

        # Filtre TV pour Fibre / Fib Pro
        if typ.upper() in ("FIBRE", "FIB PRO"):
            has_tv = ("TV" in lib.upper()) or ("HIGH TECH" in lib.upper())
            if has_tv != opt_tv:
                continue

        result.append({
            "IDOffres_SFR": str(int(r.get("id_offres_sfr") or 0)),
            "Type": (r.get("type") or "").strip(),
            "Lib_Offre": lib,
            "DebitDown": r.get("debit_down") or "",
            "DebitUp": r.get("debit_up") or "",
            "PrixOffre": _to_num(r.get("prix_offre")),
            "Recurrence": r.get("recurrence") or "",
            "PrixProTTC": r.get("prix_pro_ttc") or "",
            "Engagement": engagement,
            "EnPromo": bool(r.get("en_promo")),
            "InfoPromo": r.get("info_promo") or "",
            "ServiceInclus": r.get("service_inclus") or "",
            "Online": bool(r.get("online")),
        })
    return result


# ===========================================================================
#  ContenuCall
# ===========================================================================

@router.post("/SFR/ContenuCall")
def contenu_call(payload: dict = Body(...)):
    """Portage CR_ContenuCALL + contenuCallSFR.
    Retour STTKCallSFR : detail client SFR + panier + anomalie mobile.
    """
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    empty = {"IDtk_CallSFR": "0"}
    if not id_tk:
        return empty

    db_tkbo = get_pg_connection("ticket_bo")
    db_tk = get_pg_connection("ticket")
    db_adv = get_pg_connection("adv")

    # 1. TK_CallSFR header
    try:
        head = db_tkbo.query_one(
            """SELECT id_tk_call_sfr, id_offres_sfr, civilite_client,
                      nom_client, nom_marital_client, prenom_client,
                      date_naiss, dep_naiss, adresse1, adresse2, cp, ville,
                      adr_mail, mobile1, mobile2, type_logement,
                      anomalie_mobile, id_tk_call_sfr_type_anomalie,
                      id_tk_liste_ref_anomalie, info_cplt_anomalie
                 FROM ticket_bo.pgt_tk_call_sfr
                WHERE id_tk_liste = ? LIMIT 1""",
            (id_tk,),
        )
    except Exception:
        logger.exception("contenu_call head id=%s", id_tk)
        return empty
    if not head:
        return empty

    # 2. Statut ticket
    id_tk_statut = 0
    try:
        tk = db_tk.query_one(
            "SELECT id_tk_statut FROM ticket.pgt_tk_liste WHERE id_tk_liste = ? LIMIT 1",
            (id_tk,),
        )
        if tk:
            id_tk_statut = _to_int(tk.get("id_tk_statut"))
    except Exception:
        pass

    # 3. Offre principale
    lib_offre = ""
    mnt_offre = 0.0
    id_off = _to_int(head.get("id_offres_sfr"))
    if id_off:
        try:
            o = db_adv.query_one(
                """SELECT lib_offre, prix_offre
                     FROM adv.pgt_sfr_offres_provad
                    WHERE id_offres_sfr = ? LIMIT 1""",
                (id_off,),
            )
            if o:
                lib_offre = (o.get("lib_offre") or "").strip()
                mnt_offre = _to_num(o.get("prix_offre"))
        except Exception:
            pass

    # 4. TypeLogement forced (WinDev regle si <1)
    tl = _to_int(head.get("type_logement"))
    if tl < 1:
        tl = 2 if (head.get("adresse2") or "").strip() else 1

    dn = head.get("date_naiss")
    result = {
        "IDtk_CallSFR": str(int(head.get("id_tk_call_sfr") or 0)),
        "IDOffres_SFR": str(id_off) if id_off else "0",
        "LibOffre": lib_offre,
        "MontantOffre": mnt_offre,
        "IDTKStatut": id_tk_statut,
        "CiviliteClient": _to_int(head.get("civilite_client")),
        "NomClient": (head.get("nom_client") or "").strip(),
        "NomMaritalClient": (head.get("nom_marital_client") or "").strip(),
        "PrenomClient": (head.get("prenom_client") or "").strip(),
        "DATENAISS": dn.isoformat() if dn else "",
        "DEPNAISS": _to_int(head.get("dep_naiss")),
        "ADRESSE1": (head.get("adresse1") or "").strip(),
        "ADRESSE2": (head.get("adresse2") or "").strip(),
        "CP": (head.get("cp") or "").strip(),
        "VILLE": (head.get("ville") or "").strip(),
        "adrMail": (head.get("adr_mail") or "").strip(),
        "Mobile1": (head.get("mobile1") or "").strip(),
        "Mobile2": (head.get("mobile2") or "").strip(),
        "TypeLogement": tl,
        "AnomalieMobile": bool(head.get("anomalie_mobile")),
        "Panier": [],
    }

    if head.get("anomalie_mobile"):
        result["ContenuAnomalie"] = {
            "IDtk_CallSFR_Anomalie": str(int(head.get("id_tk_call_sfr_type_anomalie") or 0)),
            "InfoCplAnomalie": head.get("info_cplt_anomalie") or "",
            "IDTK_Liste": str(int(head.get("id_tk_liste_ref_anomalie") or 0)),
        }

    # 5. Panier
    id_tk_call = int(head.get("id_tk_call_sfr") or 0)
    if id_tk_call:
        try:
            panier = db_tkbo.query(
                """SELECT id_tk_call_sfr_panier, id_offres_sfr, type,
                          num, statut_prod, num_prise_rio
                     FROM ticket_bo.pgt_tk_call_sfr_panier
                    WHERE id_tk_call_sfr = ?
                      AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
                (id_tk_call,),
            ) or []
        except Exception:
            panier = []
        # Prefetch offres
        off_ids = [int(p.get("id_offres_sfr") or 0) for p in panier
                   if p.get("id_offres_sfr")]
        off_map: dict[int, dict] = {}
        if off_ids:
            try:
                placeholders = ",".join("?" for _ in off_ids)
                offs = db_adv.query(
                    f"""SELECT id_offres_sfr, lib_offre, prix_offre
                         FROM adv.pgt_sfr_offres_provad
                        WHERE id_offres_sfr IN ({placeholders})""",
                    tuple(off_ids),
                ) or []
                off_map = {int(o.get("id_offres_sfr") or 0): o for o in offs}
            except Exception:
                pass
        for p in panier:
            off = off_map.get(int(p.get("id_offres_sfr") or 0), {})
            result["Panier"].append({
                "IDtk_CallSFR_Panier": str(int(p.get("id_tk_call_sfr_panier") or 0)),
                "IDtk_CallSFR": str(id_tk_call),
                "IDTK_Liste": str(id_tk),
                "IDOffres_SFR": str(int(p.get("id_offres_sfr") or 0)),
                "LibOffre": (off.get("lib_offre") or "").strip(),
                "MontantOffre": _to_num(off.get("prix_offre")),
                "Type": p.get("type") or "",
                "NumBS": p.get("num") or "",
                "Statut": _to_int(p.get("statut_prod")),
                "NumPrise_RIO": p.get("num_prise_rio") or "",
            })
    return result


# ===========================================================================
#  AjoutNumBS
# ===========================================================================

@router.post("/SFR/AjoutNumBS")
def ajout_num_bs(payload: dict = Body(...),
                  id_cial: int = Depends(mobile_auth)):
    """Portage AjouterNumBS SFR : update NumBS + statut_prod=3.
    Si dernier produit non-facture -> passe le ticket a statut 17."""
    id_panier = _to_int(payload.get("IDtk_CallSFR_Panier"))
    num_bs = (payload.get("NumBS") or "").strip()
    id_tk_liste = _to_int(payload.get("IDTK_Liste"))
    if not id_panier:
        return {"nIdDemande": "0"}

    db_bo = get_pg_connection("ticket_bo")
    db_tk = get_pg_connection("ticket")
    now = datetime.now()

    try:
        db_bo.query(
            """UPDATE ticket_bo.pgt_tk_call_sfr_panier
                  SET num = ?, num_date_saisie = ?, statut_prod = 3,
                      modif_elem = 'modif', modif_date = ?, modif_op = ?
                WHERE id_tk_call_sfr_panier = ?""",
            (num_bs, now, now, id_cial, id_panier),
        )
    except Exception as e:
        logger.exception("ajout_num_bs update id=%s", id_panier)
        return {"nIdDemande": "0", "sInfoData": str(e)}

    # Retrouve l'IDTK_Liste si non fourni via la ligne panier
    if not id_tk_liste:
        try:
            row = db_bo.query_one(
                """SELECT id_tk_liste FROM ticket_bo.pgt_tk_call_sfr_panier
                    WHERE id_tk_call_sfr_panier = ? LIMIT 1""",
                (id_panier,),
            )
            if row:
                id_tk_liste = _to_int(row.get("id_tk_liste"))
        except Exception:
            pass

    # Verif panier : plus rien avec statut_prod != 3 -> ticket statut 17
    if id_tk_liste:
        try:
            check = db_bo.query_one(
                """SELECT COUNT(*) AS n
                     FROM ticket_bo.pgt_tk_call_sfr_panier
                    WHERE id_tk_liste = ?
                      AND COALESCE(statut_prod, 0) <> 3
                      AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
                (id_tk_liste,),
            )
            if check and int(check.get("n") or 0) == 0:
                db_tk.query(
                    """UPDATE ticket.pgt_tk_liste
                          SET id_tk_statut = 17, modif_date = ?, modif_op = ?,
                              modif_elem = 'modif'
                        WHERE id_tk_liste = ?""",
                    (now, id_cial, id_tk_liste),
                )
        except Exception:
            logger.exception("ajout_num_bs check panier id_tk=%s", id_tk_liste)

    return {"nIdDemande": str(id_panier)}


# ===========================================================================
#  ListeRDVTech
# ===========================================================================

@router.post("/SFR/ListeRDVTech")
def liste_rdv_tech(payload: dict = Body(...)):
    """Portage Fibre_ListerRDVTech + ListerRDVTech."""
    id_vend = _to_int(payload.get("idVendeur") or payload.get("IDSalarie"))
    jour = _parse_jour(payload.get("dateAg") or payload.get("Date"))
    if not id_vend or not jour:
        return []

    db_adv = get_pg_connection("adv")
    db_tkbo = get_pg_connection("ticket_bo")
    db_tk = get_pg_connection("ticket")

    try:
        rows = db_adv.query(
            """SELECT sc.id_contrat, sc.id_salarie, sc.date_signature,
                      sc.date_rdv_tech, sc.periode_rdv_tech, sc.num_bs,
                      sc.id_produit, sc.id_sfr_statut_rdv,
                      sp.lib_produit, tec.lib_type,
                      cl.nom, cl.prenom, cl.adresse1, cl.cp, cl.ville,
                      cl.tel, cl.gsm,
                      st.lib_statut, st.couleur_r, st.couleur_v, st.couleur_b
                 FROM adv.pgt_sfr_contrat sc
                 LEFT JOIN adv.pgt_sfr_produit sp
                        ON sp.id_produit = sc.id_produit
                 LEFT JOIN adv.pgt_sfr_etat_contrat sec
                        ON sec.id_etat = sc.id_etat_contrat
                 LEFT JOIN adv.pgt_type_etat_contrat tec
                        ON tec.id_type_etat = sec.id_type_etat
                 LEFT JOIN adv.pgt_client cl
                        ON cl.id_client = sc.id_client
                 LEFT JOIN adv.pgt_sfr_statut_rdv st
                        ON st.id_sfr_statut_rdv = sc.id_sfr_statut_rdv
                WHERE sc.id_salarie = ?
                  AND sc.date_rdv_tech::date = ?::date
                  AND (sc.modif_elem IS NULL OR sc.modif_elem NOT LIKE '%suppr%')
                  AND (tec.lib_type IS NULL
                       OR (tec.lib_type NOT LIKE '%Rejeté%'
                           AND tec.lib_type NOT LIKE '%KO%'))""",
            (id_vend, jour.isoformat()),
        ) or []
    except Exception:
        logger.exception("liste_rdv_tech id=%s j=%s", id_vend, jour)
        return []

    result = []
    for r in rows:
        id_contrat = int(r.get("id_contrat") or 0)
        # Override IDCategorie si TK_RetourRdvTechFIBRE en cours
        id_cat = _to_int(r.get("id_sfr_statut_rdv"))
        lib_stat = (r.get("lib_statut") or "").strip()
        coul = _rvb(r.get("couleur_r"), r.get("couleur_v"), r.get("couleur_b"))
        try:
            rt = db_tkbo.query_one(
                """SELECT tr.id_tk_liste, tr.id_fibre_statut_rdv, tr.info_cplt,
                          tl.cloturee
                     FROM ticket_bo.pgt_tk_retour_rdv_tech_fibre tr
                     JOIN ticket.pgt_tk_liste tl ON tl.id_tk_liste = tr.id_tk_liste
                    WHERE tr.id_contrat = ?
                      AND COALESCE(tl.cloturee, FALSE) = FALSE
                    ORDER BY tr.modif_date DESC NULLS LAST
                    LIMIT 1""",
                (id_contrat,),
            )
            if rt:
                id_cat = _to_int(rt.get("id_fibre_statut_rdv")) or id_cat
                st2 = db_adv.query_one(
                    """SELECT lib_statut, couleur_r, couleur_v, couleur_b
                         FROM adv.pgt_sfr_statut_rdv
                        WHERE id_sfr_statut_rdv = ? LIMIT 1""",
                    (id_cat,),
                )
                if st2:
                    lib_stat = (st2.get("lib_statut") or "").strip()
                    coul = _rvb(st2.get("couleur_r"), st2.get("couleur_v"),
                                 st2.get("couleur_b"))
        except Exception:
            logger.exception("liste_rdv_tech override id_contrat=%s", id_contrat)

        # Composition contenu + heure debut
        contenu = "\n".join(filter(None, [
            (r.get("lib_produit") or "").strip(),
            (r.get("num_bs") or "").strip(),
            (r.get("tel") or "").strip(),
            (r.get("gsm") or "").strip(),
        ]))
        periode = _to_int(r.get("periode_rdv_tech"))
        hh = 8 if periode == 1 else (13 if periode == 2 else 0)
        deb = datetime.combine(jour, datetime.min.time()).replace(hour=hh)

        result.append({
            "Titre": (f"{(r.get('nom') or '').strip()} "
                       f"{_capitalise((r.get('prenom') or '').strip())}").strip(),
            "InfoLieu": (f"{(r.get('adresse1') or '').strip()} - "
                          f"{(r.get('cp') or '').strip()} "
                          f"{(r.get('ville') or '').strip()}").strip(),
            "Contenu": contenu,
            "DateDebut": deb.isoformat(sep=" "),
            "IDCategorie": id_cat,
            "IDAgendaEvenement": str(id_contrat),
            "libCategorie": lib_stat,
            "CoulCategorie": coul,
            "LienCV": (r.get("num_bs") or "").strip(),
        })
    return result


# ===========================================================================
#  ListeTicketDiff
# ===========================================================================

@router.post("/SFR/ListeTicketDiff")
def liste_ticket_diff(payload: dict = Body(...)):
    """Portage Fibre_ListerAgTkDiff + ListerAgendaTicketDiff.
    Tickets 'diff' (anomalie mobile) crees par le vendeur le jour donne."""
    id_vend = _to_int(payload.get("idVendeur") or payload.get("IDSalarie"))
    jour = _parse_jour(payload.get("dateAg") or payload.get("Date"))
    if not id_vend or not jour:
        return []

    db_bo = get_pg_connection("ticket_bo")
    db_tk = get_pg_connection("ticket")
    db_adv = get_pg_connection("adv")

    # Requete cross-schema : ticket + ticket_bo + adv (TK_Statut).
    # On split en 2 : d'abord recup les IDs, puis JOIN local.
    try:
        heads = db_tk.query(
            """SELECT tl.id_tk_liste, tl.date_crea, tl.id_tk_statut, tl.cloturee,
                      ts.lib_statut
                 FROM ticket.pgt_tk_liste tl
                 LEFT JOIN adv.pgt_tk_statut ts ON ts.id_tk_statut = tl.id_tk_statut
                WHERE (tl.modif_elem IS NULL OR tl.modif_elem NOT LIKE '%suppr%')
                  AND tl.op_crea = ?
                  AND tl.date_crea::date = ?::date""",
            (id_vend, jour.isoformat()),
        ) or []
    except Exception:
        logger.exception("liste_ticket_diff heads id=%s j=%s", id_vend, jour)
        return []

    if not heads:
        return []

    tk_map = {int(h.get("id_tk_liste") or 0): h for h in heads}
    id_list = list(tk_map.keys())
    if not id_list:
        return []
    placeholders = ",".join("?" for _ in id_list)

    # 2. Filtre ticket_bo : lignes 'new' de TK_CallSFR avec un 'old' via
    # id_tk_liste_ref_anomalie (self-join)
    try:
        rows = db_bo.query(
            f"""SELECT new.id_tk_liste AS id_tk_liste_new,
                       new.id_tk_call_sfr AS id_tk_call_sfr,
                       old.id_tk_liste_ref_anomalie,
                       new.nom_client, new.prenom_client, new.adresse1,
                       new.cp, new.ville, new.adr_mail, new.mobile1,
                       new.motif_annulation, new.appel_en_cours
                  FROM ticket_bo.pgt_tk_call_sfr new
                  JOIN ticket_bo.pgt_tk_call_sfr old
                        ON new.id_tk_liste = old.id_tk_liste_ref_anomalie
                 WHERE new.id_tk_liste IN ({placeholders})""",
            tuple(id_list),
        ) or []
    except Exception:
        logger.exception("liste_ticket_diff bo")
        return []

    result = []
    for r in rows:
        id_tk = int(r.get("id_tk_liste_new") or 0)
        h = tk_map.get(id_tk, {})
        id_statut = _to_int(h.get("id_tk_statut"))
        appel_ec = bool(r.get("appel_en_cours"))

        contenu = f"{(r.get('mobile1') or '').strip()}\n{(r.get('adr_mail') or '').strip()}"
        contenu += f"\nStatut du ticket : {(h.get('lib_statut') or '').strip()}"
        if appel_ec:
            contenu += "(Appel en cours)"

        # Couleur categorie WinDev
        if id_statut == 14:
            coul = 0x808080  # GrisFonce
        elif id_statut == 15:
            coul = 0x008000  # VertFonce
        elif appel_ec:
            coul = 0x80CFFF  # OrangeClair (approx)
        else:
            coul = 0xFFFFFF  # Blanc

        deb = datetime.combine(jour, datetime.min.time()).replace(hour=9)
        result.append({
            "Titre": (f"{(r.get('nom_client') or '').strip()} "
                       f"{_capitalise((r.get('prenom_client') or '').strip())}").strip(),
            "InfoLieu": (f"{(r.get('adresse1') or '').strip()} - "
                          f"{(r.get('cp') or '').strip()} "
                          f"{(r.get('ville') or '').strip()}").strip(),
            "Contenu": contenu,
            "DateDebut": deb.isoformat(sep=" "),
            "IDCategorie": id_statut,
            "IDAgendaEvenement": str(id_tk),
            "CoulCategorie": coul,
        })
    return result


# ===========================================================================
#  StatuerRDV
# ===========================================================================

@router.post("/SFR/StatuerRDV")
def statuer_rdv(payload: dict = Body(...),
                 id_cial: int = Depends(mobile_auth)):
    """Portage Fibre_StatuerRDV.

    Payload : { idRdv (=id_contrat SFR), IdStatut, monRdv:{Contenu} }
    Cree une entree TK_RetourRdvTechFIBRE + un nouveau ticket BO type 19.
    """
    id_rdv = _to_int(payload.get("idRdv") or payload.get("IDAgendaEvenement"))
    id_statut = _to_int(payload.get("IdStatut") or payload.get("IDCategorie"))
    mon_rdv = payload.get("monRdv") or {}
    contenu = mon_rdv.get("Contenu") or payload.get("Contenu") or ""
    if not id_rdv or not id_statut:
        return {"nIdDemande": "0"}

    db_adv = get_pg_connection("adv")
    db_bo = get_pg_connection("ticket_bo")

    # Verif que le contrat SFR existe + recup NumBS
    try:
        row = db_adv.query_one(
            """SELECT num_bs FROM adv.pgt_sfr_contrat
                WHERE id_contrat = ? LIMIT 1""",
            (id_rdv,),
        )
    except Exception:
        logger.exception("statuer_rdv contrat id=%s", id_rdv)
        return {"nIdDemande": "0"}
    if not row:
        return {"nIdDemande": "0"}

    num_bs = (row.get("num_bs") or "").strip()

    # 1. Cree le ticket TK_Liste (BO type 19)
    id_tk = _create_ticket_liste("BO", 19, 1, id_cial)
    if not id_tk:
        return {"nIdDemande": "0"}

    # 2. Insert TK_RetourRdvTechFIBRE
    id_new = _new_id_wd()
    now = datetime.now()
    try:
        db_bo.query(
            """INSERT INTO ticket_bo.pgt_tk_retour_rdv_tech_fibre
                 (id_tk_retour_rdv_tech_fibre_auto,
                  id_tk_retour_rdv_tech_fibre,
                  id_tk_liste, id_contrat, num_bs, id_fibre_statut_rdv,
                  info_cplt, modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
            (id_new, id_new, id_tk, id_rdv, num_bs, id_statut,
             contenu, now, id_cial),
        )
        return {"nIdDemande": str(id_tk)}
    except Exception as e:
        logger.exception("statuer_rdv insert retour id=%s", id_rdv)
        return {"nIdDemande": "0", "sInfoData": str(e)}
