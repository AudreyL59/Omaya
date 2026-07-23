/**
 * Fiche Ticket Call Fibre cote VENDEUR (page Suivi) — wrapper de la version
 * PARTAGEE (`@shared/call/FicheTicketModalFibre`).
 *
 * Endpoints Vendeur : /api/vendeur/tickets-call/suivi/fiche-fibre/...
 * (NB au 2026-07 : seul le GET fiche est porte cote Vendeur ; les endpoints
 * d'ecriture restent a porter et repondent 404 tant que non faits — d'ou
 * l'usage principal en consultation.)
 */
import SharedFicheTicketModalFibre from '@shared/call/FicheTicketModalFibre'

const BASE = '/api/vendeur/tickets-call/suivi/fiche-fibre'

interface Props {
  idTicket: string | null
  onClose: () => void
  onAfterAction?: () => void
  readonly?: boolean
}

export default function FicheTicketModalFibre(props: Props) {
  return (
    <SharedFicheTicketModalFibre
      {...props}
      base={BASE}
      ficheUrl={(id) => `${BASE}/${id}`}
    />
  )
}
