"""Router shared Tickets — monté avec une dépendance qui fournit le
champ droit à utiliser (DroitAccès pour ADM, DroitAccèsVend pour Vendeur).

Le pattern :
    def get_tickets_router(droit_field: str) -> APIRouter:
        ...

Côté intranet, l'inclusion ressemble à :
    router.include_router(get_tickets_router("DroitAccès"), prefix="")
"""

from collections import defaultdict
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

from .info_ticket import donne_info_ticket_batch
from .schemas import (
    TicketListResponse,
    TicketRow,
    TicketSidebarItem,
    TicketStatut,
    TicketTypeDemande,
)
from .service import (
    list_statuts,
    list_tickets_par_type,
    list_types_par_droit,
    load_salaries_minimal,
    _to_int,
)


def get_tickets_router(droit_field: str) -> APIRouter:
    """Construit le router /tickets pour un intranet donné.

    droit_field : "DroitAccès" (ADM) ou "DroitAccèsVend" (Vendeur).
    """
    router = APIRouter(prefix="/tickets", tags=["tickets"])

    @router.get("/sidebar", response_model=list[TicketSidebarItem])
    def get_sidebar(user: UserToken = Depends(get_current_user)):
        """Sidebar : services groupés (BO/IT/JU/RH/...) avec leurs types
        accessibles selon les droits du user.
        """
        types_raw = list_types_par_droit(user.droits, droit_field)
        groups: dict[str, list[dict]] = defaultdict(list)
        for t in types_raw:
            groups[t["service"]].append(t)
        out: list[TicketSidebarItem] = []
        for service in sorted(groups.keys()):
            out.append(TicketSidebarItem(
                service=service,
                types=[TicketTypeDemande(**t) for t in groups[service]],
            ))
        return out

    @router.get("/statuts", response_model=list[TicketStatut])
    def get_statuts(user: UserToken = Depends(get_current_user)):
        return [TicketStatut(**s) for s in list_statuts()]

    @router.get("", response_model=TicketListResponse)
    def get_tickets(
        id_type_demande: int = Query(..., description="IDTK_TypeDemande"),
        only_open: bool = Query(True, description="Cacher les tickets cloturés"),
        user: UserToken = Depends(get_current_user),
    ):
        """Liste les tickets pour un type de demande, enrichis avec :
        - lib_statut, op_crea_nom/prenom, op_staff_nom/prenom
        - info (via DonneInfoTicket batch).

        Vérifie aussi que l'utilisateur a bien accès à ce type de demande.
        """
        # Contrôle d'accès : le type doit être dans les types autorisés du user
        types_user = list_types_par_droit(user.droits, droit_field)
        allowed_ids = {int(t["id_type_demande"]) for t in types_user if t["id_type_demande"].isdigit()}
        if int(id_type_demande) not in allowed_ids:
            raise HTTPException(
                status_code=403,
                detail="Type de demande non accessible avec vos droits",
            )

        rows_raw = list_tickets_par_type(int(id_type_demande), only_open=only_open)

        # Lookups en batch
        id_tickets = [int(r["id_ticket"]) for r in rows_raw if r["id_ticket"].isdigit()]
        id_salaries: set[int] = set()
        for r in rows_raw:
            for k in ("op_crea", "op_traitement_staff"):
                v = r.get(k) or ""
                if v.isdigit() and int(v) > 0:
                    id_salaries.add(int(v))
        salaries = load_salaries_minimal(id_salaries)
        infos = donne_info_ticket_batch(int(id_type_demande), id_tickets)
        statuts_all = list_statuts()
        statut_lib = {s["id_statut"]: s["lib_statut"] for s in statuts_all}

        rows: list[TicketRow] = []
        statuts_present: list[int] = []
        seen_statuts: set[int] = set()
        for r in rows_raw:
            id_st = r["id_statut"]
            if id_st not in seen_statuts:
                seen_statuts.add(id_st)
                statuts_present.append(id_st)
            ocrea = int(r["op_crea"]) if r["op_crea"].isdigit() else 0
            ostaff = int(r["op_traitement_staff"]) if r["op_traitement_staff"].isdigit() else 0
            ocrea_info = salaries.get(ocrea, {})
            ostaff_info = salaries.get(ostaff, {})
            rows.append(TicketRow(
                id_ticket=r["id_ticket"],
                id_type_demande=r["id_type_demande"],
                service=r["service"],
                id_statut=id_st,
                lib_statut=statut_lib.get(id_st, ""),
                date_crea=r["date_crea"],
                op_crea=r["op_crea"],
                op_crea_nom=ocrea_info.get("nom", ""),
                op_crea_prenom=ocrea_info.get("prenom", ""),
                op_dest=r["op_dest"],
                op_traitement_staff=r["op_traitement_staff"],
                op_staff_nom=ostaff_info.get("nom", ""),
                op_staff_prenom=ostaff_info.get("prenom", ""),
                info=infos.get(r["id_ticket"], ""),
                cloturee=r["cloturee"],
                date_cloture=r["date_cloture"],
                date_report=r["date_report"],
                modif_date=r["modif_date"],
                modification=r["modification"],
            ))

        statuts_ordered: list[TicketStatut] = []
        # Ordonne d'abord les statuts présents par leur IDTK_Statut (le code
        # WinDev affiche en général dans cet ordre — Non traité = 1)
        for sid in sorted(statuts_present):
            statuts_ordered.append(TicketStatut(
                id_statut=sid,
                lib_statut=statut_lib.get(sid, str(sid)),
            ))

        return TicketListResponse(
            rows=rows,
            statuts=statuts_ordered,
            total=len(rows),
        )

    return router
