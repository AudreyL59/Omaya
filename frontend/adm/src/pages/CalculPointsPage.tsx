/**
 * Fen_CalculPointsBS - Recalcul des points contrats par partenaire.
 *
 * Combo Partenaire + dates Du/Au + checkbox Simulation + Btn Calcul Point.
 * Onglet Vendeurs (agrégat par vendeur) + onglet Contrats modifiés (détail).
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Loader2, Play, Download, Calculator, TrendingUp, TrendingDown,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PageHeader from '@/components/PageHeader'

const API_BASE = '/api/adm'

interface PartenaireCombo {
  prefixe_bdd: string
  lib_partenaire: string
}
interface ContratModifieRow {
  id_contrat: string
  part: string
  num_bs: string
  date_signature: string
  famille: string
  ss_fam: string
  car: number
  kva: number
  nb_opt: string
  lib_etat: string
  id_type_etat: number
  nb_point_av: number
  nb_point_ap: number
}
interface RecalculResult {
  ok: boolean
  nb_ctts_lus: number
  nb_modifies: number
  lignes: ContratModifieRow[]
  message: string
}

interface VendeurAgg {
  num_bs: string  // pour identifier
  diff_total: number
  nb_contrats: number
}

type Tab = 'vendeurs' | 'contrats'

const currentDate = (): string =>
  new Date().toISOString().slice(0, 10)

const firstOfCurrentMonth = (): string => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
}

const shortDate = (iso: string): string =>
  !iso || iso.length < 10
    ? ''
    : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

export default function CalculPointsPage() {
  useDocumentTitle('Calcul Points Contrats')

  const [partenaires, setPartenaires] = useState<PartenaireCombo[]>([])
  const [prefixe, setPrefixe] = useState('')
  const [du, setDu] = useState(firstOfCurrentMonth())
  const [au, setAu] = useState(currentDate())
  const [simulation, setSimulation] = useState(true)

  const [loading, setLoading] = useState(false)
  const [lignes, setLignes] = useState<ContratModifieRow[]>([])
  const [nbLus, setNbLus] = useState(0)
  const [tab, setTab] = useState<Tab>('contrats')

  const loadPartenaires = useCallback(async () => {
    try {
      const r = await fetch(
        `${API_BASE}/paies/calcul-points/partenaires`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      const d: PartenaireCombo[] = await r.json()
      setPartenaires(d || [])
    } catch { /* silent */ }
  }, [])
  useEffect(() => { void loadPartenaires() }, [loadPartenaires])

  const doCalcul = async () => {
    if (!prefixe) {
      showToast('Choisis un partenaire', 'info')
      return
    }
    if (!simulation) {
      const ok = await showConfirm({
        title: 'Recalcul en base',
        message: `Mettre à jour les nb_points en base pour ${prefixe} sur ${shortDate(du)} → ${shortDate(au)} ?`,
      })
      if (!ok) return
    }
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/paies/calcul-points/recalcul`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prefixe, du, au, simulation }),
      })
      const d: RecalculResult = await r.json()
      if (!d.ok) {
        showToast(d.message || 'Erreur', 'error')
        return
      }
      setLignes(d.lignes || [])
      setNbLus(d.nb_ctts_lus)
      setTab('contrats')
      showToast(d.message || '', 'success')
    } finally { setLoading(false) }
  }

  const doExport = async () => {
    if (lignes.length === 0) {
      showToast('Aucune ligne à exporter', 'info')
      return
    }
    setLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/paies/calcul-points/export-xlsx`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ prefixe, du, au, lignes }),
        },
      )
      if (!r.ok) { showToast('Erreur export', 'error'); return }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const disp = r.headers.get('Content-Disposition') || ''
      const m = disp.match(/filename="?([^";]+)"?/)
      const fic = m ? m[1] : 'calcul_points.xlsx'
      const a = document.createElement('a')
      a.href = url; a.download = fic; a.click()
      setTimeout(() => URL.revokeObjectURL(url), 30_000)
    } finally { setLoading(false) }
  }

  // Agrégat par famille pour l'onglet Vendeurs (défaut : agrégation famille)
  const vendeursAgg: VendeurAgg[] = (() => {
    const map = new Map<string, VendeurAgg>()
    lignes.forEach((l) => {
      const key = l.famille || '?'
      const cur = map.get(key) || {
        num_bs: key, diff_total: 0, nb_contrats: 0,
      }
      cur.diff_total += l.nb_point_ap - l.nb_point_av
      cur.nb_contrats += 1
      map.set(key, cur)
    })
    return Array.from(map.values())
      .sort((a, b) => Math.abs(b.diff_total) - Math.abs(a.diff_total))
  })()

  const totalDiff = lignes.reduce(
    (s, l) => s + (l.nb_point_ap - l.nb_point_av), 0,
  )

  return (
    <div className="min-h-screen bg-[#F5F5F0] p-6">
      <div className="max-w-full mx-auto">
        <PageHeader icon={Calculator} title="Calcul Points Contrats" />

        {/* Filtres */}
        <div className="bg-white rounded-lg shadow p-4 mb-4">
          <div className="flex items-end gap-3 flex-wrap">
            <label className="flex flex-col text-xs gap-1 min-w-[220px]">
              <span className="text-[#8B7355] font-medium">Partenaire</span>
              <select value={prefixe} onChange={(e) => setPrefixe(e.target.value)}
                      className="px-2 py-1.5 border border-[#E5E0D5] rounded">
                <option value="">Choisir...</option>
                {partenaires.map((p) => (
                  <option key={p.prefixe_bdd} value={p.prefixe_bdd}>
                    {p.lib_partenaire}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-xs gap-1">
              <span className="text-[#8B7355] font-medium">Du</span>
              <input type="date" value={du} onChange={(e) => setDu(e.target.value)}
                     className="px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <label className="flex flex-col text-xs gap-1">
              <span className="text-[#8B7355] font-medium">Au</span>
              <input type="date" value={au} onChange={(e) => setAu(e.target.value)}
                     className="px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <button
              onClick={doCalcul}
              disabled={loading || !prefixe}
              className="flex items-center gap-2 px-3 py-2 rounded bg-[#17494E] text-white disabled:opacity-40 hover:bg-[#0F3438]"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Calcul Point
            </button>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={simulation}
                     onChange={(e) => setSimulation(e.target.checked)}
                     className="accent-[#17494E]" />
              <span className="text-[#8B7355] font-medium">Mode Simulation</span>
              {!simulation && (
                <span className="ml-1 text-xs px-2 py-0.5 rounded bg-red-100 text-red-800 font-semibold">
                  MAJ BASE
                </span>
              )}
            </label>
            <button
              onClick={doExport}
              disabled={loading || lignes.length === 0}
              title="Export XLSX"
              className="ml-auto p-2 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] disabled:opacity-40"
            >
              <Download className="w-4 h-4" />
            </button>
          </div>

          {nbLus > 0 && (
            <div className="mt-3 pt-3 border-t border-[#F0EDE5] flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1.5">
                <span className="text-[#8B7355]">Contrats lus :</span>
                <span className="font-semibold text-[#17494E] tabular-nums">
                  {nbLus}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-[#8B7355]">Modifiés :</span>
                <span className="font-semibold text-[#8B7355] tabular-nums">
                  {lignes.length}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-[#8B7355]">Delta total :</span>
                <span className={`font-semibold tabular-nums flex items-center gap-1 ${
                  totalDiff > 0 ? 'text-green-700' : totalDiff < 0 ? 'text-red-700' : ''
                }`}>
                  {totalDiff > 0 ? <TrendingUp className="w-3.5 h-3.5" /> :
                    totalDiff < 0 ? <TrendingDown className="w-3.5 h-3.5" /> : null}
                  {totalDiff > 0 ? '+' : ''}{totalDiff.toFixed(2)}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Onglets */}
        <div className="flex border-b border-[#E5E0D5] mb-4">
          {[
            { key: 'vendeurs' as Tab, label: 'Familles' },
            { key: 'contrats' as Tab, label: `Contrats modifiés (${lignes.length})` },
          ].map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 ${
                tab === t.key
                  ? 'border-[#17494E] text-[#17494E]'
                  : 'border-transparent text-gray-500 hover:text-[#17494E]'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Contenu onglet */}
        {tab === 'vendeurs' && (
          <div className="bg-white rounded-lg shadow p-4">
            <div className="overflow-x-auto max-h-[65vh] overflow-y-auto">
              <table className="text-xs w-full">
                <thead className="sticky top-0 bg-[#17494E] text-white z-10">
                  <tr>
                    <th className="py-2 px-2 text-left">Famille</th>
                    <th className="py-2 px-2 text-right">Nb contrats</th>
                    <th className="py-2 px-2 text-right">Delta pts</th>
                  </tr>
                </thead>
                <tbody>
                  {vendeursAgg.map((v, i) => (
                    <tr key={i} className="border-b border-[#F0EDE5] hover:bg-[#ECF1F2]">
                      <td className="py-1.5 px-2 font-medium">{v.num_bs}</td>
                      <td className="py-1.5 px-2 text-right tabular-nums">{v.nb_contrats}</td>
                      <td className={`py-1.5 px-2 text-right tabular-nums font-semibold ${
                        v.diff_total > 0 ? 'text-green-700' :
                        v.diff_total < 0 ? 'text-red-700' : ''
                      }`}>
                        {v.diff_total > 0 ? '+' : ''}{v.diff_total.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                  {vendeursAgg.length === 0 && (
                    <tr><td colSpan={3} className="py-8 text-center text-gray-400">
                      Aucune ligne
                    </td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {tab === 'contrats' && (
          <div className="bg-white rounded-lg shadow p-4">
            <div className="overflow-x-auto max-h-[65vh] overflow-y-auto">
              <table className="text-xs w-full">
                <thead className="sticky top-0 bg-[#17494E] text-white z-10">
                  <tr>
                    <th className="py-2 px-2 text-left">Part</th>
                    <th className="py-2 px-2 text-left">NumBS</th>
                    <th className="py-2 px-2 text-left">Date sign.</th>
                    <th className="py-2 px-2 text-left">Famille</th>
                    <th className="py-2 px-2 text-left">Ss Fam</th>
                    <th className="py-2 px-2 text-right">CAR</th>
                    <th className="py-2 px-2 text-right">KVA</th>
                    <th className="py-2 px-2 text-left">Options</th>
                    <th className="py-2 px-2 text-left">Etat</th>
                    <th className="py-2 px-2 text-right">Av</th>
                    <th className="py-2 px-2 text-right">Ap</th>
                    <th className="py-2 px-2 text-right">Δ</th>
                  </tr>
                </thead>
                <tbody>
                  {lignes.map((l, i) => {
                    const diff = l.nb_point_ap - l.nb_point_av
                    return (
                      <tr key={i} className="border-b border-[#F0EDE5] hover:bg-[#ECF1F2]">
                        <td className="py-1.5 px-2 font-medium">{l.part}</td>
                        <td className="py-1.5 px-2 font-mono">{l.num_bs}</td>
                        <td className="py-1.5 px-2 tabular-nums">
                          {shortDate(l.date_signature)}
                        </td>
                        <td className="py-1.5 px-2">{l.famille}</td>
                        <td className="py-1.5 px-2">{l.ss_fam}</td>
                        <td className="py-1.5 px-2 text-right tabular-nums">
                          {l.car || ''}
                        </td>
                        <td className="py-1.5 px-2 text-right tabular-nums">
                          {l.kva || ''}
                        </td>
                        <td className="py-1.5 px-2 truncate max-w-[180px]" title={l.nb_opt}>
                          {l.nb_opt}
                        </td>
                        <td className="py-1.5 px-2 truncate max-w-[140px]" title={l.lib_etat}>
                          {l.lib_etat}
                        </td>
                        <td className="py-1.5 px-2 text-right tabular-nums text-gray-600">
                          {l.nb_point_av.toFixed(2)}
                        </td>
                        <td className="py-1.5 px-2 text-right tabular-nums font-semibold">
                          {l.nb_point_ap.toFixed(2)}
                        </td>
                        <td className={`py-1.5 px-2 text-right tabular-nums font-semibold ${
                          diff > 0 ? 'text-green-700' : diff < 0 ? 'text-red-700' : ''
                        }`}>
                          {diff > 0 ? '+' : ''}{diff.toFixed(2)}
                        </td>
                      </tr>
                    )
                  })}
                  {lignes.length === 0 && (
                    <tr><td colSpan={12} className="py-8 text-center text-gray-400">
                      Aucun contrat modifié - Lance un calcul
                    </td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
