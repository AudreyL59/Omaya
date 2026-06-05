import { useCallback, useEffect, useState } from 'react'
import { CheckCircle, FileText, Loader2, Save, Wallet, XCircle } from 'lucide-react'

import type { FIProps } from './index'
import { showConfirm, showToast } from '../../ui/dialog'

interface TypeSortieOption {
  id: number
  label: string
}

interface SortieRHData {
  found: boolean
  id_ticket: string
  id_salarie: string
  id_type_demande: number
  show_sdtc: boolean
  lib_nom: string
  nom: string
  prenom: string
  type_sortie: number
  lib_sortie: string
  type_sortie_options: TypeSortieOption[]
  info_cplt: string
  doc_sortie: boolean
  doc_url: string
  date_dernier_ctt: string
}

function formatShortDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

// FI_SortieRH (types 12 / 36 / 37) - Tickets de sortie RH.
export default function FISortieRH({ apiBase, getToken, idTicket, onClose }: FIProps) {
  const [data, setData] = useState<SortieRHData | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const [typeSortie, setTypeSortie] = useState<number>(0)
  const [infoCplt, setInfoCplt] = useState<string>('')

  const reload = useCallback(() => {
    setLoading(true)
    fetch(`${apiBase}/tickets/${idTicket}/form`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((j) => {
        const dd: SortieRHData | null = j?.data?.found ? j.data : null
        setData(dd)
        if (dd) {
          setTypeSortie(dd.type_sortie || 0)
          setInfoCplt(dd.info_cplt || '')
        }
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [apiBase, idTicket, getToken])

  useEffect(() => {
    reload()
  }, [reload])

  const post = async (body: Record<string, unknown>): Promise<Record<string, unknown> | null> => {
    setSaving(true)
    try {
      const resp = await fetch(`${apiBase}/tickets/${idTicket}/form`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(body),
      })
      const j = await resp.json().catch(() => null)
      if (!resp.ok) {
        showToast(`Erreur : ${(j as { detail?: string })?.detail || resp.status}`, 'error')
        return null
      }
      return (j ?? {}) as Record<string, unknown>
    } catch {
      showToast('Erreur réseau.', 'error')
      return null
    } finally {
      setSaving(false)
    }
  }

  const handleEnregistrer = async () => {
    const r = await post({
      action: 'enregistrer',
      type_sortie: typeSortie,
      info_cplt: infoCplt,
    })
    if (!r) return
    showToast('Ticket enregistré', 'success')
    // Propose de clôturer après enregistrement (cf. WinDev)
    const ok = await showConfirm({
      title: 'Clôturer le ticket',
      message: 'Voulez-vous clôturer le ticket ?',
      confirmLabel: 'Clôturer',
    })
    if (ok) await handleCloture(false)
  }

  const handleCloture = async (confirmFirst = true) => {
    if (confirmFirst) {
      const ok = await showConfirm({
        title: 'Clôturer le ticket',
        message: 'Vous êtes sur le point de clôturer le ticket. Voulez-vous continuer ?',
        confirmLabel: 'Clôturer',
        variant: 'danger',
      })
      if (!ok) return
    }
    const r = await post({ action: 'close' })
    if (!r) return
    showToast('Ticket clôturé', 'success')
    if (onClose) onClose()
  }

  const handleVoirDoc = async () => {
    if (!data?.doc_url) return
    window.open(data.doc_url, '_blank')
    await post({ action: 'mark_doc_seen' })
  }

  const handleSDTC = () => {
    if (!data?.id_salarie) return
    // Placeholder pour Fen_SDTC (a venir : popup solde de tout compte)
    showToast('Solde de tout compte : module à brancher', 'info')
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-c-ink-icon animate-spin" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="h-full flex items-center justify-center text-c-ink-soft text-sm">
        Demande de sortie RH introuvable pour ce ticket.
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-4">
      {/* Header : libellé salarié + actions principales */}
      <div className="flex items-start justify-between mb-4 gap-4">
        <div>
          <h2 className="text-base font-semibold text-c-ink">{data.lib_nom}</h2>
          <p className="text-xs text-c-ink-soft mt-0.5">
            Fiche n° {data.id_salarie}
          </p>
          {data.date_dernier_ctt ? (
            <p className="text-xs text-emerald-700 mt-1">
              Dernier contrat signé le {formatShortDate(data.date_dernier_ctt)}
            </p>
          ) : (
            <p className="text-xs text-red-700 mt-1">Pas encore productif</p>
          )}
        </div>
        <div className="flex flex-col gap-2 shrink-0">
          <button
            onClick={handleEnregistrer}
            disabled={saving}
            className="flex items-center justify-center gap-2 px-4 py-2 rounded text-sm font-medium text-white bg-c-brand hover:opacity-90 disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Enregistrer le ticket
          </button>
          <button
            onClick={() => handleCloture(true)}
            disabled={saving}
            className="flex items-center justify-center gap-2 px-4 py-2 rounded text-sm font-medium text-red-700 border border-red-200 hover:bg-red-50 disabled:opacity-50"
          >
            <XCircle className="w-4 h-4" />
            Clôturer le ticket
          </button>
          {data.doc_sortie && data.doc_url && (
            <button
              onClick={handleVoirDoc}
              className="flex items-center justify-center gap-2 px-4 py-2 rounded text-sm font-normal text-c-brand border border-c-line hover:bg-[#ECF1F2]"
            >
              <FileText className="w-4 h-4" />
              Voir le document de sortie
            </button>
          )}
          {data.show_sdtc && (
            <button
              onClick={handleSDTC}
              className="flex items-center justify-center gap-2 px-4 py-2 rounded text-sm font-normal text-c-brand border border-c-line hover:bg-[#ECF1F2]"
            >
              <Wallet className="w-4 h-4" />
              Solde de tout compte
            </button>
          )}
        </div>
      </div>

      {/* Bloc Type de sortie + Doc + Info cplt */}
      <div className="grid grid-cols-[200px_1fr] gap-4 mt-6 max-w-3xl">
        <label className="text-sm text-c-ink-soft self-center">Type Sortie</label>
        <select
          value={typeSortie}
          onChange={(e) => setTypeSortie(parseInt(e.target.value, 10) || 0)}
          className="px-3 py-1.5 border border-c-line rounded text-sm bg-white focus:outline-none focus:ring-1 focus:ring-c-brand"
        >
          <option value={0}>—</option>
          {data.type_sortie_options.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </select>

        <label className="text-sm text-c-ink-soft self-center">Doc de Sortie</label>
        <div className="flex items-center gap-2 text-sm">
          {data.doc_sortie ? (
            <>
              <CheckCircle className="w-4 h-4 text-emerald-600" />
              <span className="text-c-ink">Reçu</span>
            </>
          ) : (
            <>
              <XCircle className="w-4 h-4 text-c-ink-faint" />
              <span className="text-c-ink-faint italic">En attente</span>
            </>
          )}
        </div>

        <label className="text-sm text-c-ink-soft pt-2">InfoCplt</label>
        <textarea
          value={infoCplt}
          onChange={(e) => setInfoCplt(e.target.value)}
          rows={5}
          className="px-3 py-2 border border-c-line rounded text-sm bg-white focus:outline-none focus:ring-1 focus:ring-c-brand resize-y"
          placeholder="Informations complémentaires…"
        />
      </div>
    </div>
  )
}
