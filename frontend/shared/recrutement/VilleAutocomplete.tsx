/**
 * VilleAutocomplete — picker de commune (CP + ville) reutilisable.
 *
 * Autocomplete debouncee : tape -> liste s'affiche en dessous, click
 * pour selectionner. Une fois selectionne, montre 'CP Ville' + bouton X
 * pour deselectionner.
 *
 * Utilise par CVSaisieModal, LieuRDVEditModal, CVFicheModal.
 */

import { useEffect, useRef, useState } from 'react'
import { Loader2, X } from 'lucide-react'
import { getToken } from '@/api'

const COL_BRUN = '#4E1D17'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface Commune {
  id_communes_france: string
  code_postal: string
  nom_ville: string
}

interface VilleAutocompleteProps {
  apiBase: string
  value: string                                  // id_communes_france ('' ou '0' = vide)
  label?: string                                 // affichage 'CP Ville' quand selectionne
  onChange: (id: string, cp: string, ville: string) => void
  placeholder?: string
  disabled?: boolean
}

export default function VilleAutocomplete({
  apiBase, value, label = '', onChange,
  placeholder = 'Tape un CP ou une ville',
  disabled = false,
}: VilleAutocompleteProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Commune[]>([])
  const [searching, setSearching] = useState(false)
  const [open, setOpen] = useState(false)
  const debounceRef = useRef<number | null>(null)
  const wrapRef = useRef<HTMLDivElement | null>(null)

  // Fetch debounced sur la saisie
  useEffect(() => {
    if (debounceRef.current) window.clearTimeout(debounceRef.current)
    if (query.trim().length < 2) {
      setResults([])
      return
    }
    debounceRef.current = window.setTimeout(() => {
      setSearching(true)
      fetch(
        `${apiBase}/recrutement/cv/communes?q=${encodeURIComponent(query.trim())}&limit=30`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
        .then(r => r.ok ? r.json() : [])
        .then((d: Commune[]) => {
          setResults(Array.isArray(d) ? d : [])
          setOpen(true)
        })
        .finally(() => setSearching(false))
    }, 250)
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current)
    }
  }, [query, apiBase])

  // Fermer le dropdown au clic exterieur
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Mode lecture : valeur deja choisie
  if (value && value !== '0') {
    return (
      <div className="flex items-center gap-1">
        <div className="flex-1 px-2 py-1.5 rounded border bg-gray-50 text-sm"
             style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
          {label || `#${value}`}
        </div>
        {!disabled && (
          <button type="button" onClick={() => onChange('', '', '')}
                  className="p-1 text-red-600 hover:text-red-800"
                  title="Désélectionner">
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    )
  }

  // Mode saisie
  return (
    <div ref={wrapRef} className="relative">
      <div className="flex items-center gap-1">
        <input type="text" value={query}
               onChange={e => setQuery(e.target.value.toUpperCase())}
               onFocus={() => { if (results.length > 0) setOpen(true) }}
               placeholder={placeholder}
               disabled={disabled}
               className="flex-1 px-2 py-1.5 rounded border text-sm"
               style={{ borderColor: COL_BORDER }} />
        {searching && (
          <Loader2 className="w-3.5 h-3.5 animate-spin"
                   style={{ color: COL_BRUN }} />
        )}
      </div>
      {open && results.length > 0 && (
        <div className="absolute z-30 left-0 right-0 mt-1 border rounded shadow-lg max-h-56 overflow-y-auto"
             style={{ borderColor: COL_BORDER, backgroundColor: 'white' }}>
          {results.map(r => (
            <button key={r.id_communes_france} type="button"
                    onClick={() => {
                      onChange(r.id_communes_france, r.code_postal, r.nom_ville)
                      setQuery(''); setResults([]); setOpen(false)
                    }}
                    className="block w-full text-left px-2 py-1.5 text-xs hover:bg-blue-50"
                    style={{ color: COL_BRUN, backgroundColor: 'white' }}>
              <strong>{r.code_postal}</strong> {r.nom_ville}
            </button>
          ))}
        </div>
      )}
      {open && !searching && query.trim().length >= 2 && results.length === 0 && (
        <div className="absolute z-30 left-0 right-0 mt-1 border rounded shadow-lg p-3 text-xs italic"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT, color: '#A68D8A' }}>
          Aucune commune trouvée.
        </div>
      )}
    </div>
  )
}
