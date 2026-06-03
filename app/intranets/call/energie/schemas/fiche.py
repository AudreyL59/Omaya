"""
Schemas Pydantic pour la fiche d'un ticket Call Energie (popup).

Phase 1 = lecture seule, colonne gauche only. Schemas plus simples que
Fibre : pas de Mobile2, pas de bloc anomalie, panier simplifie.
"""

from pydantic import BaseModel


class FicheClient(BaseModel):
    civilite: int
    nom: str
    nom_marital: str
    prenom: str
    nom_format: str
    date_naiss: str
    dep_naiss: int
    type_logement: int
    adresse1: str
    adresse2: str
    cp: str
    ville: str
    email: str
    mobile1: str
    opt_rappel: bool
    opt_partenaire: bool
    client_pro: bool
    client_rs: str
    client_siret: str


class FicheVendeur(BaseModel):
    id_salarie: int
    nom: str
    prenom: str
    gsm: str
    lib_affectation: str


class FicheVente(BaseModel):
    ref_appel: str
    intervention_vendeur: bool
    info_vente: str


class FicheOffreEnergie(BaseModel):
    """Une ligne du panier Energie."""
    id: str
    id_produit: int
    partenaire: str                # "OEN", "PRO", "ENI", "VAL", "STR", ...
    opt_energie_verte_elec: bool
    opt_energie_verte_gaz: bool
    opt_reforestation: bool
    opt_mail: bool
    opt_mandat: bool
    format_numerique: bool
    statut_prod: int
    motif_annulation: str
    num_bs: str
    num_date_saisie: str


class StatutVenteOption(BaseModel):
    id: int
    label: str


class FicheTicketEnergieResponse(BaseModel):
    id_ticket: str
    id_call: str
    id_tk_statut: int
    is_cloture: bool
    is_my_call: bool
    client: FicheClient
    vendeur: FicheVendeur
    vente: FicheVente
    panier: list[FicheOffreEnergie]
    nb_prod_total: int
    nb_prod_valide: int
    nb_prod_annule: int
    btn_valider_actif: bool
    btn_annuler_actif: bool
    statuts_vente: list[StatutVenteOption]


class DocumentInfo(BaseModel):
    url: str = ""
    kind: str = ""


class FicheDocumentsResponse(BaseModel):
    """Documents Energie : CIN + KBIS (si Pro) + Justif."""
    cin: DocumentInfo = DocumentInfo()
    kbis: DocumentInfo = DocumentInfo()
    justif: DocumentInfo = DocumentInfo()
