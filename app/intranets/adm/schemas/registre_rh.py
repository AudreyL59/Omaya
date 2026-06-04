"""Schemas Pydantic pour le Registre RH (ADM)."""

from pydantic import BaseModel


class SocieteOption(BaseModel):
    id_ste: str
    rs_interne: str


class RefOption(BaseModel):
    id: int
    label: str


class RegistreRefs(BaseModel):
    """Listes de reference pour les combos colonnes du tableau."""
    type_ctt: list[RefOption]
    type_horaire: list[RefOption]
    type_sortie: list[RefOption]


class SalarieRegistre(BaseModel):
    """Une ligne du Registre RH (jointure salarie + coordonnees + embauche + sortie + type_poste)."""
    id_salarie: str
    # Identite
    civilite: int = 0
    nom: str = ""
    prenom: str = ""
    sexe: str = ""
    nationalite: str = ""
    date_naiss: str = ""
    lieu_naiss: str = ""
    dep_naiss: int = 0
    num_ss: str = ""
    cpam: str = ""
    num_cin: str = ""
    travailleur_handi: bool = False
    # Coordonnees
    adresse1: str = ""
    adresse2: str = ""
    cp: str = ""
    ville: str = ""
    tel_mob: str = ""
    mail: str = ""
    iban: str = ""
    urg_nom: str = ""
    urg_lien: str = ""
    urg_tel: str = ""
    # Embauche
    id_ste: str = ""
    date_debut: str = ""
    date_fin_per_essai: str = ""
    dpae_num: str = ""
    dpae_date: str = ""
    id_type_poste: int = 0
    lib_poste: str = ""
    id_type_ctt: int = 0
    id_type_horaire: int = 0
    en_activite: bool = False
    coopte: bool = False
    coopteur: str = ""
    # Sortie
    date_sortie_demandee: str = ""
    date_sortie_reelle: str = ""
    demandeur_sortie: str = ""
    id_type_sortie: int = 0
