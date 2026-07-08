"""
Schemas Fen_ScoolPlanning - Planning S'Cool.
"""
from pydantic import BaseModel, Field


class PlanningRessource(BaseModel):
    """Un formateur (ressource) affiche comme ligne dans le planning."""
    id_formateur: str
    nom: str
    prenom: str
    niveau: str = ""
    is_actif: bool = True


class PlanningEvent(BaseModel):
    """Un evenement / formation sur le planning."""
    id: str
    id_formation: str
    id_formateur: str
    titre: str           # ex 'N1 DEVENIR COMMERCIAL - SFR (Formateur principal), Wasquehal'
    date_debut: str      # YYYY-MM-DD (evenement journee, pas horaire)
    date_fin: str
    couleur: str = "#17494E"
    kind: str = "formation"   # 'formation' | 'evenement'


class PlanningParams(BaseModel):
    date_deb: str
    date_fin: str
    avec_sortis: bool = False


class PlanningResult(BaseModel):
    ressources: list[PlanningRessource] = Field(default_factory=list)
    events: list[PlanningEvent] = Field(default_factory=list)
