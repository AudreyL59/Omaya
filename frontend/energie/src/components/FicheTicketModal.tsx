/**
 * Fiche Ticket Call Energie — wrapper de la version PARTAGEE.
 *
 * Le composant complet vit dans `@shared/call/FicheTicketModalEnergie`
 * (mutualise avec l'intranet Vendeur). Ici on ne fournit que les endpoints
 * propres au Call Energie. Toute evolution se fait dans le fichier partage.
 */
import SharedFicheTicketModalEnergie from '@shared/call/FicheTicketModalEnergie'

const BASE = '/api/call/energie/tickets'

interface Props {
  idTicket: string | null
  onClose: () => void
  onAfterAction?: () => void
  readonly?: boolean
}

export default function FicheTicketModal(props: Props) {
  return (
    <SharedFicheTicketModalEnergie
      {...props}
      base={BASE}
      ficheUrl={(id) => `${BASE}/${id}/fiche`}
    />
  )
}
