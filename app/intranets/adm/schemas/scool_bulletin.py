"""
Schemas Fen_ScoolBulletin - Fiche bulletin S'Cool.
"""
from pydantic import BaseModel, Field


class StagiaireBulletinCombo(BaseModel):
    """Combo Stagiaire (Code Init reqStagiaire)."""
    id_salarie: str
    nom_prenom: str    # 'NOM Prenom - Lib_Sortie' cf. WinDev


class MentionCombo(BaseModel):
    id_bulletin_mention: str
    lib_mention: str


class BulletinDetail(BaseModel):
    """Detail complet d'un bulletin."""
    id_bulletin: str = ""
    id_formation: str = ""
    id_salarie: str = ""
    du: str = ""
    au: str = ""
    type_bulletin: int = 0        # 1 = Definitif, autre = Intermediaire

    # Chiffres saisis / calcules
    nb_jours_form: int = 0
    nb_jours_pres: int = 0
    objectif_ctt: int = 0
    objectif_decale: int = 0
    objectif_coopt: int = 0

    nb_ctt_hr: int = 0
    nb_cqt_hr: int = 0
    nb_prem_hr: int = 0
    nb_mob_hr: int = 0
    nb_coopt: int = 0

    # Notes calculees (via bareme)
    note_assiduite: float = 0
    note_ctt_hr: float = 0
    note_cqt: float = 0
    note_prem: float = 0
    note_mob: float = 0
    note_coopt: float = 0
    note_obj_decale: float = 0

    # Notes saisies formateurs
    note_app_theo: float = 0
    note_app_pratique: float = 0

    # Partie formateurs
    id_bulletin_mention: str = "0"
    observation: str = ""
    axe_travail: str = ""


class BulletinPayload(BaseModel):
    id_formation: str
    id_salarie: str
    du: str = ""
    au: str = ""
    type_bulletin: int = 0

    nb_jours_form: int = 0
    nb_jours_pres: int = 0
    objectif_ctt: int = 0
    objectif_decale: int = 0
    objectif_coopt: int = 0

    nb_ctt_hr: int = 0
    nb_cqt_hr: int = 0
    nb_prem_hr: int = 0
    nb_mob_hr: int = 0
    nb_coopt: int = 0

    note_assiduite: float = 0
    note_ctt_hr: float = 0
    note_cqt: float = 0
    note_prem: float = 0
    note_mob: float = 0
    note_coopt: float = 0
    note_obj_decale: float = 0

    note_app_theo: float = 0
    note_app_pratique: float = 0

    id_bulletin_mention: str = "0"
    observation: str = ""
    axe_travail: str = ""


class RecupererProdParams(BaseModel):
    """Btn 'Recuperer la prod et les absences'."""
    id_formation: str
    id_salarie: str
    du: str
    au: str


class RecupererProdResult(BaseModel):
    ok: bool = True
    nb_jours_form: int = 0
    nb_jours_pres: int = 0
    res_note_ctt_hr: int = 0       # nb_ctt_hr calcule
    res_note_cqt: int = 0          # nb_cqt_hr
    res_note_prem: int = 0         # nb_prem_hr
    res_note_mob: int = 0          # nb_mob_hr
    res_note_coopt: int = 0        # nb_coopt


class CalculerNotesParams(BaseModel):
    """Input Btn Calculer les notes : le user a saisi objectifs + prod."""
    id_formation: str
    nb_jours_form: int
    nb_absences: int              # = nbJoursForm - res_note_assiduite (cf. WinDev)
    objectif_ctt: int
    objectif_coopt: int
    objectif_decale: int          # 0 ou 1 (non atteint / atteint)
    res_note_ctt_hr: int
    res_note_cqt: int
    res_note_prem: int
    res_note_mob: int
    res_note_coopt: int


class NoteCalculee(BaseModel):
    """Une ligne de la table Notes calculee."""
    type_note: str      # 'NoteAssiduite', 'NoteCttHR', ...
    lib_note: str       # 'Assiduité', 'Objectif Ctt', ...
    palier_calc: float  # taux calcule
    note: float         # note obtenue via bareme


class CalculerNotesResult(BaseModel):
    ok: bool = True
    notes: list[NoteCalculee] = Field(default_factory=list)
