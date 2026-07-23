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
from app.mobile.agcial import _new_id_wd, _to_int
from app.mobile.auth import _capitalise
from app.mobile.deps import mobile_auth
from app.mobile.sfr import _create_ticket_liste

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


# ===========================================================================
#  Helpers Lot 2
# ===========================================================================

def _identite_salarie(id_sal: int) -> tuple[str, str]:
    """Retourne (Nom, Prenom capitalise) d'un salarie."""
    if not id_sal:
        return "", ""
    db = get_pg_connection("rh")
    try:
        s = db.query_one(
            "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
            (int(id_sal),),
        )
    except Exception:
        return "", ""
    if not s:
        return "", ""
    return (s.get("nom") or "").strip(), (s.get("prenom") or "").strip()


def _touch_tk_liste(id_tk: int, id_op_modif: int,
                     op_dest_new: int | None = None) -> None:
    """Marque TK_Liste modification=TRUE (+ optionnel op_dest)."""
    if not id_tk:
        return
    db = get_pg_connection("ticket")
    now = datetime.now()
    try:
        if op_dest_new is not None:
            db.query(
                """UPDATE ticket.pgt_tk_liste
                      SET modification = TRUE, op_modif = ?, op_dest = ?,
                          modif_date = ?, modif_elem = 'modif'
                    WHERE id_tk_liste = ?""",
                (int(id_op_modif), int(op_dest_new), now, int(id_tk)),
            )
        else:
            db.query(
                """UPDATE ticket.pgt_tk_liste
                      SET modification = TRUE, op_modif = ?,
                          modif_date = ?, modif_elem = 'modif'
                    WHERE id_tk_liste = ?""",
                (int(id_op_modif), now, int(id_tk)),
            )
    except Exception:
        logger.exception("_touch_tk_liste id_tk=%s", id_tk)


# ===========================================================================
#  AVANCE
# ===========================================================================

@router.post("/Tickets/AVANCE/Contenu")
def avance_contenu(payload: dict = Body(...)):
    """Portage DemandeAvance_Contenu."""
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    empty = {
        "Beneficiaire": 0, "IDTK_DemandeAvance": "0", "IDTK_Liste": "0",
        "Montant": 0.0, "NomBeneficiaire": "", "PrenomBeneficiaire": "",
        "PreuveVirement": "",
    }
    if not id_tk:
        return empty

    db = get_pg_connection("ticket_bo")
    try:
        row = db.query_one(
            """SELECT id_tk_demande_avance, id_tk_liste, beneficiaire,
                      montant, preuve_virement
                 FROM ticket_bo.pgt_tk_demande_avance
                WHERE id_tk_liste = ? LIMIT 1""",
            (id_tk,),
        )
    except Exception:
        logger.exception("avance_contenu id=%s", id_tk)
        return empty
    if not row:
        return empty
    nom, prenom = _identite_salarie(_to_int(row.get("beneficiaire")))
    return {
        "Beneficiaire": _to_int(row.get("beneficiaire")),
        "IDTK_DemandeAvance": str(int(row.get("id_tk_demande_avance") or 0)),
        "IDTK_Liste": str(int(row.get("id_tk_liste") or 0)),
        "Montant": float(row.get("montant") or 0),
        "NomBeneficiaire": nom,
        "PrenomBeneficiaire": prenom,
        "PreuveVirement": _bytea_to_b64(row.get("preuve_virement")),
    }


@router.post("/Tickets/AVANCE/Save")
def avance_save(payload: dict = Body(...),
                id_cial: int = Depends(mobile_auth)):
    """Portage DemandeAvance_Save. Type demande=10, service=BO."""
    id_tk = _to_int(payload.get("IDTK_Liste"))
    id_benef = _to_int(payload.get("Beneficiaire"))
    montant = float(payload.get("Montant") or 0)

    db = get_pg_connection("ticket_bo")
    now = datetime.now()

    if id_tk:
        try:
            row = db.query_one(
                """SELECT id_tk_demande_avance
                     FROM ticket_bo.pgt_tk_demande_avance
                    WHERE id_tk_liste = ? LIMIT 1""",
                (id_tk,),
            )
            if not row:
                return {"nIdDemande": "0"}
            db.query(
                """UPDATE ticket_bo.pgt_tk_demande_avance
                      SET beneficiaire = ?, montant = ?, modif_date = ?,
                          modif_op = ?, modif_elem = 'modif'
                    WHERE id_tk_liste = ?""",
                (id_benef, montant, now, id_cial, id_tk),
            )
            _touch_tk_liste(id_tk, id_cial, id_benef)
            return {"nIdDemande": str(id_tk)}
        except Exception as e:
            logger.exception("avance_save update")
            return {"nIdDemande": "0", "sInfoData": str(e)}

    # Insert : cree ticket + insert avance
    id_new = _new_id_wd()
    id_tk_new = _create_ticket_liste("BO", 10, 1, id_cial, id_new)
    if not id_tk_new:
        return {"nIdDemande": "0"}
    try:
        db.query(
            """INSERT INTO ticket_bo.pgt_tk_demande_avance
                 (id_tk_demande_avance_auto, id_tk_demande_avance,
                  id_tk_liste, beneficiaire, montant, preuve_virement,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, NULL, ?, ?, 'new')""",
            (id_new, id_new, id_tk_new, id_benef, montant, now, id_cial),
        )
        return {"nIdDemande": str(id_tk_new)}
    except Exception as e:
        logger.exception("avance_save insert")
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ===========================================================================
#  CartePRO
# ===========================================================================

@router.post("/Tickets/CartePRO/Contenu")
def carte_pro_contenu(payload: dict = Body(...)):
    """Portage DemandeCartePro_Contenu. Retourne toutes les demandes
    liees a ce ticket (le WinDev fait REQ_ListeTkCartePro par ticket)."""
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    if not id_tk:
        return []

    db_bo = get_pg_connection("ticket_bo")
    try:
        rows = db_bo.query(
            """SELECT id_tk_demande_carte_pro, id_tk_liste, id_salarie,
                      num_suivi, op_crea, photo
                 FROM ticket_bo.pgt_tk_demande_carte_pro
                WHERE id_tk_liste = ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')""",
            (id_tk,),
        ) or []
    except Exception:
        logger.exception("carte_pro_contenu id=%s", id_tk)
        return []
    result = []
    for r in rows:
        nom, prenom = _identite_salarie(_to_int(r.get("id_salarie")))
        result.append({
            "IDTK_DemandeCartePRO": str(int(r.get("id_tk_demande_carte_pro") or 0)),
            "IDTK_Liste": str(int(r.get("id_tk_liste") or 0)),
            "IDSalarie": _to_int(r.get("id_salarie")),
            "NomSalarie": f"{nom} {_capitalise(prenom)}".strip(),
            "NumSuivi": r.get("num_suivi") or "",
            "OPCrea": _to_int(r.get("op_crea")),
            "PHOTO": _bytea_to_b64(r.get("photo")),
        })
    return result


