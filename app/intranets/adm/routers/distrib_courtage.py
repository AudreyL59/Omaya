"""Router Fen_DistribCttCourtage (Docs Dematerialises d'une societe)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

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


# ---- Grille X/Y/Tab ----

@router.get("/groupe-rem/{id_groupe_rem}/grille",
            response_model=svc.GrilleGroupeRem)
def get_grille(
    id_groupe_rem: int,
    _u: UserToken = Depends(get_current_user),
):
    return svc.get_grille(id_groupe_rem)


@router.post("/groupe-rem/{id_groupe_rem}/colonne")
def post_colonne(
    id_groupe_rem: int,
    u: UserToken = Depends(get_current_user),
):
    id_x = svc.add_colonne(id_groupe_rem, u.id_salarie)
    return {"ok": True, "id_groupe_rem_x": id_x}


@router.post("/groupe-rem/{id_groupe_rem}/ligne")
def post_ligne(
    id_groupe_rem: int,
    u: UserToken = Depends(get_current_user),
):
    id_y = svc.add_ligne(id_groupe_rem, u.id_salarie)
    return {"ok": True, "id_groupe_rem_y": id_y}


@router.put("/groupe-rem-x/{id_x}")
def put_x(
    id_x: int,
    payload: svc.EditColonnePayload,
    u: UserToken = Depends(get_current_user),
):
    svc.update_x(id_x, payload, u.id_salarie)
    return {"ok": True}


@router.put("/groupe-rem-y/{id_y}")
def put_y(
    id_y: int,
    payload: svc.EditColonnePayload,
    u: UserToken = Depends(get_current_user),
):
    svc.update_y(id_y, payload, u.id_salarie)
    return {"ok": True}


@router.delete("/groupe-rem-x/{id_x}")
def delete_x(
    id_x: int,
    id_groupe_rem: int,
    u: UserToken = Depends(get_current_user),
):
    svc.delete_x(id_x, id_groupe_rem, u.id_salarie)
    return {"ok": True}


@router.delete("/groupe-rem-y/{id_y}")
def delete_y(
    id_y: int,
    id_groupe_rem: int,
    u: UserToken = Depends(get_current_user),
):
    svc.delete_y(id_y, id_groupe_rem, u.id_salarie)
    return {"ok": True}


@router.post("/groupe-rem-x/{id_x}/move")
def move_x(
    id_x: int,
    id_groupe_rem: int,
    direction: str,   # 'left' | 'right'
    u: UserToken = Depends(get_current_user),
):
    svc.move_x(id_x, direction, id_groupe_rem, u.id_salarie)
    return {"ok": True}


@router.post("/groupe-rem-y/{id_y}/move")
def move_y(
    id_y: int,
    id_groupe_rem: int,
    direction: str,   # 'up' | 'down'
    u: UserToken = Depends(get_current_user),
):
    svc.move_y(id_y, direction, id_groupe_rem, u.id_salarie)
    return {"ok": True}


class CellulePayload(BaseModel):
    montant: float


@router.put("/groupe-rem-tab/{id_x}/{id_y}")
def put_cellule(
    id_x: int,
    id_y: int,
    payload: CellulePayload,
    u: UserToken = Depends(get_current_user),
):
    svc.update_cellule(id_x, id_y, payload.montant, u.id_salarie)
    return {"ok": True}


@router.get("/{id_distrib}/docs-courtage",
            response_model=list[svc.DocCourtageItem])
def get_docs_courtage(
    id_distrib: int,
    id_ste_gerant_societe: int | None = None,
    _u: UserToken = Depends(get_current_user),
):
    """Liste des docs de courtage disponibles pour ce distributeur.
    Cf Fen_SocieteDocCourtage : filtre par id_ste (0=commun, sinon
    reserve a la societe id_ste_gerant_societe si fourni)."""
    return svc.list_docs_courtage(id_distrib, id_ste_gerant_societe)


@router.post("/groupe-rem/{id_source}/duplicate-to")
def post_duplicate_groupe_rem(
    id_source: int,
    id_target_distrib: int,   # en query : bigint 17 chiffres
    u: UserToken = Depends(get_current_user),
):
    """Duplique un groupe REM vers un autre distributeur."""
    try:
        id_new = svc.duplicate_groupe_rem_to(
            id_source, id_target_distrib, u.id_salarie,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"ok": True, "id_groupe_rem": id_new}
