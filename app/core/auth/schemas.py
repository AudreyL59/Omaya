from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str
    intranet: str  # ex: "vendeur", "adm", "call_fibre"...


class UserToken(BaseModel):
    """Données utilisateur embarquées dans le JWT."""
    id_salarie: int
    login: str
    nom: str
    prenom: str
    is_actif: bool
    is_pause: bool
    agenda_actif: bool
    active_log: bool
    gsm: str
    id_ste: int
    prof_poste: str
    droits: list[str]  # codes internes (ex: ["IntraADM", "IntraCallRH"])


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserToken
