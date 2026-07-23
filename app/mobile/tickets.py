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
