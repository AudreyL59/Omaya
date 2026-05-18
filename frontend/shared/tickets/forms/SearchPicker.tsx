import { useEffect, useState } from 'react'
import { Loader2, Search, X } from 'lucide-react'

// Picker générique : recherche debounce sur un endpoint, liste cliquable.
// Réutilisé pour les salariés (Coopteur/JO) et les équipes (organigramme).
export interface PickerItem {
  id: string
  label: string
  sublabel?: string
}

export default function SearchPicker({
  apiBase,
  getToken,
  title,
  path, // ex: '/tickets/salaries/search'
  mapItem,
  onPick,
  onClose,
}: {
  apiBase: string
  getToken: () => string | null
  title: string
  path: string
  mapItem: (raw: any) => PickerItem
  onPick: (item: PickerItem) => void
  onClose: () => void
}) {
  const [q, setQ] = useState('')
  const [items, setItems] = useState<PickerItem[]>([])
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    const term = q.trim()
    if (term.length < 1) {
      setItems([])
      return
    }
    setSearching(true)
    const t = setTimeout(() => {
      fetch(`${apiBase}${path}?q=${encodeURIComponent(term)}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
        .then((r) => r.json())
        .then((d) => setItems(Array.isArray(d) ? d.map(mapItem) : []))
        .catch(() => setItems([]))
        .finally(() => setSearching(false))
    }, 300)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, apiBase, path])

  return (
    <>
      <div className="fixed inset-0 z-[80] bg-black/30" onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-[90] bg-white rounded-2xl shadow-xl border border-c-line w-96 p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="flex items-center gap-2 text-base font-semibold text-c-ink">
            <Search className="w-5 h-5 text-c-brand" />
            {title}
          </span>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-c-ink-faint hover:bg-c-surface-medium transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Rechercher…"
          className="w-full px-3 py-2 mb-3 border border-c-line-strong rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-c-brand-line"
        />
        <div className="max-h-72 overflow-auto -mx-1">
          {searching ? (
            <div className="p-4 flex justify-center">
              <Loader2 className="w-4 h-4 text-c-ink-icon animate-spin" />
            </div>
          ) : items.length === 0 ? (
            <div className="p-4 text-xs text-c-ink-faint text-center">
              {q.trim() ? 'Aucun résultat.' : 'Saisis un terme.'}
            </div>
          ) : (
            <ul>
              {items.map((it) => (
                <li key={it.id}>
                  <button
                    onClick={() => onPick(it)}
                    className="w-full text-left px-3 py-2 rounded-lg hover:bg-c-brand-soft transition-colors"
                  >
                    <div className="text-sm text-c-ink">{it.label}</div>
                    {it.sublabel && (
                      <div className="text-xs text-c-ink-soft truncate">
                        {it.sublabel}
                      </div>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </>
  )
}
