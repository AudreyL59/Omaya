"""Endpoints mobile Tickets (WebRest_Omayapp/Tickets/*).

Groupe le plus gros (55 endpoints au total). Fichier decoupe par lots
pour rester lisible. Ce lot 1 contient :

  TypeTickets (referentiel) :
    - TypeTickets              : tous les types de demande
    - TypeTickets/Fournitures  : types BS commande
    - TypeTickets/Reservation  : sous-familles + type resa
    - TypeTickets/SosBO        : types SOS BO
    - TypeTickets/SosJU        : types SOS Juridique

  TicketsEnCours :
    - TicketsEnCours           : liste des tickets non-clotures pour
                                  N salaries (avec logique de droits
                                  et de filtrage par type)
    - TicketsEnCours/ModifOpDEST : reaffectation d'un lot de tickets
                                    a un autre operateur destinataire
"""

from __future__ import annotations

import base64
import logging
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Body, Depends

from app.core.database.pg import get_pg_connection
from app.mobile.agcial import _to_int
from app.mobile.auth import _capitalise
from app.mobile.deps import mobile_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mobile-tickets"],
                    dependencies=[Depends(mobile_auth)])


def _bytea_to_b64(v) -> str:
    if not v:
        return ""
    if isinstance(v, memoryview):
        v = v.tobytes()
    if isinstance(v, str):
        return v
    try:
        return base64.b64encode(v).decode("ascii")
    except Exception:
        return ""


def _iso_dt(v) -> str:
    if not v:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    return str(v)


# ===========================================================================
#  TypeTickets/*  (5 endpoints referentiel)
# ===========================================================================

@router.post("/Tickets/TypeTickets")
def type_tickets(_payload: Any = Body(default=None)):
    """Portage TicketListeTypeDemande. Tous les types actifs de demande."""
    db = get_pg_connection("ticket")
    try:
        rows = db.query(
            """SELECT id_tk_type_demande, service, lib_type_demande, icone
                 FROM ticket.pgt_tk_type_demande
                WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY id_tk_type_demande""",
        ) or []
    except Exception:
        logger.exception("type_tickets")
        return []
    return [
        {"IDTK_TypeDemande": str(int(r.get("id_tk_type_demande") or 0)),
         "Service": (r.get("service") or "").strip(),
         "Lib_TypeDemande": (r.get("lib_type_demande") or "").strip(),
         "icone": _bytea_to_b64(r.get("icone"))}
        for r in rows
    ]


@router.post("/Tickets/TypeTickets/Fournitures")
def type_tickets_fournitures(_payload: Any = Body(default=None)):
    """Portage TicketListeTypeFournitures. Types BS commande."""
    db = get_pg_connection("ticket_bo")
    try:
        rows = db.query(
            """SELECT id_tk_type_commande, lib_type_bs
                 FROM ticket_bo.pgt_tk_type_commande
                WHERE COALESCE(desactiver, FALSE) = FALSE
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY lib_type_bs""",
        ) or []
    except Exception:
        logger.exception("type_tickets_fournitures")
        return []
    return [
        {"IDTK_TypeCommande": str(int(r.get("id_tk_type_commande") or 0)),
         "LibTypeBS": (r.get("lib_type_bs") or "").strip()}
        for r in rows
    ]


@router.post("/Tickets/TypeTickets/Reservation")
def type_tickets_reservation(_payload: Any = Body(default=None)):
    """Portage TicketListeTypeDemandeResa. Sous-familles de resa
    avec le lib du type parent + logo en base64."""
    db = get_pg_connection("ticket_bo")
    try:
        rows = db.query(
            """SELECT ssf.id_tk_type_resa_ss_fam, ssf.id_tk_type_resa,
                      ssf.lib_type_resa_ss_fam, ssf.logo,
                      tr.lib_type_resa
                 FROM ticket_bo.pgt_tk_type_resa_ss_fam ssf
                 LEFT JOIN ticket_bo.pgt_tk_type_resa tr
                        ON tr.id_tk_type_resa = ssf.id_tk_type_resa
                WHERE (ssf.modif_elem IS NULL OR ssf.modif_elem <> 'suppr')
                ORDER BY tr.lib_type_resa, ssf.lib_type_resa_ss_fam""",
        ) or []
    except Exception:
        logger.exception("type_tickets_reservation")
        return []
    return [
        {"IDTK_TypeResaSSFam": str(int(r.get("id_tk_type_resa_ss_fam") or 0)),
         "IDTK_TypeResa": str(int(r.get("id_tk_type_resa") or 0)),
         "Lib_TypeResa": (r.get("lib_type_resa") or "").strip(),
         "Lib_TypeResaSSFam": (r.get("lib_type_resa_ss_fam") or "").strip(),
         "Logo": _bytea_to_b64(r.get("logo"))}
        for r in rows
    ]


