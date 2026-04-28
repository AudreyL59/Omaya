from pydantic import BaseModel


class DpaeRow(BaseModel):
    id_salarie: str
    id_ste: int = 0
    rs_interne: str = ""       # societe.RS_Interne
    nom: str = ""
    prenom: str = ""
    adresse: str = ""
    cp: str = ""
    ville: str = ""
    date_entree: str = ""
    en_activite: bool = False
    date_sortie: str = ""      # DateSortieRéelle si sortie existe
    fin_demandee: str = ""     # DateSortieDemandée si sortie existe
    origine: str = ""
    detail_origine: str = ""
    id_orga: str = "0"
    agence: str = ""           # libellé du parent de l'orga (Agence)
    equipe: str = ""           # libellé de l'orga elle-même (Équipe)
    prod: bool = False


class SortieRow(BaseModel):
    id_salarie: str
    id_ste: int = 0
    rs_interne: str = ""
    nom: str = ""
    prenom: str = ""
    adresse: str = ""
    cp: str = ""
    ville: str = ""
    date_entree: str = ""
    date_sortie_reelle: str = ""
    fin_demandee: str = ""
    id_type_sortie: int = 0
    type_sortie_lib: str = ""
    id_orga: str = "0"
    agence: str = ""
    equipe: str = ""
    prod: bool = False


class OrgaResumeRow(BaseModel):
    id_orga: str
    lib_orga: str = ""
    lib_parent: str = ""
    id_parent: str = "0"
    nb_dpae: int = 0
    nb_sortants_non_prod: int = 0
    nb_jour_non_prod: int = 0
    nb_sortants_prod: int = 0
    nb_jour_prod: int = 0


class StatEntreeSortieResponse(BaseModel):
    dpae: list[DpaeRow] = []
    sorties: list[SortieRow] = []
    resume: list[OrgaResumeRow] = []
