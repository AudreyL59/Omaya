"""
Schemas Fen_GestionPodium - Gestion des Podiums.

3 onglets :
  1. Podiums Vendeurs : recherche + score visible + calcul
  2. Parametres : CRUD PodiumType + PodiumTypePart
  3. Annee Podium : valider annee (creer 12 mois par podium)
"""
from typing import Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------
# Onglet 2 - Parametres : PodiumType (colonne gauche)
# --------------------------------------------------------------------

class PodiumType(BaseModel):
    id_podium_type: str = ""
    lib_podium_type: str = ""
    lib_court: str = ""
    prod_groupe: bool = False
    qualite: bool = False
    espoir: bool = False
    is_actif: bool = True
    ordre_affichage: int = 0


class PodiumTypePayload(BaseModel):
    """Input creation / update PodiumType."""
    lib_podium_type: str = ""
    lib_court: str = ""
    prod_groupe: bool = False
    qualite: bool = False
    espoir: bool = False
    is_actif: bool = True
    ordre_affichage: int = 0


# --------------------------------------------------------------------
# Onglet 2 - Parametres : PodiumTypePart (colonne droite)
# --------------------------------------------------------------------

class PodiumTypePart(BaseModel):
    id_podium_type_part: str = ""
    id_podium_type: str = ""
    famille: str = "Tous"
    sous_fam: str = "Tous"
    prefixe_bdd: str = ""      # 'ENI'/'SFR'/'IAG'/'STR'/'VAL'/'PRO'/'OEN'/'Coopt'
    type_prod: str = ""        # 'Brut'/'HorsRejet'/'Paye'
    option_vente: str = ""     # ''/'CQ-'/'MIG-'/'CQ-MIG-'
    jour_cial_deb: int = 1
    jour_cial_fin: int = 31


class PodiumTypePartPayload(BaseModel):
    id_podium_type: str
    famille: str = "Tous"
    sous_fam: str = "Tous"
    prefixe_bdd: str = ""
    type_prod: str = ""
    option_vente: str = ""
    jour_cial_deb: int = 1
    jour_cial_fin: int = 31


# --------------------------------------------------------------------
# Onglet 3 - Annee Podium
# --------------------------------------------------------------------

class ValiderAnneeParams(BaseModel):
    annee: int


class ValiderAnneeResult(BaseModel):
    ok: bool
    nb_crees: int = 0
    message: str = ""


# --------------------------------------------------------------------
# Onglet 1 - Podiums Vendeurs
# --------------------------------------------------------------------

class ComboItem(BaseModel):
    id: str
    lib: str


class RechercherPodiumParams(BaseModel):
    id_podium_type: str
    mois: int         # 1..12
    annee: int
    is_distrib: bool = False
    id_distrib: str = ""


class VendeurPodiumRow(BaseModel):
    id_salarie: str = ""
    nom: str = ""             # deja formate 'NOM Prenom'
    date_anciennete: str = ""  # YYYY-MM-DD
    id_equipe: str = ""
    equipe_lib: str = ""
    valeur: float = 0.0
    brut: float = 0.0
    paye: float = 0.0
    taux: float = 0.0
    visible: bool = True


class RechercherPodiumResult(BaseModel):
    ok: bool
    id_podium_mois: str = ""
    score_visible: bool = False
    is_qualite: bool = False
    is_prod_groupe: bool = False
    lignes: list[VendeurPodiumRow] = Field(default_factory=list)
    message: str = ""


class SauveScoreVisibleParams(BaseModel):
    id_podium_mois: str
    score_visible: bool


# --------------------------------------------------------------------
# Btn Calcul Podium (proc globale Podium_Calcul)
# --------------------------------------------------------------------

class CalculPodiumParams(BaseModel):
    du: str  # YYYY-MM-DD
    au: str  # YYYY-MM-DD


class CalculPodiumResult(BaseModel):
    ok: bool
    nb_iterations: int = 0
    message: str = ""


# --------------------------------------------------------------------
# Btn Telecharger XLSX
# --------------------------------------------------------------------

class TelechargerParams(BaseModel):
    id_podium_type: str
    mois: int
    annee: int
    is_distrib: bool = False
    id_distrib: str = ""
    lignes: list[VendeurPodiumRow] = Field(default_factory=list)
    lib_podium: str = ""  # pour nom fichier
