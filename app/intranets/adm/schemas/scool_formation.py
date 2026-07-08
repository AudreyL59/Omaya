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


# --------------------------------------------------------------------
# Programme de formation (onglet 1)
# --------------------------------------------------------------------

class ProgrammeRow(BaseModel):
    """Ligne de Table_ProgrammeFormation (pgt_formation_programme)."""
    id_programme: str = ""
    id_formation: str = ""
    num_semaine: int = 0
    date: str = ""       # YYYY-MM-DD
    salle: int = 0
    terrain: int = 0
    duree: int = 0
    horaires: str = ""
    objectif: int = 0


class ProgrammePayload(BaseModel):
    date: str
    num_semaine: int = 0
    salle: int = 0
    terrain: int = 0
    duree: int = 0
    horaires: str = ""
    objectif: int = 0


class ConvertirModelePayload(BaseModel):
    """Cf. WinDev Btn Convertir en modele : reprend l'intitule, categorie,
    heures + programme courant pour creer un modele.
    """
    intitule: str
    categorie: str = ""
    nb_heure_salle: int = 0
    nb_heure_terrain: int = 0
    heure_jour_salle: int = 0
    heure_jour_terrain: int = 0


# --------------------------------------------------------------------
# FI_AnalysePromoScool - analyse d'une formation
# --------------------------------------------------------------------

class AnalysePromoParams(BaseModel):
    id_formations: list[str]


class EffectifRow(BaseModel):
    """Ligne TableEffectif : evolution par etape (Demarrage/Bilan N/Livraison)."""
    periode: str = ""
    date: str = ""
    nb_vend: int = 0
    nb_vend_prod: int = 0
    nb_ctt_brut: int = 0        # nb Fibre brut
    nb_ctt_hr: int = 0          # nb Fibre HR
    nb_cqt: int = 0             # nb CQT Fibre Brut
    nb_cqt_hr: int = 0          # nb CQT HR
    nb_mig: int = 0             # nb Mig Fibre Brut
    nb_mig_hr: int = 0
    nb_mob_brut: int = 0
    nb_mob_hr: int = 0


class StagiaireRow(BaseModel):
    """Ligne Table_ReqStagaireFormation1."""
    id_stagiaire: str = ""
    nom: str = ""
    prenom: str = ""
    du: str = ""
    au: str = ""
    en_activite: bool = True
    type_sortie: str = ""
    livrable: bool = False
    nb_fibre_brut: int = 0
    nb_fibre_hr: int = 0
    nb_cqt_brut: int = 0
    nb_cqt_hr: int = 0
    nb_mig_brut: int = 0
    nb_mig_hr: int = 0
    nb_mob_brut: int = 0
    nb_mob_hr: int = 0


# --------------------------------------------------------------------
# Onglet Evenement
# --------------------------------------------------------------------

class EvenementRow(BaseModel):
    id_evenement: str = ""
    date: str = ""
    id_salarie: str = ""
    nom_prenom: str = ""
    intitule: str = ""


class EvenementPayload(BaseModel):
    date: str
    id_salarie: str
    intitule: str


# --------------------------------------------------------------------
# Onglet Eleves (stagiaires enrichis)
# --------------------------------------------------------------------

class EleveRow(BaseModel):
    id_salarie: str = ""
    nom: str = ""
    prenom: str = ""
    du: str = ""
    au: str = ""
    en_activite: bool = True
    type_sortie: str = ""
    livrable: bool = False
    nb_fibre_brut: int = 0
    nb_fibre_hr: int = 0
    nb_cqt_brut: int = 0
    nb_cqt_hr: int = 0


class EleveAjoutPayload(BaseModel):
    id_salarie: str


# --------------------------------------------------------------------
# Onglet Session de recrut
# --------------------------------------------------------------------

class SessionRecrutRow(BaseModel):
    id_formation_prev_recrut: str = ""
    id_prevision_recrut: str = ""
    idorganigramme: str = ""
    lib_orga: str = ""
    date_debut: str = ""
    date_fin: str = ""
    date_session: str = ""
    lib_lieu: str = ""


class SessionRecrutPayload(BaseModel):
    id_prevision_recrut: str


# --------------------------------------------------------------------
# Onglet Bulletins
# --------------------------------------------------------------------

class BulletinRow(BaseModel):
    id_bulletin: str = ""
    id_salarie: str = ""
    stagiaire: str = ""
    du: str = ""
    au: str = ""
    type_bulletin: int = 0     # 1 = final, autres = intermediaire


# --------------------------------------------------------------------
# Onglet Bareme Notes
# --------------------------------------------------------------------

class BaremeNoteRow(BaseModel):
    id_bareme: str = ""
    type_note: str = ""
    palier: float = 0.0
    note: float = 0.0
    sens_recherche: str = "ASC"     # 'ASC' = >= palier, 'DESC' = <= palier


class BaremeNotePayload(BaseModel):
    type_note: str
    palier: float = 0.0
    note: float = 0.0
    sens_recherche: str = "ASC"


class AnalyseFormationResult(BaseModel):
    id_formation: str
    intitule: str = ""
    ville_formation: str = ""
    du: str = ""
    au: str = ""
    formation_cloturee: bool = False
    # Compteurs recrutement
    presents: int = 0
    retenus: int = 0
    jo: int = 0
    # Bulletins
    intermediaires: int = 0
    finaux: int = 0
    # Jours terrain
    nb_jours_terrain: int = 0
    # Livraison/CQT
    total_prod: int = 0
    total_livrable: int = 0
    total_cqt: int = 0
    obj_cqt: int = 0
    # Tables
    effectif: list[EffectifRow] = Field(default_factory=list)
    stagiaires: list[StagiaireRow] = Field(default_factory=list)
