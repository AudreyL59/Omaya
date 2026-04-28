import { useState } from 'react'
import { motion } from 'framer-motion'
import { X, Search, Loader2 } from 'lucide-react'
import { getToken } from '@/api'

export interface SalarieItem {
  id_salarie: string
  nom: string
  prenom: string
}

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : s
}

export default function PersonnePicker({
  onClose,
  onSelect,
  title = 'Choisir une personne',
}: {
  onClose: () => void
  onSelect: (s: SalarieItem) => void
  title?: string
}) {
  const [search, setSearch] = useState('')
  const [results, setResults] = useState<SalarieItem[]>([])
  const [selected, setSelected] = useState<SalarieItem | null>(null)
  const [loading, setLoading] = useState(false)

  const doSearch = () => {
    if (!search.trim()) return
    setLoading(true)
    fetch(
      `/api/adm/salaries/search?q=${encodeURIComponent(search.trim())}`,
      { headers: { Authorization: `Bearer ${getToken()}` } }
    )
      .then((r) => r.json())
      .then(setResults)
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E5DDDC]">
          <h2 className="text-lg font-semibold text-[#4E1D17]">{title}</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-[#EFE9E7] text-[#A68D8A]/80 hover:text-[#4E1D17]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-3">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Nom ou prenom"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) =>
                e.key === 'Enter' && (e.preventDefault(), doSearch())
              }
              autoFocus
              className="flex-1 px-3 py-2.5 border border-[#E5DDDC] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#17494E] focus:border-transparent"
            />
            <button
              type="button"
              onClick={doSearch}
              className="px-3 py-2.5 border border-[#E5DDDC] rounded-lg hover:bg-[#EFE9E7]"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4 text-[#4E1D17]" />
              )}
            </button>
          </div>

          <div className="max-h-64 overflow-y-auto border border-[#E5DDDC] rounded-lg">
            {results.length === 0 ? (
              <div className="text-center py-8 text-[#A68D8A]/80 text-sm">
                {loading ? '' : 'Saisis un nom pour rechercher'}
              </div>
            ) : (
              results.map((r) => (
                <button
                  key={r.id_salarie}
                  type="button"
                  onClick={() => setSelected(r)}
                  className={`w-full text-left px-4 py-2.5 text-sm border-b border-[#E5DDDC] last:border-0 hover:bg-[#EFE9E7] ${
                    selected?.id_salarie === r.id_salarie ? 'bg-[#EFE9E7]' : ''
                  }`}
                >
                  <span className="font-medium text-[#4E1D17]">{r.nom}</span>{' '}
                  <span className="text-[#4E1D17]/80">{capitalize(r.prenom)}</span>
                </button>
              ))
            )}
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={() => selected && onSelect(selected)}
              disabled={!selected}
              className="flex-1 px-3 py-2.5 bg-[#17494E] text-white rounded-lg text-sm font-medium hover:bg-[#17494E]/90 disabled:opacity-50"
            >
              Valider
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-3 py-2.5 border border-[#E5DDDC] rounded-lg text-sm font-medium hover:bg-[#EFE9E7]"
            >
              Annuler
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}
