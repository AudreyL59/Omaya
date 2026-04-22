from pydantic import BaseModel


class CvSaisiAnnonceurRow(BaseModel):
    id_cvtheque: str
    id_annonceur: str
    lib_annonceur: str = ""
    ope_id: str
    ope_nom: str = ""
    date_traitement: str = ""    # Date_Saisie si dans periode sinon Date_Reac
    est_reactivation: bool = False
    nom_prenom: str = ""
    commune: str = ""
    tel: str = ""
    statut_actuel: str = ""
    id_statut_actuel: int = 0    # IdCvStatut : >= 100 = RDV-like, sinon statut simple
    statut_rdv: str = ""
    fiche_reac: bool = False
    dpae: bool = False
    # Flags calcules cote serveur pour breakdown frontend
    cv_traite: bool = False
    has_rdv: bool = False
    is_present: bool = False
    is_retenu: bool = False


class AnnonceurResumeRow(BaseModel):
    id_annonceur: str
    lib_annonceur: str = ""
    nb_cv_saisis: int = 0
    nb_cv_traites: int = 0
    nb_rdv: int = 0
    nb_presents: int = 0
    nb_retenus: int = 0
    nb_jo: int = 0


class StatAnnonceursResponse(BaseModel):
    saisis: list[CvSaisiAnnonceurRow] = []
    resume: list[AnnonceurResumeRow] = []
