import { useRef } from 'react'
import { motion } from 'framer-motion'
import { X, FileText, UserCheck, LogOut, Timer, TrendingUp, TrendingDown } from 'lucide-react'
import PdfExportButton from '@/components/PdfExportButton'

// Types minimal reutilises depuis StatRHEntreeSortiePage
interface DpaeRow {
  id_salarie: string
  en_activite: boolean
  origine: string
  prod: boolean
  id_orga: string
}

interface SortieRow {
  id_salarie: string
  date_entree: string
  date_sortie_reelle: string
  fin_demandee: string
  id_type_sortie: number
  type_sortie_lib: string
  prod: boolean
  id_orga: string
}

function dureeJours(entree: string, sortie: string): number {
  const parse = (s: string): Date | null => {
    if (!s) return null
    const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})/)
    if (iso) return new Date(+iso[1], +iso[2] - 1, +iso[3])
    if (s.length >= 8 && /^\d+$/.test(s.slice(0, 8))) {
      return new Date(+s.slice(0, 4), +s.slice(4, 6) - 1, +s.slice(6, 8))
    }
    return null
  }
  const a = parse(entree)
  const b = parse(sortie)
  if (!a || !b) return 0
  return Math.max(0, Math.round((b.getTime() - a.getTime()) / (1000 * 60 * 60 * 24)))
}

