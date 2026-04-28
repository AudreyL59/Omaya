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
from app.shared.production.router import router as production_router

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
router.include_router(production_router)


@router.get("/ping")
def ping():
    return {"intranet": "adm", "status": "ok"}
