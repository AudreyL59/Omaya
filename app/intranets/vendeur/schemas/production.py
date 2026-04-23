"""
Schemas Production — extraction asynchrone de la prod.

Transposition WinDev : Fen_ChoixProd (paramètres) + Fen_suiviProdAsynchrone (résultat).
"""

from typing import Literal
from pydantic import BaseModel, Field


# --- Segment d'affectation (ListeId WinDev) ------------------------

class AffectationSegment(BaseModel):
    """
    Segment temporel d'affectation d'un salarié à un organigramme.
    Équivalent WinDev : ST_SALARIE (ID, OrgaId, OrgaDebut, Orgafin).
    """
    id_salarie: str = "0"        # 0 = segment orga-only (scope Équipe/Réseau HD)
    id_organigramme: str = "0"   # 0 = scope personnel/global
    date_debut: str              # YYYYMMDD
    date_fin: str                # YYYYMMDD


# --- Paramètres d'extraction (payload création job) ----------------

class ProductionJobCreate(BaseModel):
    """
    Params pour créer un nouveau job.
    Transposition Fen_ChoixProd → paramètres passés à Fen_suiviProdAsynchrone.
    """
    mode_date: Literal[1, 2] = 1  # 1 = par période, 2 = par mois de paiement
    date_du: str                  # YYYYMMDD
    date_au: str                  # YYYYMMDD
    partenaires: list[str] = Field(default_factory=list)  # ex: ["SFR","OEN","ENI"]
    id_type_etat: int = 0         # 0 = tous (LIKE '%'), sinon filtre

    # Scope : 1=Vendeur, 2=Équipe, 3=Réseau, 4=Réseau Hors Distrib
    scope: Literal[1, 2, 3, 4]

    # Paramètres additionnels selon le scope
    id_salarie: str = "0"         # si scope=1 (Vendeur)
    prod_groupe: bool = False     # si scope=1 (Prod Groupe avec dérogation)
    id_organigramme: str = "0"    # si scope=2 (Équipe)


# --- Job (lecture) -------------------------------------------------

class ProductionJob(BaseModel):
    """Job d'extraction (lecture depuis la table HFSQL)."""
    id_job: str
    id_salarie_user: str
    date_crea: str
    date_debut_trait: str = ""
    date_fin_trait: str = ""
    statut: str                   # pending / running / done / error
    progression_pct: int = 0
    progression_msg: str = ""
    nb_lignes: int = 0
    duree_s: int = 0
    path_resultat: str = ""
    message_erreur: str = ""
    titre: str
    params: ProductionJobCreate | None = None  # extrait du ParamsJSON


# --- Lignes contrat (résultat paginé) ------------------------------

class ContratRow(BaseModel):
    """
    Ligne d'un contrat extrait.
    Colonnes communes à tous partenaires + colonnes spécifiques en optionnel.
    """
    # Identité
    id_contrat: str
    partenaire: str                # PréfixeBDD (SFR, OEN, ENI, ...)
    num_bs: str = ""

    # Dates
    date_signature: str = ""       # YYYY-MM-DD
    date_saisie: str = ""
    mois_p: str = ""
    heure_sign: str = ""           # si dispo

    # Produit / état
    lib_produit: str = ""
    type_prod: str = ""            # Famille (ou SousFAM pour ENI/OEN)
    id_type_etat: int = 0
    lib_type_etat: str = ""        # de TypeEtatContrat
    couleur_etat: str = ""         # hex #RRGGBB
    lib_etat: str = ""             # {PREFIX}_etatContrat.Lib_Etat (interne)
    lib_etat_vend: str = ""        # {PREFIX}_etatContrat.Lib_EtatVend

    # Vendeur + affectation historique
    id_salarie: str = "0"
    vendeur_nom: str = ""
    vendeur_prenom: str = ""
    agence: str = ""               # orga parent (affectation à la date signature)
    equipe: str = ""               # orga
    poste: str = ""
    en_activite: bool = True
    date_sortie: str = ""

    # Client
    id_client: str = "0"
    client_nom: str = ""
    client_prenom: str = ""
    client_adresse1: str = ""
    client_adresse2: str = ""
    client_cp: str = ""
    client_ville: str = ""
    client_mail: str = ""
    client_mobile: str = ""
    client_age: int = 0

    # Valeurs
    nb_points: int = 0
    notation: float = 0.0
    notation_info: str = ""

    # Infos texte
    info_interne: str = ""
    info_partagee: str = ""
    code_enr: str = ""             # pas pour SFR

    # Flags comptables
    nb_ctt_brut: int = 0
    nb_ctt_hors_rejet: int = 0
    nb_ctt_paye: int = 0


class ContratPage(BaseModel):
    """Réponse paginée pour la table des contrats."""
    total: int
    page: int
    page_size: int
    rows: list[ContratRow]


# --- Référentiels ---------------------------------------------------

class PartenaireItem(BaseModel):
    lib: str                       # Lib_Partenaire
    prefix: str                    # PréfixeBDD
    is_actif: bool = True
    couleur_hex: str = ""          # depuis Couleur_R/V/B


class TypeEtatItem(BaseModel):
    id: int                        # IDTypeEtat
    lib: str                       # LibType
    couleur_hex: str = ""


# --- Stats (onglets dashboard) -------------------------------------

class RepartPartenaireRow(BaseModel):
    """Une ligne dans l'onglet Tab Stat : répartition par partenaire."""
    partenaire: str
    couleur_hex: str = ""
    brut: int = 0
    temporaire: int = 0
    envoye: int = 0
    rejet: int = 0
    resil: int = 0
    payé: int = 0
    decomm: int = 0
    racc_activ_ko: int = 0
    racc_active: int = 0


class VendeurStatRow(BaseModel):
    """Une ligne dans l'onglet Vendeurs : 1 par vendeur."""
    id_salarie: str
    nom: str
    prenom: str
    agence: str = ""
    equipe: str = ""
    poste: str = ""
    en_activite: bool = True
    date_sortie: str = ""
    nb_contrats: int = 0
    nb_paye: int = 0
    nb_hors_rejet: int = 0
    nb_points: int = 0
    # Répartition par partenaire (clé = prefix, valeur = nb contrats)
    par_partenaire: dict[str, int] = {}


class JobStats(BaseModel):
    """Stats précalculées d'un job (stockées dans meta.json)."""
    total_contrats: int = 0
    total_paye: int = 0
    total_points: int = 0
    repart_partenaires: list[RepartPartenaireRow] = []
    vendeurs: list[VendeurStatRow] = []
