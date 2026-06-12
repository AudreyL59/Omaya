/**
 * Onglet 'Déclaratif' de la fiche salarie ADM.
 *
 * Transposition de la fenetre WinDev FI_SalarieDeclaratif (lecture seule).
 * 2 dates (Du / Au) + bouton loupe → tableau filtré.
 * Colonnes : DATE | Presence | Motif Absence (uniquement si presence = faux).
 */

import { useCallback, useEffect, useState } from 'react'
import { Loader2, Search } from 'lucide-react'

import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'
import CheckMark from '../CheckMark'

interface DeclItem {
  date: string
  presence: boolean
  motif_absence: string
}

interface Props {
  idSalarie: string
}

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

function defaultDu(): string {
  // 1er du mois en cours (filtre par defaut large mais pas excessif)
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  return `${y}-${m}-01`
}

function defaultAu(): string {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export default function DeclaratifTab({ idSalarie }: Props) {
  const [du, setDu] = useState<string>(defaultDu())
  const [au, setAu] = useState<string>(defaultAu())
  const [items, setItems] = useState<DeclItem[]>([])
  const [loading, setLoading] = useState(false)

  const search = useCallback(async () => {
    if (!idSalarie) return
    if (!du || !au) {
      showToast('Renseignez une période (Du / Au).', 'info')
      return
    }
    setLoading(true)
    try {
      const url =
        `/api/adm/fiche-salarie/${idSalarie}/declaratif` +
        `?date_du=${encodeURIComponent(du)}&date_au=${encodeURIComponent(au)}`
      const r = await fetch(url, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const j = (await r.json()) as DeclItem[]
      setItems(Array.isArray(j) ? j : [])
    } catch (e) {
      showToast(`Échec chargement déclaratif : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [idSalarie, du, au])

  // Chargement initial
  useEffect(() => {
    void search()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idSalarie])

  const template = '140px 90px 1fr'

  return (
    <div className="flex flex-col gap-3 h-full">
      {/* Toolbar : Du / Au + loupe */}
      <div className="flex items-end gap-3 flex-shrink-0">
        <div className="flex flex-col">
          <label className="text-xs mb-1" style={{ color: COLOR_BRUN }}>
            Du
          </label>
          <div
            className="px-2 py-1 rounded border bg-white"
            style={{ borderColor: COLOR_BG_SOFT }}
          >
            <input
              type="date"
              value={du}
              onChange={(e) => setDu(e.target.value)}
              className="text-xs"
            />
          </div>
        </div>
        <div className="flex flex-col">
          <label className="text-xs mb-1" style={{ color: COLOR_BRUN }}>
            Au
          </label>
          <div
            className="px-2 py-1 rounded border bg-white"
            style={{ borderColor: COLOR_BG_SOFT }}
          >
            <input
              type="date"
              value={au}
              onChange={(e) => setAu(e.target.value)}
              className="text-xs"
            />
          </div>
        </div>
        <button
          type="button"
          onClick={() => void search()}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded border disabled:opacity-40"
          style={{ backgroundColor: COLOR_PRIMARY, color: 'white', borderColor: COLOR_PRIMARY }}
          title="Lancer la recherche"
        >
          <Search className="w-4 h-4" />
          Rechercher
        </button>
        {loading && (
          <Loader2 className="w-4 h-4 animate-spin" style={{ color: COLOR_PRIMARY }} />
        )}
      </div>

      {/* Tableau */}
      <div
        className="flex-1 border rounded overflow-hidden flex flex-col"
        style={{ borderColor: COLOR_BG_SOFT }}
      >
        {/* Header */}
        <div
          className="grid items-center gap-2 px-3 py-2 text-xs font-semibold border-b"
          style={{
            gridTemplateColumns: template,
            color: COLOR_BRUN,
            backgroundColor: COLOR_BG_SOFT,
            borderColor: COLOR_BG_SOFT,
          }}
        >
          <div>Date</div>
          <div className="text-center">Présence</div>
          <div>Motif absence</div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {!loading && items.length === 0 && (
            <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
              Aucune déclaration sur cette période.
            </div>
          )}
          {items.map((it, idx) => (
            <div
              key={`${it.date}-${idx}`}
              className="grid items-center gap-2 px-3 py-1.5 text-xs border-b"
              style={{
                gridTemplateColumns: template,
                borderColor: COLOR_BG_SOFT,
                color: COLOR_BRUN,
                backgroundColor: 'white',
              }}
            >
              <div>{fmtDate(it.date)}</div>
              <div className="text-center">
                <CheckMark active={it.presence} />
              </div>
              <div className="truncate" title={it.motif_absence}>
                {it.motif_absence}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
