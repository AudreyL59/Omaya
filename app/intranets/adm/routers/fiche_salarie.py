"""Endpoints REST de la Fiche Salarie ADM."""

import sys
import traceback
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.intranets.adm.services import courrier_fpe as courrier_fpe_svc
from app.intranets.adm.services import fiche_absences as absences_svc
from app.intranets.adm.services import fiche_doc_rh as doc_rh_svc
from app.intranets.adm.services import fiche_doc_rh_generate as doc_rh_gen_svc
from app.intranets.adm.services import fiche_documents as documents_svc
from app.intranets.adm.services import fiche_mutuelle as mutuelle_svc
from app.intranets.adm.services import fiche_note_frais as note_frais_svc
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


@router.post("/{id_salarie}/doc-rh/preview-pdf")
def post_doc_rh_preview_pdf(
    payload: GenerateCttwPayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Bouton 'Export PDF' : genere le PDF (publipostage + images) sans
    rien ecrire en base. Retourne le PDF en download."""
    try:
        res = doc_rh_gen_svc.preview_cttw_pdf(
            id_salarie=id_salarie,
            id_doc_rh=int(payload.id_doc_rh or 0),
            date_avenant=payload.date_avenant,
        )
        from urllib.parse import quote
        fname = res["filename"]
        return Response(
            content=res["pdf_bytes"],
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{quote(fname)}"'
                ),
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


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


# --- Onglet 'Documents' (FTP listing) ------------------------------------


@router.get("/{id_salarie}/documents")
def get_documents(
    id_salarie: int = Path(...),
    sous_rep: str = Query(
        "internes",
        description="internes | espace_salarie | adf | bilan_evo | factures",
    ),
    user: UserToken = Depends(get_current_user),
):
    """Liste les fichiers du salarie sur le FTP (/OMAYA/gestionRH/{id}/<sous>)."""
    try:
        return documents_svc.list_files(id_salarie, sous_rep)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/{id_salarie}/documents/upload")
async def post_documents_upload(
    id_salarie: int = Path(...),
    sous_rep: str = Query("internes"),
    file: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    """Upload un fichier sur le FTP (transposition WinDev Btn '+')."""
    try:
        content = await file.read()
        res = documents_svc.upload_file(
            id_salarie, sous_rep, file.filename or "fichier", content
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("error", "Echec upload"))
        return res
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.delete("/{id_salarie}/documents")
def delete_document(
    id_salarie: int = Path(...),
    sous_rep: str = Query("internes"),
    filename: str = Query(...),
    user: UserToken = Depends(get_current_user),
):
    """Supprime un fichier sur le FTP (transposition WinDev Btn 'Suppression')."""
    try:
        res = documents_svc.delete_file(id_salarie, sous_rep, filename)
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("error", "Echec suppression"))
        return res
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


class TkMutuellePayload(BaseModel):
    sous_rep: str = "internes"
    filenames: list[str]


@router.post("/{id_salarie}/documents/tk-mutuelle")
def post_documents_tk_mutuelle(
    payload: TkMutuellePayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Cree un ticket Mutuelle (type 27, service JU) avec les fichiers
    selectionnes en pieces jointes (transposition WinDev Btn 'Tk Mutuelle')."""
    try:
        res = documents_svc.create_tk_mutuelle(
            id_salarie, payload.sous_rep, payload.filenames, user.id_salarie
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("error", "Echec"))
        return res
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


# --- Onglet 'Absences' ---------------------------------------------------


@router.get("/{id_salarie}/absences")
def get_absences(
    id_salarie: int = Path(...), user: UserToken = Depends(get_current_user)
):
    """Liste des absences du salarie (tri periode desc / type / date debut)."""
    try:
        return {"items": absences_svc.load_absences(id_salarie)}
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/absences/{id_absence}/duplicate")
def post_absence_duplicate(
    id_absence: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Dupliquer' : copie l'absence (nouvel id, modif_elem='new')."""
    try:
        res = absences_svc.duplicate_absence(id_absence, user.id_salarie)
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("error", "Echec"))
        return res
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.delete("/absences/{id_absence}")
def delete_absence(
    id_absence: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Supprimer' : soft delete (modif_elem='suppr')."""
    try:
        return absences_svc.soft_delete_absence(id_absence, user.id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/absences/types")
def get_absences_types(user: UserToken = Depends(get_current_user)):
    """Combo Type d'absence."""
    try:
        return {"items": absences_svc.list_types_absence()}
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/absences/{id_absence}")
def get_absence_detail(
    id_absence: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Detail d'une absence (pour pre-remplir la popup d'edition)."""
    try:
        row = absences_svc.get_absence(id_absence)
        if not row:
            raise HTTPException(status_code=404, detail="Absence introuvable")
        return row
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


class SaveAbsencePayload(BaseModel):
    id_type_absence: int
    date_debut: str
    date_fin: str = ""


@router.post("/{id_salarie}/absences")
def post_absence(
    payload: SaveAbsencePayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Cree une absence + calcul auto Periode/NBJ/NBJ_OUVRES/nbSamedi."""
    try:
        return absences_svc.save_absence(
            id_absence=0,
            id_salarie=id_salarie,
            id_type_absence=payload.id_type_absence,
            date_debut=payload.date_debut,
            date_fin=payload.date_fin,
            op_id=user.id_salarie,
        )
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.put("/absences/{id_absence}")
def put_absence(
    payload: SaveAbsencePayload,
    id_absence: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Modifie une absence existante."""
    try:
        return absences_svc.save_absence(
            id_absence=id_absence,
            id_salarie=0,
            id_type_absence=payload.id_type_absence,
            date_debut=payload.date_debut,
            date_fin=payload.date_fin,
            op_id=user.id_salarie,
        )
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


# --- Onglet 'Mutuelle' ---------------------------------------------------


class SaveMutuellePayload(BaseModel):
    adhesion: bool = False
    adhesion_date: str = ""
    id_mutuelle: int = 0
    mutuelle_dossier: bool = False
    mutuelle_att_ss: bool = False
    mutuelle_rib: bool = False
    mutuelle_doc_envoyes: bool = False
    mutuelle_recep_certif: bool = False
    mutuelle_pas_adhesion: bool = False
    mutuelle_pas_adhesion_jusquau: str = ""
    mutuelle_resilie: bool = False
    mutuelle_resilie_date: str = ""


@router.get("/{id_salarie}/mutuelle")
def get_mutuelle(
    id_salarie: int = Path(...), user: UserToken = Depends(get_current_user)
):
    """Charge le formulaire mutuelle + combo + historique tickets."""
    try:
        return mutuelle_svc.load(id_salarie, user.id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/{id_salarie}/mutuelle")
def post_mutuelle(
    payload: SaveMutuellePayload,
    id_salarie: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Enregistrer' : UPDATE pgt_salarie_mutuelle."""
    try:
        return mutuelle_svc.save(id_salarie, payload.model_dump(), user.id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


# --- Onglet 'Note de frais' ----------------------------------------------


class SaveNoteFraisPayload(BaseModel):
    id_note_frais_type: int
    date: str
    description: str = ""
    montant_ht: float = 0
    montant_tva: float = 0
    montant_ttc: float = 0
    verifiee: bool = False


@router.get("/note-frais/types")
def get_note_frais_types(user: UserToken = Depends(get_current_user)):
    """Combo Type de note de frais."""
    try:
        return {"items": note_frais_svc.list_types()}
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/{id_salarie}/note-frais")
def get_note_frais_list(
    id_salarie: int = Path(...),
    mois: int = Query(..., description="1-12"),
    annee: int = Query(..., description="ex. 2026"),
    user: UserToken = Depends(get_current_user),
):
    """Liste les notes de la periode (mois + annee)."""
    try:
        return {"items": note_frais_svc.list_notes(id_salarie, mois, annee)}
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/note-frais/{id_note_frais}")
def get_note_frais_detail(
    id_note_frais: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Pre-remplit le formulaire d'edition."""
    try:
        row = note_frais_svc.get_note(id_note_frais)
        if not row:
            raise HTTPException(status_code=404, detail="Note de frais introuvable")
        return row
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.put("/note-frais/{id_note_frais}")
def put_note_frais(
    payload: SaveNoteFraisPayload,
    id_note_frais: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Btn Enregistrer : UPDATE de la ligne."""
    try:
        return note_frais_svc.save_note(
            id_note_frais=id_note_frais,
            id_note_frais_type=payload.id_note_frais_type,
            date_iso=payload.date,
            description=payload.description,
            montant_ht=payload.montant_ht,
            montant_tva=payload.montant_tva,
            montant_ttc=payload.montant_ttc,
            verifiee=payload.verifiee,
            op_id=user.id_salarie,
        )
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.delete("/note-frais/{id_note_frais}")
def delete_note_frais(
    id_note_frais: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Btn poubelle : soft delete (modif_elem='suppr')."""
    try:
        return note_frais_svc.soft_delete_note(id_note_frais, user.id_salarie)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/note-frais/{id_note_frais}/photo")
def get_note_frais_photo(
    id_note_frais: int = Path(...),
    user: UserToken = Depends(get_current_user),
):
    """Photo ticket (bytea) -> binaire avec mime detecte."""
    try:
        res = note_frais_svc.get_photo(id_note_frais)
        if not res:
            raise HTTPException(status_code=404, detail="Pas de photo")
        data, mime = res
        return Response(
            content=data,
            media_type=mime,
            headers={"Cache-Control": "private, max-age=60"},
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/{id_salarie}/note-frais")
async def post_note_frais_create(
    id_salarie: int = Path(...),
    id_note_frais_type: int = Query(...),
    date_iso: str = Query(..., alias="date"),
    description: str = Query(""),
    montant_ht: float = Query(0),
    montant_tva: float = Query(0),
    montant_ttc: float = Query(0),
    verifiee: bool = Query(False),
    photo: UploadFile | None = File(None),
    user: UserToken = Depends(get_current_user),
):
    """Btn '+' : cree une note (transposition Fen_NoteFraisAjout).

    Multipart : champs en query params + photo optionnelle (file).
    """
    try:
        photo_bytes = await photo.read() if photo else None
        if photo_bytes == b"":
            photo_bytes = None
        res = note_frais_svc.create_note(
            id_salarie=id_salarie,
            id_note_frais_type=id_note_frais_type,
            date_iso=date_iso,
            description=description,
            montant_ht=montant_ht,
            montant_tva=montant_tva,
            montant_ttc=montant_ttc,
            verifiee=verifiee,
            photo_bytes=photo_bytes,
            op_id=user.id_salarie,
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("error", "Echec"))
        return res
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/note-frais/{id_note_frais}/photo")
async def post_note_frais_photo(
    id_note_frais: int = Path(...),
    photo: UploadFile = File(...),
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Charger une photo' : UPDATE photo_ticket."""
    try:
        data = await photo.read()
        if not data:
            raise HTTPException(status_code=400, detail="Photo vide")
        return note_frais_svc.update_photo(id_note_frais, data, user.id_salarie)
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
