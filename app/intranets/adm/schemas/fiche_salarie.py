"""Schemas Pydantic pour la fiche salarie ADM."""

from pydantic import BaseModel


class FicheHeader(BaseModel):
    """Donnees affichees dans le header de la fiche salarie."""
    id_salarie: str
    nom: str = ""
    prenom: str = ""
    civilite: int = 0
    photo_url: str = ""
    en_activite: bool = False
    en_pause: bool = False
    id_ste: str = ""
    rs_societe: str = ""
    id_type_poste: int = 0
    lib_poste: str = ""


class FicheIdentite(BaseModel):
    """Onglet 1 : Infos Principales (FI_SalarieIdentite).

    Source : table pgt_salarie (schema rh).
    """
    id_salarie: str
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
    matricule_tr: str = ""
    agenda_actif: bool = False


class SaveIdentitePayload(BaseModel):
    civilite: int | None = None
    nom: str | None = None
    nom_marital: str | None = None
    prenom: str | None = None
    sexe: str | None = None
    nationalite: str | None = None
    date_naiss: str | None = None
    lieu_naiss: str | None = None
    dep_naiss: int | None = None
    num_ss: str | None = None
    cpam: str | None = None
    num_cin: str | None = None
    situation_fam: int | None = None
    avec_enfant: bool | None = None
    nb_enfants: int | None = None
    travailleur_handi: bool | None = None
    matricule_tr: str | None = None


class SaveResponse(BaseModel):
    ok: bool = True


class ToggleStatusPayload(BaseModel):
    """Body POST /actif ou /en-pause : nouvelle valeur."""
    value: bool
