"""Router Fen_DistribCttCourtage (Docs Dematerialises d'une societe)."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import distrib_courtage as svc

router = APIRouter(prefix="/distrib-courtage", tags=["adm-distrib-courtage"])


@router.get("/{id_ste}/infos", response_model=svc.DistribInfos)
def get_distrib_infos(
    id_ste: int,
    _u: UserToken = Depends(get_current_user),
):
    d = svc.get_distrib_infos(id_ste)
    if not d:
        raise HTTPException(404, "Société introuvable")
    return d


@router.get("/{id_distrib}/groupes-rem",
            response_model=list[svc.GroupeRemItem])
def get_distrib_groupes_rem(
    id_distrib: int,
    _u: UserToken = Depends(get_current_user),
):
    return svc.list_groupes_rem(id_distrib)


@router.get("/{id_distrib}/editions",
            response_model=list[svc.EditionCttItem])
def get_distrib_editions(
    id_distrib: int,
    _u: UserToken = Depends(get_current_user),
):
    return svc.list_editions_ctt(id_distrib)


# ---- Fen_GroupeRemFiche : combos + CRUD ----

@router.get("/combos/groupes-operateur",
            response_model=list[svc.GroupeOperateurItem])
def get_combo_groupes_op(_u: UserToken = Depends(get_current_user)):
    return svc.list_groupes_operateur()


@router.get("/combos/familles",
            response_model=list[svc.PartenaireItem])
def get_combo_familles(
    id_groupe_operateur: int,
    _u: UserToken = Depends(get_current_user),
):
    return svc.list_familles_by_grop(id_groupe_operateur)


@router.get("/combos/ss-fam")
def get_combo_ss_fam(
    famille: int,
    _u: UserToken = Depends(get_current_user),
):
    return svc.list_ss_fam(famille)


@router.get("/groupe-rem/{id_groupe_rem}",
            response_model=svc.GroupeRemDetail)
def get_groupe_rem(
    id_groupe_rem: int,
    _u: UserToken = Depends(get_current_user),
):
    d = svc.get_groupe_rem(id_groupe_rem)
    if not d:
        raise HTTPException(404, "Groupe REM introuvable")
    return d


@router.post("/groupe-rem")
def post_groupe_rem(
    payload: svc.GroupeRemPayload,
    id_distrib: int | None = None,   # override en query pour eviter perte precision JS
    u: UserToken = Depends(get_current_user),
):
    if id_distrib is not None:
        payload.id_distrib = int(id_distrib)
    id_new = svc.create_groupe_rem(payload, u.id_salarie)
    return {"ok": True, "id_groupe_rem": str(id_new)}


@router.put("/groupe-rem/{id_groupe_rem}")
def put_groupe_rem(
    id_groupe_rem: int,
    payload: svc.GroupeRemPayload,
    id_distrib: int | None = None,   # override en query
    u: UserToken = Depends(get_current_user),
):
    if id_distrib is not None:
        payload.id_distrib = int(id_distrib)
    svc.update_groupe_rem(id_groupe_rem, payload, u.id_salarie)
    return {"ok": True}
