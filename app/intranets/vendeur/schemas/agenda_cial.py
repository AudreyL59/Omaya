from pydantic import BaseModel


class CommercialItem(BaseModel):
    id_salarie: str
    nom: str
    prenom: str


class AgendaCialRDV(BaseModel):
    id_rdv: str  # string pour préserver précision
    date_debut: str
    date_fin: str
    titre: str
    contenu: str
    info_compl: str = ""
    id_categorie: int
    lib_categorie: str
    couleur_hex: str  # #RRGGBB depuis Couleur (BGR int)
    id_cv_statut: int
    id_tk_liste: str
    op_crea: int
    # Infos client (TK_Call ou TK_CallSFR selon IDTK_TypeDemande)
    client_civilite: int = 0
    client_nom: str = ""
    client_prenom: str = ""
    client_nom_marital: str = ""
    client_naissance: str = ""
    client_dep_naiss: int = 0
    client_adresse1: str = ""
    client_adresse2: str = ""
    client_cp: str = ""
    client_ville: str = ""
    client_mobile: str = ""
    client_email: str = ""
    client_type_logement: int = 0  # 0=inconnu 1=Maison 2=Appartement
    client_pro: bool = False
    client_rs: str = ""
    client_siret: str = ""
    type_demande: int = 0  # 20=Fibre (SFR), 22=Énergie
