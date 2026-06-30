/**
 * Modal picker bénéficiaire (salarié OU service).
 *
 * - mode='salarie' : recherche dans pgt_salarie (nom OU prénom contient)
 * - mode='service' : recherche dans pgt_organigramme (lib_orga contient)
 *
 * Utilisé depuis la page Suivi factures et toutes futures pages qui
 * ont besoin d'un picker de bénéficiaire.
 */
import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, X, Users, User } from 'lucide-react'
import { getToken } from '@/api'

interface Item { id: string; label: string; sous_label?: string }

interface Props {
  mode: 'salarie' | 'service'
  apiBase?: string
  onSelect: (item: Item) => void
  onClose: () => void
}

const API_BASE_DEFAULT = '/api/adm'

export default function BeneficiairePicker({
  mode, apiBase = API_BASE_DEFAULT, onSelect, onClose,
}: Props) {
  const [query, setQuery] = useState('')
  const [items, setItems] = useState<Item[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const ctl = new AbortController()
    setLoading(true)
    const url = `${apiBase}/factures/beneficiaires?mode=${mode}&q=${encodeURIComponent(query)}`
    fetch(url, {
      headers: { Authorization: `Bearer ${getToken()}` },
      signal: ctl.signal,
    })
      .then(r => r.ok ? r.json() : [])
      .then((d: Item[]) => setItems(Array.isArray(d) ? d : []))
      .catch(() => {})
      .finally(() => setLoading(false))
    return () => ctl.abort()
  }, [apiBase, mode, query])

  const title = mode === 'service'
    ? 'Choisir un service bénéficiaire'
    : 'Choisir un salarié bénéficiaire'
  const Icon = mode === 'service' ? Users : User
  const placeholder = mode === 'service'
    ? 'Filtrer par nom de service…'
    : 'Filtrer par nom ou prénom…'

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.96, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.96, opacity: 0 }}
          className="bg-white rounded-xl shadow-xl w-full max-w-md max-h-[80vh] flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="px-4 py-3 border-b border-c-line flex items-center gap-2">
            <Icon className="w-4 h-4 text-c-brand" />
            <h3 className="font-bold text-c-ink flex-1">{title}</h3>
            <button onClick={onClose}
              className="p-1 hover:bg-c-surface-soft rounded">
              <X className="w-4 h-4 text-c-ink-faint" />
            </button>
          </div>

          <div className="p-3 border-b border-c-line-soft">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-c-ink-faint" />
              <input autoFocus type="text" value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={placeholder}
                className="w-full pl-9 pr-3 py-2 border border-c-line rounded text-sm" />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <p className="text-sm text-center py-8 text-c-ink-faint italic">
                Chargement…
              </p>
            ) : items.length === 0 ? (
              <p className="text-sm text-center py-8 text-c-ink-faint italic">
                Aucun résultat
              </p>
            ) : (
              <ul className="divide-y divide-c-line-soft">
                {items.map((item) => (
                  <li key={item.id}>
                    <button type="button"
                      onClick={() => { onSelect(item); onClose() }}
                      className="w-full text-left px-4 py-2 hover:bg-c-surface-soft transition-colors">
                      <div className="text-sm text-c-ink">{item.label}</div>
                      {item.sous_label && (
                        <div className="text-xs text-c-ink-faint">{item.sous_label}</div>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
