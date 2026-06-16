"""
Router ADM : agenda de recrutement.

Réutilise les schemas et services Vendeur (même logique métier, table AgendaEvénement
dans Bdd_Omaya_Recrutement). Exposé sous /api/adm/agenda-recrutement pour isoler
le scope d'authentification ADM (droit IntraADM).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import agenda_detail as detail_svc
from app.intranets.vendeur.schemas.agenda_recrutement import (
    AgendaRDV,
    RecruteurItem,
    StatutItem,
    StatuerRequest,
)
from app.intranets.vendeur.services.agenda_recrutement import (
    lister_rdvs,
    lister_statuts,
    statuer_rdv,
    convoquer_jo,
)
from app.intranets.vendeur.services.cooptation import rechercher_vendeurs

router = APIRouter(prefix="/agenda-recrutement", tags=["adm-agenda-recrutement"])


@router.get("", response_model=list[AgendaRDV])
def get_agenda_recrutement(
    date_from: str,
    date_to: str,
    id_recruteur: int = 0,
    user: UserToken = Depends(get_current_user),
):
    """
    Liste les RDV d'un recruteur entre deux dates.

    date_from / date_to : format YYYYMMDD (ex: "20260420").
    id_recruteur : 0 = utilisateur connecté par défaut.
    """
    rec_id = id_recruteur or user.id_salarie
    return lister_rdvs(rec_id, date_from, date_to)


@router.get("/recruteurs", response_model=list[RecruteurItem])
def get_recruteurs(q: str = "", user: UserToken = Depends(get_current_user)):
    """
    Recherche les recruteurs accessibles à l'utilisateur ADM.
    ADM a typiquement un scope global (droit ProdRezo).
    """
    acces_global = "ProdRezo" in user.droits
    is_resp = user.is_resp or "ProdGR" in user.droits
    results = rechercher_vendeurs(
        user.id_salarie, q, acces_global=acces_global, is_resp=is_resp
    )
    return [
        {"id_salarie": r["id_salarie"], "nom": r["nom"], "prenom": r["prenom"]}
        for r in results
    ]


@router.get("/statuts", response_model=list[StatutItem])
def get_statuts():
    """Liste des statuts sélectionnables (IdCvStatut > 6)."""
    return lister_statuts()


@router.put("/rdv/{id_rdv}/statut")
def put_statut(
    id_rdv: int,
    data: StatuerRequest,
    user: UserToken = Depends(get_current_user),
):
    """Statue un RDV : update + log + historique."""
    if data.id_categorie == 0:
        raise HTTPException(status_code=400, detail="Statut requis")
    if data.id_categorie in (4, 7):
        if not data.motif or len(data.motif) < 5:
            raise HTTPException(
                status_code=400, detail="Motif requis (minimum 5 caractères)"
            )
    try:
        statuer_rdv(
            id_rdv=id_rdv,
            id_categorie=data.id_categorie,
            motif=data.motif,
            pb_presentation=data.pb_presentation,
            pb_elocution=data.pb_elocution,
            pb_motivation=data.pb_motivation,
            pb_horaires=data.pb_horaires,
            id_salarie_user=user.id_salarie,
            nom_user=user.nom,
            prenom_user=user.prenom,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ok": True}


@router.post("/rdv/{id_rdv}/convoc-jo")
def post_convoc_jo(
    id_rdv: int,
    user: UserToken = Depends(get_current_user),
):
    """Convoque le candidat en JO : crée TK_DemandeDPAE + TK_Liste + SMS + mail + historique."""
    try:
        info = convoquer_jo(
            id_rdv=id_rdv,
            id_salarie_user=user.id_salarie,
            nom_user=user.nom,
            prenom_user=user.prenom,
            mail_user=user.login,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "ok": True,
        "id_ticket": info["id_ticket"],
        "sms_result": info["sms_result"],
        "mail_sent": info["mail_sent"],
    }


# ---------------------------------------------------------------------------
# Fen_AgendaDetail (detail complet d'un RDV)
# ---------------------------------------------------------------------------


class SaveRdvDetailPayload(BaseModel):
    titre: str = ""
    contenu: str = ""
    id_recruteur: int = 0
    id_categorie: int = 0
    date_debut: str = ""
    date_fin: str = ""
    id_prevision_recrut: int = 0
    type_entretien: str = "Physique"   # 'Physique' | 'Visio'
    id_cv_lieux: int = 0
    id_salon_visio: int = 0
    motif_statut: str = ""
    pb_presentation: bool = False
    pb_elocution: bool = False
    pb_motivation: bool = False
    pb_horaires: bool = False


class SetOpCreaPayload(BaseModel):
    new_op: int


@router.get("/rdv/{id_rdv}/detail")
def get_rdv_detail(id_rdv: int, _user: UserToken = Depends(get_current_user)):
    """Fen_AgendaDetail : tous les champs du RDV pour pre-remplir le modal."""
    data = detail_svc.load_rdv_detail(id_rdv)
    if not data:
        raise HTTPException(status_code=404, detail="RDV introuvable")
    return data


@router.put("/rdv/{id_rdv}/detail")
def put_rdv_detail(
    id_rdv: int,
    payload: SaveRdvDetailPayload,
    user: UserToken = Depends(get_current_user),
):
    """Sauvegarde complete du RDV depuis Fen_AgendaDetail."""
    return detail_svc.save_rdv(
        id_rdv=id_rdv,
        titre=payload.titre,
        contenu=payload.contenu,
        id_recruteur=payload.id_recruteur,
        id_categorie=payload.id_categorie,
        date_debut=payload.date_debut,
        date_fin=payload.date_fin,
        id_prevision_recrut=payload.id_prevision_recrut,
        type_entretien=payload.type_entretien,
        id_cv_lieux=payload.id_cv_lieux,
        id_salon_visio=payload.id_salon_visio,
        motif_statut=payload.motif_statut,
        pb_presentation=payload.pb_presentation,
        pb_elocution=payload.pb_elocution,
        pb_motivation=payload.pb_motivation,
        pb_horaires=payload.pb_horaires,
        op_id=user.id_salarie,
    )


@router.delete("/rdv/{id_rdv}")
def delete_rdv(id_rdv: int, user: UserToken = Depends(get_current_user)):
    """Btn 'Supprimer le RDV' : soft delete (modif_elem = 'suppr')."""
    return detail_svc.soft_delete_rdv(id_rdv, user.id_salarie)


@router.post("/rdv/{id_rdv}/op-crea")
def post_op_crea(
    id_rdv: int,
    payload: SetOpCreaPayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Choisir l'Operateur' : maj OPCrea sur AgendaEvenement +
    CvSuivi lie. Retourne le libelle pour rafraichir le bouton."""
    return detail_svc.set_op_crea(id_rdv, payload.new_op, user.id_salarie)


