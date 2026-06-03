"""
Schemas Pydantic pour les tickets Call Energie.

Transposition de la fenetre Call ENI de WinDev :
- Table du haut : tickets a traiter (a prendre par un teleconseiller)
- Table du bas : tickets traites du jour

Pas de stats Fibre/Mobile/CQ/THD ici (specifiques a Call Fibre).
Le dashboard du haut sera adapte separement pour Energie.
"""

from pydantic import BaseModel


class TicketEnCours(BaseModel):
    """Ligne du tableau du haut (tickets a traiter).

    Une ligne devient ORANGE quand `appel_en_cours = True` (un ope l'a pris).
    Texte BLEU si `id_tk_statut = 34`.
    Texte ROUGE si `ticket_diff = True`.
    """
    id: str
    date_crea: str
    nom_client: str
    cp: str
    ville: str
    nom_vendeur: str
    lib_equipe: str
    lib_statut: str
    id_tk_statut: int
    fdv_interne: bool
    non_prod: bool
    appel_en_cours: bool
    ope_appel_nom: str
    ticket_diff: bool


class TicketTraite(BaseModel):
    """Ligne du tableau du bas (tickets traites du jour).

    Coloration fond :
    - ROUGE si delai_depasse (Num_DateSaisie >= Datecrea + 1h)
    - GRIS si vendeur_distrib
    - VERT si premier_contrat
    """
    id: str
    date_crea: str
    nom_client: str
    cp: str
    ville: str
    nom_vendeur: str
    agence: str
    lib_statut: str
    ref_appel: str
    nb_offres: int                # nb d'offres BRUT (toutes statuts confondus)
    nb_offres_valides: int        # offres avec statut_prod in (1, 3)
    nb_num_bs: int                # nb d'offres avec NumBS renseigne
    # Ventilation BRUT par PrefixeBDD du Partenaire ("OEN" -> 2, "PRO" -> 1, ...)
    nb_brut_par_partenaire: dict[str, int] = {}
    vendeur_distrib: bool
    premier_contrat: bool
    delai_depasse: bool


class StatPartenaire(BaseModel):
    """Un partenaire dans le dashboard du haut (cercle Offres + cercle Clients)."""
    id: str
    prefix: str           # PréfixeBDD ("OEN", "PRO", "ENI", ...)
    lib: str              # Lib_Partenaire (nom complet, fallback si pas de logo)
    logo_url: str = ""    # data:image/...;base64,... (memo LOGO de Partenaire)
    nb_offres: int        # offres validees (statut_prod in 1, 3)
    nb_clients: int       # nb tickets distincts ayant au moins 1 offre validee


class StatPartenaireAgence(BaseModel):
    """Compteur Offres/Clients par Partenaire au sein d'une agence."""
    prefix: str
    lib: str
    nb_offres: int
    nb_clients: int


class StatAgenceEnergie(BaseModel):
    """Une agence dans le detail depliable (compteurs par Partenaire)."""
    lib_agence: str
    par_partenaire: list[StatPartenaireAgence] = []


class StatsEnergie(BaseModel):
    """Stats globales du dashboard Call Energie."""
    tickets_valides: int          # nb tickets avec au moins 1 offre validee
    partenaires: list[StatPartenaire] = []
    agences: list[StatAgenceEnergie] = []


class TicketsEnCoursResponse(BaseModel):
    tickets_en_cours: list[TicketEnCours]
    serveur_now: str
    last_modif: str = ""


class TicketsTraitesResponse(BaseModel):
    tickets_traites: list[TicketTraite]
    stats: StatsEnergie


class TicketsPageResponse(BaseModel):
    tickets_en_cours: list[TicketEnCours]
    tickets_traites: list[TicketTraite]
    stats: StatsEnergie
    serveur_now: str
    last_modif: str = ""


class TicketsLiveResponse(BaseModel):
    changed: bool
    page: TicketsEnCoursResponse | None = None
    last_modif: str = ""
