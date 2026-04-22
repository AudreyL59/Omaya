import { useRef } from 'react'
import { motion } from 'framer-motion'
import { X, FileText, CheckCheck } from 'lucide-react'
import PdfExportButton from '@/components/PdfExportButton'

interface CvSaisiRow {
  ope_id: string
  lib_source: string
  annonceur_coopteur: string
}

interface CvTraiteRow {
  ope_id: string
  lib_source: string
  annonceur_coopteur: string
  statut_actuel: string
}

export default function StatSaisieCvDetailModal({
  title,
  opeId,
  saisis,
  traites,
  onClose,
}: {
  title: string
  opeId: string | null  // null = total (tous operateurs)
  saisis: CvSaisiRow[]
  traites: CvTraiteRow[]
  onClose: () => void
}) {
  const inScope = (id: string) => opeId === null || id === opeId

  const filteredSaisis = saisis.filter((r) => inScope(r.ope_id))
  const filteredTraites = traites.filter((r) => inScope(r.ope_id))

  const nbSaisis = filteredSaisis.length
  const nbTraites = filteredTraites.length

  // Breakdown par source : { source -> { total, byAnnonceur: { name -> count } } }
  const buildBreakdown = (rows: { lib_source: string; annonceur_coopteur: string }[]) => {
    const map = new Map<string, { total: number; sub: Map<string, number> }>()
    for (const r of rows) {
      const src = r.lib_source || 'Non renseigne'
      if (!map.has(src)) map.set(src, { total: 0, sub: new Map() })
      const entry = map.get(src)!
      entry.total += 1
      if (r.annonceur_coopteur) {
        entry.sub.set(
          r.annonceur_coopteur,
          (entry.sub.get(r.annonceur_coopteur) || 0) + 1
        )
      }
    }
    return [...map.entries()]
      .map(([src, v]) => ({
        source: src,
        total: v.total,
        sub: [...v.sub.entries()]
          .map(([nom, nb]) => ({ nom, nb }))
          .sort((a, b) => b.nb - a.nb),
      }))
      .sort((a, b) => b.total - a.total)
  }

  const sourcesSaisis = buildBreakdown(filteredSaisis)
  const sourcesTraites = buildBreakdown(filteredTraites)

  // Statuts des CV traités
  const statutsMap = new Map<string, number>()
  for (const r of filteredTraites) {
    const s = r.statut_actuel || 'Non renseigne'
    statutsMap.set(s, (statutsMap.get(s) || 0) + 1)
  }
  const statuts = [...statutsMap.entries()]
    .map(([lib, nb]) => ({ lib, nb }))
    .sort((a, b) => b.nb - a.nb)
  const maxStatut = statuts.reduce((m, s) => Math.max(m, s.nb), 0)

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
            <p className="text-xs text-gray-500 mt-0.5">
              Detail Stats CV Saisis &amp; traites
            </p>
          </div>
          <div className="flex items-center gap-2">
            <PdfExportButton
              targetRef={contentRef}
              filename={`detail-saisie-cv-${title.toLowerCase().replace(/\s+/g, '-')}`}
              title={`${title} - Detail Stats CV Saisis & traites`}
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
          <div className="grid grid-cols-2 gap-3">
            <KpiCard
              icon={<FileText className="w-5 h-5" />}
              label="CV Saisis"
              value={nbSaisis}
              color="text-blue-600"
            />
            <KpiCard
              icon={<CheckCheck className="w-5 h-5" />}
              label="CV Traites"
              value={nbTraites}
              color="text-emerald-600"
            />
          </div>

          {/* Sources des CV Saisis */}
          {sourcesSaisis.length > 0 && (
            <BreakdownSection
              title="Sources des CV Saisis"
              total={nbSaisis}
              groups={sourcesSaisis}
              color="bg-blue-500"
              colorSub="bg-blue-300"
            />
          )}

          {/* Sources des CV Traites */}
          {sourcesTraites.length > 0 && (
            <BreakdownSection
              title="Sources des CV Traites"
              total={nbTraites}
              groups={sourcesTraites}
              color="bg-emerald-500"
              colorSub="bg-emerald-300"
            />
          )}

          {/* Statuts des CV Traites */}
          {statuts.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase tracking-wide">
                Statut des CV Traites
              </div>
              <div className="p-4 space-y-1.5">
                {statuts.map((s) => {
                  const pct = maxStatut > 0 ? (s.nb / maxStatut) * 100 : 0
                  return (
                    <div key={s.lib}>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-gray-700 font-medium">{s.lib}</span>
                        <span className="tabular-nums font-semibold text-gray-900">
                          {s.nb}
                        </span>
                      </div>
                      <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-violet-400 transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {nbSaisis === 0 && nbTraites === 0 && (
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
  color,
}: {
  icon: React.ReactNode
  label: string
  value: number
  color: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 px-3 py-2.5">
      <div className="flex items-center gap-1.5 text-gray-400">
        {icon}
        <div className="text-[10px] uppercase tracking-wide font-medium">{label}</div>
      </div>
      <div className={`text-2xl font-bold tabular-nums mt-0.5 ${color}`}>
        {value}
      </div>
    </div>
  )
}

function BreakdownSection({
  title,
  total,
  groups,
  color,
  colorSub,
}: {
  title: string
  total: number
  groups: { source: string; total: number; sub: { nom: string; nb: number }[] }[]
  color: string
  colorSub: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase tracking-wide">
        {title}
      </div>
      <div className="p-4 space-y-3">
        {groups.map((g) => {
          const pctGroup = total > 0 ? (g.total / total) * 100 : 0
          return (
            <div key={g.source}>
              {/* Barre du groupe */}
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="font-semibold text-gray-900">{g.source}</span>
                <span className="tabular-nums text-gray-500">
                  <span className="font-semibold text-gray-900">{g.total}</span>
                  <span className="ml-1.5 text-gray-400">({pctGroup.toFixed(1)} %)</span>
                </span>
              </div>
              <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full ${color} transition-all`}
                  style={{ width: `${pctGroup}%` }}
                />
              </div>
              {/* Sous-niveaux (annonceur / coopteur) */}
              {g.sub.length > 0 && (
                <div className="pl-4 mt-1.5 space-y-1">
                  {g.sub.map((s) => {
                    const pctSub = g.total > 0 ? (s.nb / g.total) * 100 : 0
                    return (
                      <div key={s.nom}>
                        <div className="flex items-center justify-between text-[11px] mb-0.5">
                          <span className="text-gray-600 truncate">{s.nom}</span>
                          <span className="tabular-nums text-gray-500 shrink-0 ml-2">
                            {s.nb}
                            <span className="text-gray-400 ml-1">({pctSub.toFixed(0)} %)</span>
                          </span>
                        </div>
                        <div className="w-full h-1 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${colorSub} transition-all`}
                            style={{ width: `${pctSub}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
