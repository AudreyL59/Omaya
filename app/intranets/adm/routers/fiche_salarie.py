"""Endpoints REST de la Fiche Salarie ADM."""

import sys
import traceback
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import courrier_fpe as courrier_fpe_svc
from app.intranets.adm.services import fiche_doc_rh as doc_rh_svc
from app.intranets.adm.services import fiche_doc_rh_generate as doc_rh_gen_svc
from app.intranets.adm.services import fiche_organigramme as orga_svc
from app.intranets.adm.services import fiche_suivi_adm as suivi_adm_svc
from app.intranets.adm.schemas.fiche_salarie import (
    FicheCoordonnees,
    FicheEmbauche,
    FicheEmbaucheRefs,
    FicheFormateur,
    FicheHeader,
    FicheIdentite,
    SalariePartDpae,
    SalariePortail,
    SaveCoordonneesPayload,
    SaveEmbauchePayload,
    SaveFormateurPayload,
    SaveIdentitePayload,
    SaveResponse,
    SortieSalariePayload,
    SortieSalarieResponse,
    ToggleStatusPayload,
)
from app.intranets.adm.services import fiche_salarie as svc

router = APIRouter(prefix="/fiche-salarie", tags=["adm-fiche-salarie"])


@router.get("/{id_salarie}/photo")
def get_photo(id_salarie: int = Path(...), user: UserToken = Depends(get_current_user)):
    """Photo du salarie (bytea decode + content-type auto). 404 si pas de photo."""
    try:
        result = svc.load_photo(id_salarie)
        if not result:
            raise HTTPException(status_code=404, detail="Pas de photo")
        data, content_type = result
        return Response(
            content=data,
            media_type=content_type,
            headers={"Cache-Control": "private, max-age=300"},
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/{id_salarie}/header", response_model=FicheHeader)
def get_header(id_salarie: int = Path(...), user: UserToken = Depends(get_current_user)):
    try:
        data = svc.load_header(id_salarie)
        if not data:
            raise HTTPException(status_code=404, detail="Salarie introuvable")
        return data
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/{id_salarie}/identite", response_model=FicheIdentite)
def get_identite(id_salarie: int = Path(...), user: UserToken = Depends(get_current_user)):
    try:
        data = svc.load_identite(id_salarie)
        if not data:
            raise HTTPException(status_code=404, detail="Salarie introuvable")
        return data
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/{id_salarie}/identite", response_model=SaveResponse)
def save_identite(
    payload: SaveIdentitePayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    try:
        # On filtre les champs non fournis pour ne PAS ecraser avec None
        body = payload.model_dump(exclude_unset=True)
        return svc.save_identite(id_salarie, body)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/{id_salarie}/actif", response_model=SaveResponse)
def toggle_actif(
    payload: ToggleStatusPayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    try:
        return svc.set_en_activite(id_salarie, payload.value)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/{id_salarie}/en-pause", response_model=SaveResponse)
def toggle_en_pause(
    payload: ToggleStatusPayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    try:
        return svc.set_en_pause(id_salarie, payload.value)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


# --- Onglet 2 : Coordonnees ---------------------------------------------

@router.get("/{id_salarie}/coordonnees", response_model=FicheCoordonnees)
def get_coordonnees(id_salarie: int = Path(...), user: UserToken = Depends(get_current_user)):
    try:
        return svc.load_coordonnees(id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/{id_salarie}/coordonnees", response_model=SaveResponse)
def save_coordonnees(
    payload: SaveCoordonneesPayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    try:
        body = payload.model_dump(exclude_unset=True)
        return svc.save_coordonnees(id_salarie, body)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


# --- Onglet 3 : Infos Embauche ------------------------------------------

@router.get("/embauche/refs", response_model=FicheEmbaucheRefs)
def get_embauche_refs(user: UserToken = Depends(get_current_user)):
    """Combos pour l'onglet (societes, postes, type_ctt, type_horaire, type_sortie)."""
    try:
        return svc.list_embauche_refs()
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/{id_salarie}/embauche", response_model=FicheEmbauche)
def get_embauche(id_salarie: int = Path(...), user: UserToken = Depends(get_current_user)):
    try:
        return svc.load_embauche(id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/{id_salarie}/sortie/courrier-fpe.pdf")
def get_courrier_fpe_pdf(
    id_salarie: int = Path(...),
    delai_prev: str = Query("", description="Delai de prevenance (texte affiche)"),
    user: UserToken = Depends(get_current_user),
):
    """Genere et renvoie le PDF du courrier de rupture de periode d'essai
    (EtatCourrierFPE WinDev). Requiert WeasyPrint installe.
    """
    try:
        data, filename = courrier_fpe_svc.generate_courrier_fpe(id_salarie, delai_prev)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(
            status_code=500,
            detail=f"WeasyPrint non installé sur le serveur : {e}",
        )
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

    cd = f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": cd},
    )


@router.post("/{id_salarie}/sortie", response_model=SortieSalarieResponse)
def sortir(
    payload: SortieSalariePayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Action de sortie (phase B complete) :
    - UPDATE salarie_embauche en_activite=FALSE + salarie_sortie avec les champs
      du formulaire (info_cpl, courrier_*, stc_*).
    - Si codes Ohm existent : creation TK_DemandeCodeVendeur + TK_Liste.
    - Si TypeSortie > 1 : creation TK_Liste + TK_DemandeSortieRH (Service BO
      type 36 si <=4, Service JU type 37 sinon).
    - Envoi mail RH avec destinataires conditionnels (juriste si CDI/CDD,
      Cci fpe/juriste si TypeSortie > 1, etc.).
    """
    try:
        return svc.sortir_salarie(id_salarie, payload.model_dump(), user.id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/{id_salarie}/embauche", response_model=SaveResponse)
def save_embauche(
    payload: SaveEmbauchePayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    try:
        body = payload.model_dump(exclude_unset=True)
        return svc.save_embauche(id_salarie, body)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


# --- Overlay Partenaires (codes portails + societes DPAE) ----------------

@router.get("/{id_salarie}/partenaires/portails", response_model=list[SalariePortail])
def get_portails(id_salarie: int = Path(...), user: UserToken = Depends(get_current_user)):
    """Codes/login/MDP des portails partenaires du salarie."""
    try:
        return svc.list_salarie_portails(id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/{id_salarie}/partenaires/dpae", response_model=list[SalariePartDpae])
def get_part_dpae(id_salarie: int = Path(...), user: UserToken = Depends(get_current_user)):
    """Associations Partenaire <-> Societe DPAE pour ce salarie."""
    try:
        return svc.list_salarie_part_dpae(id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.delete("/partenaires/dpae/{id_salarie_partenaire}", response_model=SaveResponse)
def del_part_dpae(
    id_salarie_partenaire: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Suppression logique d'une association Partenaire-Societe DPAE."""
    try:
        return svc.delete_salarie_part_dpae(id_salarie_partenaire, user.id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/partenaires/portails/{id_salarie_partenaire}/send-codes")
def post_send_portail_codes(
    id_salarie_partenaire: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Renvoie les codes du portail au salarie par mail + SMS.

    Transposition WinDev bouton 'Renvoyer les codes' (overlay Partenaires).
    Retourne { ok, mail_envoye, sms_envoye, sms_result }.
    """
    try:
        return svc.send_portail_codes(id_salarie_partenaire, user.id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


# --- Overlay "S'Cool" : fiche Formateur ---------------------------------

@router.get("/{id_salarie}/formateur", response_model=FicheFormateur)
def get_formateur(id_salarie: int = Path(...), user: UserToken = Depends(get_current_user)):
    """Charge la fiche formateur du salarie (exists=False si pas creee)."""
    try:
        return svc.load_formateur(id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/{id_salarie}/formateur", response_model=SaveResponse)
def save_formateur(
    payload: SaveFormateurPayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Insert (si pas existe) ou Update partiel de la fiche formateur."""
    try:
        body = payload.model_dump(exclude_unset=True)
        return svc.save_formateur(id_salarie, body, user.id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


# --- Onglet Organigramme -------------------------------------------------


class SaveRattachementPayload(BaseModel):
    id_organigramme: str
    date_debut: str = ""
    date_fin: str = ""
    aff_actif: bool = True
    id_ste: str = ""


@router.get("/{id_salarie}/orga")
def get_orga_suivi(
    id_salarie: int = Path(...), user: UserToken = Depends(get_current_user)
):
    """Charge les 2 listes (rattachements + suivis) pour l'onglet 'Organigramme'."""
    try:
        return orga_svc.load_orga_suivi(id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/orga/tree")
def get_orga_children(
    id_parent: int = Query(0, description="0 = racine"),
    user: UserToken = Depends(get_current_user),
):
    """Liste les organigrammes enfants d'un noeud (pour la navigation Arbre1)."""
    try:
        return {"items": orga_svc.load_orga_children(id_parent)}
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/orga/societes")
def get_orga_societes(user: UserToken = Depends(get_current_user)):
    """Liste des societes (racine id_type_orga=1) pour le combo de la popup."""
    try:
        return {"items": orga_svc.list_societes()}
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/{id_salarie}/orga")
def create_rattachement(
    payload: SaveRattachementPayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Cree un rattachement (insert pgt_salarie_organigramme) + ferme l'ancien
    suivi 'changement d'equipe' et cree le nouveau (type=2)."""
    try:
        return orga_svc.save_rattachement(
            id_salarie=id_salarie,
            id_salarie_organigramme=0,
            id_organigramme=int(payload.id_organigramme or 0),
            date_debut=payload.date_debut,
            date_fin=payload.date_fin,
            aff_actif=payload.aff_actif,
            id_ste=int(payload.id_ste or 0),
            op_id=user.id_salarie,
        )
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.put("/orga/{id_salarie_organigramme}")
def update_rattachement(
    payload: SaveRattachementPayload,
    id_salarie_organigramme: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Modifie un rattachement existant (modif_elem='modif')."""
    try:
        return orga_svc.save_rattachement(
            id_salarie=0,
            id_salarie_organigramme=id_salarie_organigramme,
            id_organigramme=int(payload.id_organigramme or 0),
            date_debut=payload.date_debut,
            date_fin=payload.date_fin,
            aff_actif=payload.aff_actif,
            id_ste=int(payload.id_ste or 0),
            op_id=user.id_salarie,
        )
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/orga/{id_salarie_organigramme}/duplicate")
def duplicate_rattachement_route(
    id_salarie_organigramme: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Duplique le rattachement (memes valeurs, modif_elem='new', nouvel ID)."""
    try:
        return orga_svc.duplicate_rattachement(id_salarie_organigramme, user.id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.delete("/orga/{id_salarie_organigramme}")
def delete_rattachement(
    id_salarie_organigramme: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Soft delete (modif_elem='suppr')."""
    try:
        return orga_svc.soft_delete_rattachement(id_salarie_organigramme, user.id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


# --- Onglet Suivi ADM ----------------------------------------------------


class AddSuiviAdmPayload(BaseModel):
    description: str


@router.get("/{id_salarie}/suivi-adm")
def get_suivi_adm(
    id_salarie: int = Path(...), user: UserToken = Depends(get_current_user)
):
    """Liste des memos deposes sur le salarie, triee par date desc."""
    try:
        return {"items": suivi_adm_svc.load_suivi_adm(id_salarie)}
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/{id_salarie}/suivi-adm")
def post_suivi_adm(
    payload: AddSuiviAdmPayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Ajoute un nouveau memo."""
    try:
        res = suivi_adm_svc.add_suivi_adm(
            id_salarie, payload.description, user.id_salarie
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("error", "Erreur"))
        return res
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


# --- Onglet 'Contrat de travail' (Docs RH) -------------------------------


@router.get("/{id_salarie}/doc-rh")
def get_doc_rh(
    id_salarie: int = Path(...), user: UserToken = Depends(get_current_user)
):
    """Liste des documents RH du salarie pour l'onglet 'Contrat de travail'."""
    try:
        return {"items": doc_rh_svc.load_doc_rh(id_salarie)}
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/doc-rh/{id_salarie_doc_rh}/cttw-recu")
def post_doc_rh_cttw_recu(
    id_salarie_doc_rh: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Bouton 'Cttw RECU' : marque le doc comme recu (recu=true, recu_date=now)."""
    try:
        return doc_rh_svc.mark_cttw_recu(id_salarie_doc_rh, user.id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/doc-rh/{id_salarie_doc_rh}/ctt-edite-url")
def get_doc_rh_ctt_edite_url(
    id_salarie_doc_rh: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Bouton 'Voir le Ctt edite' : retourne l'URL du PDF (ou erreur)."""
    try:
        return doc_rh_svc.find_ctt_edite_url(id_salarie_doc_rh)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.delete("/doc-rh/{id_salarie_doc_rh}")
def delete_doc_rh(
    id_salarie_doc_rh: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Soft delete (modif_elem='suppr')."""
    try:
        return doc_rh_svc.soft_delete_doc_rh(id_salarie_doc_rh, user.id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/doc-rh/types-produit")
def get_doc_rh_types_produit(user: UserToken = Depends(get_current_user)):
    """Liste des types produits FDV pour la combo de la popup nouveau doc."""
    try:
        return {"items": doc_rh_svc.list_types_produit_fdv()}
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


class GenerateCttwPayload(BaseModel):
    id_doc_rh: str
    date_avenant: str = ""  # ISO YYYY-MM-DD, requis si modele = AVENANT


@router.post("/{id_salarie}/doc-rh/generate-cttw")
def post_doc_rh_generate_cttw(
    payload: GenerateCttwPayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Genere le contrat de travail (DOCX -> PDF) + cree 3 records :
    salarie_doc_rh, tk_demande_ctt_w, tk_liste (ticket type 4 RH)."""
    try:
        return doc_rh_gen_svc.generate_cttw(
            id_salarie=id_salarie,
            id_doc_rh=int(payload.id_doc_rh or 0),
            op_id=user.id_salarie,
            date_avenant=payload.date_avenant,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/{id_salarie}/doc-rh/docs-disponibles")
def get_doc_rh_docs_disponibles(
    id_salarie: int = Path(...),
    id_type_produit: int = Query(0, description="0 = type produit par defaut du salarie"),
    user: UserToken = Depends(get_current_user),
):
    """Liste des modeles de docs RH dispos pour ce salarie + type produit.

    Si id_type_produit=0, deduit le type produit de l'organigramme actif du salarie.
    Retourne aussi le default_id_type_produit pour pre-selection cote front.
    """
    try:
        default_tp = doc_rh_svc.get_type_produit_salarie(id_salarie)
        effective_tp = int(id_type_produit) if id_type_produit else int(default_tp or 0)
        docs = doc_rh_svc.list_docs_disponibles(id_salarie, effective_tp) if effective_tp else []
        return {
            "default_id_type_produit": default_tp,
            "id_type_produit": str(effective_tp),
            "items": docs,
        }
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