@router.post("/Tickets/CartePRO/Save")
def carte_pro_save(payload: dict = Body(...),
                    id_cial: int = Depends(mobile_auth)):
    """Portage DemandeCartePro_Save. Type demande=2, service=BO.
    Cree un nouveau ticket seulement si IDTK_Liste=0."""
    id_dem = _to_int(payload.get("IDTK_DemandeCartePRO"))
    id_tk_liste = _to_int(payload.get("IDTK_Liste"))
    id_sal = _to_int(payload.get("IDSalarie"))
    photo_b64 = payload.get("PHOTO") or ""

    photo_bytes = None
    if photo_b64:
        try:
            photo_bytes = base64.b64decode(photo_b64)
        except Exception:
            photo_bytes = None

    import psycopg2
    db = get_pg_connection("ticket_bo")
    now = datetime.now()

    if id_dem:
        # Update
        try:
            row = db.query_one(
                """SELECT id_tk_liste FROM ticket_bo.pgt_tk_demande_carte_pro
                    WHERE id_tk_demande_carte_pro = ? LIMIT 1""",
                (id_dem,),
            )
            if not row:
                return {"nIdDemande": "0"}
            id_tk_ref = int(row.get("id_tk_liste") or 0)
            if photo_bytes is not None:
                db.query(
                    """UPDATE ticket_bo.pgt_tk_demande_carte_pro
                          SET photo = ?, modif_date = ?, modif_op = ?,
                              modif_elem = 'modif'
                        WHERE id_tk_demande_carte_pro = ?""",
                    (psycopg2.Binary(photo_bytes), now, id_cial, id_dem),
                )
            else:
                db.query(
                    """UPDATE ticket_bo.pgt_tk_demande_carte_pro
                          SET modif_date = ?, modif_op = ?, modif_elem = 'modif'
                        WHERE id_tk_demande_carte_pro = ?""",
                    (now, id_cial, id_dem),
                )
            _touch_tk_liste(id_tk_ref, id_cial)
            return {"nIdDemande": str(id_dem)}
        except Exception as e:
            logger.exception("carte_pro_save update")
            return {"nIdDemande": "0", "sInfoData": str(e)}

    # Insert
    id_new = _new_id_wd()
    if not id_tk_liste:
        id_tk_liste = _create_ticket_liste("BO", 2, 1, id_cial, id_new)
        if not id_tk_liste:
            return {"nIdDemande": "0"}
    try:
        db.query(
            """INSERT INTO ticket_bo.pgt_tk_demande_carte_pro
                 (id_tk_demande_carte_pro_auto, id_tk_demande_carte_pro,
                  id_tk_liste, id_salarie, photo, op_crea, num_suivi,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, '', ?, ?, 'new')""",
            (id_new, id_new, id_tk_liste, id_sal,
             psycopg2.Binary(photo_bytes) if photo_bytes else None,
             id_cial, now, id_cial),
        )
        return {"nIdDemande": str(id_new)}
    except Exception as e:
        logger.exception("carte_pro_save insert")
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ===========================================================================
#  FOURNITURE
# ===========================================================================

@router.post("/Tickets/FOURNITURE/Contenu")
def fourniture_contenu(payload: dict = Body(...)):
    """Portage DemandeFourniture_Contenu. Liste des fournitures du ticket."""
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    if not id_tk:
        return []

    db = get_pg_connection("ticket_bo")
    try:
        rows = db.query(
            """SELECT df.id_tk_demande_fourniture, df.id_tk_liste,
                      df.id_tk_type_commande, df.qte, df.date_envoi,
                      df.num_suivi, df.op_crea, df.priorite_haute,
                      df.adr_livraison,
                      tc.lib_type_bs
                 FROM ticket_bo.pgt_tk_demande_fourniture df
                 LEFT JOIN ticket_bo.pgt_tk_type_commande tc
                        ON tc.id_tk_type_commande = df.id_tk_type_commande
                WHERE df.id_tk_liste = ?
                  AND (df.modif_elem IS NULL OR df.modif_elem <> 'suppr')""",
            (id_tk,),
        ) or []
    except Exception:
        logger.exception("fourniture_contenu id=%s", id_tk)
        return []
    return [
        {"IDTK_DemandeFourniture": str(int(r.get("id_tk_demande_fourniture") or 0)),
         "IDTK_Liste": str(int(r.get("id_tk_liste") or 0)),
         "Lib_TypeCommande": (r.get("lib_type_bs") or "").strip(),
         "IDTK_TypeCommande": _to_int(r.get("id_tk_type_commande")),
         "Qte": _to_int(r.get("qte")),
         "dateEnvoi": _iso_dt(r.get("date_envoi")),
         "NumSuivi": r.get("num_suivi") or "",
         "OPCrea": _to_int(r.get("op_crea")),
         "PrioriteHaute": bool(r.get("priorite_haute")),
         "AdrLivr": r.get("adr_livraison") or ""}
        for r in rows
    ]


@router.post("/Tickets/FOURNITURE/Save")
def fourniture_save(payload: dict = Body(...),
                     id_cial: int = Depends(mobile_auth)):
    """Portage DemandeFourniture_Save. Type demande=1, service=BO."""
    id_dem = _to_int(payload.get("IDTK_DemandeFourniture"))
    id_tk_liste = _to_int(payload.get("IDTK_Liste"))
    id_type_cmd = _to_int(payload.get("IDTK_TypeCommande"))
    qte = _to_int(payload.get("Qte"))
    date_envoi_s = payload.get("dateEnvoi") or ""
    priorite = bool(payload.get("PrioriteHaute"))
    num_suivi = payload.get("NumSuivi") or ""
    op_crea = _to_int(payload.get("OPCrea") or id_cial)

    from app.mobile.agcial import _parse_jour
    d_env = _parse_jour(date_envoi_s)

    db = get_pg_connection("ticket_bo")
    now = datetime.now()

    if id_dem:
        try:
            row = db.query_one(
                """SELECT id_tk_liste FROM ticket_bo.pgt_tk_demande_fourniture
                    WHERE id_tk_demande_fourniture = ? LIMIT 1""",
                (id_dem,),
            )
            if not row:
                return {"nIdDemande": "0"}
            db.query(
                """UPDATE ticket_bo.pgt_tk_demande_fourniture
                      SET id_tk_type_commande = ?, qte = ?, date_envoi = ?,
                          priorite_haute = ?, num_suivi = ?,
                          modif_date = ?, modif_op = ?, modif_elem = 'modif'
                    WHERE id_tk_demande_fourniture = ?""",
                (id_type_cmd, qte, d_env, priorite, num_suivi,
                 now, id_cial, id_dem),
            )
            _touch_tk_liste(int(row.get("id_tk_liste") or 0), id_cial)
            return {"nIdDemande": str(id_dem)}
        except Exception as e:
            logger.exception("fourniture_save update")
            return {"nIdDemande": "0", "sInfoData": str(e)}

    # Insert
    id_new = _new_id_wd()
    if not id_tk_liste:
        id_tk_liste = _create_ticket_liste("BO", 1, 1, id_cial, id_new)
        if not id_tk_liste:
            return {"nIdDemande": "0"}
    try:
        db.query(
            """INSERT INTO ticket_bo.pgt_tk_demande_fourniture
                 (id_tk_demande_fourniture_auto, id_tk_demande_fourniture,
                  id_tk_liste, id_tk_type_commande, qte, date_envoi,
                  priorite_haute, num_suivi, op_crea, date_crea,
                  adr_livraison, modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, 'new')""",
            (id_new, id_new, id_tk_liste, id_type_cmd, qte, d_env,
             priorite, num_suivi, op_crea, now, now, id_cial),
        )
        return {"nIdDemande": str(id_new)}
    except Exception as e:
        logger.exception("fourniture_save insert")
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ===========================================================================
#  SOSBO
# ===========================================================================