export default function StatDetailModal({
  title,
  orgaIds,
  dpaeRows,
  sortieRows,
  onClose,
}: {
  title: string
  orgaIds: string[]  // 1 equipe ou les equipes d'une agence (ou toutes si empty)
  dpaeRows: DpaeRow[]
  sortieRows: SortieRow[]
  onClose: () => void
}) {
  const all = orgaIds.length === 0
  const inScope = (id: string) => all || orgaIds.includes(id)

  const dpae = dpaeRows.filter((r) => inScope(r.id_orga))
  const sorties = sortieRows.filter((r) => inScope(r.id_orga))

  // KPIs
  const nbDpae = dpae.length
  const nbDpaeCvtheque = dpae.filter((r) => r.origine === 'CVtheque').length
  const nbDpaeActifs = dpae.filter((r) => r.en_activite).length
  const nbSorties = sorties.length
  const sortiesNonProd = sorties.filter((r) => !r.prod)
  const sortiesProd = sorties.filter((r) => r.prod)
  const joursNonProd = sortiesNonProd.reduce(
    (a, r) => a + dureeJours(r.date_entree, r.date_sortie_reelle || r.fin_demandee),
    0
  )
  const joursProd = sortiesProd.reduce(
    (a, r) => a + dureeJours(r.date_entree, r.date_sortie_reelle || r.fin_demandee),
    0
  )
  const moyNonProd = sortiesNonProd.length > 0 ? joursNonProd / sortiesNonProd.length : 0
  const moyProd = sortiesProd.length > 0 ? joursProd / sortiesProd.length : 0

  const pctActifs = nbDpae > 0 ? (nbDpaeActifs / nbDpae) * 100 : 0
  const pctCvtheque = nbDpae > 0 ? (nbDpaeCvtheque / nbDpae) * 100 : 0
  const pctSortisFromDpae = nbDpae > 0 ? ((nbDpae - nbDpaeActifs) / nbDpae) * 100 : 0
  const pctProd = nbSorties > 0 ? (sortiesProd.length / nbSorties) * 100 : 0
  const pctNonProd = nbSorties > 0 ? (sortiesNonProd.length / nbSorties) * 100 : 0

  // Breakdown : Sorties par type
  const sortiesParType = new Map<string, { nb: number; jours: number }>()
  for (const s of sorties) {
    const key = s.type_sortie_lib || `Type ${s.id_type_sortie}` || 'Inconnu'
    const cur = sortiesParType.get(key) || { nb: 0, jours: 0 }
    cur.nb += 1
    cur.jours += dureeJours(s.date_entree, s.date_sortie_reelle || s.fin_demandee)
    sortiesParType.set(key, cur)
  }
  const sortiesParTypeArr = [...sortiesParType.entries()]
    .map(([type, v]) => ({
      type,
      nb: v.nb,
      moy_j: v.nb > 0 ? (v.jours / v.nb).toFixed(1) : '0.0',
    }))
    .sort((a, b) => b.nb - a.nb)

  const contentRef = useRef<HTMLDivElement>(null)

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 sticky top-0 bg-white z-10">
          <div>
            <h2 className="text-lg font-bold text-gray-900">{title}</h2>
            <p className="text-xs text-gray-500 mt-0.5">Detail Entrees / Sorties</p>
          </div>
          <div className="flex items-center gap-2">
            <PdfExportButton
              targetRef={contentRef}
              filename={`detail-entree-sortie-${title.toLowerCase().replace(/\s+/g, '-')}`}
              title={`${title} - Detail Entrees / Sorties`}
            />
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div ref={contentRef} className="p-6 space-y-6">
          {/* KPI cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <KpiCard
              icon={<FileText className="w-5 h-5" />}
              label="DPAE"
              value={nbDpae}
              color="text-gray-900"
            />
            <KpiCard
              icon={<FileText className="w-5 h-5" />}
              label="DPAE CVtheque"
              value={nbDpaeCvtheque}
              sub={`${pctCvtheque.toFixed(1)} %`}
              color="text-indigo-600"
            />
            <KpiCard
              icon={<UserCheck className="w-5 h-5" />}
              label="DPAE actives"
              value={nbDpaeActifs}
              sub={`${pctActifs.toFixed(1)} %`}
              color="text-emerald-600"
            />
            <KpiCard
              icon={<LogOut className="w-5 h-5" />}
              label="Sorties"
              value={nbSorties}
              color="text-rose-600"
            />
            <KpiCard
              icon={<Timer className="w-5 h-5" />}
              label="Moy. j. non Prod"
              value={moyNonProd.toFixed(1)}
              unit="j"
              color="text-orange-600"
            />
            <KpiCard
              icon={<Timer className="w-5 h-5" />}
              label="Moy. j. Prod"
              value={moyProd.toFixed(1)}
              unit="j"
              color="text-teal-600"
            />
          </div>

          {/* Funnel DPAE */}
          {nbDpae > 0 && (
            <FunnelSection title="DPAE sur la periode">
              <FunnelBar
                label="DPAE total"
                value={nbDpae}
                pct={100}
                color="bg-gray-900"
              />
              <FunnelBar
                label="DPAE actives"
                value={nbDpaeActifs}
                pct={pctActifs}
                color="bg-emerald-500"
                icon={<TrendingUp className="w-3 h-3" />}
                indent
              />
              <FunnelBar
                label="DPAE sorties"
                value={nbDpae - nbDpaeActifs}
                pct={pctSortisFromDpae}
                color="bg-orange-500"
                icon={<TrendingDown className="w-3 h-3" />}
                indent
              />
              <FunnelBar
                label="DPAE via CVtheque"
                value={nbDpaeCvtheque}
                pct={pctCvtheque}
                color="bg-indigo-500"
                indent
              />
              <FunnelBar
                label="DPAE via Cooptation"
                value={nbDpae - nbDpaeCvtheque}
                pct={100 - pctCvtheque}
                color="bg-purple-500"
                indent
              />
            </FunnelSection>
          )}

          {/* Funnel Sorties */}
          {nbSorties > 0 && (
            <FunnelSection title="Sorties sur la periode">
              <FunnelBar
                label="Sorties total"
                value={nbSorties}
                pct={100}
                color="bg-gray-900"
              />
              <FunnelBar
                label="Prod"
                value={sortiesProd.length}
                pct={pctProd}
                color="bg-emerald-500"
                indent
              />
              <FunnelBar
                label="Non Prod"
                value={sortiesNonProd.length}
                pct={pctNonProd}
                color="bg-orange-500"
                indent
              />
            </FunnelSection>
          )}

          {/* Tableau sorties par type */}
          {sortiesParTypeArr.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase tracking-wide">
                Sorties par type
              </div>
              <table className="w-full text-sm">
                <thead className="bg-white border-b border-gray-200">
                  <tr>
                    <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">
                      Type de sortie
                    </th>
                    <th className="text-right py-2 px-3 text-xs font-medium text-gray-500 uppercase">
                      Nb
                    </th>
                    <th className="text-right py-2 px-3 text-xs font-medium text-gray-500 uppercase">
                      % sur sorties
                    </th>
                    <th className="text-right py-2 px-3 text-xs font-medium text-gray-500 uppercase">
                      Moy duree (j)
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sortiesParTypeArr.map((r) => (
                    <tr key={r.type} className="border-b border-gray-100 last:border-0">
                      <td className="py-2 px-3 font-medium text-gray-900">{r.type}</td>
                      <td className="py-2 px-3 text-right tabular-nums">{r.nb}</td>
                      <td className="py-2 px-3 text-right tabular-nums text-gray-500">
                        {((r.nb / nbSorties) * 100).toFixed(1)} %
                      </td>
                      <td className="py-2 px-3 text-right tabular-nums text-gray-500">
                        {r.moy_j}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {nbDpae === 0 && nbSorties === 0 && (
            <div className="text-center py-10 text-gray-400 text-sm italic">
              Pas de donnees pour ce scope.
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  )
}

// --- Sous-composants ------------------------------------------------------

function KpiCard({
  icon,
  label,
  value,
  sub,
  unit,
  color,
}: {
  icon: React.ReactNode
  label: string
  value: number | string
  sub?: string
  unit?: string
  color: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 px-3 py-2.5">
      <div className="flex items-center gap-1.5 text-gray-400">
        {icon}
        <div className="text-[10px] uppercase tracking-wide font-medium">{label}</div>
      </div>
      <div className={`text-xl font-bold tabular-nums mt-0.5 ${color}`}>
        {value}
        {unit && <span className="text-sm font-normal ml-1">{unit}</span>}
      </div>
      {sub && <div className="text-[10px] text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

function FunnelSection({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase tracking-wide">
        {title}
      </div>
      <div className="p-4 space-y-1.5">{children}</div>
    </div>
  )
}

function FunnelBar({
  label,
  value,
  pct,
  color,
  icon,
  indent,
}: {
  label: string
  value: number
  pct: number
  color: string
  icon?: React.ReactNode
  indent?: boolean
}) {
  return (
    <div className={`${indent ? 'pl-4' : ''}`}>
      <div className="flex items-center justify-between text-xs mb-1">
        <div className="flex items-center gap-1.5 text-gray-700 font-medium">
          {icon}
          {label}
        </div>
        <div className="tabular-nums text-gray-500">
          <span className="font-semibold text-gray-900">{value}</span>
          <span className="ml-1.5 text-gray-400">({pct.toFixed(1)} %)</span>
        </div>
      </div>
      <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} transition-all`}
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
    </div>
  )
}
