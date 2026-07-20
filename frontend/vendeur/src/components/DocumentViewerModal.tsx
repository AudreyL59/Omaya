/**
 * ============================================================================
 * SYNCED FROM frontend/fibre/src/components/DocumentViewerModal.tsx
 * (also mirrored in frontend/energie/src/components/DocumentViewerModal.tsx)
 *
 * Copie utilisee par FicheTicketModalFibre + FicheTicketModalEnergie cote
 * Vendeur (via la page /vendeur/tickets-call). TOUTE modif d'un des 4
 * exemplaires doit etre repercutee dans les autres.
 * Cf. memoire feedback_fiche_ticket_modal_sync.
 * ============================================================================
 *
 * Viewer modal pour les documents stockes sur rest.omaya.fr/DocOmaya/
 * (CIN, KBIS, Lettre de resiliation).
 */

import { motion, AnimatePresence } from 'framer-motion'
import { X, ExternalLink } from 'lucide-react'

interface Props {
  open: boolean
  title: string
  url: string
  kind: 'image' | 'pdf' | ''
  onClose: () => void
}

export default function DocumentViewerModal({ open, title, url, kind, onClose }: Props) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-black/20 z-[60] flex items-center justify-center p-4"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            onClick={(e) => e.stopPropagation()}
            className="bg-white rounded-xl shadow-2xl w-full max-w-5xl h-[90vh] flex flex-col overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-c-line">
              <h3 className="text-sm font-bold text-c-ink">{title}</h3>
              <div className="flex items-center gap-2">
                {url && (
                  <a
                    href={url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 px-2 py-1 rounded text-xs text-c-brand hover:bg-c-brand-soft"
                    title="Ouvrir dans un nouvel onglet"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Ouvrir
                  </a>
                )}
                <button
                  onClick={onClose}
                  className="p-1.5 rounded text-c-ink-soft hover:bg-c-brand-soft hover:text-c-ink"
                  aria-label="Fermer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-auto bg-gray-100 flex items-center justify-center">
              {!url || !kind ? (
                <div className="text-c-ink-faint italic text-sm">Aucun document trouvé</div>
              ) : kind === 'pdf' ? (
                <iframe
                  src={url}
                  title={title}
                  className="w-full h-full bg-white"
                />
              ) : (
                <img
                  src={url}
                  alt={title}
                  className="max-w-full max-h-full object-contain"
                />
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