@router.post("/Tickets/SOSBO/Contenu")
def sosbo_contenu(payload: dict = Body(...)):
    """Portage DemandeSOS_BO_Contenu."""
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    empty = {"IDTK_DemandeSOS_BO": "0", "IDTK_Liste": "0",
             "IDTK_TypeSOS_BO": 0, "Beneficiaire": 0,
             "NomBeneficiaire": "", "PrenomBeneficiaire": "",
             "InfoCplt": "", "Ref_A_controler": ""}
    if not id_tk:
        return empty
    db = get_pg_connection("ticket_bo")
    try:
        row = db.query_one(
            """SELECT id_tk_demande_sos_bo, id_tk_liste, beneficiaire,
                      id_tk_type_sos_bo, info_cplt, ref_a_controler
                 FROM ticket_bo.pgt_tk_demande_sos_bo
                WHERE id_tk_liste = ? LIMIT 1""",
            (id_tk,),
        )
    except Exception:
        logger.exception("sosbo_contenu id=%s", id_tk)
        return empty
    if not row:
        return empty
    nom, prenom = _identite_salarie(_to_int(row.get("beneficiaire")))
    return {
        "IDTK_DemandeSOS_BO": str(int(row.get("id_tk_demande_sos_bo") or 0)),
        "IDTK_Liste": str(int(row.get("id_tk_liste") or 0)),
        "IDTK_TypeSOS_BO": _to_int(row.get("id_tk_type_sos_bo")),
        "Beneficiaire": _to_int(row.get("beneficiaire")),
        "NomBeneficiaire": nom,
        "PrenomBeneficiaire": prenom,
        "InfoCplt": row.get("info_cplt") or "",
        "Ref_A_controler": row.get("ref_a_controler") or "",
    }


