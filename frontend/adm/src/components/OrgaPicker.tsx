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
              placeholder="Nom de l'agence ou equipe"
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

          {/* Selection courante */}
          {selected.length > 0 && (
            <div className="flex flex-wrap gap-1.5 p-2 bg-white rounded-lg border border-[#E5DDDC]">
              <span className="text-[10px] uppercase tracking-wide text-[#A68D8A] font-semibold self-center mr-1">
                Selection ({selected.length}) :
              </span>
              {selected.map((s) => (
                <span
                  key={s.id_orga}
                  className="inline-flex items-center gap-1 bg-white border border-[#E5DDDC] rounded-full px-2 py-0.5 text-xs"
                >
                  {s.lib_orga}
                  <button
                    onClick={() => toggle(s)}
                    className="text-[#A68D8A]/80 hover:text-[#4E1D17]"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Resultats de recherche */}
          <div className="max-h-72 overflow-y-auto border border-[#E5DDDC] rounded-lg">
            {results.length === 0 ? (
              <div className="text-center py-8 text-[#A68D8A]/80 text-sm">
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
                    className={`w-full text-left px-4 py-2.5 text-sm border-b border-[#E5DDDC] last:border-0 hover:bg-[#EFE9E7] flex items-start gap-2 ${
                      checked ? 'bg-white' : ''
                    }`}
                  >
                    <div
                      className={`shrink-0 mt-0.5 w-4 h-4 rounded border flex items-center justify-center ${
                        checked
                          ? 'bg-[#17494E] border-[#17494E] text-white'
                          : 'border-[#E5DDDC] bg-white'
                      }`}
                    >
                      {checked && <Check className="w-3 h-3" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Building2 className="w-3.5 h-3.5 text-[#A68D8A]/80 shrink-0" />
                        <span className="font-medium text-[#4E1D17]">{r.lib_orga}</span>
                        {r.lib_niveau && (
                          <span className="text-[10px] uppercase tracking-wide text-[#A68D8A]/80 bg-[#EFE9E7] px-1.5 py-0.5 rounded">
                            {r.lib_niveau}
                          </span>
                        )}
                      </div>
                      {r.lib_parent && (
                        <div className="text-[11px] text-[#A68D8A]/80 mt-0.5 ml-5">
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
              className="flex-1 px-3 py-2.5 bg-[#17494E] text-white rounded-lg text-sm font-medium hover:bg-[#17494E]/90 disabled:opacity-50"
            >
              Valider ({selected.length})
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
