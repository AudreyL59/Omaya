from pydantic import BaseModel


class CooptationItem(BaseModel):
    nom: str
    prenom: str
    date_saisie: str


class VendeurItem(BaseModel):
    id_salarie: str
    nom: str
    prenom: str
    poste: str = ""


class VilleItem(BaseModel):
    id: int
    nom_ville: str
    cp: str


class CooptationCreate(BaseModel):
    nom: str
    prenom: str
    date_naissance: str = ""
    age: int = 0
    cp: str
    id_ville: int
    gsm: str
    commentaire: str = ""
    id_vendeur: str  # coopteur (string pour précision)
    cooptation_directe: bool = False
    nom_parrain: str = ""
    lien_parente: str = ""
