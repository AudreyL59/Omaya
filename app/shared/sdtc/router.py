"""
Router shared SDTC (Fen_SDTC WinDev).

Endpoints :
  GET  /shared/sdtc/{id}/load                  - ouverture Fen_SDTC
  GET  /shared/sdtc/{id}/contrats              - charge tous les contrats du salarie
  POST /shared/sdtc/{id}/valider-selection     - btn 'Valider la selection'
  POST /shared/sdtc/{id}/generer-tableau       - btn 'Generation du tableau'
  POST /shared/sdtc/{id}/save-mail             - sauvegarde MailObjet/Contenu
  GET  /shared/sdtc/{id}/mail-payload          - btn 'Mail SDTC'
  POST /shared/sdtc/{id}/xls                   - export XLS TableContratTOT
  POST /shared/sdtc/{id}/pdf                   - export PDF EtatSTC_RecapPROD
"""

from __future__ import annotations

import sys
import traceback

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

from . import mail as mail_svc
from . import service as svc
from .bareme import compute_bareme
from .contrats import load_contrats
from .pdf import build_pdf
from .recap import generer_tableau
from .service import substitute_placeholders
from .validation import valider_selection
from .xls import build_workbook


router = APIRouter(prefix="/shared/sdtc", tags=["shared-sdtc"])


def _parse_id(id_salarie: str) -> int:
    try:
        return int(id_salarie)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"id_salarie invalide : {id_salarie}",
        )


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ValiderSelectionPayload(BaseModel):
    contrat_ids_traites: list[str] = []
    contrat_ids_a_traiter: list[str] = []
    mois_p_sdtc: str = ""   # YYYY-MM (cf. WinDev MoisP_SDTC pour auto-validation SFR)


class ComputeBaremePayload(BaseModel):
    """Compat ancien front : partition auto entre traites / a_traiter."""
    contrat_ids: list[str] = []
    mois_p_sdtc: str = ""


class GenererTableauPayload(BaseModel):
    contrat_ids_traites: list[str] = []
    contrat_ids_a_traiter: list[str] = []
    date_ref: str = ""      # YYYY-MM-DD (cf. WinDev Date1 pour NB_TR)


class SaveMailPayload(BaseModel):
    objet: str
    contenu_html: str


class ExportXlsPayload(BaseModel):
    contrat_ids_traites: list[str] = []
    contrat_ids_a_traiter: list[str] = []


class ExportPdfPayload(BaseModel):
    contrat_ids_traites: list[str] = []
    contrat_ids_a_traiter: list[str] = []
    commentaires: str = ""
    nb_tr: int = 0
    deco: float = 0.0
    avance: float = 0.0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/{id_salarie}/load")
def sdtc_load(id_salarie: str, _user: UserToken = Depends(get_current_user)):
    """Ouverture Fen_SDTC : DonneInfoSalarie + sortie + mutuelle + dernier
    contrat + info_salarie_html (avec placeholders)."""
    sid = _parse_id(id_salarie)
    try:
        data = svc.load(sid)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(
            status_code=500, detail=f"{type(e).__name__}: {e}"
        )
    if not data.get("found"):
        raise HTTPException(status_code=404, detail="Salarie introuvable.")
    return data


@router.get("/{id_salarie}/contrats")
def sdtc_contrats(id_salarie: str, _user: UserToken = Depends(get_current_user)):
    """afficherContrat : charge tous les contrats du salarie tous partenaires
    confondus, recalcule nb_points + UPDATE defensif, et dispatche en
    traites / a_traiter."""
    sid = _parse_id(id_salarie)
    try:
        return load_contrats(sid)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(
            status_code=500, detail=f"{type(e).__name__}: {e}"
        )


@router.post("/{id_salarie}/compute-bareme")
def sdtc_compute_bareme(
    id_salarie: str,
    payload: ComputeBaremePayload,
    user: UserToken = Depends(get_current_user),
):
    """Compatibilite ancien front : partitionne automatiquement les ids
    selectionnes entre traites / a_traiter avant d'appeler valider_selection.
    Le nouveau front doit utiliser /valider-selection directement."""
    sid = _parse_id(id_salarie)
    try:
        data = load_contrats(sid)
        selection_ids = {cid.strip() for cid in payload.contrat_ids if cid and cid.strip()}
        if not selection_ids:
            raise HTTPException(status_code=400, detail="Aucun contrat selectionne.")
        ids_traites = {
            str(c.get("id_contrat"))
            for c in (data.get("traites") or [])
            if str(c.get("id_contrat")) in selection_ids
        }
        ids_a_traiter = {
            str(c.get("id_contrat"))
            for c in (data.get("a_traiter") or [])
            if str(c.get("id_contrat")) in selection_ids
        }
        result = valider_selection(
            contrats_traites=data.get("traites") or [],
            contrats_a_traiter=data.get("a_traiter") or [],
            selected_ids_traites=ids_traites,
            selected_ids_a_traiter=ids_a_traiter,
            mois_p_sdtc=payload.mois_p_sdtc,
            op_id=user.id_salarie,
        )
        result["nb_selectionnes"] = len(selection_ids)
        result["selection_ids"] = sorted(selection_ids)
        return result
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(
            status_code=500, detail=f"{type(e).__name__}: {e}"
        )


@router.post("/{id_salarie}/valider-selection")
def sdtc_valider_selection(
    id_salarie: str,
    payload: ValiderSelectionPayload,
    user: UserToken = Depends(get_current_user),
):
    """Btn 'Valider la selection et passer a l'etape suivante' :
    - agrege TableProduitSTC sur les contrats coches
    - cas special SFR Col_IdTypeEtat=8 : UPDATE etat=6 + ajoute_histo_contrat
    - calcule bareme global + commission."""
    sid = _parse_id(id_salarie)
    try:
        data = load_contrats(sid)
        result = valider_selection(
            contrats_traites=data.get("traites") or [],
            contrats_a_traiter=data.get("a_traiter") or [],
            selected_ids_traites=set(payload.contrat_ids_traites),
            selected_ids_a_traiter=set(payload.contrat_ids_a_traiter),
            mois_p_sdtc=payload.mois_p_sdtc,
            op_id=user.id_salarie,
        )
        return result
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(
            status_code=500, detail=f"{type(e).__name__}: {e}"
        )


@router.post("/{id_salarie}/generer-tableau")
def sdtc_generer_tableau(
    id_salarie: str,
    payload: GenererTableauPayload,
    _user: UserToken = Depends(get_current_user),
):
    """Btn 'Generation du tableau a imprimer' :
    - TableContratTOT (fusion traites + a_traiter)
    - TableRecapProd + TableRecapProdPts (par produit/etat)
    - NB_TR (jours travailles depuis date_ref)."""
    sid = _parse_id(id_salarie)
    try:
        data = load_contrats(sid)
        result = generer_tableau(
            contrats_traites=data.get("traites") or [],
            contrats_a_traiter=data.get("a_traiter") or [],
            selected_ids_traites=set(payload.contrat_ids_traites),
            selected_ids_a_traiter=set(payload.contrat_ids_a_traiter),
            date_ref=payload.date_ref,
        )
        return result.to_dict()
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(
            status_code=500, detail=f"{type(e).__name__}: {e}"
        )


@router.post("/{id_salarie}/save-mail")
def sdtc_save_mail(
    id_salarie: str,
    payload: SaveMailPayload,
    user: UserToken = Depends(get_current_user),
):
    """Sauvegarde mail_objet + mail_contenu dans pgt_salarie_sortie (cf.
    fin du btn 'Generation PDFs/XLS/Mail')."""
    sid = _parse_id(id_salarie)
    try:
        return mail_svc.save_mail_content(
            id_salarie=sid,
            objet=payload.objet,
            contenu_html=payload.contenu_html,
            op_id=user.id_salarie,
        )
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(
            status_code=500, detail=f"{type(e).__name__}: {e}"
        )


