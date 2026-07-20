/**
 * ============================================================================
 * SYNCED FROM frontend/fibre/src/components/AnnulLignePanierPopup.tsx
 * (also mirrored in frontend/energie/src/components/AnnulLignePanierPopup.tsx)
 *
 * Copie utilisee par FicheTicketModalFibre + FicheTicketModalEnergie cote
 * Vendeur (via la page /vendeur/tickets-call). TOUTE modif d'un des 4
 * exemplaires doit etre repercutee dans les autres.
 * Cf. memoire feedback_fiche_ticket_modal_sync.
 * ============================================================================
 *
 * Popup d'annulation d'une ligne du panier (transposition Popup1 WinDev).
 *
 * 5 motifs hardcodes cochables + zone texte libre.
 * Au moins 1 motif coche OU des informations complementaires requis.
 */

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2 } from 'lucide-react'

const MOTIFS = [
  'Ne parle pas français',
  "N'a pas compris qu'il/elle changeait d'opérateur",
  'Pas dans la bonne tranche d\'âge (-18 ans ou + de 75 ans)',
  'a un DG',
  "La personne au téléphone n'est pas le titulaire",
]

interface Props {
  open: boolean
  loading?: boolean
  onCancel: () => void
  onConfirm: (motifs: string[], precisions: string) => void
}

export default function AnnulLignePanierPopup({ open, loading, onCancel, onConfirm }: Props) {
  const [checked, setChecked] = useState<boolean[]>(MOTIFS.map(() => false))
  const [precisions, setPrecisions] = useState('')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    if (open) {
      setChecked(MOTIFS.map(() => false))
      setPrecisions('')
      setErrorMsg('')
    }
  }, [open])

  const handleConfirm = () => {
    const motifs = MOTIFS.filter((_, i) => checked[i])
    if (motifs.length === 0 && !precisions.trim()) {
      setErrorMsg("Merci de cocher un motif ou de remplir les informations complémentaires")
      return
    }
    onConfirm(motifs, precisions)
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/70 z-[70] flex items-center justify-center p-4"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-white rounded-xl shadow-2xl w-full max-w-xl p-6 space-y-4"
          >
            <h3 className="text-lg font-semibold text-c-ink">Annulation du produit</h3>
            <div className="text-sm text-c-ink-soft">Choisissez parmi ces motifs :</div>
            <div className="space-y-2.5">
              {MOTIFS.map((label, i) => (
                <label key={i} className="flex items-start gap-2 cursor-pointer text-sm">
                  <input
                    type="checkbox"
                    checked={checked[i]}
                    onChange={(e) => {
                      const next = [...checked]
                      next[i] = e.target.checked
                      setChecked(next)
                      if (e.target.checked) setErrorMsg('')
                    }}
                    className="accent-c-brand mt-0.5"
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-c-ink">Informations complémentaires :</label>
              <textarea
                value={precisions}
                onChange={(e) => {
                  setPrecisions(e.target.value)
                  if (e.target.value.trim()) setErrorMsg('')
                }}
                rows={3}
                className="w-full px-2 py-1.5 border border-c-line rounded text-sm bg-white focus:border-c-brand focus:ring-1 focus:ring-c-brand focus:outline-none resize-none"
              />
            </div>
            {errorMsg && (
              <div className="text-sm text-red-600 font-medium">{errorMsg}</div>
            )}
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={onCancel}
                disabled={loading}
                className="px-4 py-2 rounded border border-c-line-strong text-sm font-medium text-c-ink hover:bg-c-brand-soft disabled:opacity-60"
              >
                Annuler
              </button>
              <button
                onClick={handleConfirm}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 rounded bg-gray-900 text-white text-sm font-semibold hover:brightness-110 disabled:opacity-60"
              >
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                Enregistrer le motif
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