@router.post("/Tickets/TypeTickets/SosBO")
def type_tickets_sos_bo(_payload: Any = Body(default=None)):
    """Portage TicketListeTypeSOS_BO."""
    db = get_pg_connection("ticket_bo")
    try:
        rows = db.query(
            """SELECT id_tk_type_sos_bo, lib_type_sos
                 FROM ticket_bo.pgt_tk_type_sos_bo
                WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY lib_type_sos""",
        ) or []
    except Exception:
        logger.exception("type_tickets_sos_bo")
        return []
    return [
        {"IDTK_TypeSOS_BO": str(int(r.get("id_tk_type_sos_bo") or 0)),
         "Lib_TypeSOS_BO": (r.get("lib_type_sos") or "").strip()}
        for r in rows
    ]


@router.post("/Tickets/TypeTickets/SosJU")
def type_tickets_sos_ju(_payload: Any = Body(default=None)):
    """Portage TicketListeTypeSOS_JU."""
    db = get_pg_connection("ticket_rh")
    try:
        rows = db.query(
            """SELECT id_tk_type_sos_ju, lib_type_sos, type_form
                 FROM ticket_rh.pgt_tk_type_sos_ju
                WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY lib_type_sos""",
        ) or []
    except Exception:
        logger.exception("type_tickets_sos_ju")
        return []
    return [
        {"IDTK_TypeSOS": str(int(r.get("id_tk_type_sos_ju") or 0)),
         "Lib_TypeSOS": (r.get("lib_type_sos") or "").strip(),
         "TypeForm": (r.get("type_form") or "").strip()}
        for r in rows
    ]


# ===========================================================================
#  TicketsEnCours
# ===========================================================================

def _droits_salarie(id_salarie: int) -> set[str]:
    """DonneDroitAcces + convention WinDev : "Tous" + "TkDocUleas"."""
    if not id_salarie:
        return set()
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT td.code_interne
                 FROM rh.pgt_salarie_droit_acces sd
                 JOIN rh.pgt_type_droit_acces td
                        ON td.id_type_droit_acces = sd.id_type_droit_acces
                WHERE sd.id_salarie = ?
                  AND COALESCE(sd.droit_actif, FALSE) = TRUE""",
            (int(id_salarie),),
        ) or []
    except Exception:
        logger.exception("_droits_salarie id=%s", id_salarie)
        return {"Tous", "TkDocUleas"}
    codes = {(r.get("code_interne") or "").strip() for r in rows if r.get("code_interne")}
    codes.add("Tous")
    codes.add("TkDocUleas")
    return codes


def _is_resp_or_adm(id_salarie: int) -> bool:
    """Vend est resp d'equipe OU poste contient ADM/TECH -> voit tout."""
    if not id_salarie:
        return False
    db = get_pg_connection("rh")
    try:
        row = db.query_one(
            """SELECT se.resp_equipe, tp.lib_poste
                 FROM rh.pgt_salarie_embauche se
                 LEFT JOIN rh.pgt_type_poste tp ON tp.id_type_poste = se.id_type_poste
                WHERE se.id_salarie = ? LIMIT 1""",
            (int(id_salarie),),
        )
    except Exception:
        return False
    if not row:
        return False
    if row.get("resp_equipe"):
        return True
    lib = (row.get("lib_poste") or "").upper()
    return "ADM" in lib or "TECH" in lib


