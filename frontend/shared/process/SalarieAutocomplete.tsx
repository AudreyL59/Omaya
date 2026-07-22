// Autocomplete salaries pour le modal droits d'acces Process.
// Debounce 250ms, fetch backend /process/salaries-search?q=.

import { useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'

import { searchSalaries } from './api'
import type { SalarieHit } from './types'

type Ctx = { apiBase: string; getToken: () => string | null }

export default function SalarieAutocomplete({
  ctx, value, valueLib, onChange, placeholder,
}: {
  ctx: Ctx
  value: string           // id_salarie ou ''
  valueLib: string        // 'NOM Prenom' du salarie deja selectionne (affichage)
  onChange: (id: string, lib: string) => void
  placeholder?: string
}) {
  const [q, setQ] = useState('')
  const [hits, setHits] = useState<SalarieHit[]>([])
  const [open, setOpen] = useState(false)
  const wrap = useRef<HTMLDivElement>(null)

  // Debounce recherche
  useEffect(() => {
    if (!open) return
    if (q.trim().length < 2) { setHits([]); return }
    const iv = setTimeout(() => {
      void searchSalaries(ctx, q).then(r => setHits(Array.isArray(r) ? r : []))
    }, 250)
    return () => clearTimeout(iv)
  }, [q, open, ctx])

  // Fermeture au clic exterieur
  useEffect(() => {
    if (!open) return
    const onDoc = (e: MouseEvent) => {
      if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])

  // Si un salarié est déjà sélectionné : affichage compact avec X pour changer
  if (value) {
    return (
      <div className="flex items-center gap-1 border border-c-line rounded px-2 py-1.5 bg-c-brand-soft">
        <span className="flex-1 text-sm truncate text-c-brand font-medium">
          {valueLib || `#${value}`}
        </span>
        <button type="button" onClick={() => onChange('', '')}
          className="text-red-600 hover:bg-red-50 rounded p-0.5"
          aria-label="Retirer">
          <X className="w-3 h-3" />
        </button>
      </div>
    )
  }

  return (
    <div ref={wrap} className="relative">
      <input value={q}
        onChange={e => { setQ(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
        placeholder={placeholder || 'Nom ou prénom (≥ 2 lettres)…'}
        className="w-full border border-c-line rounded px-2 py-1.5 text-sm bg-white" />
      {open && hits.length > 0 && (
        <div className="absolute z-30 top-full left-0 right-0 mt-1 bg-white border border-c-line-soft rounded shadow-lg max-h-64 overflow-y-auto">
          {hits.map(h => (
            <button key={h.ID} type="button"
              onMouseDown={e => e.preventDefault()}
              onClick={() => {
                onChange(h.ID, h.Lib)
                setQ(''); setHits([]); setOpen(false)
              }}
              className="w-full text-left px-2 py-1.5 text-sm hover:bg-c-brand-soft">
              <b>{h.Nom}</b> {h.Prenom}
            </button>
          ))}
        </div>
      )}
      {open && q.trim().length >= 2 && hits.length === 0 && (
        <div className="absolute z-30 top-full left-0 right-0 mt-1 bg-white border border-c-line-soft rounded shadow-lg p-2 text-xs italic text-c-ink-faint">
          Aucun résultat
        </div>
      )}
    </div>
  )
}
