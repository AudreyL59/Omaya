/**
 * Fiche Ticket Call Fibre (Call SFR) — wrapper de la version PARTAGEE.
 *
 * Le composant complet vit dans `@shared/call/FicheTicketModalFibre` (mutualise
 * avec l'intranet Vendeur). Ici on ne fournit que les endpoints propres au
 * Call Fibre. Toute evolution de la fiche se fait dans le fichier partage.
 */
import SharedFicheTicketModalFibre from '@shared/call/FicheTicketModalFibre'

const BASE = '/api/call/fibre/tickets'

interface Props {
  idTicket: string | null
  onClose: () => void
  onAfterAction?: () => void
  readonly?: boolean
}

export default function FicheTicketModal(props: Props) {
  return (
    <SharedFicheTicketModalFibre
      {...props}
      base={BASE}
      ficheUrl={(id) => `${BASE}/${id}/fiche`}
    />
  )
}
