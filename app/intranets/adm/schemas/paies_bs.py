"""
Schemas Fen_PaiesBS - Module paies (Btn 'Lister les contrats').
"""

from pydantic import BaseModel, Field


class PartenairePeriode(BaseModel):
    """Un partenaire coche dans le bloc CHOISIR LES PARTENAIRES avec ses
    2 periodes : signature 'normale' + hors delai.

    Note : pour SFR, hors_delai_du/au ne sont pas utilises (le WinDev
    masque ces champs pour SFR).
    """
    prefixe: str  # 'ENI', 'SFR', 'IAG', 'OEN', 'PRO', 'STR', 'VAL'
    is_actif: bool = True
    signe_du: str = ""      # YYYY-MM-DD (date_signature debut)
    signe_au: str = ""      # YYYY-MM-DD (date_signature fin)
    hors_delai_du: str = "" # YYYY-MM-DD (signature hors periode, MoisP dans mois cible)
    hors_delai_au: str = ""


class ListerContratsParams(BaseModel):
    """Input Btn Lister les contrats."""
    id_salarie: int
    mois_paiement: str  # YYYY-MM
    partenaires: list[PartenairePeriode] = Field(default_factory=list)
    afficher_part_inactifs: bool = False


class ContratRow(BaseModel):
    """Ligne de TableContratsSignes/Decomm."""
    id_contrat: str
    partenaire: str            # prefixe : ENI/SFR/...
    lib_produit: str = ""
    type_prod: str = ""        # SousFAM (ENI) ou Famille (autres)
    num_bs: str = ""
    date_signature: str = ""   # YYYY-MM-DD
    id_type_etat: int = 0      # 1,2,5,6,3,4,8...
    type_etat: str = ""        # LibType TypeEtatContrat
    id_etat: int = 0
    etat_contrat: str = ""     # Lib_Etat de {part}_etatContrat
    vendeur_nom: str = ""      # Nom + Prenom du salarie
    agence: str = ""           # ExtraitChaine affectation
    equipe: str = ""
    client_nom: str = ""       # Gauche(NOM,3) + '. ' + capitalise(Gauche(PRENOM,3)) + '.'
    client_cp: str = ""
    client_ville: str = ""
    mois_paiement: str = ""    # MoisP ou MoisP_Ra selon partenaire (YYYY-MM-DD)
    nb_points: float = 0.0
    couleur_fond: str = ""     # 'hors_delai' | 'rejet_resil' | ''

    # ENI - visibles seulement si des ENI dans la liste
    car: int = 0
    elec_actif: bool = False
    gaz_actif: bool = False
    puissance: int = 0
    opt_e_verte_elec: bool = False
    opt_e_verte_gaz: bool = False
    opt_mail: bool = False
    opt_reforestation: bool = False
    opt_protection: bool = False
    opt_entretien: bool = False

    # SFR - visibles seulement si des SFR dans la liste
    date_racc_valid: str = ""      # DateRaccActiv
    date_rdv_tech: str = ""
    date_validation: str = ""
    id_etat_sfr: int = 0
    techno: int = 0                # Technologie
    type_vente: int = 0
    portabilite: bool = False
    notation_client: float = 0.0   # Notation * 2
    prise_saisie: bool = False
    pts_porta: float = 0.0         # Portabilite * 0.2
    pts_prises: float = 0.0        # PriseSaisie * 0.2
    pts_notation: float = 0.0      # 0.1 si Notation * 2 >= 8.6


class JourNonProd(BaseModel):
    """Ligne TableJourNonProd (onglet 3)."""
    jour: str                  # YYYY-MM-DD
    eni: bool = False
    fibre: bool = False        # SFR


class ListerContratsResult(BaseModel):
    """Output Btn Lister les contrats."""
    ok: bool
    contrats_signes: list[ContratRow] = Field(default_factory=list)
    contrats_decomm: list[ContratRow] = Field(default_factory=list)
    jours_non_prod: list[JourNonProd] = Field(default_factory=list)
    has_eni: bool = False      # colonnes ENI visibles ?
    has_sfr: bool = False      # colonnes SFR visibles ?
    message: str = ""


# --------------------------------------------------------------------
# Btn 'Valider les paies'
# --------------------------------------------------------------------

class ContratMaj(BaseModel):
    """Contrat en input du bouton Valider (sous-ensemble de ContratRow)."""
    id_contrat: str
    partenaire: str            # ENI/SFR/IAG/OEN/PRO/STR/VAL
    id_type_etat: int
    id_etat: int
    type_etat: str = ""        # LibType (contient 'RESI', 'VALID', 'En ATTENTE Operateur')
    etat_contrat: str = ""
    type_prod: str = ""        # Sous-fam ENI ou Famille (FIBRE pour SFR-Fibre)
    date_signature: str        # YYYY-MM-DD
    mois_paiement: str = ""    # MoisP courant
    nb_points: float = 0.0
    date_racc_valid: str = ""  # SFR uniquement (DateRaccActiv)


class ValiderPaiesParams(BaseModel):
    """Input Btn Valider les paies."""
    id_salarie: int
    mois_paiement: str         # YYYY-MM
    date_racc_limite: str      # YYYY-MM-DD (SFR raccorde eligible si <= cette date)
    simulation: bool = True
    contrats: list[ContratMaj] = Field(default_factory=list)


class ContratMajResult(BaseModel):
    """Contrat apres validation (nouvel etat)."""
    id_contrat: str
    partenaire: str
    id_etat: int                # etatFinal
    id_type_etat: int
    etat_contrat: str           # LibetatFinal
    type_etat: str              # LibTypeEtatFinal
    mois_paiement: str          # DateP (peut etre vide si Rejet/Resil)
    updated: bool               # True si UPDATE SQL applique (non-simu + optMoisPaiement non vide)


class NbCttParJourRow(BaseModel):
    date_ctt: str     # YYYY-MM-DD
    nb_ctt: int
    type_ctt: int     # 1 = ENI/IAG/STR (3 ctts/jour = 1 TR), 2 = SFR-Fibre (1 ctt/jour = 1 TR)


class ValiderPaiesResult(BaseModel):
    """Output Btn Valider les paies."""
    ok: bool
    contrats_maj: list[ContratMajResult] = Field(default_factory=list)
    nb_ctt_par_jour: list[NbCttParJourRow] = Field(default_factory=list)
    nb_tr: int = 0
    nb_updated: int = 0        # combien d'UPDATE SQL appliques
    message: str = ""
