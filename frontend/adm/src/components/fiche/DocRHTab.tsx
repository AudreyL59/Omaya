/**
 * Onglet 'Contrat de travail' (Docs RH) de la fiche salarie ADM.
 *
 * Transposition de la fenetre WinDev FI_SalarieDocRH :
 *  - Tableau : Type Doc | Responsable | DATE Edition | Doc recu RH
 *              | Date reception | Signe en demat
 *  - Boutons :
 *    * Nouveau : ouvre Fen_SalarieDocRH (a coder, popup en attente)
 *    * Supprimer : soft delete sur la ligne selectionnee
 *    * Cttw RECU : passe recu=true sur la ligne selectionnee
 *    * Voir le Ctt edite : ouvre le PDF dans un nouvel onglet
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { CheckSquare, ExternalLink, Loader2, Plus, Trash2 } from 'lucide-react'

import { getToken } from '@/api'
import { showConfirm, showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'
import CheckMark from '../CheckMark'
import NewDocRHModal from './NewDocRHModal'

interface DocRHItem {
  id_salarie_doc_rh: string
  id_doc_rhtype: string
  type_doc_lib: string
  id_da: string
  responsable_nom: string
  date_edition: string
  recu: boolean
  recu_date: string
  signe_demat: boolean
  id_docusign: string
}

interface Props {
  idSalarie: string
}

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

export default function DocRHTab({ idSalarie }: Props) {
  const [items, setItems] = useState<DocRHItem[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [newOpen, setNewOpen] = useState(false)

  const reload = useCallback(async () => {
    if (!idSalarie) return
    setLoading(true)
    try {
      const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/doc-rh`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const j = (await r.json()) as { items: DocRHItem[] }
      setItems(j.items || [])
      if (selected && !j.items.some((i) => i.id_salarie_doc_rh === selected)) {
        setSelected(null)
      }
    } catch (e) {
      showToast(`Échec chargement docs RH : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [idSalarie, selected])

  useEffect(() => {
    void reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idSalarie])

  const selectedItem = useMemo(
    () => items.find((i) => i.id_salarie_doc_rh === selected) || null,
    [items, selected],
  )

  const handleNouveau = () => {
    setNewOpen(true)
  }

  const handleSupprimer = async () => {
    if (!selectedItem) {
      showToast('Sélectionner un document à supprimer.', 'info')
      return
    }
    const ok = await showConfirm({
      title: 'Supprimer ce document ?',
      message: 'Vous êtes sur le point de supprimer cet enregistrement. Voulez-vous continuer ?',
      confirmLabel: 'Supprimer',
      variant: 'danger',
    })
    if (!ok) return
    setBusy(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/doc-rh/${selectedItem.id_salarie_doc_rh}`,
        { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      setSelected(null)
      await reload()
      showToast('Document supprimé.', 'success')
    } catch (e) {
      showToast(`Échec suppression : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleCttwRecu = async () => {
    if (!selectedItem) {
      showToast('Sélectionner une ligne à marquer comme reçue.', 'info')
      return
    }
    setBusy(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/doc-rh/${selectedItem.id_salarie_doc_rh}/cttw-recu`,
        { method: 'POST', headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      await reload()
      showToast('Document marqué comme reçu.', 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleVoirCtt = async () => {
    if (!selectedItem) {
      showToast('Sélectionner un document pour voir le contrat.', 'info')
      return
    }
    setBusy(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/doc-rh/${selectedItem.id_salarie_doc_rh}/ctt-edite-url`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const j = (await r.json()) as { url: string; error?: string }
      if (j.error || !j.url) {
        showToast(j.error || 'Pas de ticket associé', 'info')
        return
      }
      window.open(j.url, '_blank', 'noopener,noreferrer')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <ToolBtn icon={Plus} label="Nouveau" onClick={handleNouveau} primary />
        <ToolBtn
          icon={Trash2}
          label="Supprimer"
          onClick={handleSupprimer}
          disabled={!selectedItem || busy}
          danger
        />
        <div className="flex-1" />
        <ToolBtn
          icon={CheckSquare}
          label="Cttw RECU"
          onClick={handleCttwRecu}
          disabled={!selectedItem || busy}
        />
        <ToolBtn
          icon={ExternalLink}
          label="Voir le Ctt édité"
          onClick={handleVoirCtt}
          disabled={!selectedItem || busy}
        />
        {(loading || busy) && (
          <Loader2 className="w-4 h-4 animate-spin ml-2" style={{ color: COLOR_PRIMARY }} />
        )}
      </div>

      {/* Tableau */}
      <div className="border rounded overflow-hidden" style={{ borderColor: COLOR_BG_SOFT }}>
        <div
          className="grid items-center gap-2 px-3 py-2 text-xs font-semibold border-b"
          style={{
            gridTemplateColumns: '1fr 180px 110px 95px 110px 95px',
            color: COLOR_BRUN,
            backgroundColor: COLOR_BG_SOFT,
            borderColor: COLOR_BG_SOFT,
          }}
        >
          <div>Type Doc</div>
          <div>Responsable</div>
          <div>DATE Édition</div>
          <div className="text-center">Doc reçu RH</div>
          <div>Date réception</div>
          <div className="text-center">Signé démat</div>
        </div>
        <div className="max-h-[480px] overflow-y-auto">
          {!loading && items.length === 0 && (
            <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
              Aucun document.
            </div>
          )}
          {items.map((it) => {
            const isSelected = selected === it.id_salarie_doc_rh
            return (
              <div
                key={it.id_salarie_doc_rh}
                onClick={() => setSelected(it.id_salarie_doc_rh)}
                className="grid items-center gap-2 px-3 py-1.5 text-xs border-b cursor-pointer"
                style={{
                  gridTemplateColumns: '1fr 180px 110px 95px 110px 95px',
                  backgroundColor: isSelected ? COLOR_BG_SOFT : 'white',
                  borderColor: COLOR_BG_SOFT,
                  color: COLOR_BRUN,
                }}
              >
                <div className="truncate font-medium" title={it.type_doc_lib}>
                  {it.type_doc_lib || '—'}
                </div>
                <div className="truncate" title={it.responsable_nom}>
                  {it.responsable_nom}
                </div>
                <div>{fmtDate(it.date_edition)}</div>
                <div className="text-center"><CheckMark active={it.recu} /></div>
                <div>{fmtDate(it.recu_date)}</div>
                <div className="text-center"><CheckMark active={it.signe_demat} /></div>
              </div>
            )
          })}
        </div>
      </div>

      {newOpen && (
        <NewDocRHModal
          idSalarie={idSalarie}
          onClose={() => setNewOpen(false)}
          onCreated={() => {
            setNewOpen(false)
            void reload()
          }}
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
