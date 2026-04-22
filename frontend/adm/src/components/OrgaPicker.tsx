import { useState } from 'react'
import { motion } from 'framer-motion'
import { X, Search, Loader2, Building2, Check } from 'lucide-react'
import { getToken } from '@/api'

export interface OrgaItem {
  id_orga: string  // string pour preserver la precision (ids > 2^53)
  lib_orga: string
  lib_niveau: string
  lib_parent: string
}

export default function OrgaPicker({
  onClose,
  onSelect,
  title = 'Choisir des agences ou equipes',
  initialSelected = [],
}: {
  onClose: () => void
  onSelect: (orgas: OrgaItem[]) => void
  title?: string
  initialSelected?: OrgaItem[]
}) {
  const [search, setSearch] = useState('')
  const [results, setResults] = useState<OrgaItem[]>([])
  const [selected, setSelected] = useState<OrgaItem[]>(initialSelected)
  const [loading, setLoading] = useState(false)

  const doSearch = () => {
    if (!search.trim()) return
    setLoading(true)
    fetch(
      `/api/adm/organigrammes/search?q=${encodeURIComponent(search.trim())}`,
      { headers: { Authorization: `Bearer ${getToken()}` } }
    )
      .then((r) => r.json())
      .then(setResults)
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  const toggle = (o: OrgaItem) => {
    setSelected((prev) => {
      const exists = prev.find((x) => x.id_orga === o.id_orga)
      if (exists) return prev.filter((x) => x.id_orga !== o.id_orga)
      return [...prev, o]
    })
  }

  const isSelected = (o: OrgaItem) =>
    selected.some((x) => x.id_orga === o.id_orga)

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
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-3">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Nom de l'agence ou equipe"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) =>
                e.key === 'Enter' && (e.preventDefault(), doSearch())
              }
              autoFocus
              className="flex-1 px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
            />
            <button
              type="button"
              onClick={doSearch}
              className="px-3 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4 text-gray-700" />
              )}
            </button>
          </div>

          {/* Selection courante */}
          {selected.length > 0 && (
            <div className="flex flex-wrap gap-1.5 p-2 bg-gray-50 rounded-lg border border-gray-200">
              <span className="text-[10px] uppercase tracking-wide text-gray-500 font-semibold self-center mr-1">
                Selection ({selected.length}) :
              </span>
              {selected.map((s) => (
                <span
                  key={s.id_orga}
                  className="inline-flex items-center gap-1 bg-white border border-gray-300 rounded-full px-2 py-0.5 text-xs"
                >
                  {s.lib_orga}
                  <button
                    onClick={() => toggle(s)}
                    className="text-gray-400 hover:text-gray-700"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Resultats de recherche */}
          <div className="max-h-72 overflow-y-auto border border-gray-200 rounded-lg">
            {results.length === 0 ? (
              <div className="text-center py-8 text-gray-400 text-sm">
                {loading ? '' : "Saisis un nom d'agence ou d'equipe pour rechercher"}
              </div>
            ) : (
              results.map((r) => {
                const checked = isSelected(r)
                return (
                  <button
                    key={r.id_orga}
                    type="button"
                    onClick={() => toggle(r)}
                    className={`w-full text-left px-4 py-2.5 text-sm border-b border-gray-100 last:border-0 hover:bg-gray-50 flex items-start gap-2 ${
                      checked ? 'bg-gray-50' : ''
                    }`}
                  >
                    <div
                      className={`shrink-0 mt-0.5 w-4 h-4 rounded border flex items-center justify-center ${
                        checked
                          ? 'bg-gray-900 border-gray-900 text-white'
                          : 'border-gray-300 bg-white'
                      }`}
                    >
                      {checked && <Check className="w-3 h-3" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Building2 className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                        <span className="font-medium text-gray-900">{r.lib_orga}</span>
                        {r.lib_niveau && (
                          <span className="text-[10px] uppercase tracking-wide text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                            {r.lib_niveau}
                          </span>
                        )}
                      </div>
                      {r.lib_parent && (
                        <div className="text-[11px] text-gray-400 mt-0.5 ml-5">
                          {r.lib_parent}
                        </div>
                      )}
                    </div>
                  </button>
                )
              })
            )}
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={() => onSelect(selected)}
              disabled={selected.length === 0}
              className="flex-1 px-3 py-2.5 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50"
            >
              Valider ({selected.length})
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-3 py-2.5 border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50"
            >
              Annuler
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}
