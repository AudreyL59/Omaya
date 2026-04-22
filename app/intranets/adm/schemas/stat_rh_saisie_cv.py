from pydantic import BaseModel


class CvSaisiRow(BaseModel):
    id_cvtheque: str
    ope_id: str                 # id de l'operateur (saisie ou reactivation)
    ope_nom: str = ""
    date_traitement: str = ""    # Date_Saisie si dans la periode, sinon DateREAC
    est_reactivation: bool = False
    nom_prenom: str = ""
    commune: str = ""
    tel: str = ""
    statut_actuel: str = ""
    id_source: int = 0
    lib_source: str = ""
    annonceur_coopteur: str = ""


class CvTraiteRow(BaseModel):
    id_cvtheque: str
    ope_id: str                 # OPCrea
    ope_nom: str = ""
    date_traitement: str = ""    # Datecrea du CvSuivi
    nom_prenom: str = ""
    commune: str = ""
    tel: str = ""
    statut_actuel: str = ""      # Lib du IdCvStatut du CvSuivi
    id_cv_statut: int = 0
    date_saisie: str = ""        # Date de saisie originale du CV
    id_source: int = 0
    lib_source: str = ""
    annonceur_coopteur: str = ""


class OpeResumeRow(BaseModel):
    id_ope: str
    nom: str = ""
    nb_cv_saisis: int = 0
    nb_cv_traites: int = 0


class StatSaisieCvResponse(BaseModel):
    saisis: list[CvSaisiRow] = []
    traites: list[CvTraiteRow] = []
    resume: list[OpeResumeRow] = []