@router.get("/recruteurs-agenda-actif")
def get_recruteurs_agenda_actif(_user: UserToken = Depends(get_current_user)):
    """Combo Recruteur Fen_AgendaDetail : tous les salaries avec
    agenda_actif=TRUE. Different de /recruteurs qui filtre par droits
    cooptation."""
    return detail_svc.list_recruteurs_agenda_actif()


@router.get("/categories")
def get_all_categories(_user: UserToken = Depends(get_current_user)):
    """Combo Statut Fen_AgendaDetail : toutes les categories (sans filtre
    id_cv_statut>6 utilise par /statuts pour la statuation rapide)."""
    return detail_svc.list_all_categories()


@router.get("/sessions-en-cours")
def get_sessions_en_cours(_user: UserToken = Depends(get_current_user)):
    """ReqPrevRecEncours : sessions de recrutement actives."""
    return detail_svc.list_sessions_en_cours()


@router.get("/lieux")
def get_lieux(_user: UserToken = Depends(get_current_user)):
    """Referentiel des lieux de RDV."""
    return detail_svc.list_lieux()


@router.get("/lieux/{id_cv_lieu_rdv}")
def get_lieu(id_cv_lieu_rdv: int, _user: UserToken = Depends(get_current_user)):
    """Detail d'un lieu (adresse + commune)."""
    data = detail_svc.get_lieu(id_cv_lieu_rdv)
    if not data:
        raise HTTPException(status_code=404, detail="Lieu introuvable")
    return data


@router.get("/salons-visio")
def get_salons_visio(
    id_recruteur: int,
    _user: UserToken = Depends(get_current_user),
):
    """Liste des salons visio d'un recruteur (combo)."""
    return detail_svc.list_salons_visio_by_recruteur(id_recruteur)


@router.get("/salons-visio/{id_salon_visio}")
def get_salon_visio(
    id_salon_visio: int,
    _user: UserToken = Depends(get_current_user),
):
    """Detail d'un salon visio : lien + id + mdp."""
    data = detail_svc.get_salon_visio(id_salon_visio)
    if not data:
        raise HTTPException(status_code=404, detail="Salon introuvable")
    return data
