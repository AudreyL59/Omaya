from fastapi import APIRouter, Depends

from app.core.auth.dependencies import require_intranet
from app.intranets.adm.menu import router as menu_router
from app.intranets.adm.routers.stat_rh_rdv import router as stat_rh_rdv_router
from app.intranets.adm.routers.stat_rh_entree_sortie import router as stat_rh_es_router
from app.intranets.adm.routers.stat_rh_saisie_cv import router as stat_rh_saisie_cv_router
from app.intranets.adm.routers.stat_rh_annonceurs import router as stat_rh_annonceurs_router
from app.intranets.adm.routers.salaries import router as salaries_router
from app.intranets.adm.routers.organigrammes import router as organigrammes_router
from app.intranets.adm.routers.organigramme import router as organigramme_router
from app.intranets.adm.routers.annonceurs import router as annonceurs_router
from app.intranets.adm.routers.agenda_recrutement import router as agenda_recrutement_router
from app.intranets.adm.routers.mon_compte import router as mon_compte_router
from app.intranets.adm.routers.recherche import router as recherche_router
from app.intranets.adm.routers.registre_rh import router as registre_rh_router
from app.intranets.adm.routers.fiche_salarie import router as fiche_salarie_router
from app.intranets.adm.routers.dpae import router as dpae_router
from app.intranets.adm.routers.ctt_travail import router as ctt_travail_router
from app.intranets.adm.routers.ctt_ulease import router as ctt_ulease_router
from app.intranets.adm.routers.parc_auto import router as parc_auto_router
from app.intranets.adm.routers.gestion_carte_carb import router as carte_carb_router
from app.intranets.adm.routers.recherche_ulease import router as recherche_ulease_router
from app.intranets.adm.routers.formations_iag import router as formations_iag_router
from app.intranets.adm.routers.suivi_mutuelle import router as suivi_mutuelle_router
from app.intranets.adm.routers.params_rh import router as params_rh_router
from app.intranets.adm.routers.params_cv import router as params_cv_router
from app.intranets.adm.routers.imports import router as imports_router
from app.intranets.adm.routers.factures import router as factures_router
from app.intranets.adm.routers.suivi_sfr import router as suivi_sfr_router
from app.intranets.adm.routers.suivi_energie import router as suivi_energie_router
from app.intranets.adm.routers.recherche_ville import router as recherche_ville_router
from app.intranets.adm.routers.societes import router as societes_router
from app.intranets.adm.routers.distrib_courtage import router as distrib_courtage_router
from app.intranets.adm.routers.doc_courtage import router as doc_courtage_router
from app.intranets.adm.routers.suivi_distrib import router as suivi_distrib_router
from app.intranets.adm.routers.gestion_exo_cash import router as gestion_exo_cash_router
from app.intranets.adm.routers.paies_bs import router as paies_bs_router
from app.intranets.adm.routers.fiche_salaires import router as fiche_salaires_router
from app.intranets.adm.routers.export_tr import router as export_tr_router
from app.intranets.adm.routers.tableau_divers import router as tableau_divers_router
from app.intranets.adm.routers.podium import router as podium_router
from app.intranets.adm.routers.calcul_points_bs import router as calcul_points_bs_router
from app.intranets.adm.routers.tableau_salarie import router as tableau_salarie_router
from app.intranets.adm.routers.sms_perf import router as sms_perf_router
from app.intranets.adm.routers.scool_formation import router as scool_formation_router
from app.intranets.adm.routers.scool_planning import router as scool_planning_router
from app.intranets.adm.routers.scool_bulletin import router as scool_bulletin_router
from app.intranets.adm.routers.scool_stagiaire_fiche import router as scool_stagiaire_fiche_router
from app.shared.production.router import router as production_router
from app.shared.recrutement.router import get_recherche_cv_router
from app.shared.tickets.router import get_tickets_router

router = APIRouter(
    prefix="/adm",
    tags=["adm"],
    dependencies=[Depends(require_intranet("adm"))],
)

router.include_router(menu_router)
router.include_router(stat_rh_rdv_router)
router.include_router(stat_rh_es_router)
router.include_router(stat_rh_saisie_cv_router)
router.include_router(stat_rh_annonceurs_router)
router.include_router(salaries_router)
router.include_router(organigrammes_router)
router.include_router(organigramme_router)
router.include_router(annonceurs_router)
router.include_router(agenda_recrutement_router)
router.include_router(mon_compte_router)
router.include_router(recherche_router)
router.include_router(registre_rh_router)
router.include_router(fiche_salarie_router)
router.include_router(dpae_router)
router.include_router(ctt_travail_router)
router.include_router(ctt_ulease_router)
router.include_router(parc_auto_router)
router.include_router(carte_carb_router)
router.include_router(recherche_ulease_router)
router.include_router(formations_iag_router)
router.include_router(suivi_mutuelle_router)
router.include_router(params_rh_router)
router.include_router(params_cv_router)
router.include_router(imports_router)
router.include_router(factures_router)
router.include_router(suivi_sfr_router)
router.include_router(suivi_energie_router)
router.include_router(recherche_ville_router)
router.include_router(societes_router)
router.include_router(distrib_courtage_router)
router.include_router(doc_courtage_router)
router.include_router(suivi_distrib_router)
router.include_router(gestion_exo_cash_router)
router.include_router(paies_bs_router)
router.include_router(fiche_salaires_router)
router.include_router(export_tr_router)
router.include_router(tableau_divers_router)
router.include_router(podium_router)
router.include_router(calcul_points_bs_router)
router.include_router(tableau_salarie_router)
router.include_router(sms_perf_router)
router.include_router(scool_formation_router)
router.include_router(scool_planning_router)
router.include_router(scool_bulletin_router)
router.include_router(scool_stagiaire_fiche_router)
router.include_router(production_router)
# Module recrutement/recherche-cv shared (ADM voit tout)
router.include_router(get_recherche_cv_router("adm"))
# Module tickets shared : filtre par DroitAccès pour ADM
router.include_router(get_tickets_router("DroitAccès"))


@router.get("/ping")
def ping():
    return {"intranet": "adm", "status": "ok"}
