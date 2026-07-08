"""
Schemas Fen_CalculPointsBS - Recalcul des points contrats par partenaire.
"""
from pydantic import BaseModel, Field


class PartenaireCombo(BaseModel):
    """Combo Partenaire (Fen_CalculPointsBS)."""
    prefixe_bdd: str
    lib_partenaire: str


class RecalculParams(BaseModel):
    """Input Btn Calcul Point."""
    prefixe: str     # 'ENI' / 'SFR' / 'IAG' / 'STR' / 'VAL' / 'PRO' / 'OEN' / 'TLC'
    du: str          # YYYY-MM-DD
    au: str          # YYYY-MM-DD
    simulation: bool = True


class ContratModifieRow(BaseModel):
    """Ligne TableContratModif (une par contrat dont les points ont change)."""
    id_contrat: str = ""
    part: str = ""
    num_bs: str = ""
    date_signature: str = ""
    famille: str = ""
    ss_fam: str = ""
    car: int = 0
    kva: int = 0
    nb_opt: str = ""
    lib_etat: str = ""
    id_type_etat: int = 0
    nb_point_av: float = 0.0
    nb_point_ap: float = 0.0


class RecalculResult(BaseModel):
    ok: bool
    nb_ctts_lus: int = 0
    nb_modifies: int = 0
    lignes: list[ContratModifieRow] = Field(default_factory=list)
    message: str = ""


class ExportXlsxParams(BaseModel):
    """Export XLSX de la table TableContratModif."""
    prefixe: str
    du: str
    au: str
    lignes: list[ContratModifieRow]
