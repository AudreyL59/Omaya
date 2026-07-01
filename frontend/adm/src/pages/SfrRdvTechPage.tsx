/**
 * Fen_SuiviRDVTECH - Suivi SFR > RDV Tech.
 *
 * Page de suivi des retours de RDV technicien FIBRE.
 *
 * Filtres : Du/Au + radio Ouverts/Cloturés/Tous (defaut Clôturés
 * cf screen WinDev).
 * Tableau : Fiche créée le, DateCloture, Cloturée, Statut Ticket,
 * Vendeur, NumBS SFR, DateRDVTech, Période, DateSignature,
 * Statut RDV, Info Cplt.
 *
 * 2 boutons :
 *   - Voir le ticket : ouvre TicketCallContenuModal (type RDVTech)
 *     -> pour l'instant reutilise le modal existant
 *   - Voir le contrat : placeholder (Fen_FicheSFR pas encore dev)
 */
import { useState } from 'react'
import {
  Search, Loader2, ArrowLeft, FileText, Eye, CalendarClock,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  useTableSortFilter, SortableTh, FilterInput,
} from '@shared/production/_tableHelpers'
import RdvTechContenuModal from '@/components/sfr/RdvTechContenuModal'

const API_BASE = '/api/adm'

interface Row {
  id_tk_liste: string; id_contrat: string
  id_tk_retour_rdv_tech_fibre: string
  date_crea: string; date_cloture: string; cloturee: boolean
  lib_statut: string; vendeur: string
  num_bs: string; num_bs_sfr: string
  date_rdv_tech: string; periode_rdv_tech: string
  date_signature: string
  id_fibre_statut_rdv: number; lib_statut_rdv: string
  info_cplt: string
}

const todayIso = (): string => new Date().toISOString().slice(0, 10)
const shortDate = (iso: string): string =>
  !iso || iso.length < 10 ? '' : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

