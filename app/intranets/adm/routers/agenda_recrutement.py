"""
Router ADM : agenda de recrutement.

Réutilise les schemas et services Vendeur (même logique métier, table AgendaEvénement
dans Bdd_Omaya_Recrutement). Exposé sous /api/adm/agenda-recrutement pour isoler
le scope d'authentification ADM (droit IntraADM).
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
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
