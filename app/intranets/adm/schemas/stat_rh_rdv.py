from pydantic import BaseModel


class RdvRow(BaseModel):
    id_cvtheque: str
    nom: str
    prenom: str
    gsm: str
    date_crea: str        # CvSuivi.Datecrea (date de planif)
    date_debut: str       # AgendaEvénement.DateDébut (date du RDV)
    lib_categorie: str
    statut_lib: str
    recruteur_nom: str
    op_crea_nom: str


class AggRow(BaseModel):
    id: str
    nom: str
    rdv: int = 0
    presents: int = 0
    retenus: int = 0
    venus_jo: int = 0


class StatRdvResponse(BaseModel):
    rdv: list[RdvRow] = []
    operateurs: list[AggRow] = []
    recruteurs: list[AggRow] = []
    non_statues: int = 0
