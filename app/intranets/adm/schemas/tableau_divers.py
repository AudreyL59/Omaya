"""
Schemas Fen_TableauDivers - Generation de tableaux divers (Valandre + Comptable).
"""
from pydantic import BaseModel, Field


class DemandeRow(BaseModel):
    """Ligne du tableau vendeurs a exporter (Fen_TableauDivers)."""
    id_salarie: str = ""
    choix: bool = True
    nom: str = ""
    prenom: str = ""
    poste: str = ""       # Formate WinDev : 'Vendeur' / 'Chef d equipe' / 'Responsable agence' / 'Dir. Co. Partenaire' / 'Resp. BO Eni' / 'Agent BO Eni'
    email: str = ""
    agence: str = ""
    equipe: str = ""
    type_demande: str = "Première demande"


class ListerDemandesParams(BaseModel):
    du: str    # YYYY-MM-DD
    au: str    # YYYY-MM-DD


class ListerDemandesResult(BaseModel):
    ok: bool
    lignes: list[DemandeRow] = Field(default_factory=list)
    message: str = ""


class GenererValandreParams(BaseModel):
    lignes: list[DemandeRow]


class GenererComptableParams(BaseModel):
    du: str   # YYYY-MM-DD
    au: str   # YYYY-MM-DD
