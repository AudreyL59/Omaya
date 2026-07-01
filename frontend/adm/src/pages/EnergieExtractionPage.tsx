/**
 * Fen_ExtractionEnergie - Suivi Énergie > Extraction Call.
 *
 * Liste les tickets Call Energie OEN sur la periode Du/Au :
 *   - Toggle Validé (StatutProd IN 1,3) / Annulé (StatutProd 2)
 *   - Tableau : Date souscription, Numéro CM, Nom, Prénom,
 *     Téléphone, Adresse mail, Date activation, Type contrat
 *     (ELEC/GAZ/DUAL), Commercial
 *   - Export XLSX
 *
 * Onglet unique 'Tickets' (cf screen WinDev, meme si un seul onglet).
 */
import { useState } from 'react'
import {
  Search, Loader2, ArrowLeft, Download as DownloadIcon, FileDown,
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
  id_tk_liste: string
  date_souscription: string
  numero_cm: string
  nom: string; prenom: string
  telephone: string; adresse_mail: string
  date_activation: string
  type_contrat: string
  commercial: string
}

const todayIso = (): string => new Date().toISOString().slice(0, 10)
const shortDate = (iso: string): string =>
  !iso || iso.length < 10 ? '' : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

export default function EnergieExtractionPage() {
  useDocumentTitle('Extraction Énergie')
  const [du, setDu] = useState(todayIso())
  const [au, setAu] = useState(todayIso())
  const [statut, setStatut] = useState<'valide' | 'annule'>('valide')
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)

  const rechercher = async () => {
    if (du > au) { showToast('Dates incohérentes', 'error'); return }
    setLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/suivi-energie/extraction?du=${du}&au=${au}&statut=${statut}`,
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
    { key: 'date_souscription', dir: 'desc' },
    (r) => [
      r.nom, r.prenom, r.numero_cm, r.commercial,
      r.adresse_mail, r.telephone, r.type_contrat,
    ].join(' '),
  )
  const visible = tsf.rows as unknown as Row[]

  const exportXlsx = async () => {
    setExporting(true)
    try {
      const r = await fetch(
        `${API_BASE}/suivi-energie/extraction/export.xlsx?du=${du}&au=${au}&statut=${statut}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const cd = r.headers.get('content-disposition') || ''
      const m = /filename="?([^";]+)"?/.exec(cd)
      a.download = m ? m[1] : `extraction-energie-${statut}-${du}-${au}.xlsx`
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
          <DownloadIcon className="w-4 h-4 text-c-brand" /> Extraction Énergie
        </h1>
      </div>

      {/* Onglet Tickets (unique, mais on garde l'affichage cf WinDev) */}
      <div className="flex gap-1 border-b border-c-line mb-3">
        <button type="button"
          className="px-4 py-1.5 text-sm font-medium rounded-t bg-white border border-c-line border-b-white text-c-brand">
          Tickets
        </button>
      </div>

      {/* Filtres */}
      <div className="flex items-center gap-3 mb-3 bg-white p-3 rounded-xl border border-c-line text-sm flex-wrap">
        <label className="text-c-ink-faint text-xs">Du</label>
        <input type="date" value={du} onChange={e => setDu(e.target.value)}
          className="px-2 py-1 border border-c-line rounded text-xs h-7" />
        <label className="text-c-ink-faint text-xs">Au</label>
        <input type="date" value={au} onChange={e => setAu(e.target.value)}
          className="px-2 py-1 border border-c-line rounded text-xs h-7" />

        <div className="flex gap-0 ml-2">
          {([['Validé', 'valide'], ['Annulé', 'annule']] as const).map(([label, val], i) => (
            <button key={val} type="button" onClick={() => setStatut(val)}
              className={`px-3 h-7 text-xs border border-c-line ${
                i === 0 ? 'rounded-l' : 'rounded-r'
              } ${
                statut === val
                  ? 'bg-c-brand text-white border-c-brand'
                  : 'bg-white text-c-ink-soft'
              }`}>
              {label}
            </button>
          ))}
        </div>

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
              {exporting ? 'Génération…' : 'Export EXCEL'}
            </button>
          </>
        )}
      </div>

      <div className="bg-white rounded-xl border border-c-line overflow-hidden flex-1 flex flex-col">
        <div className="px-3 py-1.5 border-b border-c-line-soft text-xs text-c-ink-faint">
          {visible.length} / {rows.length} ticket(s)
        </div>
        <div className="flex-1 overflow-auto">
          <table className="w-full text-xs">
            <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0 z-10">
              <tr>
                <SortableTh label="Date de souscription" sortKey="date_souscription" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Numéro de CM" sortKey="numero_cm" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Nom" sortKey="nom" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Prénom" sortKey="prenom" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Téléphone" sortKey="telephone" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Adresse mail" sortKey="adresse_mail" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Date d'activation" sortKey="date_activation" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Type de contrat" sortKey="type_contrat" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Commercial" sortKey="commercial" sort={tsf.sort} onSort={tsf.toggleSort} />
              </tr>
            </thead>
            <tbody className="divide-y divide-c-line-soft">
              {visible.length === 0 ? (
                <tr>
                  <td colSpan={9} className="text-center py-12 text-c-ink-faint-2 italic">
                    {rows.length === 0
                      ? 'Choisis filtres puis Rechercher.'
                      : 'Aucun résultat.'}
                  </td>
                </tr>
              ) : visible.map(r => (
                <tr key={r.id_tk_liste} className="hover:bg-c-surface-soft">
                  <td className="px-2 py-1.5">{shortDate(r.date_souscription)}</td>
                  <td className="px-2 py-1.5 tabular-nums">{r.numero_cm}</td>
                  <td className="px-2 py-1.5">{r.nom}</td>
                  <td className="px-2 py-1.5">{r.prenom}</td>
                  <td className="px-2 py-1.5 tabular-nums">{r.telephone}</td>
                  <td className="px-2 py-1.5">{r.adresse_mail}</td>
                  <td className="px-2 py-1.5">{shortDate(r.date_activation)}</td>
                  <td className="px-2 py-1.5">
                    {r.type_contrat && (
                      <span className="px-1.5 py-0.5 rounded bg-c-brand/10 text-c-brand text-[10px] font-medium">
                        {r.type_contrat}
                      </span>
                    )}
                  </td>
                  <td className="px-2 py-1.5">{r.commercial}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
