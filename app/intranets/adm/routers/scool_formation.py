"""
Router Fen_ScoolFormation.

Endpoints (droit 'FormScool') :
  GET  /adm/scool/formations                    - Liste
  GET  /adm/scool/formations/{id}               - Detail
  POST /adm/scool/formations                    - Create
  PUT  /adm/scool/formations/{id}               - Update
  DELETE /adm/scool/formations/{id}             - Soft delete
  POST /adm/scool/formations/{id}/dupliquer     - Duplique
  GET  /adm/scool/modeles                       - Liste modeles
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.schemas.scool_formation import (
    AnalyseFormationResult, AnalysePromoParams,
    BaremeNotePayload, BaremeNoteRow, BulletinRow,
    ConvertirModelePayload, EleveAjoutPayload, EleveRow,
    EvenementPayload, EvenementRow,
    FormateurCombo, FormationDetail,
    FormationPayload, FormationRow,
    ListeFormationsParams, ModeleFormationCombo, ModeleFormationRow,
    ProgrammePayload, ProgrammeRow,
    SessionRecrutPayload, SessionRecrutRow,
)
from app.intranets.adm.services import scool_formation as svc

router = APIRouter(prefix="/scool", tags=["adm-scool"])


def _require_droit(user: UserToken, code: str) -> None:
    if code not in (user.droits or []):
        raise HTTPException(status_code=403, detail=f"Droit manquant : {code}")


@router.get("/formations", response_model=list[FormationRow])
def get_formations(
    afficher_depuis_le: str = Query("", description="YYYY-MM-DD"),
    uniquement_actives: bool = Query(True),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    return svc.list_formations(ListeFormationsParams(
        afficher_depuis_le=afficher_depuis_le,
        uniquement_actives=uniquement_actives,
    ))


@router.get("/formations/{id_formation}", response_model=FormationDetail)
def get_formation(
    id_formation: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    detail = svc.get_formation(id_formation)
    if not detail:
        raise HTTPException(404, "Formation introuvable")
    return detail


@router.post("/formations")
def post_formation(
    payload: FormationPayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    if not payload.intitule.strip():
        raise HTTPException(400, "Intitulé requis")
    op_id = int(user.id_salarie or 0)
    new_id = svc.create_formation(payload, op_id)
    return {"ok": bool(new_id), "id_formation": new_id}


@router.put("/formations/{id_formation}")
def put_formation(
    id_formation: str,
    payload: FormationPayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.update_formation(id_formation, payload, op_id)
    return {"ok": ok}


@router.delete("/formations/{id_formation}")
def del_formation(
    id_formation: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.delete_formation(id_formation, op_id)
    return {"ok": ok}


@router.post("/formations/{id_formation}/dupliquer")
def dup_formation(
    id_formation: str,
    dupliquer_programme: bool = Query(False),
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    new_id = svc.duplicate_formation(
        id_formation, op_id, dupliquer_programme,
    )
    return {"ok": bool(new_id), "id_formation": new_id}


@router.get("/modeles", response_model=list[ModeleFormationRow])
def get_modeles(user: UserToken = Depends(get_current_user)):
    _require_droit(user, "FormScool")
    return svc.list_modeles()


@router.get("/modeles-combo", response_model=list[ModeleFormationCombo])
def get_modeles_combo(user: UserToken = Depends(get_current_user)):
    """Combo 'Utiliser ce modele' de Fen_ScoolFormation_Ajout.
    Premier item = 'Ne pas utiliser de modele' (id=0).
    """
    _require_droit(user, "FormScool")
    return svc.list_modeles_combo()


@router.get("/formateurs", response_model=list[FormateurCombo])
def get_formateurs(user: UserToken = Depends(get_current_user)):
    """Combos Formateur1..5 de Fen_ScoolFormation_Ajout : formateurs
    actifs (JOIN pgt_formateur + pgt_salarie + pgt_salarie_embauche).
    """
    _require_droit(user, "FormScool")
    return svc.list_formateurs()


# --------------------------------------------------------------------
# Programme de formation (onglet 1 Fen_ScoolFormation_Fiche)
# --------------------------------------------------------------------

@router.get("/formations/{id_formation}/programme",
            response_model=list[ProgrammeRow])
def get_programme(
    id_formation: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    return svc.list_programme(id_formation)


@router.post("/formations/{id_formation}/programme")
def post_programme(
    id_formation: str,
    payload: ProgrammePayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    new_id = svc.add_programme(id_formation, payload, op_id)
    return {"ok": bool(new_id), "id_programme": new_id}


@router.put("/formations/{id_formation}/programme/{id_programme}")
def put_programme(
    id_formation: str,
    id_programme: str,
    payload: ProgrammePayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.update_programme(id_programme, payload, op_id)
    return {"ok": ok}


@router.delete("/formations/{id_formation}/programme/{id_programme}")
def del_programme(
    id_formation: str,
    id_programme: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.delete_programme(id_programme, op_id)
    return {"ok": ok}


@router.delete("/formations/{id_formation}/programme")
def del_programme_all(
    id_formation: str,
    user: UserToken = Depends(get_current_user),
):
    """Cf. WinDev Btn Supprimer la date - clic fleche."""
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    n = svc.delete_programme_all(id_formation, op_id)
    return {"ok": bool(n)}


@router.post("/formations/{id_formation}/programme/{id_programme}/dupliquer")
def dup_programme(
    id_formation: str,
    id_programme: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    new_id = svc.duplicate_programme(id_programme, op_id)
    return {"ok": bool(new_id), "id_programme": new_id}


@router.post("/formations/{id_formation}/convertir-modele")
def post_convertir_modele(
    id_formation: str,
    payload: ConvertirModelePayload,
    user: UserToken = Depends(get_current_user),
):
    """Cf. WinDev Btn Convertir en modele."""
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    new_id = svc.convertir_en_modele(id_formation, payload, op_id)
    return {"ok": bool(new_id), "id_modele": new_id}


# --------------------------------------------------------------------
# FI_AnalysePromoScool
# --------------------------------------------------------------------

@router.post("/formations/analyse-promo",
             response_model=list[AnalyseFormationResult])
def post_analyse_promo(
    payload: AnalysePromoParams,
    user: UserToken = Depends(get_current_user),
):
    """Cf. WinDev Btn 'Faire l'analyse des sessions selectionnees'."""
    _require_droit(user, "FormScool")
    return svc.analyser_promotions(payload)


