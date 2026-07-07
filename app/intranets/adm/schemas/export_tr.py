"""
Schemas Fen_ExportFicTR - Export pour Commande de TR (Titres Restaurant).
"""
from pydantic import BaseModel, Field


class ExportTRRow(BaseModel):
    """Ligne du tableau vendeur (une par salarie a exporter).

    Colonnes CSV : MATRICULE / civilite / NOM / PRENOM / DATE_DE_NAISSANCE
    / ADRESSE_1 / adresse_2 / adresse_3 / CODE_POSTAL / VILLE / email /
    PAYS / NOMBRE_DE_TITRES / ref_pdist / nom_de_l_employeur /
    reference_chargement.
    """
    id_salarie: str = ""
    matricule: str = ""
    civilite: str = ""
    nom: str = ""
    prenom: str = ""
    date_naissance: str = ""      # ISO YYYY-MM-DD (converti en JJMMAAAA a l'export)
    adresse_1: str = ""
    adresse_2: str = ""
    adresse_3: str = ""
    code_postal: str = ""
    ville: str = ""
    email: str = ""
    pays: str = "France"
    nombre_titres: str = ""
    ref_pdist: str = ""            # = raison_sociale
    nom_employeur: str = ""        # = raison_sociale
    reference_chargement: str = ""


class RechercheParEntiteParams(BaseModel):
    id_ste: str
    mois_paiement: str  # YYYY-MM


class RechercheParSalarieParams(BaseModel):
    id_salarie: str


class RechercheResult(BaseModel):
    ok: bool
    lignes: list[ExportTRRow] = Field(default_factory=list)
    message: str = ""


class ExportCsvParams(BaseModel):
    lignes: list[ExportTRRow]
    lib_entite: str = ""  # nom entite pour nom fichier