@router.post("/Tickets/SOSBO/Save")
def sosbo_save(payload: dict = Body(...),
                id_cial: int = Depends(mobile_auth)):
    """Portage DemandeSOS_BO_Save. Type demande=11, service=BO."""
    id_dem = _to_int(payload.get("IDTK_DemandeSOS_BO"))
    id_tk_liste = _to_int(payload.get("IDTK_Liste"))
    id_benef = _to_int(payload.get("Beneficiaire"))
    id_type = _to_int(payload.get("IDTK_TypeSOS_BO"))
    ref = payload.get("Ref_A_controler") or ""
    info_cplt = payload.get("InfoCplt") or ""

    db = get_pg_connection("ticket_bo")
    now = datetime.now()

    if id_dem:
        try:
            row = db.query_one(
                """SELECT id_tk_liste FROM ticket_bo.pgt_tk_demande_sos_bo
                    WHERE id_tk_demande_sos_bo = ? LIMIT 1""",
                (id_dem,),
            )
            if not row:
                return {"nIdDemande": "0"}
            id_tk_ref = int(row.get("id_tk_liste") or 0)
            db.query(
                """UPDATE ticket_bo.pgt_tk_demande_sos_bo
                      SET beneficiaire = ?, id_tk_type_sos_bo = ?,
                          ref_a_controler = ?, info_cplt = ?,
                          modif_date = ?, modif_op = ?, modif_elem = 'modif'
                    WHERE id_tk_demande_sos_bo = ?""",
                (id_benef, id_type, ref, info_cplt, now, id_cial, id_dem),
            )
            _touch_tk_liste(id_tk_ref, id_cial, id_benef)
            return {"nIdDemande": str(id_dem)}
        except Exception as e:
            logger.exception("sosbo_save update")
            return {"nIdDemande": "0", "sInfoData": str(e)}

    # Insert
    id_new = _new_id_wd()
    if not id_tk_liste:
        id_tk_liste = _create_ticket_liste("BO", 11, 1, id_cial, id_new)
        if not id_tk_liste:
            return {"nIdDemande": "0"}
    try:
        db.query(
            """INSERT INTO ticket_bo.pgt_tk_demande_sos_bo
                 (id_tk_demande_sos_bo_auto, id_tk_demande_sos_bo,
                  id_tk_liste, beneficiaire, id_tk_type_sos_bo,
                  ref_a_controler, info_cplt,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
            (id_new, id_new, id_tk_liste, id_benef, id_type, ref, info_cplt,
             now, id_cial),
        )
        return {"nIdDemande": str(id_new)}
    except Exception as e:
        logger.exception("sosbo_save insert")
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ===========================================================================
#  SOSJU
# ===========================================================================

@router.post("/Tickets/SOSJU/Contenu")
def sosju_contenu(payload: dict = Body(...)):
    """Portage DemandeSOS_JU_Contenu. Selon TypeForm de TK_TypeSOS_JU,
    resout LibElem depuis salarie / type_poste / societe / vehicule."""
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    empty = {"IDTK_DemandeSOS_JU": "0", "IDTK_Liste": "0",
             "IDTK_TypeSOS_JU": 0, "IDElem": 0, "RefDemande": "",
             "Descriptif": "", "LibTypeSOS_JU": "", "LibElem": ""}
    if not id_tk:
        return empty
    db = get_pg_connection("ticket_rh")
    try:
        row = db.query_one(
            """SELECT id_tk_demande_sos_ju, id_tk_liste, id_tk_type_sos_ju,
                      id_elem, ref_demande, descriptif
                 FROM ticket_rh.pgt_tk_demande_sos_ju
                WHERE id_tk_liste = ? LIMIT 1""",
            (id_tk,),
        )
    except Exception:
        logger.exception("sosju_contenu id=%s", id_tk)
        return empty
    if not row:
        return empty

    id_type = _to_int(row.get("id_tk_type_sos_ju"))
    id_elem = _to_int(row.get("id_elem"))
    type_form = ""
    try:
        tf = db.query_one(
            """SELECT type_form FROM ticket_rh.pgt_tk_type_sos_ju
                WHERE id_tk_type_sos_ju = ? LIMIT 1""",
            (id_type,),
        )
        if tf:
            type_form = (tf.get("type_form") or "").strip()
    except Exception:
        pass

    lib_elem = ""
    if id_elem:
        if type_form == "Salarie":
            nom, prenom = _identite_salarie(id_elem)
            lib_elem = f"{nom} {_capitalise(prenom)}".strip()
        elif type_form == "Poste":
            try:
                rh_db = get_pg_connection("rh")
                p = rh_db.query_one(
                    """SELECT lib_poste FROM rh.pgt_type_poste
                        WHERE id_type_poste = ? LIMIT 1""",
                    (id_elem,),
                )
                if p:
                    lib_elem = (p.get("lib_poste") or "").strip()
            except Exception:
                pass
        elif type_form == "Societe":
            try:
                rh_db = get_pg_connection("rh")
                s = rh_db.query_one(
                    """SELECT rs_interne FROM rh.pgt_societe
                        WHERE id_ste = ? LIMIT 1""",
                    (id_elem,),
                )
                if s:
                    lib_elem = (s.get("rs_interne") or "").strip()
            except Exception:
                pass

    return {
        "IDTK_DemandeSOS_JU": str(int(row.get("id_tk_demande_sos_ju") or 0)),
        "IDTK_Liste": str(int(row.get("id_tk_liste") or 0)),
        "IDTK_TypeSOS_JU": id_type,
        "IDElem": id_elem,
        "RefDemande": row.get("ref_demande") or "",
        "Descriptif": row.get("descriptif") or "",
        "LibTypeSOS_JU": type_form,
        "LibElem": lib_elem,
    }


@router.post("/Tickets/SOSJU/Save")
def sosju_save(payload: dict = Body(...),
                id_cial: int = Depends(mobile_auth)):
    """Portage DemandeSOS_JU_Save. Type demande=17, service=JU.
    op_dest = idCial (WinDev)."""
    id_dem = _to_int(payload.get("IDTK_DemandeSOS_JU"))
    id_tk_liste = _to_int(payload.get("IDTK_Liste"))
    id_type = _to_int(payload.get("IDTK_TypeSOS_JU"))
    id_elem = _to_int(payload.get("IDElem"))
    ref = payload.get("RefDemande") or ""
    descriptif = payload.get("Descriptif") or ""

    db = get_pg_connection("ticket_rh")
    now = datetime.now()

    if id_dem:
        try:
            row = db.query_one(
                """SELECT id_tk_liste FROM ticket_rh.pgt_tk_demande_sos_ju
                    WHERE id_tk_demande_sos_ju = ? LIMIT 1""",
                (id_dem,),
            )
            if not row:
                return {"nIdDemande": "0"}
            id_tk_ref = int(row.get("id_tk_liste") or 0)
            db.query(
                """UPDATE ticket_rh.pgt_tk_demande_sos_ju
                      SET id_tk_type_sos_ju = ?, id_elem = ?,
                          ref_demande = ?, descriptif = ?,
                          modif_date = ?, modif_op = ?, modif_elem = 'modif'
                    WHERE id_tk_demande_sos_ju = ?""",
                (id_type, id_elem, ref, descriptif, now, id_cial, id_dem),
            )
            _touch_tk_liste(id_tk_ref, id_cial, id_cial)
            return {"nIdDemande": str(id_dem)}
        except Exception as e:
            logger.exception("sosju_save update")
            return {"nIdDemande": "0", "sInfoData": str(e)}

    # Insert
    id_new = _new_id_wd()
    if not id_tk_liste:
        id_tk_liste = _create_ticket_liste("JU", 17, 1, id_cial, id_new)
        if not id_tk_liste:
            return {"nIdDemande": "0"}
    try:
        db.query(
            """INSERT INTO ticket_rh.pgt_tk_demande_sos_ju
                 (id_tk_demande_sos_ju_auto, id_tk_demande_sos_ju,
                  id_tk_liste, id_tk_type_sos_ju, id_elem, ref_demande,
                  descriptif, modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
            (id_new, id_new, id_tk_liste, id_type, id_elem, ref, descriptif,
             now, id_cial),
        )
        return {"nIdDemande": str(id_new)}
    except Exception as e:
        logger.exception("sosju_save insert")
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ===========================================================================
#  Helpers Lot 3
# ===========================================================================

_TYPE_CONGE_TO_ABSENCE = {
    "Maladie": 2,
    "Congés payés": 4,
    "Conges payés": 4,
    "Congés sans solde": 5,
    "Conges sans solde": 5,
}


def _absence_id_for(type_conge: str, existing: int) -> int:
    if existing:
        return existing
    return _TYPE_CONGE_TO_ABSENCE.get((type_conge or "").strip(), 14)


def _cloture_tk_liste(id_tk: int, id_op: int, id_statut: int = 4) -> None:
    """Cloture un ticket (statut donne, cloturee=TRUE)."""
    if not id_tk:
        return
    db = get_pg_connection("ticket")
    now = datetime.now()
    try:
        db.query(
            """UPDATE ticket.pgt_tk_liste
                  SET cloturee = TRUE, date_cloture = ?, id_tk_statut = ?,
                      modification = TRUE, op_modif = ?, id_modif = 0,
                      type_modif = 'TKSTATUT', modif_date = ?, modif_op = ?,
                      modif_elem = 'modif'
                WHERE id_tk_liste = ?""",
            (now, id_statut, int(id_op), now, int(id_op), int(id_tk)),
        )
    except Exception:
        logger.exception("_cloture_tk_liste id=%s", id_tk)


# ===========================================================================
#  CONGES
# ===========================================================================

@router.post("/Tickets/CONGES/Contenu")
def conges_contenu(payload: dict = Body(...)):
    """Portage DemandeCongés_Contenu."""
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    empty = {
        "IDTK_DemandeConges": "0", "IDSalarie": 0,
        "sTypeconge": "", "sPeriodeconge": "", "sdateDeb": "", "sdateFin": "",
        "sMotif": "", "idResp": 0, "SignatureDemandeur": "",
        "NomBeneficiaire": "", "PrenomBeneficiaire": "",
        "PosteBeneficiaire": "", "LibOrgaBeneficiaire": "",
        "infoSte": {"LOGO": ""},
    }
    if not id_tk:
        return empty

    db_trh = get_pg_connection("ticket_rh")
    db_tk = get_pg_connection("ticket")
    db_rh = get_pg_connection("rh")

    try:
        row = db_trh.query_one(
            """SELECT id_tk_demande_conges, id_salarie, type_conges,
                      periode_conges, date_debut, date_fin, motifs,
                      signature_demandeur
                 FROM ticket_rh.pgt_tk_demande_conges
                WHERE id_tk_liste = ? LIMIT 1""",
            (id_tk,),
        )
    except Exception:
        logger.exception("conges_contenu id=%s", id_tk)
        return empty

    id_resp = 0
    try:
        tl = db_tk.query_one(
            "SELECT op_dest FROM ticket.pgt_tk_liste WHERE id_tk_liste = ? LIMIT 1",
            (id_tk,),
        )
        if tl:
            id_resp = _to_int(tl.get("op_dest"))
    except Exception:
        pass

    if not row:
        return {**empty, "IDTK_DemandeConges": str(id_tk),
                "idResp": id_resp, "IdResp2": id_resp}

    id_sal = _to_int(row.get("id_salarie"))
    nom, prenom = _identite_salarie(id_sal)

    # Poste + affectation
    lib_poste = ""
    lib_orga = ""
    id_ste = 0
    try:
        s = db_rh.query_one(
            """SELECT se.id_ste, tp.lib_poste
                 FROM rh.pgt_salarie_embauche se
                 LEFT JOIN rh.pgt_type_poste tp ON tp.id_type_poste = se.id_type_poste
                WHERE se.id_salarie = ? LIMIT 1""",
            (id_sal,),
        )
        if s:
            lib_poste = (s.get("lib_poste") or "").strip()
            id_ste = _to_int(s.get("id_ste"))
    except Exception:
        pass

    try:
        aff = db_rh.query_one(
            """SELECT o.lib_orga
                 FROM rh.pgt_salarie_organigramme so
                 JOIN rh.pgt_organigramme o
                        ON o.idorganigramme = so.idorganigramme
                WHERE so.id_salarie = ?
                  AND COALESCE(so.aff_actif, FALSE) = TRUE
                  AND (so.modif_elem IS NULL OR so.modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (id_sal,),
        )
        if aff:
            lib_orga = (aff.get("lib_orga") or "").strip()
    except Exception:
        pass

    # Logo societe
    logo_b64 = ""
    if id_ste:
        try:
            st = db_rh.query_one(
                "SELECT logo FROM rh.pgt_societe WHERE id_ste = ? LIMIT 1",
                (id_ste,),
            )
            if st:
                logo_b64 = _bytea_to_b64(st.get("logo"))
        except Exception:
            pass

    d_deb = row.get("date_debut")
    d_fin = row.get("date_fin")
    return {
        "IDTK_DemandeConges": str(int(row.get("id_tk_demande_conges") or 0)),
        "IDSalarie": id_sal,
        "sTypeconge": (row.get("type_conges") or "").strip(),
        "sPeriodeconge": (row.get("periode_conges") or "").strip(),
        "sdateDeb": d_deb.isoformat() if hasattr(d_deb, "isoformat") else str(d_deb or ""),
        "sdateFin": d_fin.isoformat() if hasattr(d_fin, "isoformat") else str(d_fin or ""),
        "sMotif": row.get("motifs") or "",
        "idResp": id_resp,
        "SignatureDemandeur": _bytea_to_b64(row.get("signature_demandeur")),
        "NomBeneficiaire": nom,
        "PrenomBeneficiaire": prenom,
        "PosteBeneficiaire": lib_poste,
        "LibOrgaBeneficiaire": lib_orga,
        "infoSte": {"LOGO": logo_b64},
    }


@router.post("/Tickets/CONGES/Save")
def conges_save(payload: dict = Body(...),
                id_cial: int = Depends(mobile_auth)):
    """Portage DemandeCongés_Save. Type demande=13, service=DR.
    Le calcul auto du op_dest (resp) est simplifie V1 : on prend
    idResp du payload si fourni, sinon fallback = idCial. TODO V2 :
    logique RecupListeDaDr complete."""
    id_dem = _to_int(payload.get("IDTK_DemandeConges"))
    id_sal = _to_int(payload.get("IDSalarie"))
    type_conge = payload.get("sTypeconge") or ""
    periode = payload.get("sPeriodeconge") or ""
    d_deb = payload.get("sdateDeb")
    d_fin = payload.get("sdateFin")
    motifs = payload.get("sMotif") or ""
    sig_b64 = payload.get("SignatureDemandeur") or ""
    id_type_abs = _to_int(payload.get("IDTypeAbsence"))
    id_resp = _to_int(payload.get("idResp") or id_cial)

    from app.mobile.agcial import _parse_jour
    d_deb_p = _parse_jour(d_deb)
    d_fin_p = _parse_jour(d_fin)

    sig_bytes = None
    if sig_b64:
        try:
            sig_bytes = base64.b64decode(sig_b64)
        except Exception:
            sig_bytes = None

    import psycopg2
    db = get_pg_connection("ticket_rh")
    now = datetime.now()

    id_type_abs = _absence_id_for(type_conge, id_type_abs)

    if id_dem:
        # Update
        try:
            row = db.query_one(
                """SELECT id_tk_liste FROM ticket_rh.pgt_tk_demande_conges
                    WHERE id_tk_demande_conges = ? LIMIT 1""",
                (id_dem,),
            )
            if not row:
                return {"nIdDemande": "0"}
            args = [type_conge, id_type_abs, periode, d_deb_p, d_fin_p, motifs]
            sql = """UPDATE ticket_rh.pgt_tk_demande_conges
                        SET type_conges = ?, id_type_absence = ?,
                            periode_conges = ?, date_debut = ?, date_fin = ?,
                            motifs = ?"""
            if sig_bytes is not None:
                sql += ", signature_demandeur = ?"
                args.append(psycopg2.Binary(sig_bytes))
            sql += """, modif_date = ?, modif_op = ?, modif_elem = 'modif'
                      WHERE id_tk_demande_conges = ?"""
            args.extend([now, id_cial, id_dem])
            db.query(sql, tuple(args))
            _touch_tk_liste(int(row.get("id_tk_liste") or 0), id_cial)
            return {"nIdDemande": str(id_dem)}
        except Exception as e:
            logger.exception("conges_save update")
            return {"nIdDemande": "0", "sInfoData": str(e)}

    # Insert
    id_new = _new_id_wd()
    id_tk_liste = _create_ticket_liste("DR", 13, 1, id_cial, id_new)
    if not id_tk_liste:
        return {"nIdDemande": "0"}

    # Override op_dest = idResp calcule
    if id_resp and id_resp != id_cial:
        try:
            db_tk = get_pg_connection("ticket")
            db_tk.query(
                """UPDATE ticket.pgt_tk_liste SET op_dest = ?
                    WHERE id_tk_liste = ?""",
                (id_resp, id_tk_liste),
            )
        except Exception:
            pass

    try:
        db.query(
            """INSERT INTO ticket_rh.pgt_tk_demande_conges
                 (id_tk_demande_conges_auto, id_tk_demande_conges,
                  id_tk_liste, id_salarie, type_conges, id_type_absence,
                  periode_conges, date_debut, date_fin, motifs,
                  signature_demandeur, modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
            (id_new, id_new, id_tk_liste, id_sal, type_conge, id_type_abs,
             periode, d_deb_p, d_fin_p, motifs,
             psycopg2.Binary(sig_bytes) if sig_bytes else None,
             now, id_cial),
        )
        # TODO V2 : envoiSMS au resp + au demandeur (Perf-Exo, non porte)
        return {"nIdDemande": str(id_new)}
    except Exception as e:
        logger.exception("conges_save insert")
        return {"nIdDemande": "0", "sInfoData": str(e)}


@router.post("/Tickets/CONGES/Validation")
def conges_validation(payload: dict = Body(...),
                        id_cial: int = Depends(mobile_auth)):
    """Portage DemandeCongés_Validation. Cloture ticket + INSERT
    absence (calcul NBJ ouvrés + samedis simplifie).
    TODO V2 : signature resp + generation PDF + FTP + envoi SMS."""
    id_dem = _to_int(payload.get("IDTK_DemandeConges"))
    sig_b64 = payload.get("SignatureDemandeur") or ""
    if not id_dem:
        return {"nIdDemande": "0"}

    import psycopg2
    db = get_pg_connection("ticket_rh")
    dbrh = get_pg_connection("rh")
    now = datetime.now()

    try:
        row = db.query_one(
            """SELECT id_tk_liste, id_salarie, type_conges, id_type_absence,
                      periode_conges, date_debut, date_fin
                 FROM ticket_rh.pgt_tk_demande_conges
                WHERE id_tk_demande_conges = ? LIMIT 1""",
            (id_dem,),
        )
    except Exception:
        logger.exception("conges_validation id=%s", id_dem)
        return {"nIdDemande": "0"}
    if not row:
        return {"nIdDemande": "0"}

    # Signature resp
    if sig_b64:
        try:
            sig_bytes = base64.b64decode(sig_b64)
            db.query(
                """UPDATE ticket_rh.pgt_tk_demande_conges
                      SET signature_resp = ?, modif_date = ?, modif_op = ?
                    WHERE id_tk_demande_conges = ?""",
                (psycopg2.Binary(sig_bytes), now, id_cial, id_dem),
            )
        except Exception:
            logger.exception("conges_validation signature")

    d_deb = row.get("date_debut")
    d_fin = row.get("date_fin")
    id_type_abs = _absence_id_for(row.get("type_conges"),
                                    _to_int(row.get("id_type_absence")))

    # INSERT absence
    if d_deb and d_fin and isinstance(d_deb, date) and isinstance(d_fin, date):
        # Calcul NBJ / NBJ_OUVRES / nb_samedi
        nbj = (d_fin - d_deb).days + 1
        nb_ouvres = 0
        nb_samedi = 0
        cur = d_deb
        while cur <= d_fin:
            wd = cur.weekday()  # 0=lundi..6=dimanche
            if wd < 5:
                nb_ouvres += 1
            elif wd == 5:
                nb_samedi += 1
            cur = cur + timedelta(days=1)

        # Periode fiscale (Juil-Juin)
        if d_deb.month <= 6:
            periode = f"{d_deb.year - 1}-{d_deb.year}"
        else:
            periode = f"{d_deb.year}-{d_deb.year + 1}"

        id_new_abs = _new_id_wd()
        try:
            dbrh.query(
                """INSERT INTO rh.pgt_absence
                     (id_absence_auto, id_absence, id_salarie, id_type_absence,
                      date_debut, date_fin, nbj, nbj_ouvres, nb_samedi, periode,
                      modif_op, modif_date, modif_elem)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                (id_new_abs, id_new_abs,
                 _to_int(row.get("id_salarie")), id_type_abs,
                 d_deb, d_fin, nbj, nb_ouvres, nb_samedi, periode,
                 id_cial, now),
            )
        except Exception:
            logger.exception("conges_validation absence")

    _cloture_tk_liste(_to_int(row.get("id_tk_liste")), id_cial, id_statut=4)
    return {"nIdDemande": str(id_dem)}


@router.post("/Tickets/CONGES/Refus")
def conges_refus(payload: dict = Body(...),
                  id_cial: int = Depends(mobile_auth)):
    """Portage DemandeCongés_Refus. Cloture ticket statut 4.
    TODO V2 : envoi SMS de refus."""
    id_dem = _to_int(payload.get("IDTK_DemandeConges"))
    if not id_dem:
        return {"nIdDemande": "0"}
    db = get_pg_connection("ticket_rh")
    try:
        row = db.query_one(
            """SELECT id_tk_liste FROM ticket_rh.pgt_tk_demande_conges
                WHERE id_tk_demande_conges = ? LIMIT 1""",
            (id_dem,),
        )
    except Exception:
        logger.exception("conges_refus id=%s", id_dem)
        return {"nIdDemande": "0"}
    if not row:
        return {"nIdDemande": "0"}
    _cloture_tk_liste(_to_int(row.get("id_tk_liste")), id_cial, id_statut=4)
    return {"nIdDemande": str(id_dem)}


@router.post("/Tickets/CONGES/Annulation")
def conges_annulation(payload: dict = Body(...),
                        id_cial: int = Depends(mobile_auth)):
    """Portage DemandeCongés_Annulation. Cloture ticket."""
    id_dem = _to_int(payload.get("IDTK_DemandeConges"))
    if not id_dem:
        return {"nIdDemande": "0"}
    db = get_pg_connection("ticket_rh")
    try:
        row = db.query_one(
            """SELECT id_tk_liste FROM ticket_rh.pgt_tk_demande_conges
                WHERE id_tk_demande_conges = ? LIMIT 1""",
            (id_dem,),
        )
    except Exception:
        logger.exception("conges_annulation id=%s", id_dem)
        return {"nIdDemande": "0"}
    # Le WinDev accepte aussi que sMonIddemande = idTk_liste directement
    if not row:
        _cloture_tk_liste(id_dem, id_cial, id_statut=4)
        return {"nIdDemande": str(id_dem)}
    _cloture_tk_liste(_to_int(row.get("id_tk_liste")), id_cial, id_statut=4)
    return {"nIdDemande": str(id_dem)}


# ===========================================================================
#  EnvoiFacture
# ===========================================================================

@router.post("/Tickets/EnvoiFacture/Contenu")
def envoi_facture_contenu(payload: dict = Body(...)):
    """Portage DemandeFacture_Contenu."""
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    empty = {
        "IDTK_DemandeFacturation": "0", "IDTK_Liste": "0",
        "Montant": 0.0, "PreuveVirement": "", "FicFacture": "",
        "Num": "", "DateAchat": "", "lib": "", "desc": "",
    }
    if not id_tk:
        return empty
    db = get_pg_connection("ticket_bo")
    try:
        row = db.query_one(
            """SELECT id_tk_demande_facturation_distrib, id_tk_liste,
                      montant, fic_preuve_virement, fic_facture,
                      num_commande, date_achat, lib_facture, descriptif
                 FROM ticket_bo.pgt_tk_demande_facturation
                WHERE id_tk_liste = ? LIMIT 1""",
            (id_tk,),
        )
    except Exception:
        logger.exception("envoi_facture_contenu id=%s", id_tk)
        return empty
    if not row:
        return empty
    return {
        "IDTK_DemandeFacturation": str(int(row.get("id_tk_demande_facturation_distrib") or 0)),
        "IDTK_Liste": str(int(row.get("id_tk_liste") or 0)),
        "Montant": float(row.get("montant") or 0),
        "PreuveVirement": row.get("fic_preuve_virement") or "",
        "FicFacture": row.get("fic_facture") or "",
        "Num": row.get("num_commande") or "",
        "DateAchat": _iso_dt(row.get("date_achat")),
        "lib": row.get("lib_facture") or "",
        "desc": row.get("descriptif") or "",
    }


@router.post("/Tickets/EnvoiFacture/Save")
def envoi_facture_save(payload: dict = Body(...),
                        id_cial: int = Depends(mobile_auth)):
    """Portage DemandeFacture_Save. Type demande=33, service=BO."""
    id_tk = _to_int(payload.get("IDTK_Liste"))
    lib = payload.get("lib") or ""
    desc = payload.get("desc") or ""
    montant = float(payload.get("Montant") or 0)
    num = payload.get("Num") or ""
    from app.mobile.agcial import _parse_jour
    date_achat = _parse_jour(payload.get("DateAchat"))

    db = get_pg_connection("ticket_bo")
    now = datetime.now()

    if id_tk:
        try:
            row = db.query_one(
                """SELECT id_tk_demande_facturation_distrib
                     FROM ticket_bo.pgt_tk_demande_facturation
                    WHERE id_tk_liste = ? LIMIT 1""",
                (id_tk,),
            )
            if not row:
                return {"nIdDemande": "0"}
            db.query(
                """UPDATE ticket_bo.pgt_tk_demande_facturation
                      SET lib_facture = ?, descriptif = ?, montant = ?,
                          num_commande = ?, date_achat = ?,
                          modif_date = ?, modif_op = ?, modif_elem = 'modif'
                    WHERE id_tk_liste = ?""",
                (lib, desc, montant, num, date_achat, now, id_cial, id_tk),
            )
            _touch_tk_liste(id_tk, id_cial, id_cial)
            return {"nIdDemande": str(id_tk)}
        except Exception as e:
            logger.exception("envoi_facture_save update")
            return {"nIdDemande": "0", "sInfoData": str(e)}

    # Insert
    id_new = _new_id_wd()
    id_tk_new = _create_ticket_liste("BO", 33, 1, id_cial, id_new)
    if not id_tk_new:
        return {"nIdDemande": "0"}
    try:
        db.query(
            """INSERT INTO ticket_bo.pgt_tk_demande_facturation
                 (id_tk_demande_facturation_distrib, id_tk_liste,
                  lib_facture, descriptif, montant, num_commande, date_achat,
                  fic_preuve_virement, fic_facture,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, '', '', ?, ?, 'new')""",
            (id_new, id_tk_new, lib, desc, montant, num, date_achat,
             now, id_cial),
        )
        return {"nIdDemande": str(id_tk_new)}
    except Exception as e:
        logger.exception("envoi_facture_save insert")
        return {"nIdDemande": "0", "sInfoData": str(e)}


@router.post("/Tickets/EnvoiFacture/SaveFacture")
def envoi_facture_save_facture(payload: dict = Body(...),
                                 id_cial: int = Depends(mobile_auth)):
    """Portage DemandeFacture_SaveFacture. Update fic_facture apres
    upload. TODO V2 : le WinDev fait FTP OVH factures/ ou fDeplace ;
    ici on stocke juste le nom fourni par le mobile."""
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    nom_fic = payload.get("NomFic") or ""
    if not id_tk:
        return {"nIdDemande": "0"}
    db = get_pg_connection("ticket_bo")
    now = datetime.now()
    try:
        db.query(
            """UPDATE ticket_bo.pgt_tk_demande_facturation
                  SET fic_facture = ?, modif_date = ?, modif_op = ?,
                      modif_elem = 'modif'
                WHERE id_tk_liste = ?""",
            (nom_fic, now, id_cial, id_tk),
        )
        _touch_tk_liste(id_tk, id_cial, id_cial)
        return {"nIdDemande": str(id_tk)}
    except Exception as e:
        logger.exception("envoi_facture_save_facture id=%s", id_tk)
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ===========================================================================
#  RESA
# ===========================================================================

@router.post("/Tickets/RESA/Contenu")
def resa_contenu(payload: dict = Body(...)):
    """Portage DemandeResa_Contenu."""
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    if not id_tk:
        return {}
    db = get_pg_connection("ticket_bo")
    try:
        row = db.query_one(
            """SELECT dr.id_tk_demande_resa, dr.id_tk_liste,
                      dr.id_tk_type_resa_ss_fam, dr.ville_dep, dr.ville_arr,
                      dr.jour_dep, dr.jour_arr, dr.heure_dep, dr.heure_arr,
                      dr.beneficiaire, dr.info_cplt, dr.liste_bene_supp,
                      dr.ar, dr.jour_r_dep, dr.jour_r_arr,
                      dr.heure_r_dep, dr.heure_r_arr,
                      ssf.id_tk_type_resa, ssf.lib_type_resa_ss_fam,
                      tr.lib_type_resa
                 FROM ticket_bo.pgt_tk_demande_resa dr
                 LEFT JOIN ticket_bo.pgt_tk_type_resa_ss_fam ssf
                        ON ssf.id_tk_type_resa_ss_fam = dr.id_tk_type_resa_ss_fam
                 LEFT JOIN ticket_bo.pgt_tk_type_resa tr
                        ON tr.id_tk_type_resa = ssf.id_tk_type_resa
                WHERE dr.id_tk_liste = ? LIMIT 1""",
            (id_tk,),
        )
    except Exception:
        logger.exception("resa_contenu id=%s", id_tk)
        return {}
    if not row:
        return {}
    nom, prenom = _identite_salarie(_to_int(row.get("beneficiaire")))
    return {
        "AR": bool(row.get("ar")),
        "Beneficiaire": _to_int(row.get("beneficiaire")),
        "ListeBeneSupp": row.get("liste_bene_supp") or "",
        "Heure_Arr": str(row.get("heure_arr") or ""),
        "Heure_Dep": str(row.get("heure_dep") or ""),
        "HeureR_Arr": str(row.get("heure_r_arr") or ""),
        "HeureR_Dep": str(row.get("heure_r_dep") or ""),
        "IDTK_DemandeResa": str(int(row.get("id_tk_demande_resa") or 0)),
        "IDTK_Liste": str(int(row.get("id_tk_liste") or 0)),
        "IDTK_TypeResa": _to_int(row.get("id_tk_type_resa")),
        "IDTK_TypeResaSSFam": _to_int(row.get("id_tk_type_resa_ss_fam")),
        "InfoCplt": row.get("info_cplt") or "",
        "Jour_Arr": _iso_dt(row.get("jour_arr")),
        "Jour_Dep": _iso_dt(row.get("jour_dep")),
        "JourR_Arr": _iso_dt(row.get("jour_r_arr")),
        "JourR_Dep": _iso_dt(row.get("jour_r_dep")),
        "Lib_TypeResa": (row.get("lib_type_resa") or "").strip(),
        "Lib_TypeResaSSFam": (row.get("lib_type_resa_ss_fam") or "").strip(),
        "NomBeneficiaire": nom,
        "PrenomBeneficiaire": prenom,
        "Ville_Arr": row.get("ville_arr") or "",
        "Ville_Dep": row.get("ville_dep") or "",
        "ListePJ": [],  # TODO V2 : FTP DocTicket/{id}/ listing
    }


@router.post("/Tickets/RESA/Save")
def resa_save(payload: dict = Body(...),
              id_cial: int = Depends(mobile_auth)):
    """Portage DemandeResa_Save. Type demande=9, service=BO."""
    id_tk_liste = _to_int(payload.get("IDTK_Liste"))
    id_ssf = _to_int(payload.get("IDTK_TypeResaSSFam"))
    v_dep = payload.get("Ville_Dep") or ""
    v_arr = payload.get("Ville_Arr") or ""
    from app.mobile.agcial import _parse_jour
    j_dep = _parse_jour(payload.get("Jour_Dep"))
    j_arr = _parse_jour(payload.get("Jour_Arr"))
    jr_dep = _parse_jour(payload.get("JourR_Dep"))
    jr_arr = _parse_jour(payload.get("JourR_Arr"))
    h_dep = payload.get("Heure_Dep") or None
    h_arr = payload.get("Heure_Arr") or None
    hr_dep = payload.get("HeureR_Dep") or None
    hr_arr = payload.get("HeureR_Arr") or None
    id_benef = _to_int(payload.get("Beneficiaire"))
    info_cplt = payload.get("InfoCplt") or ""
    liste_supp = payload.get("ListeBeneSupp") or ""
    ar = bool(payload.get("AR"))

    db = get_pg_connection("ticket_bo")
    now = datetime.now()

    if id_tk_liste:
        try:
            row = db.query_one(
                """SELECT id_tk_demande_resa FROM ticket_bo.pgt_tk_demande_resa
                    WHERE id_tk_liste = ? LIMIT 1""",
                (id_tk_liste,),
            )
            if not row:
                return {"nIdDemande": "0"}
            db.query(
                """UPDATE ticket_bo.pgt_tk_demande_resa
                      SET id_tk_type_resa_ss_fam = ?, ville_dep = ?, ville_arr = ?,
                          jour_dep = ?, jour_arr = ?, heure_dep = ?, heure_arr = ?,
                          beneficiaire = ?, info_cplt = ?, liste_bene_supp = ?,
                          ar = ?, jour_r_dep = ?, jour_r_arr = ?,
                          heure_r_dep = ?, heure_r_arr = ?,
                          modif_date = ?, modif_op = ?, modif_elem = 'modif'
                    WHERE id_tk_liste = ?""",
                (id_ssf, v_dep, v_arr, j_dep, j_arr, h_dep, h_arr,
                 id_benef, info_cplt, liste_supp, ar,
                 jr_dep, jr_arr, hr_dep, hr_arr,
                 now, id_cial, id_tk_liste),
            )
            _touch_tk_liste(id_tk_liste, id_cial, id_benef)
            return {"nIdDemande": str(id_tk_liste)}
        except Exception as e:
            logger.exception("resa_save update")
            return {"nIdDemande": "0", "sInfoData": str(e)}

    # Insert
    id_new = _new_id_wd()
    id_tk_new = _create_ticket_liste("BO", 9, 1, id_cial, id_new)
    if not id_tk_new:
        return {"nIdDemande": "0"}
    try:
        db.query(
            """INSERT INTO ticket_bo.pgt_tk_demande_resa
                 (id_tk_demande_resa_auto, id_tk_demande_resa, id_tk_liste,
                  id_tk_type_resa_ss_fam, ville_dep, ville_arr,
                  jour_dep, jour_arr, heure_dep, heure_arr,
                  beneficiaire, info_cplt, liste_bene_supp, pj, ar,
                  jour_r_dep, jour_r_arr, heure_r_dep, heure_r_arr,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?,
                       ?, ?, ?, ?, ?, ?, 'new')""",
            (id_new, id_new, id_tk_new, id_ssf, v_dep, v_arr,
             j_dep, j_arr, h_dep, h_arr,
             id_benef, info_cplt, liste_supp, ar,
             jr_dep, jr_arr, hr_dep, hr_arr,
             now, id_cial),
        )
        # TODO V2 : FTP_CreaRep("DocTicket/{id}") pour les PJ
        return {"nIdDemande": str(id_tk_new)}
    except Exception as e:
        logger.exception("resa_save insert")
        return {"nIdDemande": "0", "sInfoData": str(e)}


@router.post("/Tickets/RESA/EnrPhoto")
def resa_enr_photo(payload: dict = Body(...)):
    """Portage DemandeResa_EnrPhoto. Enregistre une photo/PJ liee au
    ticket sur le FTP OVH ou en local.

    Payload STPhotoDPAE : { IDTK_Liste, nomPhoto, maphoto (base64) }
    TODO V2 : envoi FTP OVH. Ici on ecrit uniquement en local si
    D:\\OMAYA\\DocTicket\\{id}\\ existe.
    """
    id_tk = _to_int(payload.get("IDTK_Liste"))
    nom = payload.get("nomPhoto") or ""
    photo_b64 = payload.get("maphoto") or ""
    if not id_tk or not nom or not photo_b64:
        return {"nIdDemande": "0"}

    try:
        photo_bytes = base64.b64decode(photo_b64)
    except Exception:
        return {"nIdDemande": "0", "sInfoData": "Base64 invalide"}

    import os
    base_dir = os.path.join(r"D:\OMAYA\DocTicket", str(id_tk))
    try:
        os.makedirs(base_dir, exist_ok=True)
        with open(os.path.join(base_dir, nom), "wb") as f:
            f.write(photo_bytes)
    except Exception:
        logger.exception("resa_enr_photo write id=%s", id_tk)
        return {"nIdDemande": "0"}
    return {"nIdDemande": str(id_tk)}


# ===========================================================================
#  SortieRH
# ===========================================================================

@router.post("/Tickets/SortieRH/Save")
def sortie_rh_save(payload: dict = Body(...),
                     id_cial: int = Depends(mobile_auth)):
    """Portage DemandeSortieRH_Save. Type demande=12, service=RH.
    Verif anti-doublon : meme (id_salarie, type_sortie) non-cloturé.
    TODO V2 : upload PDF InfoCplt via FTP OVH."""
    id_tk = _to_int(payload.get("IDTK_Liste"))
    id_sal = _to_int(payload.get("IDSalarie"))
    type_sortie = (payload.get("TypeSortie") or "").strip()
    info_cplt = payload.get("InfoCplt") or ""

    db_trh = get_pg_connection("ticket_rh")
    db_tk = get_pg_connection("ticket")
    now = datetime.now()

    action = ""
    if id_tk:
        try:
            row = db_trh.query_one(
                """SELECT id_tk_demande_sortie_rh
                     FROM ticket_rh.pgt_tk_demande_sortie_rh
                    WHERE id_tk_demande_sortie_rh = ? LIMIT 1""",
                (id_tk,),
            )
            if row:
                action = "Modif"
        except Exception:
            pass

    if not action:
        # Verif anti-doublon
        try:
            dup = db_tk.query_one(
                """SELECT tsr.id_tk_liste
                     FROM ticket_rh.pgt_tk_demande_sortie_rh tsr
                     JOIN ticket.pgt_tk_liste tl ON tl.id_tk_liste = tsr.id_tk_liste
                    WHERE tsr.id_salarie = ?
                      AND tsr.type_sortie = ?
                      AND COALESCE(tl.cloturee, FALSE) = FALSE
                    LIMIT 1""",
                (id_sal, type_sortie),
            )
            if dup:
                id_tk = _to_int(dup.get("id_tk_liste"))
                action = "Modif"
        except Exception:
            logger.exception("sortie_rh_save dedup")

    doc_sortie = False  # TODO V2 : upload FTP puis TRUE

    if action == "Modif":
        try:
            db_trh.query(
                """UPDATE ticket_rh.pgt_tk_demande_sortie_rh
                      SET type_sortie = ?, doc_sortie = ?,
                          modif_date = ?, modif_op = ?, modif_elem = 'modif'
                    WHERE id_tk_demande_sortie_rh = ?""",
                (type_sortie, doc_sortie, now, id_cial, id_tk),
            )
            # Cherche id_tk_liste
            row = db_trh.query_one(
                """SELECT id_tk_liste FROM ticket_rh.pgt_tk_demande_sortie_rh
                    WHERE id_tk_demande_sortie_rh = ? LIMIT 1""",
                (id_tk,),
            )
            if row:
                _touch_tk_liste(_to_int(row.get("id_tk_liste")), id_cial)
            return {"nIdDemande": str(id_tk)}
        except Exception as e:
            logger.exception("sortie_rh_save update")
            return {"nIdDemande": "0", "sInfoData": str(e)}

    # Insert
    id_new = _new_id_wd()
    id_tk_new = _create_ticket_liste("RH", 12, 1, id_cial, id_new)
    if not id_tk_new:
        return {"nIdDemande": "0"}
    try:
        db_trh.query(
            """INSERT INTO ticket_rh.pgt_tk_demande_sortie_rh
                 (id_tk_demande_sortie_rh_auto, id_tk_demande_sortie_rh,
                  id_tk_liste, id_salarie, type_sortie, doc_sortie,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
            (id_new, id_new, id_tk_new, id_sal, type_sortie, doc_sortie,
             now, id_cial),
        )
        return {"nIdDemande": str(id_tk_new)}
    except Exception as e:
        logger.exception("sortie_rh_save insert")
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ===========================================================================
#  DocDistrib
# ===========================================================================

@router.post("/Tickets/DocDistrib/Contenu")
def doc_distrib_contenu(payload: dict = Body(...)):
    """Portage DemandeDocDistrib_Contenu. JOIN vers Doc_Distrib +
    TypeDocDistributeur + societe pour libelles."""
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    empty = {"idDocDistrib": 0, "idTicket": 0, "datePrevue": "",
             "libDoc": "", "libSte": ""}
    if not id_tk:
        return empty

    db_bo = get_pg_connection("ticket_bo")
    db_rh = get_pg_connection("rh")
    try:
        row = db_bo.query_one(
            """SELECT id_doc_distrib
                 FROM ticket_bo.pgt_tk_demande_doc_distrib
                WHERE id_tk_liste = ? LIMIT 1""",
            (id_tk,),
        )
    except Exception:
        logger.exception("doc_distrib_contenu id=%s", id_tk)
        return empty
    if not row:
        return empty

    id_doc = _to_int(row.get("id_doc_distrib"))
    date_prev = ""
    lib_doc = ""
    lib_ste = ""
    try:
        d = db_rh.query_one(
            """SELECT dd.date_prevue, dd.id_ste, dd.id_type_doc_distributeur,
                      td.lib_doc, ste.raison_sociale
                 FROM rh.pgt_doc_distrib dd
                 LEFT JOIN rh.pgt_type_doc_distributeur td
                        ON td.id_type_doc_distributeur = dd.id_type_doc_distributeur
                 LEFT JOIN rh.pgt_societe ste ON ste.id_ste = dd.id_ste
                WHERE dd.id_doc_distrib = ? LIMIT 1""",
            (id_doc,),
        )
        if d:
            date_prev = _iso_dt(d.get("date_prevue"))
            lib_doc = (d.get("lib_doc") or "").strip()
            lib_ste = (d.get("raison_sociale") or "").strip()
    except Exception:
        logger.exception("doc_distrib_contenu doc id=%s", id_doc)

    return {
        "idDocDistrib": id_doc,
        "idTicket": id_tk,
        "datePrevue": date_prev,
        "libDoc": lib_doc,
        "libSte": lib_ste,
    }


@router.post("/Tickets/DocDistrib/Save")
def doc_distrib_save(payload: dict = Body(...),
                       id_cial: int = Depends(mobile_auth)):
    """Portage DemandeDocDistrib_Enr. Simplifie V1 : update
    LienFichier (le nom du PDF fusionne) + passe le ticket a
    statut 31. TODO V2 : fusion PDF + upload FTP + envoi mail
    juristes."""
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    lib_doc = payload.get("libDoc") or ""
    nom_fic = payload.get("nomFic") or f"{id_tk}_{lib_doc.replace(' ', '_')}.pdf"
    if not id_tk:
        return {"nIdDemande": "0"}

    db_bo = get_pg_connection("ticket_bo")
    db_tk = get_pg_connection("ticket")
    now = datetime.now()
    try:
        db_bo.query(
            """UPDATE ticket_bo.pgt_tk_demande_doc_distrib
                  SET lien_fichier = ?, modif_date = ?, modif_op = ?,
                      modif_elem = 'modif'
                WHERE id_tk_liste = ?""",
            (nom_fic, now, id_cial, id_tk),
        )
        db_tk.query(
            """UPDATE ticket.pgt_tk_liste
                  SET id_tk_statut = 31, modif_date = ?, modif_op = ?,
                      modif_elem = 'modif'
                WHERE id_tk_liste = ?""",
            (now, id_cial, id_tk),
        )
        return {"nIdDemande": str(id_tk)}
    except Exception as e:
        logger.exception("doc_distrib_save id=%s", id_tk)
        return {"nIdDemande": "0", "sInfoData": str(e)}
