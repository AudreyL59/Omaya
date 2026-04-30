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
        cloturee: bool = Query(False, description="True = clôturés uniquement"),
        date_du: str = Query("", description="Format YYYYMMDD (vide = pas de borne)"),
        date_au: str = Query("", description="Format YYYYMMDD (vide = pas de borne)"),
        user: UserToken = Depends(get_current_user),
    ):
        """Liste les tickets pour un type de demande (filtre date / clôture).

        Enrichit chaque ligne avec :
          - lib_statut (TK_Statut)
          - op_dest_nom/prenom (= "Opérateur" dans la table WinDev)
          - op_staff_nom/prenom (= "Opé Staff", formaté Prenom + initiale)
          - info via DonneInfoTicket batch.

        Vérifie l'accès au type de demande selon les droits du user.
        """
        # Contrôle d'accès
        types_user = list_types_par_droit(user.droits, droit_field)
        allowed_ids = {int(t["id_type_demande"]) for t in types_user if t["id_type_demande"].isdigit()}
        if int(id_type_demande) not in allowed_ids:
            raise HTTPException(
                status_code=403,
                detail="Type de demande non accessible avec vos droits",
            )

        # Conversion dates YYYYMMDD → format WinDev compact 17 chars
        def _to_wd(s: str, end: bool = False) -> str:
            if not s or len(s) < 8 or not s[:8].isdigit():
                return ""
            ymd = s[:8]
            return f"{ymd}{'235959999' if end else '000000000'}"

        rows_raw = list_tickets_par_type(
            int(id_type_demande),
            cloturee=cloturee,
            date_du=_to_wd(date_du, end=False),
            date_au=_to_wd(date_au, end=True),
        )

        # Batch : salaries (OPDEST + OpTraitementStaff)
        id_salaries: set[int] = set()
        for r in rows_raw:
            for k in ("op_dest", "op_traitement_staff", "op_crea"):
                v = r.get(k) or ""
                if v.isdigit() and int(v) > 0:
                    id_salaries.add(int(v))
        salaries = load_salaries_minimal(id_salaries)

        id_tickets = [int(r["id_ticket"]) for r in rows_raw if r["id_ticket"].isdigit()]
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
            odest = int(r["op_dest"]) if r["op_dest"].isdigit() else 0
            ostaff = int(r["op_traitement_staff"]) if r["op_traitement_staff"].isdigit() else 0
            ocrea = int(r["op_crea"]) if r["op_crea"].isdigit() else 0
            odest_info = salaries.get(odest, {})
            ostaff_info = salaries.get(ostaff, {})
            ocrea_info = salaries.get(ocrea, {})
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
                op_dest_nom=odest_info.get("nom", ""),
                op_dest_prenom=odest_info.get("prenom", ""),
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
