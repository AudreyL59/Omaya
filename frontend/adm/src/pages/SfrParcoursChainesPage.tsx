/**
 * Fen_ParcoursChaine - Suivi SFR > Parcours Chaînés.
 *
 * Affiche par vendeur ses stats parcours chaînés (FIBRE + MOBILE
 * dans le même ticket) sur la plage Du/Au.
 *
 * Tableau colorisé par ligne :
 *   - Vert : tx global >= 80% ET tx chaînés >= 80%
 *   - Orange : tx global >= 80% ET tx chaînés < 80%
 *   - Jaune : tx global < 80% ET tx chaînés >= 80%
 *   - Rouge : les 2 < 80%
 *
 * 2 boutons d'action : Autoriser / Interdire les tickets Diff
 * (= gère pgt_salarie_droit_acces id_type_droit_acces=209).
 *
 * Export XLSX avec fond colore par ligne.
 */
import { useState } from 'react'
import {
  Search, Loader2, ArrowLeft, FileDown, Link2, Link2Off, GitBranch,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  useTableSortFilter, SortableTh, FilterInput,
} from '@shared/production/_tableHelpers'

const API_BASE = '/api/adm'

interface Row {
  id_sa: string; vendeur: string
  en_activite: boolean; agence: string; equipe: string
  droit_diff: boolean
  nb_tk_valides: number; nb_parcours_chaines: number
  nb_tk_chaine_tot: number; nb_tk_diff: number
  pourcent_global: number; pourcent_chaines: number
  couleur_hex: string
}

const todayIso = (): string => new Date().toISOString().slice(0, 10)

