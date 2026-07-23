"""Endpoints mobile 'petits WS unitaires' (WebRest_Omayapp/*).

Portage iso-signature des WS WinDev unitaires. Certains sont directement
implementes ici (SQL simple), d'autres reutilisent les services deja
portes cote web. Les stubs 501 restants sont en attente des TXT.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.core.database.pg import get_pg_connection
from app.mobile.deps import mobile_auth
from app.intranets.vendeur.services import ticket_call_procs as tc

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mobile-misc"],
                    dependencies=[Depends(mobile_auth)])


def _new_id_wd() -> int:
    """idEntierDateHeureSys() de WinDev."""
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
#  PartCall (portage direct depuis les services existants)
# ---------------------------------------------------------------------------

@router.post("/PartCall")
def part_call(_payload: dict = Body(default={})):
    """Liste des partenaires actifs cote Call.
    Portage ListePartCall WinDev -> tc.list_part_call().
    """
    return tc.list_part_call()


# ---------------------------------------------------------------------------
#  AjoutLog (crealog WinDev)
# ---------------------------------------------------------------------------

@router.post("/AjoutLog")
def ajout_log(payload: dict = Body(...)):
    """Enregistrement d'un log applicatif mobile.

    Payload WinDev : {sAdrClient, type, detail, Login, Nom, sSupportClient}
    """
    db = get_pg_connection("divers")
    now = datetime.now()
    try:
        db.query(
            """INSERT INTO divers.pgt_logconnexion
                 (id_logconnexion, date, heure, ip, type, detail,
                  login, nom, support, modif_date, s_ite)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Omaya Mobile2')""",
            (_new_id_wd(), now.date(), now.time(),
             payload.get("sAdrClient") or "",
             payload.get("type") or "",
             payload.get("detail") or "",
             payload.get("Login") or "",
             payload.get("Nom") or "",
             payload.get("sSupportClient") or "",
             now),
        )
    except Exception:
        logger.exception("ajout_log")
    return {}  # WinDev ne renvoie rien


# ---------------------------------------------------------------------------
#  ExoNews (contenu du jour)
# ---------------------------------------------------------------------------

@router.post("/ExoNews")
def exo_news(_payload: dict = Body(default={})):
    """Contenu InfoExoNew du jour. Retourne juste la chaine contenu
    (ou vide si aucun contenu du jour).
    """
    db = get_pg_connection("divers")
    today_iso = date.today().isoformat()  # YYYY-MM-DD
    try:
        row = db.query_one(
            """SELECT contenu_info
                 FROM divers.pgt_infoexonew
                WHERE date_jour::date = ?::date
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                LIMIT 1""",
            (today_iso,),
        )
    except Exception:
        logger.exception("exo_news")
        return ""
    return (row or {}).get("contenu_info") or ""


# ---------------------------------------------------------------------------
#  Referentiels (ListePoste / ListeSteActive / ListeTypeProd)
# ---------------------------------------------------------------------------

@router.post("/ListePoste")
def liste_poste(_payload: dict = Body(default={})):
    """Portage ListerPoste WinDev. Retour : [{idPoste, libPoste}]."""
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT id_type_poste, lib_poste
                 FROM rh.pgt_type_poste
                WHERE id_type_poste > 0
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY lib_poste ASC""",
        ) or []
    except Exception:
        logger.exception("liste_poste")
        return []
    return [
        {"idPoste": int(r.get("id_type_poste") or 0),
         "libPoste": r.get("lib_poste") or ""}
        for r in rows
    ]


@router.post("/ListeSteActive")
def liste_ste_active(_payload: dict = Body(default={})):
    """Portage ListeSteActive WinDev. Retour : [{IdSte, RS_Interne}]."""
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT id_ste, rs_interne
                 FROM rh.pgt_societe
                WHERE COALESCE(is_actif, FALSE) = TRUE
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY rs_interne ASC""",
        ) or []
    except Exception:
        logger.exception("liste_ste_active")
        return []
    return [
        {"IdSte": int(r.get("id_ste") or 0),
         "RS_Interne": (r.get("rs_interne") or "").strip()}
        for r in rows
    ]


