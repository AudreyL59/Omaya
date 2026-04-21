from pydantic import BaseModel


class OrgaSalarie(BaseModel):
    id_salarie: str
    nom: str
    prenom: str
    poste: str = ""  # Lib_Poste
    categorie: str = ""  # Catégorie du poste (Prod, Staff, etc.)
    is_resp: bool = False
    is_resp_adjoint: bool = False
    # Infos supplémentaires
    date_debut: str = ""  # DateAncienneté (fallback DateDebut)
    anciennete_jours: int = 0
    date_dernier_ctt: str = ""  # Dernier contrat signé (si productif)
    cj_envoye: bool = False
    formation_iag: bool = False
    en_pause: bool = False
    chauffeur: bool = False
    mutuelle_adhesion: bool = False
    mutuelle_id: int = 0
    mutuelle_lib: str = ""
    mutuelle_fin_date: str = ""  # Date de fin d'adhésion si "PasAdhésion"
    absent: bool = False
    absence_type_id: int = 0
    absence_lib: str = ""
    absence_date_debut: str = ""
    absence_date_fin: str = ""


class OrgaTreeNode(BaseModel):
    id: str
    lib: str
    lib_niveau: str = ""  # "Société", "Région", "Agence", "Équipe"…
    id_type_niveau: int = 0
    salaries: list[OrgaSalarie] = []
    children: list["OrgaTreeNode"] = []


OrgaTreeNode.model_rebuild()