export default function SfrParcoursChainesPage() {
  useDocumentTitle('Parcours Chaînés SFR')
  const [du, setDu] = useState(todayIso())
  const [au, setAu] = useState(todayIso())
  const [rows, setRows] = useState<Row[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)

  const rechercher = async () => {
    if (du > au) { showToast('Dates incohérentes', 'error'); return }
    setLoading(true); setSelected(new Set())
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/parcours-chaines?du=${du}&au=${au}`,
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
    { key: 'pourcent_chaines', dir: 'desc' },
    (r) => `${r.vendeur} ${r.agence} ${r.equipe}`,
  )
  const visible = tsf.rows as unknown as Row[]

  const toggleAll = () => {
    if (visible.every(r => selected.has(r.id_sa))) {
      const s = new Set(selected); for (const r of visible) s.delete(r.id_sa); setSelected(s)
    } else {
      const s = new Set(selected); for (const r of visible) s.add(r.id_sa); setSelected(s)
    }
  }
  const toggle = (id: string) => {
    const s = new Set(selected); if (s.has(id)) s.delete(id); else s.add(id); setSelected(s)
  }

  const doDroitDiff = async (actif: boolean) => {
    const ids = Array.from(selected).map(id => parseInt(id, 10))
    if (ids.length === 0) { showToast('Aucun vendeur sélectionné.', 'info'); return }
    const ok = await showConfirm({
      title: actif
        ? 'Autoriser les tickets Diff SFR'
        : 'Interdire les tickets Diff SFR',
      message: actif
        ? `Vous êtes sur le point de valider le droit aux tickets Diff SFR pour ${ids.length} vendeur(s). Continuer ?`
        : `Vous êtes sur le point de supprimer le droit aux tickets Diff SFR pour ${ids.length} vendeur(s). Continuer ?`,
    })
    if (!ok) return
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/parcours-chaines/droit-diff`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ ids_salarie: ids, actif }),
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      const d: { nb_updated: number } = await r.json()
      showToast(`${d.nb_updated} vendeur(s) ${actif ? 'autorisé(s)' : 'interdit(s)'}`, 'success')
      // refresh
      await rechercher()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  const exportXlsx = async () => {
    setExporting(true)
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/parcours-chaines/export.xlsx?du=${du}&au=${au}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const cd = r.headers.get('content-disposition') || ''
      const m = /filename="?([^";]+)"?/.exec(cd)
      a.download = m ? m[1] : `parcours-chaines-${du}-${au}.xlsx`
      document.body.appendChild(a); a.click()
      document.body.removeChild(a); URL.revokeObjectURL(url)
    } catch (e) {
      showToast(`Erreur export : ${(e as Error).message}`, 'error')
    } finally { setExporting(false) }
  }

  const fmtPct = (n: number): string =>
    `${n.toFixed(1).replace('.', ',')} %`

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-110px)] text-c-ink">
      <div className="flex items-center gap-2 mb-3">
        <Link to=".." relative="path"
          className="p-1.5 hover:bg-c-surface-soft rounded text-c-ink-faint-2">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-lg font-bold flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-c-brand" />
          Vérif Tx Parcours chaînés
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
          <button type="button" onClick={exportXlsx} disabled={exporting}
            className="flex items-center gap-1.5 px-2.5 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft h-7 disabled:opacity-50 disabled:cursor-wait">
            {exporting ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                       : <FileDown className="w-3.5 h-3.5" />}
            {exporting ? 'Génération…' : 'Export Excel'}
          </button>
        )}
      </div>

      {/* Boutons d'action droits Diff */}
      <div className="flex items-center gap-3 mb-3 bg-white px-3 py-2 rounded-xl border border-c-line text-sm flex-wrap">
        <button type="button" onClick={() => doDroitDiff(true)}
          disabled={selected.size === 0}
          className="flex items-center gap-2 px-3 py-1 rounded text-c-brand hover:bg-c-brand/10 disabled:opacity-30 text-xs">
          <Link2 className="w-4 h-4" />
          Autoriser les tickets Diff à la sélection de vendeurs
        </button>
        <button type="button" onClick={() => doDroitDiff(false)}
          disabled={selected.size === 0}
          className="flex items-center gap-2 px-3 py-1 rounded text-red-600 hover:bg-red-50 disabled:opacity-30 text-xs">
          <Link2Off className="w-4 h-4" />
          Interdire les tickets Diff à la sélection de vendeurs
        </button>
        <div className="flex-1" />
        <FilterInput value={tsf.filter} onChange={tsf.setFilter}
          placeholder="Filtrer vendeur/agence/équipe…" />
      </div>

      <div className="bg-white rounded-xl border border-c-line overflow-hidden flex-1 flex flex-col">
        <div className="px-3 py-1.5 border-b border-c-line-soft text-xs text-c-ink-faint flex items-center gap-3">
          {visible.length} / {rows.length} vendeur(s) | {selected.size} sélectionné(s)
          {/* Légende */}
          <div className="ml-auto flex items-center gap-3 text-[10px]">
            <Legend color="#bbf7d0" label="Tx Glob ≥ 80% & Chaînés ≥ 80%" />
            <Legend color="#fed7aa" label="Glob ≥ 80% & Chaînés < 80%" />
            <Legend color="#fef3c7" label="Glob < 80% & Chaînés ≥ 80%" />
            <Legend color="#fecaca" label="Les 2 < 80%" />
          </div>
        </div>
        <div className="flex-1 overflow-auto">
          <table className="w-full text-xs">
            <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0 z-10">
              <tr>
                <th className="px-2 py-2 text-center w-8">
                  <input type="checkbox"
                    checked={visible.length > 0 && visible.every(r => selected.has(r.id_sa))}
                    onChange={toggleAll} />
                </th>
                <SortableTh label="Vendeur" sortKey="vendeur" sort={tsf.sort} onSort={tsf.toggleSort} />
                <SortableTh label="Actif" sortKey="en_activite" sort={tsf.sort} onSort={tsf.toggleSort} align="center" />
                <SortableTh label="Droit Diff" sortKey="droit_diff" sort={tsf.sort} onSort={tsf.toggleSort} align="center" />
                <SortableTh label="nb PC Validés" sortKey="nb_tk_valides" sort={tsf.sort} onSort={tsf.toggleSort} align="right" />
                <SortableTh label="nb PC potentiels" sortKey="nb_parcours_chaines" sort={tsf.sort} onSort={tsf.toggleSort} align="right" />
                <SortableTh label="% PC validés Prod chaînés" sortKey="pourcent_global" sort={tsf.sort} onSort={tsf.toggleSort} align="right" />
                <SortableTh label="nb Tk Validés Prod globale" sortKey="nb_tk_chaine_tot" sort={tsf.sort} onSort={tsf.toggleSort} align="right" />
                <SortableTh label="% PC Val Prod globale" sortKey="pourcent_chaines" sort={tsf.sort} onSort={tsf.toggleSort} align="right" />
              </tr>
            </thead>
            <tbody className="divide-y divide-c-line-soft">
              {visible.length === 0 ? (
                <tr>
                  <td colSpan={9} className="text-center py-12 text-c-ink-faint-2 italic">
                    {rows.length === 0
                      ? 'Choisis dates puis Rechercher.'
                      : 'Aucun résultat avec ce filtre.'}
                  </td>
                </tr>
              ) : visible.map(r => (
                <tr key={r.id_sa}
                  onClick={() => toggle(r.id_sa)}
                  className="cursor-pointer hover:opacity-90"
                  style={r.couleur_hex ? { background: r.couleur_hex } : {}}>
                  <td className="px-2 py-1.5 text-center">
                    <input type="checkbox" checked={selected.has(r.id_sa)}
                      onChange={() => toggle(r.id_sa)}
                      onClick={(e) => e.stopPropagation()} />
                  </td>
                  <td className="px-2 py-1.5 font-medium">{r.vendeur}</td>
                  <td className="px-2 py-1.5 text-center">{r.en_activite ? '✓' : ''}</td>
                  <td className="px-2 py-1.5 text-center">{r.droit_diff ? '✓' : ''}</td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{r.nb_tk_valides}</td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{r.nb_parcours_chaines}</td>
                  <td className="px-2 py-1.5 text-right tabular-nums font-medium">
                    {fmtPct(r.pourcent_global)}
                  </td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{r.nb_tk_chaine_tot}</td>
                  <td className="px-2 py-1.5 text-right tabular-nums font-medium">
                    {fmtPct(r.pourcent_chaines)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1">
      <span className="inline-block w-3 h-3 rounded"
        style={{ background: color, border: '1px solid rgba(0,0,0,0.1)' }} />
      {label}
    </span>
  )
}
