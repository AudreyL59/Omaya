/**
 * AdmTicketsPage : wrapper de @shared/tickets/TicketsPage cote ADM.
 *
 * Branche le callback onOpenFicheSalarie pour que les FI* (ex: FISortieRH)
 * puissent ouvrir <FicheSalarieModal/> en popup depuis le ticket.
 * Cote Vendeur, le wrapper n'existe pas et le lien fait un fallback vers
 * /adm/salaries/registre.
 */

import { useState } from 'react'
import { AnimatePresence } from 'framer-motion'

import TicketsPage from '@shared/tickets/TicketsPage'
import FicheSalarieModal from '@/components/FicheSalarieModal'
import { getToken } from '@/api'

const ADM_API = '/api/adm'

interface OpenFiche {
  id: string
  nom: string
  prenom: string
}

export default function AdmTicketsPage() {
  const [fiche, setFiche] = useState<OpenFiche | null>(null)

  return (
    <>
      <TicketsPage
        apiBase={ADM_API}
        getToken={getToken}
        onOpenFicheSalarie={(id, nom, prenom) => setFiche({ id, nom, prenom })}
      />
      <AnimatePresence>
        {fiche && (
          <FicheSalarieModal
            idSalarie={fiche.id}
            nom={fiche.nom}
            prenom={fiche.prenom}
            onClose={() => setFiche(null)}
          />
        )}
      </AnimatePresence>
    </>
  )
}
