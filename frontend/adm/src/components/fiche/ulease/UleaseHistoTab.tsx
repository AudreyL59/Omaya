/**
 * Sous-onglet 'Historique Attribution' de l'onglet Ulease.
 *
 * Tableau vehicule_conducteur JOIN vehicule_fiche.
 * 2 boutons (en placeholder, en attente des fenetres Parc Auto / SalarieDocUlease) :
 *  - Voir la fiche véhicule
 *  - Générer la mise à dispo
 */

import { useCallback, useEffect, useState } from 'react'
import { ExternalLink, FileText, Loader2 } from 'lucide-react'

import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'
import CheckMark from '../../CheckMark'
import SalarieDocUleaseModal from './SalarieDocUleaseModal'

interface HistoItem {
  id_vehicule_pc: string
  id_vehicule: string
  immat: string
  temporaire: boolean
  perception_date: string
  perception_heure: string
  restitution_date: string
  restitution_heure: string
}

interface Props {
  idConducteur: string
}

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

function fmtHeure(h: string): string {
  return h ? h.slice(0, 5) : ''
}

export default function UleaseHistoTab({ idConducteur }: Props) {
  const [items, setItems] = useState<HistoItem[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)
  const [docOpen, setDocOpen] = useState(false)

  const reload = useCallback(async () => {
    if (!idConducteur) return
    setLoading(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/ulease/${idConducteur}/histo-attribution`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const j = (await r.json()) as HistoItem[]
      setItems(Array.isArray(j) ? j : [])
    } catch (e) {
      showToast(`Échec chargement historique : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [idConducteur])

  useEffect(() => {
    void reload()
  }, [reload])

  const selectedItem = items.find((i) => i.id_vehicule_pc === selected) || null

  const template = '110px 70px 1fr 90px 70px 90px 70px'

  return (
    <div className="flex flex-col gap-2 h-full">
      <div className="flex items-center gap-2 flex-shrink-0">
        <ToolBtn
          icon={ExternalLink}
          label="Voir la fiche véhicule"
          onClick={() =>
            showToast(
              'Fiche véhicule : à implémenter (Fen_FicheVehicule – module Parc Auto).',
              'info',
            )
          }
          disabled={!selectedItem}
        />
        <ToolBtn
          icon={FileText}
          label="Générer la mise à dispo"
          onClick={() => {
            if (!selectedItem) {
              showToast('Sélectionner une attribution.', 'info')
              return
            }
            setDocOpen(true)
          }}
          disabled={!selectedItem}
        />
        {loading && (
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
          <div>IMMAT</div>
          <div className="text-center">Tempo</div>
          <div />
          <div>Du</div>
          <div>Heure</div>
          <div>Au</div>
          <div>Heure</div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {!loading && items.length === 0 && (
            <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
              Aucun véhicule attribué.
            </div>
          )}
          {items.map((it) => {
            const sel = selected === it.id_vehicule_pc
            return (
              <div
                key={it.id_vehicule_pc}
                onClick={() => setSelected(it.id_vehicule_pc)}
                className="grid items-center gap-2 px-3 py-1.5 text-xs border-b cursor-pointer"
                style={{
                  gridTemplateColumns: template,
                  backgroundColor: sel ? COLOR_BG_SOFT : 'white',
                  borderColor: COLOR_BG_SOFT,
                  color: COLOR_BRUN,
                }}
              >
                <div className="font-medium">{it.immat || '—'}</div>
                <div className="text-center">
                  <CheckMark active={it.temporaire} />
                </div>
                <div />
                <div>{fmtDate(it.perception_date)}</div>
                <div>{fmtHeure(it.perception_heure)}</div>
                <div>{fmtDate(it.restitution_date)}</div>
                <div>{fmtHeure(it.restitution_heure)}</div>
              </div>
            )
          })}
        </div>
      </div>

      {docOpen && selectedItem && (
        <SalarieDocUleaseModal
          idSalarie={idConducteur}
          idVehiculePC={selectedItem.id_vehicule_pc}
          onClose={() => setDocOpen(false)}
        />
      )}
    </div>
  )
}

function ToolBtn({
  icon: Icon,
  label,
  onClick,
  disabled,
}: {
  icon: typeof ExternalLink
  label: string
  onClick: () => void
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded border disabled:opacity-40"
      style={{ backgroundColor: 'white', color: COLOR_PRIMARY, borderColor: COLOR_PRIMARY }}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  )
}
