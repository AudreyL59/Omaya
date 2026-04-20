from pydantic import BaseModel


class CvStatutItem(BaseModel):
    id_cv_statut: int
    lib_statut: str


class CvSourceItem(BaseModel):
    id_cv_source: int
    lib_source: str


class CvAnnonceurItem(BaseModel):
    id_cv_annonceur: int
    lib_annonceur: str


class CommuneCPItem(BaseModel):
    """Code postal + ville avec ses coordonnées GPS."""
    cp: str
    ville: str
    id_communes_france: str  # string pour précision
    latitude: float
    longitude: float


class CvSearchRequest(BaseModel):
    # Mode de recherche : "cp", "tel", "nom"
    mode: str

    # Par CP
    latitude: float | None = None
    longitude: float | None = None
    rayon_km: int = 30
    date_debut: str = ""  # YYYYMMDD
    date_fin: str = ""
    age_min: int = 0
    age_max: int = 100
    id_cv_source: int = 0  # 0 = tous, 1 = Cooptation, 2 = Annonceurs
    id_coopteur: str = ""  # si source = Cooptation (ID salarie)
    id_annonceur: int = 0  # si source = Annonceurs (IDCvAnnonceur)
    profil: int = 0  # 0 = tous, 1 = ENI, 2 = FIBRE, 3 = Les 2
    id_cv_statut: int = 0  # 0 = tous

    # Par Tél
    tel: str = ""

    # Par Nom
    nom: str = ""
    prenom: str = ""


class CvSuiviItem(BaseModel):
    id_cv_suivi: str
    datecrea: str
    op_crea: int
    op_crea_nom: str
    id_cv_statut: int
    statut_lib: str
    type_elem: str
    id_elem: str
    observation: str


class CvFiche(BaseModel):
    id_cvtheque: str
    origine: int = 0
    nom: str = ""
    prenom: str = ""
    pays: str = ""
    adresse: str = ""
    cp: str = ""
    ville: str = ""
    id_communes_france: int = 0
    date_naissance: str = ""
    age: int = 0
    permis_b: bool = False
    vehicule: bool = False
    mail: str = ""
    gsm: str = ""
    fic_cv: str = ""
    cv_url: str = ""
    id_cv_poste: int = 0
    id_cv_source: int = 0
    id_elem_source: int = 0
    nom_coopteur: str = ""  # si source = Cooptation
    id_ste: int = 0
    observation: str = ""
    id_cv_statut: int = 0  # dernier statut (depuis CvSuivi)
    traite_en_cours: bool = False
    op_traite: int = 0


class CvFicheResponse(BaseModel):
    fiche: CvFiche
    suivi: list[CvSuiviItem]


class TraitementRequest(BaseModel):
    is_traite: bool  # True = verrouille (je traite), False = libère


class ObservationAddRequest(BaseModel):
    observation: str


class CvSaveRequest(BaseModel):
    nom: str = ""
    prenom: str = ""
    pays: str = ""
    adresse: str = ""
    id_communes_france: int = 0
    date_naissance: str = ""
    permis_b: bool = False
    vehicule: bool = False
    mail: str = ""
    gsm: str = ""
    id_cv_poste: int = 0
    id_cv_source: int = 0
    id_elem_source: int = 0
    id_ste: int = 0
    observation: str = ""
    saisir_obser: str = ""  # à concaténer à observation avec timestamp
    id_cv_statut: int = 0  # nouveau statut (si != de l'ancien, ajout CvSuivi)
    confirm_statut_6: bool = False  # confirmation requise si statut=6


class CvResultItem(BaseModel):
    id_cvtheque: str
    identite: str
    op_traitement: str = ""
    date_saisie: str = ""
    statut_actuel: int = 0
    statut_actuel_lib: str = ""
    statut_periode: int = 0
    statut_periode_lib: str = ""
    source: int = 0
    source_lib: str = ""
    age: int = 0
    tel: str = ""
    localisation: str = ""
    detail_source: str = ""
    agence: str = ""
    equipe: str = ""
    commentaire: str = ""
