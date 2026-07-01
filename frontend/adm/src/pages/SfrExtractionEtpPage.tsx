/**
 * Fen_ETP - Suivi SFR > Extraction ETP.
 *
 * Compte pour chaque cluster (FIBRE, hors TK, hors HorsCible) sur
 * la periode Du/Au :
 *   - nb vendeurs ayant <= 2 contrats
 *   - nb vendeurs ayant >= 3 contrats
 * Chaque vendeur n'est comptabilise que dans son cluster majoritaire.
 *
 * Ligne 'Somme' en bas avec les totaux + export XLSX.
 */
import { useState } from 'react'
import {
  Search, Loader2, ArrowLeft, Users, FileDown,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  useTableSortFilter, SortableTh, FilterInput,
} from '@shared/production/_tableHelpers'

const API_BASE = '/api/adm'

interface Row {
  code_cluster: string; libelle_cluster: string; courtier: string
  inf_ou_egal_2: number; sup_ou_egal_3: number
}

const todayIso = (): string => new Date().toISOString().slice(0, 10)

export default function SfrExtractionEtpPage() {
  useDocumentTitle('Extraction ETP')
  const [du, setDu] = useState(todayIso())
  const [au, setAu] = useState(todayIso())
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)

  const rechercher = async () => {
    if (du > au) { showToast('Dates incohérentes', 'error'); return }
    setLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/extraction-etp?du=${du}&au=${au}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      setRows(await r.json())
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }

  const tsf = useTableSortFilter(
    rows as unknown as Array<Record<string, unknown>>,
    { key: 'sup_ou_egal_3', dir: 'desc' },
    (r) => `${r.code_cluster} ${r.libelle_cluster} ${r.courtier}`,
  )
  const visible = tsf.rows as unknown as Row[]

  const totalInf = visible.reduce((a, r) => a + r.inf_ou_egal_2, 0)
  const totalSup = visible.reduce((a, r) => a + r.sup_ou_egal_3, 0)

  const exportXlsx = async () => {
    setExporting(true)
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/extraction-etp/export.xlsx?du=${du}&au=${au}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const cd = r.headers.get('content-disposition') || ''
      const m = /filename="?([^";]+)"?/.exec(cd)
      a.download = m ? m[1] : `extraction-etp-${du}-${au}.xlsx`
      document.body.appendChild(a); a.click()
      document.body.removeChild(a); URL.revokeObjectURL(url)
    } catch (e) {
      showToast(`Erreur export : ${(e as Error).message}`, 'error')
    } finally { setExporting(false) }
  }

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-110px)] text-c-ink">
      <div className="flex items-center gap-2 mb-3">
        <Link to=".." relative="path"
          className="p-1.5 hover:bg-c-surface-soft rounded text-c-ink-faint-2">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-lg font-bold flex items-center gap-2">
          <Users className="w-4 h-4 text-c-brand" /> Extraction ETP
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
        <button type="button" onClick={rechercher} disabled={loading}
          className="flex items-center gap-2 px-4 bg-c-brand text-white rounded text-sm font-medium hover:opacity-90 disabled:opacity-50 h-7">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" />
                   : <Search className="w-4 h-4" />}
          Rechercher
        </button>
        <div className="flex-1" />
        {rows.length > 0 && (
          <>
            <FilterInput value={tsf.filter} onChange={tsf.setFilter}
              placeholder="Filtrer…" />
            <button type="button" onClick={exportXlsx} disabled={exporting}
              className="flex items-center gap-1.5 px-2.5 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft h-7 disabled:opacity-50 disabled:cursor-wait">
              {exporting ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                         : <FileDown className="w-3.5 h-3.5" />}
              {exporting ? 'Génération…' : 'XLSX'}
            </button>
          </>
        )}
      </div>

      <div className="bg-white rounded-xl border border-c-line overflow-hidden flex-1 flex flex-col">
        <div className="px-3 py-1.5 border-b border-c-line-soft text-xs text-c-ink-faint">
          {visible.length} / {rows.length} cluster(s) — {totalInf + totalSup} vendeur(s)
        </div>
        <div className="flex-1 overflow-auto">
          <table className="w-full text-xs">
            <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0 z-10">
              <tr>
                <SortableTh label="Code Cluster" sortKey="code_cluster" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Libellé Cluster" sortKey="libelle_cluster" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Courtier" sortKey="courtier" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Inf ou égal à 2" sortKey="inf_ou_egal_2" sort={tsf.sort} onSort={tsf.toggleSort} align="right" />
                <SortableTh label="Sup ou égal à 3" sortKey="sup_ou_egal_3" sort={tsf.sort} onSort={tsf.toggleSort} align="right" />
              </tr>
            </thead>
            <tbody className="divide-y divide-c-line-soft">
              {visible.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-12 text-c-ink-faint-2 italic">
                    {rows.length === 0
                      ? 'Choisis dates puis Rechercher.'
                      : 'Aucun résultat avec ce filtre.'}
                  </td>
                </tr>
              ) : visible.map(r => (
                <tr key={r.code_cluster} className="hover:bg-c-surface-soft">
                  <td className="px-2 py-1.5 tabular-nums">{r.code_cluster}</td>
                  <td className="px-2 py-1.5">{r.libelle_cluster}</td>
                  <td className="px-2 py-1.5">{r.courtier}</td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{r.inf_ou_egal_2}</td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{r.sup_ou_egal_3}</td>
                </tr>
              ))}
            </tbody>
            {visible.length > 0 && (
              <tfoot className="bg-c-surface-soft font-bold sticky bottom-0">
                <tr>
                  <td colSpan={2} className="px-2 py-2">Somme</td>
                  <td className="px-2 py-2"></td>
                  <td className="px-2 py-2 text-right tabular-nums">{totalInf}</td>
                  <td className="px-2 py-2 text-right tabular-nums">{totalSup}</td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>
    </div>
  )
}
