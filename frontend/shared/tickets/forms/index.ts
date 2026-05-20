// Registre des fenêtres internes WinDev FI_* (colonne "Détail du ticket").
// Clé = IDTK_TypeDemande (string). Le conteneur monte le composant
// correspondant ; placeholder si le type n'est pas encore implémenté.
//
// Ordre d'implémentation = ordre du switch WinDev (Fen_TicketContenu).

import type { ComponentType } from 'react'

import FIAvance from './FIAvance'
import FICartePro from './FICartePro'
import FIConges from './FIConges'
import FICttCourtage from './FICttCourtage'
import FICttW from './FICttW'
import FICttWDemande from './FICttWDemande'
import FIDPAE from './FIDPAE'
import FIFourniture from './FIFourniture'
import FIRDVTech from './FIRDVTech'
import FIResa from './FIResa'
import FISOSBO from './FISOSBO'
import FISOSJU from './FISOSJU'

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
  '9': FIResa,       // Réservation
  '10': FIAvance,    // Demande d'avance
  '11': FISOSBO,     // SOS BO
  '13': FIConges,    // Congés
  '17': FISOSJU,     // SOS Juridique
  '19': FIRDVTech,   // Retour RDV Tech FIBRE
  '21': FIDPAE,      // DPAE à venir (même formulaire)
  '23': FICttCourtage, // Contrat de Courtage / Attestation
  '40': FICttWDemande, // Contrat W - Demande
}
