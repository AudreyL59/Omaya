export interface TicketTypeDemande {
  id_type_demande: string
  service: string
  lib_type_demande: string
  icone_data_url: string
}

export interface TicketStatut {
  id_statut: number
  lib_statut: string
}

export interface TicketSidebarItem {
  service: string
  types: TicketTypeDemande[]
}

export interface TicketRow {
  id_ticket: string
  id_type_demande: string
  service: string
  id_statut: number
  lib_statut: string
  date_crea: string
  op_crea: string
  op_crea_nom: string
  op_crea_prenom: string
  op_dest: string
  op_dest_nom: string
  op_dest_prenom: string
  op_traitement_staff: string
  op_staff_nom: string
  op_staff_prenom: string
  info: string
  cloturee: boolean
  date_cloture: string
  date_report: string
  modif_date: string
  modification: boolean
}

export interface TicketListResponse {
  rows: TicketRow[]
  statuts: TicketStatut[]
  total: number
}

// ---------------------------------------------------------------
// Live update — réponses du long-polling (/tickets/poll)
// ---------------------------------------------------------------

export interface TicketStreamEvent {
  // added/modified est décidé côté client (présence dans la liste) ;
  // le backend ne renvoie que la ligne.
  kind?: 'added' | 'modified'
  row: TicketRow
}

export interface TicketStreamPayload {
  events: TicketStreamEvent[]
  cursor: string
}

// ---------------------------------------------------------------
// Fen_TicketContenu — détail + bloc "Informations générales"
// ---------------------------------------------------------------

export interface TicketDetail {
  id_ticket: string
  id_type_demande: string
  service: string
  lib_type_demande: string
  id_statut: number
  lib_statut: string
  op_dest: string
  op_dest_nom: string
  op_dest_prenom: string
  op_traitement_staff: string
  op_staff_nom: string
  op_staff_prenom: string
  cloturee: boolean
  date_cloture: string
  date_crea: string
}

export interface SalarieItem {
  id_salarie: string
  nom: string
  prenom: string
}

export interface SaveInfosResponse {
  ok: boolean
  closed: boolean
}
