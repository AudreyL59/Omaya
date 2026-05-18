"""Router shared Tickets — monté avec une dépendance qui fournit le
champ droit à utiliser (DroitAccès pour ADM, DroitAccèsVend pour Vendeur).

Le pattern :
    def get_tickets_router(droit_field: str) -> APIRouter:
        ...

Côté intranet, l'inclusion ressemble à :
    router.include_router(get_tickets_router("DroitAccès"), prefix="")
"""

import asyncio
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.core.auth.security import decode_access_token
from app.core.database import get_connection

from .forms import FORM_HANDLERS
from .info_ticket import donne_info_ticket_batch
from .schemas import (
    SaveInfosRequest,
    SaveInfosResponse,
    SalarieItem,
    StatuerRequest,
    StatuerResponse,
    SupprimerRequest,
    SupprimerResponse,
    TicketDetail,
    TicketListResponse,
    TicketRow,
    TicketSidebarItem,
    TicketStatut,
    TicketTypeDemande,
)
from .service import (
    _now_windev,
    apply_ouverture,
    get_lib_type_demande,
    load_ticket_raw,
    list_statuts,
    list_tickets_modified_since,
    list_tickets_par_type,
    list_type_ids_par_droit,
    list_types_par_droit,
    load_salaries_minimal,
    save_ticket_infos,
    search_organigrammes,
    search_salaries,
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
    # Live update — long-polling (cf. /poll plus bas).
    # SSE abandonné : IIS/ARR bufferise le chunked encoding.
    # -------------------------------------------------------------

    POLL_INTERVAL_S = 3.0      # fréquence de polling DB pendant le long-poll

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

    LONGPOLL_MAX_S = 25.0      # durée max d'attente avant réponse vide

    @router.get("/poll")
    async def poll_tickets(
        request: Request,
        id_type_demande: int = Query(..., description="IDTK_TypeDemande à surveiller"),
        cloturee: bool = Query(False),
        date_du: str = Query(""),
        date_au: str = Query(""),
        cursor: str = Query("", description="Curseur ModifDate compact reçu au tour précédent"),
        token: str = Query("", description="JWT (fallback si pas de header Bearer)"),
    ):
        """Long-polling : renvoie les tickets ajoutés/modifiés depuis `cursor`.

        Choix du long-polling plutôt que SSE : IIS/ARR bufferise le
        `Transfer-Encoding: chunked` du SSE même avec responseBufferLimit=0.
        Une réponse JSON classique (Content-Length) traverse ARR sans souci.

        Protocole :
          - 1er appel sans `cursor` → renvoie {events: [], cursor: <now>}
            immédiatement (juste pour initialiser le curseur côté client).
          - appels suivants avec `cursor` → attend jusqu'à 25 s qu'un ticket
            bouge (poll DB toutes les ~3 s), renvoie dès qu'il y a du nouveau,
            sinon {events: [], cursor: <inchangé>} au timeout.

        Le client reboucle immédiatement après chaque réponse.

        Auth flexible : header Bearer OU query param `token`.
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

        # 1er appel : pas de curseur → on initialise sans attendre.
        if not cursor:
            return {"events": [], "cursor": _now_windev()}

        # Conversion YYYYMMDD → WinDev compact 17 chars (cf. get_tickets)
        def _to_wd(s: str, end: bool = False) -> str:
            if not s or len(s) < 8 or not s[:8].isdigit():
                return ""
            ymd = s[:8]
            return f"{ymd}{'235959999' if end else '000000000'}"

        date_du_wd = _to_wd(date_du, end=False)
        date_au_wd = _to_wd(date_au, end=True)

        loop = asyncio.get_event_loop()
        deadline = loop.time() + LONGPOLL_MAX_S
        while True:
            if await request.is_disconnected():
                return {"events": [], "cursor": cursor}
            try:
                rows_raw = await asyncio.to_thread(
                    list_tickets_modified_since,
                    int(id_type_demande), cursor, cloturee,
                    date_du_wd, date_au_wd,
                )
            except Exception as e:
                raise HTTPException(500, f"Erreur poll tickets : {e}")

            if rows_raw:
                new_cursor = cursor
                for r in rows_raw:
                    mc = r.get("_modif_compact") or ""
                    if mc and mc > new_cursor:
                        new_cursor = mc
                enriched = await asyncio.to_thread(_enrich_rows, rows_raw)
                events = [{"row": row} for row in enriched]
                return {"events": events, "cursor": new_cursor}

            if loop.time() >= deadline:
                return {"events": [], "cursor": cursor}
            await asyncio.sleep(POLL_INTERVAL_S)

    # -------------------------------------------------------------
    # Action de masse : Statuer la sélection (Fen_TicketChoixStatut)
    # -------------------------------------------------------------

    @router.post("/statuer", response_model=StatuerResponse)
    def statuer(
        req: StatuerRequest,
        user: UserToken = Depends(get_current_user),
    ):
        """Change le statut (ou clôture) des tickets sélectionnés.

        Transposition fidèle du code WinDev "Statuer la sélection" :
          - clôture  : UPDATE TK_Liste SET Cloturée=1, DateCloture=now,
                        ModifDate=now WHERE IDTK_Liste IN (...)
          - statut   : UPDATE TK_Liste SET IDTK_Statut=?, ModifDate=now
                        WHERE IDTK_Liste IN (...)
        """
        ids = [int(t) for t in req.id_tickets if t and str(t).isdigit()]
        if not ids:
            raise HTTPException(400, "Aucun ticket sélectionné")
        if not req.cloturee and not req.id_statut:
            raise HTTPException(400, "Statut manquant")

        ids_sql = ",".join(str(i) for i in ids)
        now = _now_windev()
        db = get_connection("ticket")
        try:
            if req.cloturee:
                db.query(
                    f"""UPDATE TK_Liste
                    SET Cloturée = 1, DateCloture = ?, ModifDate = ?
                    WHERE IDTK_Liste IN ({ids_sql})""",
                    (now, now),
                )
            else:
                db.query(
                    f"""UPDATE TK_Liste
                    SET IDTK_Statut = ?, ModifDate = ?
                    WHERE IDTK_Liste IN ({ids_sql})""",
                    (int(req.id_statut), now),
                )
        except Exception as e:
            raise HTTPException(500, f"Erreur lors du statut : {e}")

        return StatuerResponse(updated=len(ids))

    # -------------------------------------------------------------
    # Action de masse : Supprimer la sélection (soft-delete)
    # -------------------------------------------------------------

    @router.post("/supprimer", response_model=SupprimerResponse)
    def supprimer(
        req: SupprimerRequest,
        user: UserToken = Depends(get_current_user),
    ):
        """Soft-delete des tickets sélectionnés.

        Transposition fidèle du code WinDev "Supprimer la sélection" :
          TK_Liste.ModifDate = now
          TK_Liste.ModifOP   = user (usersCial)
          TK_Liste.ModifELEM = 'suppr'
        Les tickets 'suppr' sont exclus de tous les SELECT (liste + poll).
        """
        ids = [int(t) for t in req.id_tickets if t and str(t).isdigit()]
        if not ids:
            raise HTTPException(400, "Aucun ticket sélectionné")

        ids_sql = ",".join(str(i) for i in ids)
        now = _now_windev()
        db = get_connection("ticket")
        try:
            db.query(
                f"""UPDATE TK_Liste
                SET ModifELEM = 'suppr', ModifDate = ?, ModifOP = ?
                WHERE IDTK_Liste IN ({ids_sql})""",
                (now, int(user.id_salarie)),
            )
        except Exception as e:
            raise HTTPException(500, f"Erreur lors de la suppression : {e}")

        return SupprimerResponse(deleted=len(ids))

    # -------------------------------------------------------------
    # Fen_TicketContenu — bloc "Informations générales" (commun)
    # -------------------------------------------------------------

    def _enrich_detail(raw: dict) -> TicketDetail:
        """Complète un raw TK_Liste avec libellés statut/type + noms."""
        ids: set[int] = set()
        for k in ("op_dest", "op_traitement_staff"):
            v = raw.get(k) or ""
            if v.isdigit() and int(v) > 0:
                ids.add(int(v))
        salaries = load_salaries_minimal(ids)
        statut_lib = {s["id_statut"]: s["lib_statut"] for s in list_statuts()}
        odest = int(raw["op_dest"]) if raw["op_dest"].isdigit() else 0
        ostaff = (
            int(raw["op_traitement_staff"])
            if raw["op_traitement_staff"].isdigit() else 0
        )
        od = salaries.get(odest, {})
        os_ = salaries.get(ostaff, {})
        id_type = int(raw["id_type_demande"]) if raw["id_type_demande"].isdigit() else 0
        return TicketDetail(
            id_ticket=raw["id_ticket"],
            id_type_demande=raw["id_type_demande"],
            service=raw["service"],
            lib_type_demande=get_lib_type_demande(id_type) if id_type else "",
            id_statut=raw["id_statut"],
            lib_statut=statut_lib.get(raw["id_statut"], ""),
            op_dest=raw["op_dest"],
            op_dest_nom=od.get("nom", ""),
            op_dest_prenom=od.get("prenom", ""),
            op_traitement_staff=raw["op_traitement_staff"],
            op_staff_nom=os_.get("nom", ""),
            op_staff_prenom=os_.get("prenom", ""),
            cloturee=raw["cloturee"],
            date_cloture=raw["date_cloture"],
            date_crea=raw["date_crea"],
        )

    @router.get("/salaries/search", response_model=list[SalarieItem])
    def salaries_search(
        q: str = Query(..., min_length=1),
        user: UserToken = Depends(get_current_user),
    ):
        """Recherche salarié par début de nom (Fen_RechercheNomSalarié)."""
        return [SalarieItem(**s) for s in search_salaries(q)]

    @router.get("/organigrammes/search")
    def organigrammes_search(
        q: str = Query(..., min_length=1),
        user: UserToken = Depends(get_current_user),
    ):
        """Recherche d'équipe (organigramme) par libellé."""
        return search_organigrammes(q)

    @router.post("/{id_ticket}/ouvrir", response_model=TicketDetail)
    def ouvrir_ticket(
        id_ticket: str,
        user: UserToken = Depends(get_current_user),
    ):
        """Ouverture d'un ticket (code init Fen_TicketContenu) :
        applique la règle statut<2 → 2 (sauf types 38/39) puis renvoie
        le détail enrichi pour le bloc "Informations générales".
        """
        if not id_ticket.isdigit():
            raise HTTPException(400, "id_ticket invalide")
        raw = apply_ouverture(int(id_ticket), int(user.id_salarie))
        if raw is None:
            raise HTTPException(404, "Ticket introuvable")
        return _enrich_detail(raw)

    @router.post("/{id_ticket}/infos", response_model=SaveInfosResponse)
    def enregistrer_infos(
        id_ticket: str,
        req: SaveInfosRequest,
        user: UserToken = Depends(get_current_user),
    ):
        """Enregistre les infos générales (transposition saveTicket())."""
        if not id_ticket.isdigit():
            raise HTTPException(400, "id_ticket invalide")
        try:
            res = save_ticket_infos(
                int(id_ticket),
                int(req.id_statut),
                req.op_dest,
                req.op_traitement_staff,
                req.cloturee,
                req.date_cloture,
                int(user.id_salarie),
                req.prendre_en_charge,
            )
        except Exception as e:
            raise HTTPException(500, f"Erreur enregistrement : {e}")
        if not res.get("ok"):
            raise HTTPException(404, "Ticket introuvable")
        return SaveInfosResponse(ok=True, closed=res.get("closed", False))

    # -------------------------------------------------------------
    # Détail du ticket — fenêtres internes WinDev FI_* (dispatch
    # générique selon IDTK_TypeDemande, cf. forms/FORM_HANDLERS).
    # -------------------------------------------------------------

    def _handler_for(id_ticket: str):
        if not id_ticket.isdigit():
            raise HTTPException(400, "id_ticket invalide")
        raw = load_ticket_raw(int(id_ticket))
        if raw is None:
            raise HTTPException(404, "Ticket introuvable")
        id_type = (
            int(raw["id_type_demande"])
            if raw["id_type_demande"].isdigit() else 0
        )
        return id_type, FORM_HANDLERS.get(id_type)

    @router.get("/{id_ticket}/form")
    def get_ticket_form(
        id_ticket: str,
        user: UserToken = Depends(get_current_user),
    ):
        """Détail du ticket : renvoie les données du formulaire spécifique
        au type (None si le type n'a pas encore de FI_* implémentée).
        """
        id_type, handler = _handler_for(id_ticket)
        if handler is None:
            return {"id_type_demande": str(id_type), "has_form": False, "data": None}
        try:
            data = handler.load(int(id_ticket))
        except Exception as e:
            raise HTTPException(500, f"Erreur chargement formulaire : {e}")
        return {
            "id_type_demande": str(id_type),
            "has_form": True,
            "data": data,
        }

    @router.post("/{id_ticket}/form")
    def post_ticket_form(
        id_ticket: str,
        payload: dict,
        user: UserToken = Depends(get_current_user),
    ):
        """Enregistre le formulaire spécifique au type du ticket."""
        _id_type, handler = _handler_for(id_ticket)
        if handler is None:
            raise HTTPException(400, "Aucun formulaire pour ce type de demande")
        try:
            res = handler.save(int(id_ticket), payload or {}, int(user.id_salarie))
        except Exception as e:
            raise HTTPException(500, f"Erreur enregistrement formulaire : {e}")
        if not res.get("ok"):
            raise HTTPException(400, res.get("error") or "Échec de l'enregistrement")
        return res

    @router.get("/{id_ticket}/form/print")
    def print_ticket_form(
        id_ticket: str,
        id_ligne: str = Query("", description="Ligne à imprimer (selon le type)"),
        user: UserToken = Depends(get_current_user),
    ):
        """Impression PDF du détail (états WinDev). Disponible si le
        handler du type implémente print_pdf().
        """
        _id_type, handler = _handler_for(id_ticket)
        if handler is None or not hasattr(handler, "print_pdf"):
            raise HTTPException(400, "Pas d'impression pour ce type de demande")
        try:
            pdf = handler.print_pdf(int(id_ticket), {"id_ligne": id_ligne})
        except Exception as e:
            raise HTTPException(500, f"Erreur génération PDF : {e}")
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="ticket_{id_ticket}.pdf"'
            },
        )

    @router.get("/{id_ticket}/form/file")
    def get_ticket_form_file(
        id_ticket: str,
        name: str = Query(..., description="Nom du fichier (document)"),
        user: UserToken = Depends(get_current_user),
    ):
        """Sert un document attaché au ticket (ex: photos DPAE via FTP).
        Disponible si le handler du type implémente get_file().
        """
        _id_type, handler = _handler_for(id_ticket)
        if handler is None or not hasattr(handler, "get_file"):
            raise HTTPException(400, "Pas de document pour ce type de demande")
        try:
            data, mime = handler.get_file(int(id_ticket), name)
        except FileNotFoundError as e:
            raise HTTPException(404, str(e))
        except Exception as e:
            raise HTTPException(500, f"Erreur récupération document : {e}")
        return Response(
            content=data,
            media_type=mime,
            headers={
                "Content-Disposition": f'inline; filename="{name}"'
            },
        )

    return router
