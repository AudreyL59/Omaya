from pydantic import BaseModel


class SessionItem(BaseModel):
    id_prevision_recrut: str
    date_session: str
    nom_ville: str
    label: str  # "DD/MM/YYYY - Ville"
    id_recruteur: str = ""  # IDSalarie du recruteur assigné à la session
    recruteur_nom: str = ""
    id_lieu_rdv: int = 0  # IDcvLieuRdv (1 = Visio)


class LieuRdvItem(BaseModel):
    id_cv_lieu_rdv: int
    lib_lieu: str


class LieuRdvInfo(BaseModel):
    id_cv_lieu_rdv: int
    lib_lieu: str
    adresse1: str = ""
    adresse2: str = ""
    cp: str = ""
    nom_ville: str = ""
    latitude: float = 0
    longitude: float = 0


class SalonVisioItem(BaseModel):
    id_salon_visio: str
    lib_salon: str


class SalonVisioInfo(BaseModel):
    id_salon_visio: str
    lib_salon: str
    lien: str = ""
    id_reunion: str = ""
    mdp: str = ""


class PriseRdvRequest(BaseModel):
    id_cvtheque: str
    id_recruteur: str  # IDSalarie du recruteur
    id_session: str = ""  # 0 / "" si aucune
    date_rdv: str  # ISO "YYYY-MM-DD"
    heure_rdv: str  # "HH:MM"
    type_entretien: str  # "Physique" ou "Visio"
    id_lieu_rdv: int = 0  # si Physique
    id_salon_visio: str = ""  # si Visio
    envoyer_sms: bool = True
