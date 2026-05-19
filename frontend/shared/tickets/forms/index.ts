// Registre des fenêtres internes WinDev FI_* (colonne "Détail du ticket").
// Clé = IDTK_TypeDemande (string). Le conteneur monte le composant
// correspondant ; placeholder si le type n'est pas encore implémenté.
//
// Ordre d'implémentation = ordre du switch WinDev (Fen_TicketContenu).

import type { ComponentType } from 'react'

import FICartePro from './FICartePro'
import FICttW from './FICttW'
import FICttWDemande from './FICttWDemande'
import FIDPAE from './FIDPAE'
import FIFourniture from './FIFourniture'

export interface FIProps {
  apiBase: string
  getToken: () => string | null
  idTicket: string
}

export const FI_COMPONENTS: Record<string, ComponentType<FIProps>> = {
  '1': FIFourniture, // Commande Fourniture
  '2': FICartePro,   // Carte PRO
  '3': FIDPAE,       // DPAE
  '4': FICttW,       // Contrat W - Signature
  '21': FIDPAE,      // DPAE à venir (même formulaire)
  '40': FICttWDemande, // Contrat W - Demande
}
