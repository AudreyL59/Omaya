from pydantic import BaseModel


class ClusterCard(BaseModel):
    code_vad: str          # "14" en mode département, "14-01" en mode sous-cluster
    code_vad_full: str     # "14-01" (toujours le CodeVAD complet source)
    nom: str               # "14 - Calvados" ou "14-01 - Sous-zone"
    exp_lib: str           # "Réseau" ou Lib_ORGA
    exp_rs: str            # raison sociale ou nom département
    logo_ste: str = ""     # base64 PNG/SVG ou vide
    obj_ctt: int
    nb_ctt_brut: int
    nb_s1: int
    nb_racc_sfr: int
    nb_fib_hors_att: int
    ratio: float           # nb_ctt_brut / obj_ctt (1.0 = 100%), capé à 100% pour la jauge
    ratio_reel: float      # valeur non capée (peut dépasser 100%)
    tx_rac: float          # nb_racc_sfr / nb_fib_hors_att * 100
    tx_s1: float           # nb_racc_sfr / (nb_fib_hors_att + nb_s1) * 100
    couleur_jauge: str     # hex #RRGGBB
    couleur_racc: str      # hex #RRGGBB


class GroupementItem(BaseModel):
    id: str                # IdOrganigramme en string (8 octets possible)
    label: str             # Lib_ORGA
