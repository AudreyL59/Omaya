"""
Schemas Pydantic pour la fiche d'un ticket Call Fibre (popup).

Transposition de PAGE_TicketFicheFibre. Phase 1 = lecture seule.
"""

from pydantic import BaseModel


class FicheClient(BaseModel):
    civilite: int                 # 1=M, 2=Mme, 3=Mlle (a confirmer)
    nom: str
    nom_marital: str
    prenom: str
    nom_format: str               # "M. NOM ép MARITAL Prenom" pre-formate
    date_naiss: str               # YYYY-MM-DD
    dep_naiss: int
    type_logement: int            # 1=Maison, 2=Appartement
    adresse1: str
    adresse2: str
    cp: str
    ville: str
    email: str
    mobile1: str                  # eventuellement masque "0612345xx"
    mobile2: str
    opt_rappel: bool              # consentement "rappele immediatement"
    opt_partenaire: bool          # consentement "transmission aux partenaires"
    client_pro: bool
    client_rs: str                # raison sociale (si pro)
    client_siret: str             # SIRET (si pro)


class FicheVendeur(BaseModel):
    id_salarie: int
    nom: str
    prenom: str
    gsm: str                      # eventuellement masque
    lib_affectation: str          # "Plateau/Staff => Service IT" (a calculer)


class FicheVente(BaseModel):
    ref_appel: str
    intervention_vendeur: bool
    mobile_propose_vendeur: bool
    info_vente: str


class FicheAnomalie(BaseModel):
    active: bool                  # bloc visible si True
    id_type: int                  # IDTK_CallSFR_TypeAnomalie
    info_cplt: str


class FicheOffre(BaseModel):
    """Une ligne du panier de la fiche."""
    id: str                       # IDTK_CallSFR_Panier
    id_offre: str                 # IDOffres_SFR (du catalogue)
    lib_offre: str
    type: str                     # "FIBRE" / "MOBILE"
    opt_tv: bool
    portabilite: bool
    type_vente: int               # 1=CQ, 2=CQ VLA, autres=Migration
    statut_prod: int              # 0=ND, 1=Validé, 2=Annulé, 3=Num BS, 4=Validé-Différé
    motif_annulation: str
    num_portabilite: str
    num_rio: str
    num_prise_optique: str
    opt_choisies: str


class StatutVenteOption(BaseModel):
    id: int
    label: str


class FicheTicketFibreResponse(BaseModel):
    """Reponse complete de GET /tickets/{id}/fiche."""
    id_ticket: str
    id_call_sfr: str
    id_tk_statut: int
    is_cloture: bool
    is_statut_34: bool            # afficher libelle special
    is_my_call: bool              # mobile demasque ou pas
    client: FicheClient
    vendeur: FicheVendeur
    vente: FicheVente
    anomalie: FicheAnomalie
    panier: list[FicheOffre]
    nb_prod_total: int
    nb_prod_valide: int
    nb_prod_annule: int
    btn_valider_actif: bool
    btn_annuler_actif: bool
    statuts_vente: list[StatutVenteOption]


class FicheTestEligibiliteResponse(BaseModel):
    """Image TestEligibilite (data URL) pour une ligne du panier (FIBRE only)."""
    test_eligibilite: str         # "data:image/jpeg;base64,..." ou ""


class DocumentInfo(BaseModel):
    """Reference vers un document hebergé sur rest.omaya.fr/DocOmaya/."""
    url: str = ""                 # URL absolue, vide si pas trouve
    kind: str = ""                # "pdf" / "image" / ""


class FicheDocumentsResponse(BaseModel):
    """Documents disponibles pour un ticket (CIN + KBIS)."""
    cin: DocumentInfo = DocumentInfo()
    kbis: DocumentInfo = DocumentInfo()


class LettreResilResponse(BaseModel):
    """Lettre de resiliation pour une ligne de panier (FIBRE + pas portabilite)."""
    url: str = ""
    kind: str = ""


class SaveClientPayload(BaseModel):
    """Champs client editables (cf. ColonneGauche de la fiche)."""
    civilite: int = 0
    nom: str = ""
    nom_marital: str = ""
    prenom: str = ""
    date_naiss: str = ""           # ISO YYYY-MM-DD ou vide
    dep_naiss: int = 0
    type_logement: int = 0         # 1=Maison, 2=Appart
    adresse1: str = ""
    adresse2: str = ""
    cp: str = ""
    ville: str = ""
    email: str = ""


class SaveVentePayload(BaseModel):
    """Champs vente (cf. ColonneDroite + Ref Appel)."""
    ref_appel: str = ""
    intervention_vendeur: bool = False
    mobile_propose_vendeur: bool = False
    info_vente: str = ""


class SaveAnomaliePayload(BaseModel):
    """Champs anomalie mobile (bloc conditionnel)."""
    active: bool = False
    id_type: int = 0
    info_cplt: str = ""


class SaveVenteRequest(BaseModel):
    """Body de POST /tickets/{id}/save-vente."""
    client: SaveClientPayload
    vente: SaveVentePayload
    anomalie: SaveAnomaliePayload


class SaveOffreRequest(BaseModel):
    """Body de POST /tickets/panier/{id_panier}/save-offre."""
    portabilite: bool = False
    num_portabilite: str = ""
    num_rio: str = ""
    num_prise_optique: str = ""
    opt_choisies: str = ""
    type_vente: int = 0
    statut_prod: int = 0


class SaveResponse(BaseModel):
    ok: bool = True


# --- Phase 3 ---------------------------------------------------------------

class VerrouPeek(BaseModel):
    appel_en_cours: bool = False
    ope_appel_id: int = 0
    ope_appel_nom: str = ""
    date_h_appel: str = ""
    duree_minutes: int = 0
    duree_secondes: int = 0


class VerrouResponse(BaseModel):
    """Reponse a POST /tickets/{id}/verrou/prendre.

    - ok=True : verrou pose (eventuellement avec SMS resultat)
    - needs_confirm=True : un autre ope a le verrou -> frontend doit confirmer
      avant de renvoyer la requete avec force=True
    """
    ok: bool = False
    needs_confirm: bool = False
    peek: VerrouPeek | None = None
    sms: str = ""


class PrendreAppelRequest(BaseModel):
    force: bool = False


class AnnulLignePanierRequest(BaseModel):
    motifs: list[str] = []
    precisions: str = ""


class ActionVenteRequest(BaseModel):
    """Body pour annuler-vente / valider-vente.

    Reprend les memes champs que SaveVenteRequest (le code WinDev save les
    infos vente dans le meme call). Pour renvoyer-complement, le body
    peut etre vide (pas de save).
    """
    client: SaveClientPayload | None = None
    vente: SaveVentePayload | None = None
    anomalie: SaveAnomaliePayload | None = None


class ActionVenteResponse(BaseModel):
    ok: bool = True
    sms: str = ""
