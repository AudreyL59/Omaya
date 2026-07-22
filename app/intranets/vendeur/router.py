from fastapi import APIRouter, Depends

from app.core.auth.dependencies import require_intranet

from app.intranets.vendeur.menu import router as menu_router
from app.intranets.vendeur.routers.mon_compte import router as mon_compte_router
from app.intranets.vendeur.routers.cooptation import router as cooptation_router
from app.intranets.vendeur.routers.agenda_recrutement import router as agenda_recrutement_router
from app.intranets.vendeur.routers.agenda_cial import router as agenda_cial_router
from app.intranets.vendeur.routers.cvtheque import router as cvtheque_router
from app.intranets.vendeur.routers.organigramme import router as organigramme_router
from app.intranets.vendeur.routers.gestion_ohm import router as gestion_ohm_router
from app.intranets.vendeur.routers.scool import router as scool_router
from app.intranets.vendeur.routers.scool_suivi import router as scool_suivi_router
from app.shared.production.router import router as production_router
from app.shared.recrutement.router import get_recherche_cv_router
from app.shared.tickets.router import get_tickets_router
from app.intranets.vendeur.routers.clusters import router as clusters_router
from app.intranets.vendeur.routers.tickets import router as tickets_router
from app.shared.process.router import get_process_router
from app.intranets.vendeur.routers.tickets_call import router as tickets_call_router
from app.intranets.vendeur.routers.tickets_call_suivi import router as tickets_call_suivi_router
from app.intranets.vendeur.routers.ticket_call_energie import router as ticket_call_energie_router
from app.intranets.vendeur.routers.ticket_call_fibre import router as ticket_call_fibre_router
from app.intranets.vendeur.routers.ticket_call_ws_common import router as ticket_call_ws_common_router
from app.shared.dialogues.router import get_dialogues_router

router = APIRouter(
    prefix="/vendeur",
    tags=["vendeur"],
    dependencies=[Depends(require_intranet("vendeur"))],
)

# Menu dynamique
router.include_router(menu_router)

# Pages
router.include_router(mon_compte_router)
router.include_router(cooptation_router)
router.include_router(agenda_recrutement_router)
router.include_router(agenda_cial_router)
router.include_router(cvtheque_router)
# Nouvelle CVtheque (partagee ADM/Vendeur/Call RH) : filtre auto
# id_cvsource=1 + id_elem_source=user cote factory pour Vendeur.
router.include_router(get_recherche_cv_router("vendeur"))
router.include_router(organigramme_router)
router.include_router(gestion_ohm_router)
router.include_router(scool_router)
router.include_router(scool_suivi_router)
router.include_router(production_router)
router.include_router(clusters_router)
# Module tickets shared : filtre par DroitAccèsVend pour Vendeur
router.include_router(get_tickets_router("DroitAccèsVend"))
router.include_router(tickets_router)
router.include_router(get_process_router("vendeur", can_edit=False))
router.include_router(tickets_call_router)
# Nouvelle page 'Tickets Call Suivi' (fusion Fibre + Energie avec
# filtrage orga, cf. droit ProdRezo)
router.include_router(tickets_call_suivi_router)
# Ticket Call Energie + Fibre (Phase 2 proxy vers WebRest_Omayapp WinDev,
# migration progressive vers PG cf. docs/tickets_call_screens_analysis.md)
router.include_router(ticket_call_energie_router)
router.include_router(ticket_call_fibre_router)
router.include_router(ticket_call_ws_common_router)
router.include_router(get_dialogues_router("vendeur"))
