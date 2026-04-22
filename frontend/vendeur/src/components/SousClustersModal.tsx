import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2, X } from 'lucide-react'
import { getToken } from '@/api'
import ClusterCard, { type ClusterData } from '@/components/ClusterCard'

interface SousClustersModalProps {
  open: boolean
  onClose: () => void
  parent: ClusterData | null
  moisDu: number
  anneeDu: number
  moisAu: number
  anneeAu: number
  jetons: string[]
}

export default function SousClustersModal({
  open,
  onClose,
  parent,
  moisDu,
  anneeDu,
  moisAu,
  anneeAu,
  jetons,
}: SousClustersModalProps) {
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<ClusterData[]>([])

  useEffect(() => {
    if (!open || !parent) return
    setLoading(true)

    const params = new URLSearchParams({
      mois_du: String(moisDu),
      annee_du: String(anneeDu),
      mois_au: String(moisAu),
      annee_au: String(anneeAu),
      code_vad: parent.code_vad_full,
    })
    jetons.forEach((j) => params.append('jetons', j))

    fetch(`/api/vendeur/clusters?${params.toString()}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d: ClusterData[]) => setItems(Array.isArray(d) ? d : []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [open, parent, moisDu, anneeDu, moisAu, anneeAu, jetons])

  return (
    <AnimatePresence>
      {open && parent && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2 }}
            className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl max-h-[85vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Sous-clusters · {parent.nom}
                </h2>
                <p className="text-sm text-gray-500 mt-0.5">
                  Détail par code VAD
                </p>
              </div>
              <button
                onClick={onClose}
                className="p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {loading ? (
                <div className="flex items-center justify-center h-48">
                  <Loader2 className="w-6 h-6 text-gray-300 animate-spin" />
                </div>
              ) : items.length === 0 ? (
                <div className="text-center py-12 text-gray-400 text-sm">
                  Aucun sous-cluster sur cette période.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {items.map((c) => (
                    <ClusterCard key={c.code_vad_full} cluster={c} />
                  ))}
                </div>
              )}
            </div>

            <div className="flex justify-end px-6 py-3 border-t border-gray-200">
              <button
                onClick={onClose}
                className="px-5 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors"
              >
                Fermer
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