# ====================================================================
# Onglet Evenement
# ====================================================================

@router.get("/formations/{id_formation}/evenements",
            response_model=list[EvenementRow])
def get_evenements(
    id_formation: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    return svc.list_evenements(id_formation)


@router.post("/formations/{id_formation}/evenements")
def post_evenement(
    id_formation: str,
    payload: EvenementPayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    new_id = svc.add_evenement(id_formation, payload, op_id)
    return {"ok": bool(new_id), "id_evenement": new_id}


@router.put("/formations/{id_formation}/evenements/{id_evenement}")
def put_evenement(
    id_formation: str,
    id_evenement: str,
    payload: EvenementPayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.update_evenement(id_evenement, payload, op_id)
    return {"ok": ok}


@router.delete("/formations/{id_formation}/evenements/{id_evenement}")
def del_evenement(
    id_formation: str,
    id_evenement: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.delete_evenement(id_evenement, op_id)
    return {"ok": ok}


# ====================================================================
# Onglet Eleves
# ====================================================================

@router.get("/formations/{id_formation}/eleves",
            response_model=list[EleveRow])
def get_eleves(
    id_formation: str,
    uniquement_actifs: bool = False,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    return svc.list_eleves(id_formation, uniquement_actifs)


@router.post("/formations/{id_formation}/eleves")
def post_eleve(
    id_formation: str,
    payload: EleveAjoutPayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.add_eleve(id_formation, payload, op_id)
    return {"ok": ok}


@router.post("/formations/{id_formation}/eleves/{id_salarie}/toggle-livrable")
def post_toggle_livrable(
    id_formation: str,
    id_salarie: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.toggle_livrable(id_formation, id_salarie, op_id)
    return {"ok": ok}


@router.delete("/formations/{id_formation}/eleves/{id_salarie}")
def del_eleve(
    id_formation: str,
    id_salarie: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.delete_eleve(id_formation, id_salarie, op_id)
    return {"ok": ok}


# ====================================================================
# Onglet Session de recrut
# ====================================================================

@router.get("/formations/{id_formation}/sessions-recrut",
            response_model=list[SessionRecrutRow])
def get_sessions_recrut(
    id_formation: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    return svc.list_sessions_recrut(id_formation)


@router.post("/formations/{id_formation}/sessions-recrut")
def post_session_recrut(
    id_formation: str,
    payload: SessionRecrutPayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    new_id = svc.add_session_recrut(id_formation, payload, op_id)
    return {"ok": bool(new_id), "id_session": new_id}


@router.delete("/formations/{id_formation}/sessions-recrut/{id_session}")
def del_session_recrut(
    id_formation: str,
    id_session: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.delete_session_recrut(id_session, op_id)
    return {"ok": ok}


# ====================================================================
# Onglet Bulletins
# ====================================================================

@router.get("/formations/{id_formation}/bulletins",
            response_model=list[BulletinRow])
def get_bulletins(
    id_formation: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    return svc.list_bulletins(id_formation)


@router.delete("/formations/{id_formation}/bulletins/{id_bulletin}")
def del_bulletin(
    id_formation: str,
    id_bulletin: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.delete_bulletin(id_bulletin, op_id)
    return {"ok": ok}


# ====================================================================
# Onglet Bareme Notes
# ====================================================================

@router.get("/formations/{id_formation}/baremes",
            response_model=list[BaremeNoteRow])
def get_baremes(
    id_formation: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    return svc.list_baremes(id_formation)


@router.post("/formations/{id_formation}/baremes")
def post_bareme(
    id_formation: str,
    payload: BaremeNotePayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    new_id = svc.add_bareme(id_formation, payload, op_id)
    return {"ok": bool(new_id), "id_bareme": new_id}


@router.put("/formations/{id_formation}/baremes/{id_bareme}")
def put_bareme(
    id_formation: str,
    id_bareme: str,
    payload: BaremeNotePayload,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.update_bareme(id_bareme, payload, op_id)
    return {"ok": ok}


@router.delete("/formations/{id_formation}/baremes/{id_bareme}")
def del_bareme(
    id_formation: str,
    id_bareme: str,
    user: UserToken = Depends(get_current_user),
):
    _require_droit(user, "FormScool")
    op_id = int(user.id_salarie or 0)
    ok = svc.delete_bareme(id_bareme, op_id)
    return {"ok": ok}
