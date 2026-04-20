from pydantic import BaseModel


class RecruteurItem(BaseModel):
    id_salarie: str
    nom: str
    prenom: str


class StatutItem(BaseModel):
    id_categorie: int
    lib_categorie: str
    id_cv_statut: int


class StatuerRequest(BaseModel):
    id_categorie: int
    motif: str = ""
    pb_presentation: bool = False
    pb_elocution: bool = False
    pb_motivation: bool = False
    pb_horaires: bool = False


class AgendaRDV(BaseModel):
    id_evenement: str  # string pour préserver la précision (ID > 2^53)
    date_debut: str  # ISO / WinDev format
    date_fin: str
    titre: str
    contenu: str  # historique des statuts
    id_categorie: int
    lib_categorie: str  # libellé statut
    couleur_hex: str  # #RRGGBB depuis AgendaCatégorie
    id_cv_statut: int
    # Candidat (via CvSuivi → cvtheque)
    id_cvtheque: str = "0"
    nom: str = ""
    prenom: str = ""
    gsm: str = ""
    mail: str = ""
    adresse: str = ""
    cp: str = ""
    ville: str = ""
    profil: str = ""
    observ: str = ""
    id_cv_source: int = 0
    id_elem_source: int = 0
    cv_url: str = ""
    statut_modif: bool = False  # True = le RDV n'a pas encore été statué
