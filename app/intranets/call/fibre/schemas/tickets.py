"""
Schemas Pydantic pour les tickets Call Fibre.

Transposition de la fenetre principale Call SFR de WinDev :
- Table du haut : tickets a traiter (a prendre par un teleconseiller)
- Table du bas : tickets traites aujourd'hui (offres Fibre/Mobile, num BS, ...)
- Compteurs globaux + stats par agence
"""

from pydantic import BaseModel


class TicketEnCours(BaseModel):
    """Ligne du tableau du haut (tickets a traiter).

    Une ligne devient ORANGE quand `appel_en_cours = True` (un opé l'a pris).
    Texte ROUGE si `ticket_diff = True` (ticket marque differe).
    Texte BLEU si `id_tk_statut = 34` (statut special, a confirmer cote metier).
    """
    id: str                       # IDTK_Liste (8 octets) -> string pour l'API
    date_crea: str                # ISO YYYY-MM-DD HH:MM:SS
    nom_client: str               # "M. NOM ép MARITAL Prenom" (deja formate)
    cp: str
    ville: str                    # sans parentheses
    nom_vendeur: str              # "Nom Prenom"
    lib_equipe: str               # "PARENT_Lib => Lib"
    lib_statut: str
    id_tk_statut: int             # pour coloration bleue (34)
    fdv_interne: bool             # PAS VendeurDistrib (= vendeur interne)
    non_prod: bool                # 1er contrat du vendeur (jamais signé un SFR avant)
    # Verrou opé
    appel_en_cours: bool
    ope_appel_nom: str            # vide si aucun verrou
    ticket_diff: bool


class OffrePanier(BaseModel):
    """Une offre dans le panier d'un ticket traite."""
    type: str                     # "FIBRE" / "MOBILE"
    type_vente: int               # 1 = CQ, 2 = CQ VLA, autre = Migration
    statut_prod: int              # 1 ou 3 = valide
    num: str                      # numero BS SFR (vide tant que pas renseigne)
    num_date_saisie: str          # ISO ou ""
    lib_offre: str


class TicketTraite(BaseModel):
    """Ligne du tableau du bas (tickets traites du jour).

    Coloration fond :
    - GRIS si `vendeur_distrib = True`
    - VERT si `premier_contrat = True`
    - ROUGE si `delai_saisie_h >= 1` (delai entre Datecrea et Num_DateSaisie)
    """
    id: str                       # IDTK_Liste
    date_crea: str
    nom_client: str
    cp: str
    ville: str
    nom_vendeur: str
    agence: str                   # affectation du vendeur a la date de creation
    lib_statut: str
    ref_appel: str
    # Compteurs panier
    nb_offres: int                # total
    nb_fibre_valide: int          # FIBRE statutProd in (1, 3)
    nb_mobile_valide: int         # MOBILE statutProd in (1, 3)
    col_offres_fibre: str         # texte avec les offres + CQ/Mig
    # Hints couleur ligne (le frontend tranche)
    vendeur_distrib: bool
    premier_contrat: bool
    delai_depasse: bool
    # DEBUG TEMPORAIRE (a retirer une fois le bug delai_depasse identifie)
    debug_nds: str = ""
    debug_diff_h: int = -1


class StatAgence(BaseModel):
    """Une carte de stats agence (en bas a gauche du tableau de bord)."""
    id_orga: str                  # ID organigramme
    lib_orga: str
    nb_fibre: int
    nb_mobile: int
    gimmick_url: str = ""         # URL du logo (ou data:image/...)


class StatsGlobales(BaseModel):
    """4 compteurs principaux affiches en haut a droite (cartes rondes).

    Issus du tableau du bas (tickets traites du jour).
    """
    paniers_valides: int          # CompteurPanierValid : Fibre+Mobile statutProd in (1,3)
    offres_fibre_thd: int         # CompteurTHD : Fibre avec NUM renseigne
    cq_fibre_valides: int         # CompteurCQvalid : Fibre + TypeVente in (1, 2)
    mobiles_valides: int          # CompteurMobileValid : Mobile statutProd in (1, 3)
    # Detail par agence
    agences_internes: list[StatAgence] = []
    nb_fibre_power: int = 0
    nb_mobile_power: int = 0
    nb_fibre_fox: int = 0
    nb_mobile_fox: int = 0


class TicketsEnCoursResponse(BaseModel):
    """Reponse rapide : tableau du haut + serveur_now + last_modif.

    Charge en premier au mount (~5 queries HFSQL).
    """
    tickets_en_cours: list[TicketEnCours]
    serveur_now: str              # ISO YYYY-MM-DD HH:MM:SS
    last_modif: str = ""          # token pour /tickets/live


class TicketsTraitesResponse(BaseModel):
    """Reponse plus lente : tableau du bas + stats.

    Charge en arriere-plan apres l'affichage des en cours.
    """
    tickets_traites: list[TicketTraite]
    stats: StatsGlobales


class TicketsPageResponse(BaseModel):
    """Reponse globale (full) : en-cours + traites + stats. Compatibilite."""
    tickets_en_cours: list[TicketEnCours]
    tickets_traites: list[TicketTraite]
    stats: StatsGlobales
    serveur_now: str
    last_modif: str = ""


class TicketsLiveResponse(BaseModel):
    """Long polling : ne renvoie QUE les en-cours pour rester rapide."""
    changed: bool
    page: TicketsEnCoursResponse | None = None
    last_modif: str = ""
