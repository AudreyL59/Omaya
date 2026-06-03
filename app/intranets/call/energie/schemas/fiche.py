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
    partenaire: str                # PrefixeBDD : "OEN", "PRO", "ENI", "VAL", "STR", ...
    partenaire_lib: str = ""       # Lib_Partenaire (nom complet)
    # Options ENERGIE generales
    opt_energie_verte_elec: bool
    opt_energie_verte_gaz: bool
    opt_reforestation: bool
    opt_mail: bool
    opt_mandat: bool               # ENI : checkbox "Mandat"
    format_numerique: bool         # PRO : checkbox "Format numérique"
    # Options VAL (Valoris)
    opt_accept_com_parte: bool
    opt_consent_consult_distri: bool
    # Autres options
    opt_e_communication: bool
    opt_e_facture: bool
    opt_optin_commercial: bool
    # Etat commercial
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
    # Credentials portail Ohm Energie (calcules selon le vendeur)
    ohm_login: str = ""
    ohm_mdp: str = ""


class DocumentInfo(BaseModel):
    url: str = ""
    kind: str = ""


class FicheDocumentsResponse(BaseModel):
    """Documents Energie : CIN + KBIS (si Pro).

    Note : la fiche de clarification (Justif OEN) est detectee separement
    via /tickets/panier/{id_panier}/clarification car liee a la ligne du
    panier, pas au ticket.
    """
    cin: DocumentInfo = DocumentInfo()
    kbis: DocumentInfo = DocumentInfo()
    justif: DocumentInfo = DocumentInfo()


# --- Save (Phase 2) -------------------------------------------------------

class SaveClientPayload(BaseModel):
    civilite: int = 0
    nom: str = ""
    nom_marital: str = ""
    prenom: str = ""
    date_naiss: str = ""
    dep_naiss: int = 0
    type_logement: int = 0
    adresse1: str = ""
    adresse2: str = ""
    cp: str = ""
    ville: str = ""
    email: str = ""


class SaveVentePayload(BaseModel):
    ref_appel: str = ""
    intervention_vendeur: bool = False
    info_vente: str = ""


class SaveVenteRequest(BaseModel):
    """Body POST /tickets/{id}/save-vente : infos client + vente."""
    client: SaveClientPayload
    vente: SaveVentePayload


class SaveOffreRequest(BaseModel):
    """Body POST /tickets/panier/{id_panier}/save-offre.

    Tous les champs sont optionnels (Optional via valeurs par defaut). On
    n'update que ceux qui sont fournis dans le payload.
    """
    statut_prod: int | None = None
    num_bs: str | None = None
    opt_mandat: bool | None = None
    format_numerique: bool | None = None
    opt_accept_com_parte: bool | None = None
    opt_consent_consult_distri: bool | None = None
    opt_e_communication: bool | None = None
    opt_e_facture: bool | None = None
    opt_optin_commercial: bool | None = None
    opt_energie_verte_elec: bool | None = None
    opt_energie_verte_gaz: bool | None = None
    opt_reforestation: bool | None = None
    opt_mail: bool | None = None


class SaveResponse(BaseModel):
    ok: bool = True