def _tickets_by_salarie(id_vend: int, seen_ids: set[int],
                          droits: set[str], is_resp_or_adm: bool) -> list[dict]:
    """Portage ReqListeTK_bySalarie. Retourne les tickets non-clotures
    OU cloturés recemment crees PAR ce salarie."""
    db_tk = get_pg_connection("ticket")
    db_rh = get_pg_connection("rh")
    db_bo = get_pg_connection("ticket_bo")
    db_trh = get_pg_connection("ticket_rh")

    try:
        rows = db_tk.query(
            """SELECT tl.id_tk_liste, tl.date_crea, tl.op_crea,
                      tl.id_tk_type_demande, tl.id_tk_statut,
                      tl.modification, tl.op_modif, tl.type_modif,
                      tl.new_comment, tl.op_comment,
                      td.lib_type_demande, td.droit_acces, td.droit_acces_vend,
                      st.lib_statut
                 FROM ticket.pgt_tk_liste tl
                 LEFT JOIN ticket.pgt_tk_type_demande td
                        ON td.id_tk_type_demande = tl.id_tk_type_demande
                 LEFT JOIN ticket.pgt_tk_statut st
                        ON st.id_tk_statut = tl.id_tk_statut
                WHERE COALESCE(tl.cloturee, FALSE) = FALSE
                  AND (tl.modif_elem IS NULL OR tl.modif_elem NOT LIKE '%suppr%')
                  AND tl.op_crea = ?
                ORDER BY tl.date_crea DESC""",
            (int(id_vend),),
        ) or []
    except Exception:
        logger.exception("_tickets_by_salarie id=%s", id_vend)
        return []

    # Prefetch identites operateurs (op_crea)
    op_ids = {int(r.get("op_crea") or 0) for r in rows if r.get("op_crea")}
    op_map: dict[int, dict] = {}
    if op_ids:
        try:
            placeholders = ",".join("?" for _ in op_ids)
            ops = db_rh.query(
                f"""SELECT id_salarie, nom, prenom
                     FROM rh.pgt_salarie
                    WHERE id_salarie IN ({placeholders})""",
                tuple(op_ids),
            ) or []
            op_map = {int(o.get("id_salarie") or 0): o for o in ops}
        except Exception:
            pass

    result = []
    today = date.today()

    for r in rows:
        id_tk = int(r.get("id_tk_liste") or 0)
        if id_tk in seen_ids:
            continue
        id_type = _to_int(r.get("id_tk_type_demande"))
        id_statut = _to_int(r.get("id_tk_statut"))
        droit_acc = (r.get("droit_acces") or "").strip()
        droit_acc_v = (r.get("droit_acces_vend") or "").strip()

        # Filtre droits (WinDev : voir si code appartient a mesDroits)
        acces = (droit_acc in droits) or (droit_acc_v in droits)

        if not is_resp_or_adm:
            if not (id_type in (13, 20) or acces):
                continue

        add = True
        lib_info = ""
        info_cplt1 = ""
        info_cplt2 = ""

        # Cas WinDev
        if id_type == 4:
            # RH Contrat W : verifie contrat_valide + Sign/Paraphe/Mention
            try:
                cw = db_trh.query_one(
                    """SELECT id_salarie, signature, paraphe, lu_app, photo_salarie,
                              contrat_valide
                         FROM ticket_rh.pgt_tk_demande_ctt_w
                        WHERE id_tk_liste = ? LIMIT 1""",
                    (id_tk,),
                )
            except Exception:
                cw = None
            if not cw or not cw.get("contrat_valide"):
                add = False
            else:
                lib_info, info_cplt1, info_cplt2 = _info_ctt_generic(
                    cw.get("id_salarie"), cw.get("signature"),
                    cw.get("paraphe"), cw.get("lu_app"),
                    cw.get("photo_salarie"), "pour")
        elif id_type == 23:
            # RH Contrat Courtage
            try:
                cw = db_bo.query_one(
                    """SELECT id_salarie, signature, paraphe, lu_app, photo_salarie,
                              contrat_valide
                         FROM ticket_bo.pgt_tk_demande_ctt_courtage
                        WHERE id_tk_liste = ? LIMIT 1""",
                    (id_tk,),
                )
            except Exception:
                cw = None
            if not cw or not cw.get("contrat_valide"):
                add = False
            else:
                lib_info, info_cplt1, info_cplt2 = _info_ctt_generic(
                    cw.get("id_salarie"), cw.get("signature"),
                    cw.get("paraphe"), cw.get("lu_app"),
                    cw.get("photo_salarie"), None)
        elif id_type == 24:
            # Cde ExoCash : skip statut 28 (panier)
            if id_statut == 28:
                add = False
        elif id_type in (20, 22):
            # Skip si dateCrea > 2 jours
            d_crea = r.get("date_crea")
            if isinstance(d_crea, datetime):
                dc = d_crea.date()
            elif isinstance(d_crea, date):
                dc = d_crea
            else:
                dc = today
            if (today - dc).days > 2:
                add = False
        elif id_type == 31:
            if id_statut == 31:
                add = False
        elif id_type == 34:
            # Doc Ulease
            try:
                cw = db_trh.query_one(
                    """SELECT id_salarie, signature, paraphe, lu_app, photo_salarie,
                              contrat_valide
                         FROM ticket_rh.pgt_tk_demande_sign_ulease
                        WHERE id_tk_liste = ? LIMIT 1""",
                    (id_tk,),
                )
            except Exception:
                cw = None
            if not cw or not cw.get("contrat_valide"):
                add = False
            else:
                lib_info, info_cplt1, info_cplt2 = _info_ctt_generic(
                    cw.get("id_salarie"), cw.get("signature"),
                    cw.get("paraphe"), cw.get("lu_app"),
                    cw.get("photo_salarie"), "pour")
        elif id_type == 35:
            # PV Liv/Rest Ulease
            try:
                cw = db_trh.query_one(
                    """SELECT id_salarie, signature, paraphe, lu_app, photo_salarie,
                              contrat_valide
                         FROM ticket_rh.pgt_tk_demande_sign_pv_ulease
                        WHERE id_tk_liste = ? LIMIT 1""",
                    (id_tk,),
                )
            except Exception:
                cw = None
            if not cw or not cw.get("contrat_valide"):
                add = False
            else:
                lib_info, info_cplt1, info_cplt2 = _info_ctt_generic(
                    cw.get("id_salarie"), cw.get("signature"),
                    cw.get("paraphe"), cw.get("lu_app"),
                    cw.get("photo_salarie"), None)

        # NOTE : DonneInfoTicket(idTk, idType) non porte V1 pour les
        # autres cas (SOSBO/SOSJU/CONGES/AVANCE/RESA/FOURNITURE/...) ;
        # a completer session dediee. Ici lib_info reste vide.

        if not add:
            seen_ids.add(id_tk)
            continue

        op = op_map.get(int(r.get("op_crea") or 0), {})
        lib_op = ""
        if op:
            lib_op = (f"Par {(op.get('nom') or '').strip()} "
                       f"{_capitalise((op.get('prenom') or '').strip())}").strip()

        result.append({
            "IDTK_Liste": str(id_tk),
            "IDTK_TypeDemande": id_type,
            "Lib_TypeDemande": (r.get("lib_type_demande") or "").strip(),
            "Lib_Statut": (r.get("lib_statut") or "").strip(),
            "DATECREA": _iso_dt(r.get("date_crea")),
            "opCrea": _to_int(r.get("op_crea")),
            "LibOp": lib_op,
            "LibInfo": lib_info,
            "InfoCplt1": info_cplt1,
            "InfoCplt2": info_cplt2,
            "Modification": bool(r.get("modification")),
            "opModif": _to_int(r.get("op_modif")),
            "TypeModif": r.get("type_modif") or "",
            "NewComment": r.get("new_comment") or "",
            "opComment": _to_int(r.get("op_comment")),
        })
        seen_ids.add(id_tk)

    return result


