/**
 * Sous-onglet 'Édition documents' de l'onglet Ulease.
 *
 * Tableau salarie_doc_ulease JOIN doc_ulease_type.
 * Boutons :
 *  - Doc reçu signé : UPDATE RECU=1 + RECUDATE
 *  - Générer un document ULEASE : placeholder (Fen_SalariéDocUlease)
 */

import { useCallback, useEffect, useState } from 'react'
import { CheckCircle, FilePlus, Loader2 } from 'lucide-react'

import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'
import CheckMark from '../../CheckMark'
import SalarieDocUleaseModal from './SalarieDocUleaseModal'

interface DocItem {
  id_salarie_doc_ulease: string
  date_edition: string
  lib_type: string
  recu: boolean
  recu_date: string
}

interface Props {
  idSalarie: string
}

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

export default function UleaseDocEditionTab({ idSalarie }: Props) {
  const [items, setItems] = useState<DocItem[]>([])
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)
  const [docOpen, setDocOpen] = useState(false)

  const reload = useCallback(async () => {
    if (!idSalarie) return
    setLoading(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/ulease/doc-edition`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const j = (await r.json()) as DocItem[]
      setItems(Array.isArray(j) ? j : [])
    } catch (e) {
      showToast(`Échec chargement documents : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [idSalarie])

  useEffect(() => {
    void reload()
  }, [reload])

  const selectedItem = items.find((i) => i.id_salarie_doc_ulease === selected) || null

  const handleMarkRecu = async () => {
    if (!selectedItem) {
      showToast('Sélectionner un document.', 'info')
      return
    }
    setBusy(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/ulease/doc-edition/${selectedItem.id_salarie_doc_ulease}/recu`,
        { method: 'POST', headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      showToast('Document marqué comme reçu.', 'success')
      await reload()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const template = '1fr 110px 70px 130px'

  return (
    <div className="flex flex-col gap-2 h-full">
      <div className="flex items-center gap-2 flex-shrink-0">
        <ToolBtn
          icon={CheckCircle}
          label="Doc reçu signé"
          onClick={() => void handleMarkRecu()}
          disabled={!selectedItem || busy}
          primary
        />
        <ToolBtn
          icon={FilePlus}
          label="Générer un document ULEASE"
          onClick={() => setDocOpen(true)}
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
          <div>Lib_Type</div>
          <div>Date édition</div>
          <div className="text-center">Reçu signé</div>
          <div>Date réception signé</div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {!loading && items.length === 0 && (
            <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
              Aucun document édité.
            </div>
          )}
          {items.map((it) => {
            const sel = selected === it.id_salarie_doc_ulease
            return (
              <div
                key={it.id_salarie_doc_ulease}
                onClick={() => setSelected(it.id_salarie_doc_ulease)}
                className="grid items-center gap-2 px-3 py-1.5 text-xs border-b cursor-pointer"
                style={{
                  gridTemplateColumns: template,
                  backgroundColor: sel ? COLOR_BG_SOFT : 'white',
                  borderColor: COLOR_BG_SOFT,
                  color: COLOR_BRUN,
                }}
              >
                <div className="truncate" title={it.lib_type}>
                  {it.lib_type || '—'}
                </div>
                <div>{fmtDate(it.date_edition.slice(0, 10))}</div>
                <div className="text-center">
                  <CheckMark active={it.recu} />
                </div>
                <div>{fmtDate(it.recu_date.slice(0, 10))}</div>
              </div>
            )
          })}
        </div>
      </div>

      {docOpen && (
        <SalarieDocUleaseModal
          idSalarie={idSalarie}
          onClose={() => setDocOpen(false)}
          onGenerated={() => void reload()}
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
  primary,
}: {
  icon: typeof CheckCircle
  label: string
  onClick: () => void
  disabled?: boolean
  primary?: boolean
}) {
  const color = primary ? 'white' : COLOR_PRIMARY
  const bg = primary ? COLOR_PRIMARY : 'white'
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded border disabled:opacity-40"
      style={{ backgroundColor: bg, color, borderColor: COLOR_PRIMARY }}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  )
}
