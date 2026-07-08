"""
Schemas Fen_SMSPerf - Gestion SMS Perf-Exo.

3 tables principales :
- pgt_smsanimation : config globale (toggle actif + liste staff destinataire)
- pgt_smsanimation_regleenvoi : regles d'envoi (une ligne par code animation)
- pgt_smsanimation_orgadest : equipes destinataires du SMS par code
- pgt_sms_animation_orga_periode : equipes incluses dans les scores
"""
from pydantic import BaseModel, Field


# --------------------------------------------------------------------
# Toggle Perf-Exo actif/inactif
# --------------------------------------------------------------------

class TogglePayload(BaseModel):
    is_actif: bool


# --------------------------------------------------------------------
# Staff destinataires (jetons)
# --------------------------------------------------------------------

class StaffItem(BaseModel):
    id_salarie: str
    nom: str
    prenom: str


class StaffSaveParams(BaseModel):
    id_salaries: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------
# Regles d'envoi (SmsAnimation_RegleEnvoi)
# --------------------------------------------------------------------

class RegleEnvoi(BaseModel):
    id_regle: str = ""
    type_sms: str = "Perf-Exo"
    code_animation: str = ""
    texte_sms: str = ""
    heure_envoi: int = 0            # en heures (0..23)
    heure_debut: int = 0            # heure signature debut
    heure_fin: int = 0              # heure signature fin
    ordre: int = 0
    sms_groupe: bool = False        # False = individuel, True = groupe
    partenaire: str = ""            # 'ENI'/'SFR'/... ou ''
    prod_groupe: int = 1            # 1=Vendeur, 2=Equipe, 3=Agence
    periode_calcul: int = 1         # 1=Journalier, 2=Hebdomadaire, 3=Mensuel
    nb_bs_min: int = 1              # objectif minimum
    is_actif: bool = True


class RegleEnvoiPayload(BaseModel):
    """Input creation / update regle."""
    code_animation: str
    texte_sms: str = ""
    heure_envoi: int = 0
    heure_debut: int = 0
    heure_fin: int = 0
    ordre: int = 0
    sms_groupe: bool = False
    partenaire: str = ""
    prod_groupe: int = 1
    periode_calcul: int = 1
    nb_bs_min: int = 1
    is_actif: bool = True


# --------------------------------------------------------------------
# Destinataires SMS (SmsAnimation_OrgaDest)
# --------------------------------------------------------------------

class DestinataireRow(BaseModel):
    id_dest: str = ""
    idorganigramme: str = ""
    lib_orga: str = ""
    anim_code: str = ""
    du: str = ""       # YYYY-MM-DD ou vide
    au: str = ""
    is_actif: bool = True


class DestinatairePayload(BaseModel):
    anim_code: str
    idorganigramme: str
    du: str = ""
    au: str = ""
    is_actif: bool = True


# --------------------------------------------------------------------
# Equipes scores (SmsAnimation_OrgaPeriode)
# --------------------------------------------------------------------

class EquipeScoreRow(BaseModel):
    id_orga_periode: str = ""
    idorganigramme: str = ""
    lib_orga: str = ""
    code_animation: str = ""
    type: str = "Perf-Exo"
    du: str = ""
    au: str = ""
    is_actif: bool = True


class EquipeScorePayload(BaseModel):
    code_animation: str
    idorganigramme: str
    type: str = "Perf-Exo"
    du: str = ""
    au: str = ""
    is_actif: bool = True


# --------------------------------------------------------------------
# Envoyer SMS (proc Animation_SmsPerf)
# --------------------------------------------------------------------

class EnvoyerSmsParams(BaseModel):
    date_jour: str    # YYYY-MM-DD


class EnvoyerSmsResult(BaseModel):
    ok: bool
    nb_sms_envoyes: int = 0
    nb_regles_traitees: int = 0
    message: str = ""
