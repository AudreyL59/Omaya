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
