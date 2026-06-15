/**
 * Popup standalone 'Fen_TicketContenu' — version legere (lecture seule sur
 * les infos generales) pour les boutons 'Voir le ticket' depuis d'autres
 * ecrans (fiche salarie, etc.).
 *
 * Charge le detail via POST /tickets/{id}/ouvrir (qui applique aussi la
 * regle WinDev statut<2 → 2 cote backend), affiche un header avec
 * libelle du type de demande + statut, puis monte la fenetre interne
 * FI_* correspondante (registre FI_COMPONENTS) ou un placeholder si le
 * type n'est pas encore implemente.
 *
 * NB : pour la version "complete" (combo statut editable + op_dest +
 * staff + boutons d'action), utiliser TicketContenuModal de TicketsPage.
 * Ce wrapper standalone est conçu pour ouvrir un ticket en lecture
 * depuis n'importe ou.
 */

import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Loader2, X } from 'lucide-react'

import { showToast } from '../ui/dialog'
import { FI_COMPONENTS } from './forms'
import type { TicketDetail } from './types'

interface Props {
  apiBase: string
  getToken: () => string | null
  idTicket: string
  onClose: () => void
  /** Si fourni, transmis a la fenetre interne (ouvre une fiche salarie). */
  onOpenFicheSalarie?: (idSalarie: string, nom: string, prenom: string) => void
}

function fmtDateTime(iso: string): string {
  if (!iso || iso.length < 10) return ''
  const d = `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
  const t = iso.length >= 16 ? iso.slice(11, 16) : ''
  return t ? `${d} ${t}` : d
}

export default function TicketContenuStandalone({
  apiBase,
  getToken,
  idTicket,
  onClose,
  onOpenFicheSalarie,
}: Props) {
  const [detail, setDetail] = useState<TicketDetail | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!idTicket) return
    setLoading(true)
    setDetail(null)
    ;(async () => {
      try {
        const r = await fetch(`${apiBase}/tickets/${idTicket}/ouvrir`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
        })
        if (!r.ok) {
          const e = await r.json().catch(() => null)
          showToast(`Erreur : ${e?.detail || r.status}`, 'error')
          return
        }
        const d = (await r.json()) as TicketDetail
        setDetail(d)
      } catch {
        showToast('Erreur réseau (ouverture du ticket).', 'error')
      } finally {
        setLoading(false)
      }
    })()
  }, [apiBase, getToken, idTicket])

  const FI = detail ? FI_COMPONENTS[detail.id_type_demande] : null

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-[60] flex items-center justify-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-white rounded-lg shadow-xl w-[95vw] max-w-4xl flex flex-col max-h-[90vh]"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-c-line">
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-bold text-c-ink truncate">
                {detail
                  ? `Ticket #${detail.id_ticket} — ${detail.lib_type_demande}`
                  : 'Détail du ticket'}
              </h3>
              {detail && (
                <div className="text-xs text-c-ink-soft mt-0.5">
                  Service {detail.service} ·{' '}
                  Statut « {detail.lib_statut || '—'} »
                  {detail.cloturee ? ' · Clôturé' : ''}
                  {detail.date_crea
                    ? ` · Créé le ${fmtDateTime(detail.date_crea)}`
                    : ''}
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1 hover:bg-c-surface-medium rounded shrink-0"
              aria-label="Fermer"
            >
              <X className="w-4 h-4 text-c-ink" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 min-h-0 overflow-auto p-4">
            {loading && (
              <div className="flex items-center justify-center py-10">
                <Loader2 className="w-5 h-5 animate-spin text-c-brand" />
              </div>
            )}
            {!loading && detail && FI && (
              <FI
                apiBase={apiBase}
                getToken={getToken}
                idTicket={detail.id_ticket}
                onClose={onClose}
                onOpenFicheSalarie={onOpenFicheSalarie}
              />
            )}
            {!loading && detail && !FI && (
              <div className="text-sm text-c-ink-faint text-center py-10">
                Formulaire spécifique au type «&nbsp;
                {detail.lib_type_demande}&nbsp;»
                <br />
                (à venir)
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
