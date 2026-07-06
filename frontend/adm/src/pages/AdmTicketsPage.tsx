/**
 * AdmTicketsPage : wrapper de @shared/tickets/TicketsPage cote ADM.
 *
 * Branche le callback onOpenFicheSalarie pour que les FI* (ex: FISortieRH)
 * puissent ouvrir <FicheSalarieModal/> en popup depuis le ticket.
 * Cote Vendeur, le wrapper n'existe pas et le lien fait un fallback vers
 * /adm/salaries/registre.
 */

import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'

import TicketsPage from '@shared/tickets/TicketsPage'
import FicheSalarieModal from '@/components/FicheSalarieModal'
import { getToken } from '@/api'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

const ADM_API = '/api/adm'

interface OpenFiche {
  id: string
  nom: string
  prenom: string
}

export default function AdmTicketsPage() {
  useDocumentTitle('Tickets')
  const [searchParams] = useSearchParams()
  const [fiche, setFiche] = useState<OpenFiche | null>(null)
  const autoOpenedRef = useRef(false)

  // Auto-ouverture de la fiche salarie depuis ?ouvrir=<id>&nom=...&prenom=...
  // (navigation 'Terminer ma DPAE' qui ouvre aussi la fiche).
  useEffect(() => {
    if (autoOpenedRef.current) return
    const id = searchParams.get('ouvrir')
    if (!id) return
    autoOpenedRef.current = true
    setFiche({
      id,
      nom: searchParams.get('nom') || '',
      prenom: searchParams.get('prenom') || '',
    })
  }, [searchParams])

  return (
    <>
      <TicketsPage
        apiBase={ADM_API}
        getToken={getToken}
        onOpenFicheSalarie={(id, nom, prenom) => setFiche({ id, nom, prenom })}
        initialTypeId={searchParams.get('type') || undefined}
        initialTicketId={searchParams.get('ticket') || undefined}
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
