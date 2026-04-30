"""Schemas Pydantic pour le module Tickets."""

from pydantic import BaseModel


class TicketTypeDemande(BaseModel):
    """Type de demande (TK_TypeDemande) — visible dans la sidebar."""
    id_type_demande: str
    service: str                 # 5 chars : BO, IT, JU, RH, ...
    lib_type_demande: str
    icone_data_url: str = ""     # data:image/...;base64,... (optionnel)


class TicketStatut(BaseModel):
    id_statut: int
    lib_statut: str


class TicketSidebarItem(BaseModel):
    """Item de la sidebar : un service avec ses types accessibles."""
    service: str                 # ex: "RH"
    types: list[TicketTypeDemande]


class TicketRow(BaseModel):
    """Une ligne dans le tableau des tickets."""
    id_ticket: str
    id_type_demande: str
    service: str
    id_statut: int
    lib_statut: str = ""
    date_crea: str
    op_crea: str = ""
    op_crea_nom: str = ""
    op_crea_prenom: str = ""
    op_dest: str = ""
    op_traitement_staff: str = ""
    op_staff_nom: str = ""
    op_staff_prenom: str = ""
    info: str = ""               # généré par donne_info_ticket
    cloturee: bool = False
    date_cloture: str = ""
    date_report: str = ""
    modif_date: str = ""         # ModifDate (ISO) — utilisé pour SSE since
    modification: bool = False   # flag WinDev "modifié"


class TicketListResponse(BaseModel):
    """Réponse paginée + groupée par statut.

    Le frontend regroupe lui-même via `id_statut` ; on renvoie aussi la liste
    des statuts présents dans l'ordre logique pour faciliter l'affichage.
    """
    rows: list[TicketRow] = []
    statuts: list[TicketStatut] = []   # ordonnée
    total: int = 0