@router.get("/{id_salarie}/mail-payload")
def sdtc_mail_payload(
    id_salarie: str, _user: UserToken = Depends(get_current_user)
):
    """Btn 'Mail SDTC' : payload pour pre-remplir Fen_EnvoieEmail
    (expediteur fpe@, A service_paie@cneidf, CC a.dubois/m.doineau/fpe,
    objet/html stockes)."""
    sid = _parse_id(id_salarie)
    try:
        return mail_svc.get_mail_payload(sid)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(
            status_code=500, detail=f"{type(e).__name__}: {e}"
        )


@router.post("/{id_salarie}/xls")
def sdtc_export_xls(
    id_salarie: str,
    payload: ExportXlsPayload,
    _user: UserToken = Depends(get_current_user),
):
    """Genere le XLS TableContratTOT (sortie complete)."""
    sid = _parse_id(id_salarie)
    base = svc.load(sid)
    if not base.get("found"):
        raise HTTPException(status_code=404, detail="Salarie introuvable.")
    data = load_contrats(sid)
    ids_traites = set(payload.contrat_ids_traites)
    ids_a_traiter = set(payload.contrat_ids_a_traiter)
    traites = [c for c in (data.get("traites") or []) if str(c.get("id_contrat")) in ids_traites]
    a_traiter = [c for c in (data.get("a_traiter") or []) if str(c.get("id_contrat")) in ids_a_traiter]
    if not traites and not a_traiter:
        raise HTTPException(status_code=400, detail="Aucun contrat selectionne.")
    lib = (base.get("salarie") or {}).get("lib_nom") or ""
    content = build_workbook(traites, a_traiter, lib_salarie=lib)
    filename = f"SDTC_{lib.replace(' ', '_') or sid}.xlsx"
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{id_salarie}/pdf")
def sdtc_export_pdf(
    id_salarie: str,
    payload: ExportPdfPayload,
    _user: UserToken = Depends(get_current_user),
):
    """Genere le PDF EtatSTC_RecapPROD + remplit le HTML mesInfos avec les
    placeholders (MONTANT_COMM/CP/DECO/AVANCE/NB_TR/DATEABS)."""
    sid = _parse_id(id_salarie)
    base = svc.load(sid)
    if not base.get("found"):
        raise HTTPException(status_code=404, detail="Salarie introuvable.")
    data = load_contrats(sid)
    ids_traites = set(payload.contrat_ids_traites)
    ids_a_traiter = set(payload.contrat_ids_a_traiter)
    traites = [c for c in (data.get("traites") or []) if str(c.get("id_contrat")) in ids_traites]
    a_traiter = [c for c in (data.get("a_traiter") or []) if str(c.get("id_contrat")) in ids_a_traiter]
    consideres = traites + a_traiter
    if not consideres:
        raise HTTPException(status_code=400, detail="Aucun contrat selectionne.")

    bareme_obj = compute_bareme(a_traiter).to_dict() if a_traiter else compute_bareme([]).to_dict()
    # Substitute placeholders dans le HTML mesInfos pour pre-stocker
    info_html_filled = substitute_placeholders(
        base.get("info_salarie_html") or "",
        comm_tot_stc=bareme_obj.get("comm_tot_stc", 0.0),
        date_anciennete_yyyymmdd=(base.get("salarie") or {}).get(
            "date_anciennete_yyyymmdd", ""
        ),
        deco=payload.deco,
        avance=payload.avance,
        nb_tr=payload.nb_tr,
        date_dernier_ctt=base.get("date_dernier_ctt", ""),
    )

    content = build_pdf(
        salarie=base.get("salarie") or {},
        bareme=bareme_obj,
        contrats_consideres=consideres,
        nb_tr=payload.nb_tr,
        commentaires=payload.commentaires,
        info_salarie_html=info_html_filled,
    )
    lib = (base.get("salarie") or {}).get("lib_nom") or ""
    filename = f"SDTC_{lib.replace(' ', '_') or sid}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
