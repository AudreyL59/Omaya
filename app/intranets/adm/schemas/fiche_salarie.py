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
    # Embauche / sortie (pour le bandeau "Emb. le ... / sorti(e) en ...")
    date_debut: str = ""
    date_sortie_demandee: str = ""
    date_sortie_reelle: str = ""
    lib_sortie: str = ""
    # Tooltip "Fiche creee le ... par X / Derniere modif le ... par Y"
    datecrea: str = ""
    op_crea: str = ""
    modif_date: str = ""
    modif_op: str = ""


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


class SortieSalariePayload(BaseModel):
    """Body POST /{id}/sortie : declenche une action de sortie."""
    type_sortie: int  # 1=Annul DUE, 2=FPE Salarie, 3=FPE entreprise, 4=Demission,
                      # 5=Licenciement, 6=Rupture conv, 10=Dem presumee


# --- Onglet 2 : Coordonnees ---------------------------------------------

class FicheCoordonnees(BaseModel):
    id_salarie: str
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


# --- Onglet 3 : Infos Embauche ------------------------------------------

class RefOption(BaseModel):
    id: int
    label: str


class StringRefOption(BaseModel):
    id: str
    label: str


class FicheEmbaucheRefs(BaseModel):
    """Combos pour l'onglet Infos Embauche."""
    societes: list[StringRefOption] = []
    postes: list[RefOption] = []
    type_ctt: list[RefOption] = []
    type_horaire: list[RefOption] = []
    type_sortie: list[RefOption] = []


class FicheEmbauche(BaseModel):
    """Onglet 3 : Infos Embauche (salarie_embauche + salarie_sortie)."""
    id_salarie: str
    # Embauche
    date_debut: str = ""
    date_fin_per_essai: str = ""
    date_anciennete: str = ""
    en_activite: bool = False
    dpae_date: str = ""
    dpae_num: str = ""
    dpae_ope: str = ""
    id_type_poste: int = 0
    id_type_ctt: int = 0
    id_type_horaire: int = 0
    id_ste: str = ""
    id_ste_dpae_energie: str = ""
    id_ste_dpae_fibre: str = ""
    coopte: bool = False
    coopteur: str = ""
    coopteur_lib: str = ""
    j_odirecte: bool = False
    jo_coopteur: str = ""
    jo_coopteur_lib: str = ""
    resp_equipe: bool = False
    resp_adjoint: bool = False
    chauffeur: bool = False
    multi_prod: bool = False
    cin_envoyee: bool = False
    cj_envoye: bool = False
    formation_iag: bool = False
    formation_iag_date: str = ""
    formation_iag_score: int = 0
    id_cvtheque: str = ""
    # Sortie
    id_type_sortie: int = 0
    date_sortie_demandee: str = ""
    date_sortie_reelle: str = ""
    demandeur_sortie: str = ""
    info_cpl: str = ""
    courrier_date_envoi: str = ""
    courrier_num_suivi: str = ""
    courrier_date_recep: str = ""
    courrier_delai_prev: str = ""
    stc_date_envoi: str = ""
    stc_num_suivi: str = ""
    stc_date_recep: str = ""
    stc_retourne_le: str = ""


class SaveEmbauchePayload(BaseModel):
    date_debut: str | None = None
    date_fin_per_essai: str | None = None
    date_anciennete: str | None = None
    en_activite: bool | None = None
    dpae_date: str | None = None
    dpae_num: str | None = None
    dpae_ope: str | None = None
    id_type_poste: int | None = None
    id_type_ctt: int | None = None
    id_type_horaire: int | None = None
    id_ste: str | None = None
    id_ste_dpae_energie: str | None = None
    id_ste_dpae_fibre: str | None = None
    coopte: bool | None = None
    coopteur: str | None = None
    j_odirecte: bool | None = None
    jo_coopteur: str | None = None
    id_cvtheque: str | None = None
    resp_equipe: bool | None = None
    resp_adjoint: bool | None = None
    chauffeur: bool | None = None
    multi_prod: bool | None = None
    cin_envoyee: bool | None = None
    cj_envoye: bool | None = None
    formation_iag: bool | None = None
    formation_iag_date: str | None = None
    formation_iag_score: int | None = None
    # Sortie (modifiable depuis les blocs INFORMATION DE SORTIE / COURRIER / SDTC)
    id_type_sortie: int | None = None
    date_sortie_demandee: str | None = None
    date_sortie_reelle: str | None = None
    info_cpl: str | None = None
    courrier_date_envoi: str | None = None
    courrier_num_suivi: str | None = None
    courrier_date_recep: str | None = None
    courrier_delai_prev: str | None = None
    stc_date_envoi: str | None = None
    stc_num_suivi: str | None = None
    stc_date_recep: str | None = None
    stc_retourne_le: str | None = None


# --- Overlay "S'Cool" : fiche Formateur ---------------------------------

class FicheFormateur(BaseModel):
    """Fiche formateur d'un salarie (table scool.pgt_formateur)."""
    id_formateur: str
    niveau: int = 0           # 0 = pas defini, 1 = Debutant, 2 = Formateur
    formateur_actif: bool = False
    exists: bool = False      # False si pas encore enregistre


class SaveFormateurPayload(BaseModel):
    niveau: int | None = None
    formateur_actif: bool | None = None


# --- Overlays embauche : Partenaires + DPAE -----------------------------

class SalariePortail(BaseModel):
    """Une ligne du tableau "portails partenaire du salarie"."""
    id_salarie_partenaire: str
    id_partenaire: str
    lib_partenaire: str = ""
    code: str = ""
    login: str = ""
    mdp: str = ""


class SalariePartDpae(BaseModel):
    """Une ligne du tableau "associations Partenaire <-> Societe DPAE"."""
    id_salarie_partenaire: str
    id_partenaire: str
    lib_partenaire: str = ""
    id_ste: str
    rs_societe: str = ""


class SaveCoordonneesPayload(BaseModel):
    adresse1: str | None = None
    adresse2: str | None = None
    cp: str | None = None
    ville: str | None = None
    tel_fixe: str | None = None
    tel_mob: str | None = None
    mail: str | None = None
    mail2: str | None = None
    urg_nom: str | None = None
    urg_lien: str | None = None
    urg_tel: str | None = None
    iban: str | None = None
    bic: str | None = None
