"""
Schemas Fen_ScoolFormation - Gestion des formations S'Cool.
"""
from pydantic import BaseModel, Field


class FormationRow(BaseModel):
    """Ligne de la table Liste_FormationScool."""
    id_formation: str = ""
    intitule: str = ""
    date_debut: str = ""    # YYYY-MM-DD
    date_fin: str = ""
    ville_formation: str = ""
    type_produit: str = ""
    categorie: str = ""
    formateur1_nom: str = ""
    formateur2_nom: str = ""
    nb_heure_salle: int = 0
    nb_heure_terrain: int = 0
    heure_jour_salle: int = 0
    heure_jour_terrain: int = 0
    duree: int = 0
    formation_active: bool = True
    formation_cloturee: bool = False


class FormationDetail(FormationRow):
    """Detail complet d'une formation."""
    dest_promo: str = ""
    formateur3_nom: str = ""
    formateur4_nom: str = ""
    formateur5_nom: str = ""
    formateur1_id: str = ""
    formateur2_id: str = ""
    formateur3_id: str = ""
    formateur4_id: str = ""
    formateur5_id: str = ""


class FormationPayload(BaseModel):
    """Input creation / update."""
    intitule: str
    date_debut: str = ""
    date_fin: str = ""
    ville_formation: str = ""
    type_produit: str = ""
    categorie: str = ""
    nb_heure_salle: int = 0
    nb_heure_terrain: int = 0
    heure_jour_salle: int = 8
    heure_jour_terrain: int = 8
    duree: int = 0
    dest_promo: str = ""
    formateur1_id: str = ""
    formateur2_id: str = ""
    formateur3_id: str = ""
    formateur4_id: str = ""
    formateur5_id: str = ""
    formation_active: bool = True
    formation_cloturee: bool = False
    # Ajout Fen_ScoolFormation_Ajout : si != "0", clone le programme du modele
    id_modele_form: str = ""


class FormateurCombo(BaseModel):
    """Combo formateur (Fen_ScoolFormation_Ajout)."""
    id_formateur: str
    lib: str          # 'NOM Prenom (N)'
    niveau: str = ""
    is_actif: bool = True


class ListeFormationsParams(BaseModel):
    afficher_depuis_le: str = ""
    uniquement_actives: bool = True


class ModeleFormationRow(BaseModel):
    """Modele de formation (pgt_form_modele)."""
    id_modele: str = ""
    intitule: str = ""
    categorie: str = ""
    nb_heure_salle: int = 0
    nb_heure_terrain: int = 0
    heure_jour_salle: int = 0
    heure_jour_terrain: int = 0


class ModeleFormationCombo(BaseModel):
    """Combo 'Utiliser ce modele' de Fen_ScoolFormation_Ajout.
    Format 'Categorie - Intitule' (cf. WinDev reqListeModele).
    """
    id_modele: str
    nom_formation: str    # 'Categorie - Intitule'
