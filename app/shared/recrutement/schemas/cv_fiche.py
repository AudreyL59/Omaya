"""Schemas pour Fen_CVFiche (shared : ADM + Vendeur + Call RH)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class CVFicheDetail(BaseModel):
    """Fiche CV complete (lecture)."""
    id_cvtheque: str
    nom: str = ""
    prenom: str = ""
    adresse: str = ""
    id_communes_france: str = ""
    code_postal: str = ""
    nom_ville: str = ""
    pays: str = ""
    date_naissance: str = ""
    age: int = 0
    permis_b: bool = False
    vehicule: bool = False
    mail: str = ""
    gsm: str = ""
    id_cvposte: str = ""
    id_cvsource: str = ""
    id_elem_source: str = ""
    id_ste: str = ""
    id_cv_statut: str = ""   # statut courant (dernier CvSuivi)
    date_rappel: str = ""
    observ: str = ""
    fic_cv: str = ""
    date_saisie: str = ""
    date_reac: str = ""

    # Champs derives
    coopteur_nom: str = ""    # si source=1


class CVSuiviRow(BaseModel):
    id_cv_suivi: str
    datecrea: str
    op_crea: str
    op_nom: str = ""
    id_cv_statut: str
    statut_lib: str = ""
    type_elem: str = ""
    id_elem: str = ""
    observation: str = ""


class CVFichePayload(BaseModel):
    """Payload PUT /cv/{id} (enregistrer)."""
    nom: str = ""
    prenom: str = ""
    adresse: str = ""
    id_communes_france: str = ""
    pays: str = ""
    date_naissance: str = ""
    permis_b: bool = False
    vehicule: bool = False
    mail: str = ""
    gsm: str = ""
    id_cvposte: str = ""
    id_cvsource: str = ""
    id_elem_source: str = ""
    id_ste: str = ""
    id_cv_statut: str = ""    # statut a appliquer (genere un CvSuivi si change)
    date_rappel: str = ""
    nouvelle_observation: str = ""


class CVStatutQuickPayload(BaseModel):
    """Payload pour bouton statut rapide (refus, msg rep, etudiant, etc.)."""
    id_cv_statut: int
    observation: str = ""
    date_rappel: Optional[str] = None   # uniquement pour statut=2 (A recontacter)


class CVObservationPayload(BaseModel):
    """Payload pour bouton 'disquette' (ajoute juste une obs datee)."""
    observation: str
