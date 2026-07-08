"""
Schemas Fen_TableauSalarie - Tableau des salaries par equipe.
"""
from pydantic import BaseModel, Field


class OrgaCombo(BaseModel):
    """Une equipe/agence (organigramme) pour le picker."""
    id_orga: str
    lib_orga: str
    lib_parent: str = ""


class RechercherParams(BaseModel):
    """Input Btn Lancer la recherche."""
    id_orga: str
    mois_paiement: str  # YYYY-MM


class VendeurRow(BaseModel):
    """Ligne TableVendeur."""
    id_salarie: str = ""
    nom: str = ""
    prenom: str = ""
    poste: str = ""
    is_actif: bool = True
    is_sortie: bool = False
    date_entree: str = ""       # YYYY-MM-DD
    type_sortie: str = ""       # libelle (Demission, ...)
    eq_terrain: str = ""        # nom de l'orga terrain
    is_resp: bool = False
    absences: str = ""          # multi-ligne (les \n separent)
    avance: float = 0.0


class RechercherResult(BaseModel):
    ok: bool
    lignes: list[VendeurRow] = Field(default_factory=list)
    message: str = ""


class ExportXlsxParams(BaseModel):
    """Export XLSX groupe par equipe terrain."""
    id_orga: str
    lib_orga: str        # pour titre + nom fichier
    mois_paiement: str
    lignes: list[VendeurRow]
