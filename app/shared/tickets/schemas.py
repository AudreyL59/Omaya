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
    op_dest_nom: str = ""
    op_dest_prenom: str = ""
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


class StatuerRequest(BaseModel):
    """Action de masse 'Statuer la sélection' (cf. Fen_TicketChoixStatut).

    - cloturee=True  → clôture (Cloturée=1, DateCloture=now, ModifDate=now),
                       id_statut ignoré (équivaut au cas WinDev idStatut=666).
    - cloturee=False → changement de statut (IDTK_Statut=id_statut,
                       ModifDate=now).
    """
    id_tickets: list[str]
    id_statut: int | None = None
    cloturee: bool = False


class StatuerResponse(BaseModel):
    updated: int


class SupprimerRequest(BaseModel):
    """Action de masse 'Supprimer la sélection' (soft-delete).

    Transposition WinDev : ModifDate=now, ModifOP=user, ModifELEM='suppr'.
    Les tickets marqués 'suppr' sont exclus de tous les SELECT.
    """
    id_tickets: list[str]


class SupprimerResponse(BaseModel):
    deleted: int


# ---------------------------------------------------------------
# Fen_TicketContenu — bloc "Informations générales" (commun)
# ---------------------------------------------------------------

class TicketDetail(BaseModel):
    """Détail d'un ticket pour l'écran d'édition (infos générales)."""
    id_ticket: str
    id_type_demande: str
    service: str
    lib_type_demande: str = ""
    id_statut: int
    lib_statut: str = ""
    op_dest: str = ""
    op_dest_nom: str = ""
    op_dest_prenom: str = ""
    op_traitement_staff: str = ""
    op_staff_nom: str = ""
    op_staff_prenom: str = ""
    cloturee: bool = False
    date_cloture: str = ""
    date_crea: str = ""


class SaveInfosRequest(BaseModel):
    """Enregistrer les infos générales (cf. WinDev saveTicket()).

    op_dest / op_traitement_staff : "" = inchangé/non renseigné.
    Le passage cloturee=True renseigne DateCloture (si non fournie = now).
    """
    id_statut: int
    op_dest: str = ""
    op_traitement_staff: str = ""
    cloturee: bool = False
    date_cloture: str = ""        # YYYYMMDD (vide = now si cloturee)
    prendre_en_charge: bool = False  # "Je m'occupe" → op_staff = user


class SaveInfosResponse(BaseModel):
    ok: bool = True
    closed: bool = False          # True si le ticket vient d'être clôturé


class SalarieItem(BaseModel):
    id_salarie: str
    nom: str
    prenom: str
    poste: str = ""
    lib_societe: str = ""
    date_embauche: str = ""       # ISO YYYY-MM-DD
    actif: bool = False           # salarie_embauche.EnActivité