def _info_ctt_generic(id_sal: Any, sig, paraphe, lu_app, photo, prefix: str | None
                       ) -> tuple[str, str, str]:
    """Assemble LibInfo / InfoCplt1 / InfoCplt2 pour les tickets de type
    signature (CttW, CttCourtage, Ulease...)."""
    id_sal = _to_int(id_sal)
    if not id_sal:
        return "", "", "000"
    db_rh = get_pg_connection("rh")
    try:
        s = db_rh.query_one(
            """SELECT s.nom, s.prenom, c.tel_mob, c.mail
                 FROM rh.pgt_salarie s
                 LEFT JOIN rh.pgt_salarie_coordonnees c
                        ON c.id_salarie = s.id_salarie
                WHERE s.id_salarie = ? LIMIT 1""",
            (id_sal,),
        )
    except Exception:
        s = None
    if not s:
        return "", "", "000"
    nom = (s.get("nom") or "").strip()
    prenom = _capitalise((s.get("prenom") or "").strip())
    tel = (s.get("tel_mob") or "").strip()
    mail = (s.get("mail") or "").strip()
    lib = (f"{prefix} {nom} {prenom}" if prefix else f"{nom} {prenom}").strip()
    cpl1 = f"{tel}//{mail}"
    sign = "1" if (sig and photo) else "0"
    parc = "1" if paraphe else "0"
    ment = "1" if lu_app else "0"
    return lib, cpl1, f"{sign}{parc}{ment}"


@router.post("/Tickets/TicketsEnCours")
def tickets_en_cours(payload: Any = Body(...),
                      id_auth: int = Depends(mobile_auth)):
    """Portage TicketsEnCoursBySalarie.

    Payload : tableau d'IDs salaries (variant WinDev direct) OU
    {salaries: [ids]}. Retourne les tickets non-clotures de chaque
    vendeur avec application des droits + regles specifiques par
    type de demande.
    """
    if isinstance(payload, list):
        vendeurs = [_to_int(x) for x in payload if _to_int(x)]
    elif isinstance(payload, dict):
        vendeurs = [_to_int(x) for x in
                     (payload.get("salaries") or payload.get("vendeurs") or [])
                     if _to_int(x)]
        if not vendeurs and _to_int(payload.get("IDSalarie") or id_auth):
            vendeurs = [_to_int(payload.get("IDSalarie") or id_auth)]
    else:
        vendeurs = [id_auth] if id_auth else []

    if not vendeurs:
        return []

    seen: set[int] = set()
    result: list[dict] = []
    for vend in vendeurs:
        droits = _droits_salarie(vend)
        is_resp = _is_resp_or_adm(vend)
        result.extend(_tickets_by_salarie(vend, seen, droits, is_resp))
    return result


@router.post("/Tickets/TicketsEnCours/ModifOpDEST")
def tickets_modif_op_dest(payload: dict = Body(...),
                            id_op: int = Depends(mobile_auth)):
    """Portage TicketModifOpéDest. Reaffecte un lot de tickets a un
    nouvel operateur destinataire (op_dest).

    Payload : { idOpé (nouveau op_dest), users (auteur modif),
                MesTickets: [ids] } OU MesTickets direct en variant.
    NB : pas de modif pour les tickets type 20 (Call SFR).
    """
    id_op_new = _to_int(payload.get("idOpé") or payload.get("idOpe")
                         or payload.get("idOpeDest"))
    users = _to_int(payload.get("users") or id_op)
    tickets = payload.get("MesTickets") or payload.get("tickets") or []
    if not id_op_new or not tickets:
        return {"nIdDemande": "0"}

    db = get_pg_connection("ticket")
    now = datetime.now()
    n_modif = 0
    for tk in tickets:
        id_tk = _to_int(tk)
        if not id_tk:
            continue
        try:
            row = db.query_one(
                """SELECT id_tk_type_demande FROM ticket.pgt_tk_liste
                    WHERE id_tk_liste = ? LIMIT 1""",
                (id_tk,),
            )
        except Exception:
            continue
        if not row or _to_int(row.get("id_tk_type_demande")) == 20:
            continue  # pas de modif pour Call SFR
        try:
            db.query(
                """UPDATE ticket.pgt_tk_liste
                      SET op_dest = ?, modif_date = ?, modif_op = ?
                    WHERE id_tk_liste = ?""",
                (id_op_new, now, users, id_tk),
            )
            n_modif += 1
        except Exception:
            logger.exception("tickets_modif_op_dest id_tk=%s", id_tk)
    return {"nIdDemande": str(n_modif)}