export default function SfrRdvTechPage() {
  useDocumentTitle('Suivi des RDV TECH')
  const [du, setDu] = useState(todayIso())
  const [au, setAu] = useState(todayIso())
  const [etat, setEtat] = useState<'ouverts' | 'clotures' | 'tous'>('clotures')
  const [rows, setRows] = useState<Row[]>([])
  const [selected, setSelected] = useState<string>('')
  const [contenuRow, setContenuRow] = useState<Row | null>(null)
  const [loading, setLoading] = useState(false)

  const rechercher = async () => {
    if (du > au) { showToast('Dates incohérentes', 'error'); return }
    setLoading(true); setSelected('')
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/rdv-tech?du=${du}&au=${au}&etat=${etat}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const d: Row[] = await r.json()
      setRows(d)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }

  const tsf = useTableSortFilter(
    rows as unknown as Array<Record<string, unknown>>,
    { key: 'date_crea', dir: 'desc' },
    (r) => [
      r.num_bs_sfr, r.vendeur, r.lib_statut, r.lib_statut_rdv, r.info_cplt,
    ].join(' '),
  )
  const visible = tsf.rows as unknown as Row[]

  const sel = visible.find(r => r.id_tk_liste === selected)

  const voirTicket = () => {
    if (!sel) { showToast('Sélectionne une ligne d\'abord.', 'info'); return }
    setContenuRow(sel)
  }

  const voirContrat = () => {
    if (!sel) { showToast('Sélectionne une ligne d\'abord.', 'info'); return }
    showToast('Fiche contrat SFR : à venir (Fen_FicheSFR)', 'info')
  }

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-110px)] text-c-ink">
      <div className="flex items-center gap-2 mb-3">
        <Link to=".." relative="path"
          className="p-1.5 hover:bg-c-surface-soft rounded text-c-ink-faint-2">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-lg font-bold flex items-center gap-2">
          <CalendarClock className="w-4 h-4 text-c-brand" />
          Suivi des RDV TECH
        </h1>
      </div>

      {/* Filtres */}
      <div className="flex items-center gap-3 mb-3 bg-white p-3 rounded-xl border border-c-line text-sm flex-wrap">
        <label className="text-c-ink-faint text-xs">Du</label>
        <input type="date" value={du} onChange={e => setDu(e.target.value)}
          className="px-2 py-1 border border-c-line rounded text-xs h-7" />
        <label className="text-c-ink-faint text-xs">Au</label>
        <input type="date" value={au} onChange={e => setAu(e.target.value)}
          className="px-2 py-1 border border-c-line rounded text-xs h-7" />
        <div className="flex gap-3 items-center text-xs ml-2">
          {(['ouverts', 'clotures', 'tous'] as const).map(e => (
            <label key={e} className="flex items-center gap-1 cursor-pointer">
              <input type="radio" checked={etat === e} onChange={() => setEtat(e)} />
              {e === 'ouverts' ? 'Ouverts' : e === 'clotures' ? 'Clôturés' : 'Tous'}
            </label>
          ))}
        </div>
        <button type="button" onClick={rechercher} disabled={loading}
          className="flex items-center gap-2 px-4 bg-c-brand text-white rounded text-sm font-medium hover:opacity-90 disabled:opacity-50 h-7">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" />
                   : <Search className="w-4 h-4" />}
          Rechercher
        </button>
      </div>

      {/* Boutons d'action */}
      <div className="flex items-center gap-3 mb-3 bg-white px-3 py-2 rounded-xl border border-c-line text-sm flex-wrap">
        <button type="button" onClick={voirTicket} disabled={!sel}
          className="flex items-center gap-2 px-3 py-1 rounded text-c-brand hover:bg-c-brand/10 disabled:opacity-30 text-xs">
          <FileText className="w-4 h-4" /> Voir le ticket
        </button>
        <button type="button" onClick={voirContrat} disabled={!sel}
          className="flex items-center gap-2 px-3 py-1 rounded text-c-brand hover:bg-c-brand/10 disabled:opacity-30 text-xs">
          <Eye className="w-4 h-4" /> Voir le contrat
        </button>
        <div className="flex-1" />
        <FilterInput value={tsf.filter} onChange={tsf.setFilter}
          placeholder="Filtrer…" />
      </div>

      <div className="bg-white rounded-xl border border-c-line overflow-hidden flex-1 flex flex-col">
        <div className="px-3 py-1.5 border-b border-c-line-soft text-xs text-c-ink-faint">
          {visible.length} / {rows.length} RDV
        </div>
        <div className="flex-1 overflow-auto">
          <table className="w-full text-xs">
            <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0 z-10">
              <tr>
                <SortableTh label="Fiche créée le" sortKey="date_crea" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Date Clôture" sortKey="date_cloture" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Clôt." sortKey="cloturee" sort={tsf.sort} onSort={tsf.toggleSort} align="center" />
                <SortableTh label="Statut Ticket" sortKey="lib_statut" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Vendeur" sortKey="vendeur" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="NumBS SFR" sortKey="num_bs_sfr" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Date RDV Tech" sortKey="date_rdv_tech" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Période" sortKey="periode_rdv_tech" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Signature" sortKey="date_signature" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Statut RDV" sortKey="lib_statut_rdv" sort={tsf.sort} onSort={tsf.toggleSort} />
                <th className="px-2 py-2 text-left">Info Cplt</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-c-line-soft">
              {visible.length === 0 ? (
                <tr>
                  <td colSpan={11} className="text-center py-12 text-c-ink-faint-2 italic">
                    {rows.length === 0
                      ? 'Choisis filtres puis Rechercher.'
                      : 'Aucun résultat.'}
                  </td>
                </tr>
              ) : visible.map(r => {
                const isSel = r.id_tk_liste === selected
                return (
                  <tr key={r.id_tk_retour_rdv_tech_fibre}
                    onClick={() => setSelected(r.id_tk_liste)}
                    onDoubleClick={() => setContenuRow(r)}
                    className={`cursor-pointer ${isSel ? 'bg-c-brand/10' : 'hover:bg-c-surface-soft'}`}>
                    <td className="px-2 py-1.5">{shortDate(r.date_crea)}</td>
                    <td className="px-2 py-1.5">{shortDate(r.date_cloture)}</td>
                    <td className="px-2 py-1.5 text-center">{r.cloturee ? '✓' : ''}</td>
                    <td className="px-2 py-1.5">{r.lib_statut}</td>
                    <td className="px-2 py-1.5">{r.vendeur}</td>
                    <td className="px-2 py-1.5 tabular-nums">{r.num_bs_sfr}</td>
                    <td className="px-2 py-1.5">{shortDate(r.date_rdv_tech)}</td>
                    <td className="px-2 py-1.5">{r.periode_rdv_tech}</td>
                    <td className="px-2 py-1.5">{shortDate(r.date_signature)}</td>
                    <td className="px-2 py-1.5">{r.lib_statut_rdv}</td>
                    <td className="px-2 py-1.5 truncate max-w-[200px]" title={r.info_cplt}>
                      {r.info_cplt}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {contenuRow && (
        <RdvTechContenuModal row={contenuRow}
          onClose={() => setContenuRow(null)}
          onChanged={() => { void rechercher() }} />
      )}
    </div>
  )
}
