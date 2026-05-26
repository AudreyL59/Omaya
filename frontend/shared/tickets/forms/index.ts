// Registre des fenêtres internes WinDev FI_* (colonne "Détail du ticket").
// Clé = IDTK_TypeDemande (string). Le conteneur monte le composant
// correspondant ; placeholder si le type n'est pas encore implémenté.
//
// Ordre d'implémentation = ordre du switch WinDev (Fen_TicketContenu).

import type { ComponentType } from 'react'

import FIAttExoCash from './FIAttExoCash'
import FIAvance from './FIAvance'
import FICartePro from './FICartePro'
import FICdeExoCash from './FICdeExoCash'
import FIConges from './FIConges'
import FICttCourtage from './FICttCourtage'
import FICttW from './FICttW'
import FICttWDemande from './FICttWDemande'
import FIDocDistrib from './FIDocDistrib'
import FIDPAE from './FIDPAE'
import FIDPAEDistrib from './FIDPAEDistrib'
import FIFactDistrib from './FIFactDistrib'
import FIFactureDR from './FIFactureDR'
import FIFourniture from './FIFourniture'
import FIMutuelle from './FIMutuelle'
import FIRDVTech from './FIRDVTech'
import FIResa from './FIResa'
import FISOSBO from './FISOSBO'
import FISOSJU from './FISOSJU'

export interface FIProps {
  apiBase: string
  getToken: () => string | null
  idTicket: string
  /** Ferme la popup « Détail du ticket » (cf. WinDev Ferme()). */
  onClose?: () => void
}

export const FI_COMPONENTS: Record<string, ComponentType<FIProps>> = {
  '1': FIFourniture, // Commande Fourniture
  '2': FICartePro,   // Carte PRO
  '3': FIDPAE,       // DPAE
  '4': FICttW,       // Contrat W - Signature
  '9': FIResa,       // Réservation
  '10': FIAvance,    // Demande d'avance
  '11': FISOSBO,     // SOS BO
  '13': FIConges,    // Congés
  '17': FISOSJU,     // SOS Juridique
  '19': FIRDVTech,   // Retour RDV Tech FIBRE
  '21': FIDPAE,      // DPAE à venir (même formulaire)
  '23': FICttCourtage, // Contrat de Courtage / Attestation
  '24': FICdeExoCash,  // Commande ExoCash
  '25': FIAttExoCash,  // Attribution ExoCash
  '27': FIMutuelle,    // Demande Mutuelle
  '28': FIFactDistrib, // Facturation Distrib
  '29': FIDPAEDistrib, // Nouveau Vendeur Distrib
  '30': FIDPAEDistrib, // Intégration Nouveau Distrib
  '31': FIDocDistrib,  // Réclamation Documents
  '33': FIFactureDR,   // Facture BO
  '40': FICttWDemande, // Contrat W - Demande
}
