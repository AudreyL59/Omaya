/**
 * Onglet 'Suivi ADM' de la fiche salarie ADM.
 *
 * Transposition de la fenetre WinDev FI_SalarieSuiviADM :
 *  - Tableau chronologique : Depose le | Depose par | Message
 *  - Textarea + bouton Ajouter pour saisir un nouveau memo
 * Pas de modification ni suppression cote UI (cf. WinDev).
 */

import { useCallback, useEffect, useState } from 'react'
import { Check, Loader2 } from 'lucide-react'

import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'

interface SuiviItem {
  id_salarie_suivi_adm: string
  op_crea_id: string
  op_crea_nom: string
  description: string
  date_crea: string
}

interface Props {
  idSalarie: string
}

function fmtDateTime(iso: string): string {
  if (!iso || iso.length < 10) return ''
  const d = `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
  if (iso.length < 16) return d
  return `${d} ${iso.slice(11, 16)}`
}

// Initiales : "LOUDIEUX Audrey" -> "LA"
const getInitials = (name: string): string => {
  if (!name) return '?'
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 1) return parts[0][0].toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

// Couleur deterministe par nom (palette OMAYA)
const _AVATAR_COLORS = [
  '#8B7355', '#17494E', '#B25E43', '#4E7C59',
  '#7A5D82', '#C77D3E', '#3D6B8C', '#8E4162',
]
const colorFromName = (name: string): string => {
  if (!name) return '#8B7355'
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) >>> 0
  }
  return _AVATAR_COLORS[hash % _AVATAR_COLORS.length]
}

export default function SuiviADMTab({ idSalarie }: Props) {
  const [items, setItems] = useState<SuiviItem[]>([])
  const [loading, setLoading] = useState(false)
  const [saisie, setSaisie] = useState('')
  const [sending, setSending] = useState(false)

  const reload = useCallback(async () => {
    if (!idSalarie) return
    setLoading(true)
    try {
      const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/suivi-adm`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const j = (await r.json()) as { items: SuiviItem[] }
      setItems(j.items || [])
    } catch (e) {
      showToast(`Échec chargement suivi ADM : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [idSalarie])

  useEffect(() => {
    void reload()
  }, [reload])

  const handleAjouter = async () => {
    if (!saisie.trim()) {
      showToast('Le mémo est vide.', 'info')
      return
    }
    setSending(true)
    try {
      const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/suivi-adm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ description: saisie }),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      setSaisie('')
      await reload()
      showToast('Mémo ajouté.', 'success')
    } catch (e) {
      showToast(`Échec ajout : ${(e as Error).message}`, 'error')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Liste memos - style cards + avatar (cf. FI_DetailDistributeur) */}
      <div className="max-h-[400px] overflow-y-auto">
        {loading && (
          <div className="p-3 flex items-center gap-2 text-xs" style={{ color: COLOR_BRUN }}>
            <Loader2 className="w-4 h-4 animate-spin" /> Chargement…
          </div>
        )}
        {!loading && items.length === 0 && (
          <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
            Aucun mémo déposé.
          </div>
        )}
        {!loading && items.length > 0 && (
          <ul className="space-y-3">
            {items.map((it) => {
              const initials = getInitials(it.op_crea_nom)
              const bg = colorFromName(it.op_crea_nom)
              return (
                <li
                  key={it.id_salarie_suivi_adm}
                  className="bg-white border rounded-lg p-3 shadow-sm hover:shadow transition-shadow"
                  style={{ borderColor: COLOR_BG_SOFT }}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className="shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-semibold"
                      style={{ backgroundColor: bg }}
                      title={it.op_crea_nom}
                    >
                      {initials}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline justify-between gap-2 mb-1">
                        <span
                          className="text-sm font-medium truncate"
                          style={{ color: COLOR_BRUN }}
                        >
                          {it.op_crea_nom || 'Inconnu'}
                        </span>
                        <span className="text-[11px] text-gray-500 shrink-0 tabular-nums">
                          {fmtDateTime(it.date_crea)}
                        </span>
                      </div>
                      <p
                        className="text-sm whitespace-pre-wrap break-words leading-relaxed"
                        style={{ color: '#3F3F3F' }}
                      >
                        {it.description}
                      </p>
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      {/* Saisie nouveau mémo */}
      <div className="flex flex-col gap-2 p-4 rounded" style={{ backgroundColor: COLOR_BG_SOFT }}>
        <label
          className="text-xs font-semibold uppercase tracking-wider"
          style={{ color: COLOR_BRUN }}
        >
          Saisir un nouveau mémo
        </label>
        <div className="flex items-start gap-3">
          <textarea
            value={saisie}
            onChange={(e) => setSaisie(e.target.value)}
            rows={3}
            className="flex-1 px-2 py-1 border rounded text-sm bg-white"
            style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN, resize: 'vertical' }}
            placeholder="Ton message…"
          />
          <button
            type="button"
            onClick={handleAjouter}
            disabled={sending || !saisie.trim()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded text-white disabled:opacity-40"
            style={{ backgroundColor: COLOR_PRIMARY }}
          >
            {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
            Ajouter
          </button>
        </div>
      </div>
    </div>
  )
}
