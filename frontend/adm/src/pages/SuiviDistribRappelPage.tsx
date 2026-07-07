/**
 * Fen_SuiviDistribRappel - "Rappel récup Doc Distrib".
 *
 * Vue transversale des documents distributeur non fournis dont la
 * date prévue arrive dans les <jours> prochains jours (défaut 15).
 *
 * 3 boutons :
 *   - + Créer un ticket : appel /tickets/reclam (déjà en place)
 *   - Voir le ticket : redirige vers /tickets/{id_tk}
 *   - Actualiser : reload
 *
 * Cf. WinDev Fen_SuiviDistribRappel.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Bell, Loader2, Plus, RefreshCw, Ticket,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '@/components/PageHeader'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  useTableSortFilter, SortableTh, FilterInput,
} from '@shared/production/_tableHelpers'

const API_BASE = '/api/adm'

interface Rappel {
  id_doc_distrib: string
  id_type_doc_distributeur: string
  lib_doc: string
  date_prevue: string
  id_ste: string
  raison_sociale: string
  id_gerant: string
  gerant_nom: string
  afaire_signer: boolean
  id_doc_courtage: string
  id_tk: string
  date_ticket: string
  ticket_rappel_fait: boolean
}

const shortDate = (iso: string): string =>
  !iso || iso.length < 10
    ? ''
    : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

export default function SuiviDistribRappelPage() {
  useDocumentTitle('Suivi Docs Distributeurs')
  const nav = useNavigate()
  const [rows, setRows] = useState<Rappel[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<string>('')
  const [creating, setCreating] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setSelected('')
    try {
      const r = await fetch(
        `${API_BASE}/distributeurs/rappels?jours=15`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      setRows(d.items || [])
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const tsf = useTableSortFilter(
    rows as unknown as Array<Record<string, unknown>>,
    { key: 'date_prevue', dir: 'asc' },
    (r) =>
      [r.lib_doc, r.raison_sociale, r.gerant_nom]
        .join(' '),
  )
  const visible = tsf.rows as unknown as Rappel[]
  const sel = visible.find((r) => r.id_doc_distrib === selected) || null

  const canCreate = !!sel && !sel.ticket_rappel_fait
  const canVoir = !!sel && !!sel.id_tk

  const createTicket = async () => {
    if (!sel) return
    if (sel.afaire_signer) {
      showToast(
        'Ce document nécessite une redirection vers l\'écran Contrat de Courtage.',
        'info',
      )
      return
    }
    const ok = await showConfirm({
      title: 'Créer un ticket',
      message: 'Vous êtes sur le point de créer un ticket. Voulez-vous continuer ?',
    })
    if (!ok) return
    setCreating(true)
    try {
      const r = await fetch(
        `${API_BASE}/distributeurs/${sel.id_ste}/tickets/reclam`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            id_doc_distrib: Number(sel.id_doc_distrib),
            id_gerant: Number(sel.id_gerant),
          }),
        },
      )
      const d = await r.json()
      if (!d.ok) {
        showToast(d.error || 'Erreur', 'error')
        return
      }
      const smsMsg = d.sms_statut ? ` — SMS : ${d.sms_statut}` : ''
      showToast(`Ticket créé${smsMsg}`, 'success')
      void load()
    } finally {
      setCreating(false)
    }
  }

  const voirTicket = () => {
    if (!sel || !sel.id_tk) return
    nav(`/tickets?ticket=${sel.id_tk}`)
  }

  return (
    <div className="min-h-screen bg-[#F5F5F0] p-6">
      <div className="max-w-7xl mx-auto">
        <PageHeader icon={Bell} title="Rappel récup Doc Distrib" />

        <div className="bg-white rounded-lg shadow p-4">
          {/* Actions top */}
          <div className="flex items-center gap-2 mb-4">
            <button
              onClick={createTicket}
              disabled={!canCreate || creating}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#8B7355] text-white disabled:opacity-40 hover:bg-[#725e46]"
            >
              {creating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Plus className="w-4 h-4" />
              )}
              Créer un ticket
            </button>
            <button
              onClick={voirTicket}
              disabled={!canVoir}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#8B7355] text-[#8B7355] disabled:opacity-40 hover:bg-[#ECF1F2]"
            >
              <Ticket className="w-4 h-4" />
              Voir le ticket
            </button>
            <button
              onClick={() => void load()}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#8B7355] text-[#8B7355] disabled:opacity-40 hover:bg-[#ECF1F2] ml-auto"
            >
              <RefreshCw
                className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`}
              />
              Actualiser
            </button>
          </div>

          {/* Filter */}
          <div className="mb-3">
            <FilterInput
              value={tsf.filter}
              onChange={tsf.setFilter}
              placeholder="Rechercher (doc, société, gérant)..."
            />
          </div>

          {loading ? (
            <div className="flex items-center justify-center p-8">
              <Loader2 className="w-6 h-6 animate-spin text-[#8B7355]" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[#8B7355] border-b border-[#E5E0D5]">
                    <SortableTh label="Lib Doc" sortKey="lib_doc"
                      sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Date Prévue" sortKey="date_prevue"
                      sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Raison Sociale" sortKey="raison_sociale"
                      sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Gérant" sortKey="gerant_nom"
                      sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Ticket de réclamation fait"
                      sortKey="ticket_rappel_fait"
                      sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Date Ticket" sortKey="date_ticket"
                      sort={tsf.sort} onSort={tsf.toggleSort} />
                  </tr>
                </thead>
                <tbody>
                  {visible.map((r) => {
                    const isSelected = r.id_doc_distrib === selected
                    return (
                      <tr
                        key={r.id_doc_distrib}
                        onClick={() => setSelected(r.id_doc_distrib)}
                        className={`cursor-pointer border-b border-[#F0EDE5] hover:bg-[#ECF1F2] ${
                          isSelected ? 'bg-[#ECF1F2] ring-1 ring-[#8B7355]' : ''
                        }`}
                      >
                        <td className="py-2 px-2">{r.lib_doc}</td>
                        <td className="py-2 px-2 tabular-nums">
                          {shortDate(r.date_prevue)}
                        </td>
                        <td className="py-2 px-2">{r.raison_sociale}</td>
                        <td className="py-2 px-2">{r.gerant_nom}</td>
                        <td className="py-2 px-2 text-center">
                          {r.ticket_rappel_fait ? (
                            <span className="text-green-700">✓</span>
                          ) : (
                            <span className="text-gray-300">—</span>
                          )}
                        </td>
                        <td className="py-2 px-2 tabular-nums text-xs">
                          {shortDate(r.date_ticket)}
                        </td>
                      </tr>
                    )
                  })}
                  {visible.length === 0 && (
                    <tr>
                      <td colSpan={6} className="py-6 text-center text-gray-400">
                        Aucun document à rappeler.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          <div className="mt-3 text-xs text-gray-500">
            {visible.length} document{visible.length > 1 ? 's' : ''} à fournir
            (date prévue &le; aujourd'hui + 15 jours)
          </div>
        </div>
      </div>
    </div>
  )
}
