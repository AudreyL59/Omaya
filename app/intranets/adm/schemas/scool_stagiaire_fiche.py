"""
Schemas Fen_ScoolStagiaire_Fiche - Fiche detaillee d'un stagiaire.

Cf. WinDev Fen_ScoolStagiaire_Fiche(IDformation, idStagiaire, TypeProd).
3 onglets :
  - Declaratif de presence
  - Production ENI Jour/Jour (si TypeProd = 'ENI')
  - Production SFR Jour/Jour (si TypeProd = 'SFR')
"""
from pydantic import BaseModel


# --------------------------------------------------------------------
# Onglet Declaratif de presence
# --------------------------------------------------------------------

class PresenceRow(BaseModel):
    """Ligne Table_Presence.
    Presence :  1 = present, 0 = absent journee, -1 = demi-journee.
    TypeJournee : 1 = salle, 2 = terrain, 7 = ? (WinDev valeur par defaut).
    Periode : 1 = matin, 2 = aprem, 3 = journee.
    """
    date: str = ""            # YYYY-MM-DD
    type_journee: int = 1
    presence: int = 1
    id_motif: int = 0
    motif_absence: str = ""   # libelle
    periode: int = 0
    emarg_matin: bool = False   # true si signature presente
    emarg_aprem: bool = False


class RecapPresence(BaseModel):
    nb_jours_salle: float = 0.0
    nb_jours_terrain: float = 0.0
    total_jours: float = 0.0


# --------------------------------------------------------------------
# Onglet Production ENI ou SFR
# --------------------------------------------------------------------

class ProdEniRow(BaseModel):
    """Ligne Table_Prod (onglet ENI)."""
    date: str = ""
    num_sem: int = 0
    sem_prod: str = ""            # 'Semaine 1'
    # Programme
    salle: float = 0.0
    terrain: float = 0.0
    duree: float = 0.0
    # Assiduite
    absent: float = 0.0
    present: float = 0.0
    # ObjBS
    objectif_bs_jour: float = 0.0
    # Total & ADF
    total_ctt: int = 0
    total_adf: int = 0
    # ENI
    eni_gaz: int = 0
    eni_dual: int = 0
    eni_elec: int = 0
    eni_gaz_vert: int = 0
    eni_elec_verte: int = 0
    eni_mail: int = 0
    # Presse / ASSU / Coopt
    presse: int = 0
    assu: int = 0
    cooptation: int = 0
    # Ratios (calcules)
    objectif: float = 0.0        # totalCtt / obj
    pourcent_dual: float = 0.0
    pourcent_elec: float = 0.0
    pourcent_mail: float = 0.0
    pourcent_gv: float = 0.0
    pourcent_ev: float = 0.0
    pourcent_adf: float = 0.0
    pourcent_presse: float = 0.0


class ProdSfrRow(BaseModel):
    """Ligne Table_ProdSFR."""
    date: str = ""
    num_sem: int = 0
    sem_prod: str = ""
    salle: float = 0.0
    terrain: float = 0.0
    duree: float = 0.0
    absent: float = 0.0
    present: float = 0.0
    objectif_bs_jour: float = 0.0
    total_ctt: int = 0
    total_adf: int = 0
    power8: int = 0
    premium: int = 0
    fibre8: int = 0
    power: int = 0
    migration: int = 0
    mobile: int = 0
    assu: int = 0
    presse: int = 0
    cooptation: int = 0
    objectif: float = 0.0
    pourcent_adf: float = 0.0
    pourcent_presse: float = 0.0


# --------------------------------------------------------------------
# Fiche stagiaire complete
# --------------------------------------------------------------------

class ScoolStagiaireFiche(BaseModel):
    """Reponse complete de la fiche stagiaire."""
    # Header
    id_formation: str = ""
    id_salarie: str = ""
    nom_prenom: str = ""
    lib_formation: str = ""
    date_debut: str = ""
    date_fin: str = ""
    niveau_form: str = ""
    heure_jour_salle: float = 8.0
    heure_jour_terrain: float = 8.0
    type_prod: str = ""            # 'ENI' | 'SFR'
    axe_travail_1: str = ""
    axe_travail_2: str = ""
    livrable: bool = False
    # Onglet 1
    presence: list[PresenceRow] = []
    recap_presence: RecapPresence = RecapPresence()
    # Onglet 2 (ENI)
    prod_eni: list[ProdEniRow] = []
    # Onglet 3 (SFR)
    prod_sfr: list[ProdSfrRow] = []
    # Totaux formation (bas de tableau)
    tot_salle: float = 0.0
    tot_terrain: float = 0.0
    tot_duree: float = 0.0
    tot_absent: float = 0.0
    tot_present: float = 0.0
    tot_obj_bs: float = 0.0
    tot_ctt: int = 0
    tot_adf: int = 0
    tot_presse: int = 0
    tot_assu: int = 0
    tot_coopt: int = 0


# --------------------------------------------------------------------
# Payloads
# --------------------------------------------------------------------

class StagiaireHeaderPayload(BaseModel):
    """Btn Enregistrer : Formation_salarie.DateDebut/DateFin + Livrable."""
    id_formation: str
    id_salarie: str
    date_debut: str = ""
    date_fin: str = ""
    livrable: bool = False
    axe_travail_1: str = ""
    axe_travail_2: str = ""


class AjoutLigneProdPayload(BaseModel):
    """Btn 'Ajouter une ligne au tableau' onglet Production ENI/SFR :
    saisit une date -> cree une decl presence par defaut (jour salle,
    present)."""
    id_formation: str
    id_salarie: str
    date: str


class MotifAbsenceCombo(BaseModel):
    id_type_absence: int
    lib_absence: str
