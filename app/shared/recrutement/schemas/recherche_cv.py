"""Schemas Pydantic pour Fen_RechercheCV (shared)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ComboItem(BaseModel):
    id: str
    label: str


class CommuneItem(BaseModel):
    id_communes_france: str
    code_postal: str
    nom_ville: str
    latitude_deg: float | None = None
    longitude_deg: float | None = None


class SearchCVFiltres(BaseModel):
    """Tous les criteres de Fen_RechercheCV.

    mode : 1 = CP, 2 = Agence, 3 = Tel, 4 = Nom
    sous_mode_cp : 1 = avec ville (rayon), 2 = sans commune, 3 = sans geolocaliser
    select_type_date : 1 = par date de saisie/reac/rappel, 2 = par date modif CvSuivi
    select_profil : 1=ENI, 2=FIBRE, 3=Les2, 4=Autre (avec id_cvposte)
    """
    mode: int = 1
    sous_mode_cp: int = 1
    select_type_date: int = 1
    select_profil: int = 3

    # Periode (toujours)
    date_debut: Optional[str] = None
    date_fin: Optional[str] = None

    # Mode CP
    id_communes_france: Optional[list[str]] = None
    rayon_km: Optional[int] = None
    centre_lat: Optional[float] = None
    centre_lon: Optional[float] = None

    # Mode Agence
    id_organigrammes: Optional[list[str]] = None

    # Mode Tel
    tel: Optional[str] = None

    # Mode Nom
    nom: Optional[str] = None
    prenom: Optional[str] = None

    # Filtres communs (mode 1+2 uniquement)
    id_cvsource: Optional[str] = None
    id_elem_source: Optional[str] = None
    id_cvposte: Optional[str] = None
    id_ste: Optional[str] = None
    cv_statut_appel: Optional[str] = None
    age_min: int = 0
    age_max: int = 100

    # Limite (perf safety)
    limit: int = 1000


class CVRow(BaseModel):
    id_cvtheque: str
    identite: str
    nom: str
    prenom: str
    op_traitement: str = ""        # nom du salarie qui traite (vide si libre)
    op_traitement_id: str = ""     # id_salarie du proprio en cours
    statut_actuel: str = ""        # id_cv_statut courant
    statut_periode: str = ""       # id_cv_statut a la date_fin (si applicable)
    source: str = ""               # id_cvsource
    detail_source: str = ""        # nom coopteur ou lib annonceur
    age: int = 0
    tel: str = ""
    localisation: str = ""
    date_saisie: str = ""
    date_rappel: str = ""
    agence: str = ""
    equipe: str = ""
    commentaire: str = ""
