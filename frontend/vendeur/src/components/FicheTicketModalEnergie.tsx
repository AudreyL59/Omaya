/**
 * Fiche Ticket Call Energie cote VENDEUR (page Suivi) — wrapper de la version
 * PARTAGEE (`@shared/call/FicheTicketModalEnergie`).
 *
 * Endpoints Vendeur : /api/vendeur/tickets-call/suivi/fiche-energie/...
 * (NB au 2026-07 : seul le GET fiche est porte cote Vendeur ; les endpoints
 * d'ecriture restent a porter — d'ou l'usage principal en consultation.)
 */
import SharedFicheTicketModalEnergie from '@shared/call/FicheTicketModalEnergie'

const BASE = '/api/vendeur/tickets-call/suivi/fiche-energie'

interface Props {
  idTicket: string | null
  onClose: () => void
  onAfterAction?: () => void
  readonly?: boolean
}

export default function FicheTicketModalEnergie(props: Props) {
  return (
    <SharedFicheTicketModalEnergie
      {...props}
      base={BASE}
      ficheUrl={(id) => `${BASE}/${id}`}
    />
  )
}
