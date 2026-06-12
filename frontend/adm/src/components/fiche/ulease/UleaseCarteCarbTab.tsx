/**
 * Sous-onglet 'Attribution Carte Carburant' de l'onglet Ulease.
 *
 * Tableau CarteAttribution JOIN CarteCarburant.
 * 3 boutons :
 *  - +       : ajouter (placeholder Fen_AttCarteCarb – module Parc Auto)
 *  - crayon  : modifier (placeholder)
 *  - suppr   : soft delete
 */

import { useCallback, useEffect, useState } from 'react'
import { Loader2, Pencil, Plus, Trash2 } from 'lucide-react'

import { getToken } from '@/api'
import { showConfirm, showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'

interface AttItem {
  id_carte_attribution: string
  num_carte: string
  du: string
  au: string
}

interface Props {
  idConducteur: string
}

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

export default function UleaseCarteCarbTab({ idConducteur }: Props) {
  const [items, setItems] = useState<AttItem[]>([])
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)

  const reload = useCallback(async () => {
    if (!idConducteur) return
    setLoading(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/ulease/${idConducteur}/attribution-carte`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const j = (await r.json()) as AttItem[]
      setItems(Array.isArray(j) ? j : [])
    } catch (e) {
      showToast(`Échec chargement attributions : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [idConducteur])

  useEffect(() => {
    void reload()
  }, [reload])

  const selectedItem = items.find((i) => i.id_carte_attribution === selected) || null

  const handleNouveau = () =>
    showToast(
      'Attribution carte carburant : à implémenter (Fen_AttCarteCarb – module Parc Auto).',
      'info',
    )

  const handleModifier = () => {
    if (!selectedItem) {
      showToast('Sélectionner une attribution.', 'info')
      return
    }
    showToast(
      'Modification attribution : à implémenter (Fen_AttCarteCarb).',
      'info',
    )
  }

  const handleSupprimer = async () => {
    if (!selectedItem) {
      showToast('Sélectionner une attribution.', 'info')
      return
    }
    const ok = await showConfirm({
      title: 'Supprimer cette attribution ?',
      message: 'Vous êtes sur le point de supprimer cette attribution de carte carburant. Voulez-vous continuer ?',
      confirmLabel: 'Supprimer',
      variant: 'danger',
    })
    if (!ok) return
    setBusy(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/ulease/attribution-carte/${selectedItem.id_carte_attribution}`,
        { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      setSelected(null)
      await reload()
      showToast('Attribution supprimée.', 'success')
    } catch (e) {
      showToast(`Échec suppression : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const template = '1fr 110px 110px'

  return (
    <div className="flex flex-col gap-2 h-full">
      <div className="flex items-center gap-2 flex-shrink-0">
        <ToolBtn icon={Plus} label="Nouveau" onClick={handleNouveau} primary />
        <ToolBtn
          icon={Pencil}
          label="Modifier"
          onClick={handleModifier}
          disabled={!selectedItem || busy}
        />
        <ToolBtn
          icon={Trash2}
          label="Supprimer"
          onClick={() => void handleSupprimer()}
          disabled={!selectedItem || busy}
          danger
        />
        {(loading || busy) && (
          <Loader2 className="w-4 h-4 animate-spin ml-2" style={{ color: COLOR_PRIMARY }} />
        )}
      </div>

      <div
        className="flex-1 border rounded overflow-hidden flex flex-col"
        style={{ borderColor: COLOR_BG_SOFT }}
      >
        <div
          className="grid items-center gap-2 px-3 py-2 text-xs font-semibold border-b"
          style={{
            gridTemplateColumns: template,
            color: COLOR_BRUN,
            backgroundColor: COLOR_BG_SOFT,
            borderColor: COLOR_BG_SOFT,
          }}
        >
          <div>Numéro de carte</div>
          <div>Du</div>
          <div>Au</div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {!loading && items.length === 0 && (
            <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
              Aucune attribution.
            </div>
          )}
          {items.map((it) => {
            const sel = selected === it.id_carte_attribution
            return (
              <div
                key={it.id_carte_attribution}
                onClick={() => setSelected(it.id_carte_attribution)}
                className="grid items-center gap-2 px-3 py-1.5 text-xs border-b cursor-pointer"
                style={{
                  gridTemplateColumns: template,
                  backgroundColor: sel ? COLOR_BG_SOFT : 'white',
                  borderColor: COLOR_BG_SOFT,
                  color: COLOR_BRUN,
                }}
              >
                <div className="font-medium">{it.num_carte || '—'}</div>
                <div>{fmtDate(it.du)}</div>
                <div>{fmtDate(it.au)}</div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function ToolBtn({
  icon: Icon,
  label,
  onClick,
  disabled,
  primary,
  danger,
}: {
  icon: typeof Plus
  label: string
  onClick: () => void
  disabled?: boolean
  primary?: boolean
  danger?: boolean
}) {
  const color = primary ? 'white' : danger ? '#B91C1C' : COLOR_PRIMARY
  const bg = primary ? COLOR_PRIMARY : 'white'
  const border = primary ? COLOR_PRIMARY : danger ? '#B91C1C' : COLOR_PRIMARY
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded border disabled:opacity-40"
      style={{ backgroundColor: bg, color, borderColor: border }}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  )
}
