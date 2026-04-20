from pydantic import BaseModel


class IdentiteResponse(BaseModel):
    id_salarie: int
    civilite: int = 0
    nom: str = ""
    nom_marital: str = ""
    prenom: str = ""
    sexe: str = ""
    nationalite: str = ""
    date_naiss: str = ""
    lieu_naiss: str = ""
    dep_naiss: int = 0
    num_ss: str = ""
    cpam: str = ""
    num_cin: str = ""
    situation_fam: int = 0
    avec_enfant: bool = False
    nb_enfants: int = 0
    travailleur_handi: bool = False
    photo: str = ""  # Base64


class CoordonneesResponse(BaseModel):
    adresse1: str = ""
    adresse2: str = ""
    cp: str = ""
    ville: str = ""
    tel_fixe: str = ""
    tel_mob: str = ""
    mail: str = ""
    mail2: str = ""
    urg_nom: str = ""
    urg_lien: str = ""
    urg_tel: str = ""
    iban: str = ""
    bic: str = ""


class MonCompteResponse(BaseModel):
    identite: IdentiteResponse
    coordonnees: CoordonneesResponse


class DocumentItem(BaseModel):
    nom: str
    taille_mo: float
    date: str
    url: str