@router.post("/ListeTypeProd")
def liste_type_prod(_payload: dict = Body(default={})):
    """Portage ListeProdSte WinDev (filtre type='FDV').
    Retour : [{IDProduit, LibProd}].
    """
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT id_type_produit, lib
                 FROM rh.pgt_type_produit
                WHERE type = ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY lib ASC""",
            ("FDV",),
        ) or []
    except Exception:
        logger.exception("liste_type_prod")
        return []
    return [
        {"IDProduit": int(r.get("id_type_produit") or 0),
         "LibProd": r.get("lib") or ""}
        for r in rows
    ]


# ---------------------------------------------------------------------------
#  ListeVilleByCP
# ---------------------------------------------------------------------------

@router.post("/ListeVilleByCP")
def liste_ville_by_cp(payload: dict = Body(...)):
    """Portage ListeVilleByCP(CP) WinDev.
    Payload : {CP: str}
    Retour : [{ID, NomVille, CP}].
    """
    cp = (payload.get("CP") or payload.get("cp") or "").strip()
    if not cp:
        return []
    db = get_pg_connection("divers")
    try:
        rows = db.query(
            """SELECT id_communes_france, nom_ville, code_postal
                 FROM divers.pgt_communes_france
                WHERE code_postal = ?
                ORDER BY nom_ville ASC""",
            (cp,),
        ) or []
    except Exception:
        logger.exception("liste_ville_by_cp cp=%s", cp)
        return []
    return [
        {"ID": int(r.get("id_communes_france") or 0),
         "NomVille": r.get("nom_ville") or "",
         "CP": r.get("code_postal") or ""}
        for r in rows
    ]


# ---------------------------------------------------------------------------
#  NotifPush (Enr + Liste)
# ---------------------------------------------------------------------------

@router.post("/NotifPush/EnrNotif")
def notifpush_enr(payload: dict = Body(...)):
    """Portage EnregistreNotif WinDev.
    Payload : {ID, IdSalarie, MessageNotif, ContenuNotif, TitreNotif}
    Regle WinDev : si ID vide -> nouveau, sinon -> suppr (soft delete).
    Retour STRéponseTK : {nIdDemande, sInfoData}.
    """
    db = get_pg_connection("divers")
    now = datetime.now()
    raw_id = payload.get("ID")
    id_notif = _to_int(raw_id)
    id_salarie = _to_int(payload.get("IdSalarie"))
    marep = {"nIdDemande": "0", "sInfoData": ""}

    if not id_notif:
        # Creation
        id_notif = _new_id_wd()
        try:
            db.query(
                """INSERT INTO divers.pgt_notificationpush
                     (id_notification_push, id_salarie, message_notif,
                      contenu_notif, titre_notif,
                      modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'new')""",
                (id_notif, id_salarie,
                 payload.get("MessageNotif") or "",
                 payload.get("ContenuNotif") or "",
                 payload.get("TitreNotif") or "",
                 now, id_salarie),
            )
            marep["nIdDemande"] = str(id_notif)
        except Exception as e:
            logger.exception("notifpush_enr: insert")
            marep["sInfoData"] = str(e)
    else:
        # Suppression logique (convention WinDev : re-envoyer l'ID = soft delete)
        try:
            db.query(
                """UPDATE divers.pgt_notificationpush
                      SET modif_date = ?, modif_elem = 'suppr'
                    WHERE id_notification_push = ?""",
                (now, id_notif),
            )
            marep["nIdDemande"] = str(id_notif)
        except Exception as e:
            logger.exception("notifpush_enr: suppr")
            marep["sInfoData"] = str(e)
    return marep


@router.post("/NotifPush/Liste")
def notifpush_liste(payload: dict = Body(...)):
    """Portage ListeNotifs WinDev.
    Payload : ST_SALARIE (utilise l'attribut ID).
    Retour : [{ID, IdSalarie, MessageNotif, ContenuNotif, TitreNotif}]
    """
    id_salarie = _to_int(payload.get("ID"))
    if not id_salarie:
        return []
    db = get_pg_connection("divers")
    try:
        rows = db.query(
            """SELECT id_notification_push, id_salarie, message_notif,
                      contenu_notif, titre_notif
                 FROM divers.pgt_notificationpush
                WHERE id_salarie = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY id_notification_push ASC""",
            (id_salarie,),
        ) or []
    except Exception:
        logger.exception("notifpush_liste id_sal=%s", id_salarie)
        return []
    return [
        {"ID": str(int(r.get("id_notification_push") or 0)),
         "IdSalarie": int(r.get("id_salarie") or 0),
         "MessageNotif": r.get("message_notif") or "",
         "ContenuNotif": r.get("contenu_notif") or "",
         "TitreNotif": r.get("titre_notif") or ""}
        for r in rows
    ]


# ---------------------------------------------------------------------------
#  Stubs 501 en attente des TXT WinDev
# ---------------------------------------------------------------------------

@router.post("/News/Liste")
def news_liste(_payload: dict = Body(default={})):
    raise HTTPException(501, "News/Liste non encore porte (TXT manquant)")


@router.post("/Podium")
def podium(_payload: dict = Body(default={})):
    raise HTTPException(501, "Podium non encore porte (TXT manquant)")
