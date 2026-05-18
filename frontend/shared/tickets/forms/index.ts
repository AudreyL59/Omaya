// Registre des fenêtres internes WinDev FI_* (colonne "Détail du ticket").
// Clé = IDTK_TypeDemande (string). Le conteneur monte le composant
// correspondant ; placeholder si le type n'est pas encore implémenté.
//
// Ordre d'implémentation = ordre du switch WinDev (Fen_TicketContenu).

import type { ComponentType } from 'react'

import FIFourniture from './FIFourniture'

export interface FIProps {
  apiBase: string
  getToken: () => string | null
  idTicket: string
}

export const FI_COMPONENTS: Record<string, ComponentType<FIProps>> = {
  '1': FIFourniture, // Commande Fourniture
}
