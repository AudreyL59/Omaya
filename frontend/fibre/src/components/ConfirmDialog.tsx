/**
 * Dialog de confirmation generique pour les actions du panier Call Fibre.
 * Reproduit POPUP_ValideVente / POPUP_AnnulVente / POPUP_RenvoiPanier WinDev.
 */

import { motion, AnimatePresence } from 'framer-motion'
import { Loader2 } from 'lucide-react'

interface Props {
  open: boolean
  title: string
  confirmLabel: string
  confirmColor: 'green' | 'red' | 'orange'
  loading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export default function ConfirmDialog({
  open,
  title,
  confirmLabel,
  confirmColor,
  loading,
  onConfirm,
  onCancel,
}: Props) {
  const btnCls =
    confirmColor === 'green'
      ? 'bg-green-600 hover:bg-green-700'
      : confirmColor === 'red'
        ? 'bg-red-600 hover:bg-red-700'
        : 'bg-orange-500 hover:bg-orange-600'
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
            className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6 text-center space-y-5"
          >
            <h3 className="text-lg font-semibold text-c-ink">{title}</h3>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={onCancel}
                disabled={loading}
                className="px-4 py-2 rounded border border-c-line-strong text-sm font-medium text-c-ink hover:bg-c-brand-soft disabled:opacity-60"
              >
                Annuler
              </button>
              <button
                onClick={onConfirm}
                disabled={loading}
                className={`flex items-center gap-2 px-4 py-2 rounded text-white text-sm font-semibold disabled:opacity-60 ${btnCls}`}
              >
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                {confirmLabel}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
