"""Router shared Tickets — monté avec une dépendance qui fournit le
champ droit à utiliser (DroitAccès pour ADM, DroitAccèsVend pour Vendeur).

Le pattern :
    def get_tickets_router(droit_field: str) -> APIRouter:
        ...

Côté intranet, l'inclusion ressemble à :
    router.include_router(get_tickets_router("DroitAccès"), prefix="")
"""

import asyncio
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.core.auth.security import decode_access_token

from .info_ticket import donne_info_ticket_batch
from .schemas import (
    TicketListResponse,
    TicketRow,
    TicketSidebarItem,
    TicketStatut,
    TicketTypeDemande,
)
from .service import (
    _now_windev,
    list_statuts,
    list_tickets_modified_since,
    list_tickets_par_type,
    list_type_ids_par_droit,
    list_types_par_droit,
    load_salaries_minimal,
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
        # Contrôle d'accès — version "light" sans charger les mémos
        # Lib_TypeDemande (cachée 60s, donc 0 query après le 1er hit).
        if int(id_type_demande) not in list_type_ids_par_droit(user.droits, droit_field):
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

        # Lookups indépendants — lancés en parallèle pour réduire la latence
        # (chaque query bridge HFSQL = ~400ms de subprocess overhead).
        id_salaries: set[int] = set()
        for r in rows_raw:
            for k in ("op_dest", "op_traitement_staff", "op_crea"):
                v = r.get(k) or ""
                if v.isdigit() and int(v) > 0:
                    id_salaries.add(int(v))
        id_tickets = [int(r["id_ticket"]) for r in rows_raw if r["id_ticket"].isdigit()]

        with ThreadPoolExecutor(max_workers=3) as pool:
            f_salaries = pool.submit(load_salaries_minimal, id_salaries)
            f_infos = pool.submit(donne_info_ticket_batch, int(id_type_demande), id_tickets)
            f_statuts = pool.submit(list_statuts)
            salaries = f_salaries.result()
            infos = f_infos.result()
            statuts_all = f_statuts.result()
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

    # -------------------------------------------------------------
    # SSE — push live des tickets ajoutés/modifiés depuis l'ouverture
    # -------------------------------------------------------------

    POLL_INTERVAL_S = 4.0      # fréquence de polling DB
    HEARTBEAT_EVERY_S = 25.0   # commentaire ": ping" pour keep-alive proxies

    def _enrich_rows(rows_raw: list[dict]) -> list[dict]:
        """Enrichit (op_dest, op_staff, op_crea, lib_statut, info)."""
        if not rows_raw:
            return []
        id_salaries: set[int] = set()
        id_tickets: list[int] = []
        type_demandes: set[int] = set()
        for r in rows_raw:
            for k in ("op_dest", "op_traitement_staff", "op_crea"):
                v = r.get(k) or ""
                if v.isdigit() and int(v) > 0:
                    id_salaries.add(int(v))
            if r["id_ticket"].isdigit():
                id_tickets.append(int(r["id_ticket"]))
            if r["id_type_demande"].isdigit():
                type_demandes.add(int(r["id_type_demande"]))

        salaries = load_salaries_minimal(id_salaries)
        statuts_all = list_statuts()
        statut_lib = {s["id_statut"]: s["lib_statut"] for s in statuts_all}
        # En pratique le stream est filtré sur 1 type_demande
        infos: dict[str, str] = {}
        for tid in type_demandes:
            ids_for_type = [
                int(r["id_ticket"]) for r in rows_raw
                if r["id_type_demande"] == str(tid) and r["id_ticket"].isdigit()
            ]
            if ids_for_type:
                infos.update(donne_info_ticket_batch(tid, ids_for_type))

        out: list[dict] = []
        for r in rows_raw:
            odest = int(r["op_dest"]) if r["op_dest"].isdigit() else 0
            ostaff = int(r["op_traitement_staff"]) if r["op_traitement_staff"].isdigit() else 0
            ocrea = int(r["op_crea"]) if r["op_crea"].isdigit() else 0
            odest_info = salaries.get(odest, {})
            ostaff_info = salaries.get(ostaff, {})
            ocrea_info = salaries.get(ocrea, {})
            row = TicketRow(
                id_ticket=r["id_ticket"],
                id_type_demande=r["id_type_demande"],
                service=r["service"],
                id_statut=r["id_statut"],
                lib_statut=statut_lib.get(r["id_statut"], ""),
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
            )
            out.append(row.model_dump())
        return out

    @router.get("/stream")
    async def stream_tickets(
        request: Request,
        id_type_demande: int = Query(..., description="IDTK_TypeDemande à streamer"),
        cloturee: bool = Query(False),
        date_du: str = Query(""),
        date_au: str = Query(""),
        token: str = Query("", description="JWT (fallback si pas de header Bearer)"),
    ):
        """SSE — pousse les tickets ajoutés ou modifiés depuis l'ouverture
        du stream pour le type de demande sélectionné.

        Auth flexible : header Bearer OU query param `token` (utile car
        l'EventSource natif côté navigateur ne permet pas de headers).

        Format des événements :
          event: ready
          data: {"cursor_start": "20260430...."}

          event: tickets
          data: {"events": [{"kind":"added"|"modified","row":{...}}], "cursor": "..."}

          : ping        (commentaire SSE — keep-alive proxies)
        """
        # Auth manuelle (Bearer header sinon ?token=)
        auth_header = request.headers.get("Authorization", "")
        jwt = ""
        if auth_header.lower().startswith("bearer "):
            jwt = auth_header[7:].strip()
        elif token:
            jwt = token.strip()
        if not jwt:
            raise HTTPException(401, "Token manquant (Bearer ou ?token=)")
        payload = decode_access_token(jwt)
        if payload is None:
            raise HTTPException(401, "Token invalide ou expiré")
        droits = payload.get("droits", []) or []

        if int(id_type_demande) not in list_type_ids_par_droit(droits, droit_field):
            raise HTTPException(403, "Type de demande non accessible avec vos droits")

        # Conversion YYYYMMDD → WinDev compact 17 chars (cf. get_tickets)
        def _to_wd(s: str, end: bool = False) -> str:
            if not s or len(s) < 8 or not s[:8].isdigit():
                return ""
            ymd = s[:8]
            return f"{ymd}{'235959999' if end else '000000000'}"

        date_du_wd = _to_wd(date_du, end=False)
        date_au_wd = _to_wd(date_au, end=True)
        cursor_start = _now_windev()

        async def event_gen():
            cursor = cursor_start
            loop = asyncio.get_event_loop()
            last_emit = loop.time()
            yield f"event: ready\ndata: {json.dumps({'cursor_start': cursor_start})}\n\n"
            try:
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        rows_raw = await asyncio.to_thread(
                            list_tickets_modified_since,
                            int(id_type_demande), cursor, cloturee,
                            date_du_wd, date_au_wd,
                        )
                    except Exception as e:
                        yield f"event: error\ndata: {json.dumps({'msg': str(e)})}\n\n"
                        await asyncio.sleep(POLL_INTERVAL_S)
                        continue

                    if rows_raw:
                        max_modif = cursor
                        for r in rows_raw:
                            mc = r.get("_modif_compact") or ""
                            if mc and mc > max_modif:
                                max_modif = mc
                        cursor = max_modif

                        enriched = await asyncio.to_thread(_enrich_rows, rows_raw)
                        kind_by_id = {}
                        for r in rows_raw:
                            dc = r.get("_date_crea_compact") or ""
                            kind_by_id[r["id_ticket"]] = (
                                "added" if dc and dc > cursor_start else "modified"
                            )
                        events = [
                            {
                                "kind": kind_by_id.get(row["id_ticket"], "modified"),
                                "row": row,
                            }
                            for row in enriched
                        ]
                        payload = {"events": events, "cursor": cursor}
                        yield f"event: tickets\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                        last_emit = loop.time()
                    else:
                        now = loop.time()
                        if now - last_emit >= HEARTBEAT_EVERY_S:
                            yield ": ping\n\n"
                            last_emit = now

                    await asyncio.sleep(POLL_INTERVAL_S)
            except asyncio.CancelledError:
                return

        return StreamingResponse(
            event_gen(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",  # désactive le buffering nginx/IIS ARR
                "Connection": "keep-alive",
            },
        )

    return router
