import { useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  FileText,
  CheckCheck,
  UserCheck,
  GraduationCap,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import PdfExportButton from '@/components/PdfExportButton'

interface RdvRow {
  id_cvtheque: string
  op_crea_id: string
  op_crea_nom: string
  recruteur_id: string
  recruteur_nom: string
  statut_lib: string
  lib_source: string
  annonceur_coopteur: string
  est_present: boolean
  est_retenu: boolean
  est_jo: boolean
}

type Mode = 'operateur' | 'recruteur' | 'total'

export default function StatRdvDetailModal({
  title,
  mode,
  id,
  rdv,
  onClose,
}: {
  title: string
  mode: Mode
  id: string | null         // null / '' = total
  rdv: RdvRow[]
  onClose: () => void
}) {
  const inScope = (r: RdvRow) => {
    if (!id || mode === 'total') return true
    return mode === 'operateur' ? r.op_crea_id === id : r.recruteur_id === id
  }
  const filtered = rdv.filter(inScope)

  const nbRdv = filtered.length
  const nbPresents = filtered.filter((r) => r.est_present).length
  const nbRetenus = filtered.filter((r) => r.est_retenu).length
  const nbJO = filtered.filter((r) => r.est_jo).length

  const pct = (n: number, d: number) =>
    d > 0 ? `${((n / d) * 100).toFixed(1)} %` : '0.0 %'

  // Breakdown par Source (avec sous-niveau annonceur/coopteur)
  const sourceMap = new Map<string, { total: number; sub: Map<string, number> }>()
  for (const r of filtered) {
    const src = r.lib_source || 'Non renseigne'
    if (!sourceMap.has(src)) sourceMap.set(src, { total: 0, sub: new Map() })
    const g = sourceMap.get(src)!
    g.total += 1
    if (r.annonceur_coopteur) {
      g.sub.set(
        r.annonceur_coopteur,
        (g.sub.get(r.annonceur_coopteur) || 0) + 1
      )
    }
  }
  const sources = [...sourceMap.entries()]
    .map(([src, v]) => ({
      source: src,
      total: v.total,
      sub: [...v.sub.entries()]
        .map(([nom, nb]) => ({ nom, nb }))
        .sort((a, b) => b.nb - a.nb),
    }))
    .sort((a, b) => b.total - a.total)

  // Breakdown par Statut RDV (horizontal bars)
  const statutMap = new Map<string, number>()
  for (const r of filtered) {
    const s = r.statut_lib || 'Non renseigne'
    statutMap.set(s, (statutMap.get(s) || 0) + 1)
  }
  const statuts = [...statutMap.entries()]
    .map(([lib, nb]) => ({ lib, nb }))
    .sort((a, b) => b.nb - a.nb)
  const maxStatut = statuts.reduce((m, s) => Math.max(m, s.nb), 0)

  // Accordion : click source → breakdown par contrepartie (operateur ↔ recruteur ou annonceur)
  const [expandedSource, setExpandedSource] = useState<string | null>(null)
  const showPerParty = mode === 'total' || mode === 'operateur' || mode === 'recruteur'

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
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 sticky top-0 bg-white z-10">
          <div>
            <h2 className="text-lg font-bold text-gray-900">{title}</h2>
            <p className="text-xs text-gray-500 mt-0.5">Detail Stats RDV Pris</p>
          </div>
          <div className="flex items-center gap-2">
            <PdfExportButton
              targetRef={contentRef}
              filename={`detail-rdv-${mode}-${title.toLowerCase().replace(/\s+/g, '-')}`}
              title={`${title} - Detail Stats RDV Pris`}
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
          {/* KPI */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <KpiCard
              icon={<FileText className="w-5 h-5" />}
              label="RDV"
              value={nbRdv}
              color="text-gray-900"
            />
            <KpiCard
              icon={<UserCheck className="w-5 h-5" />}
              label="Presents"
              value={nbPresents}
              sub={pct(nbPresents, nbRdv)}
              color="text-teal-600"
            />
            <KpiCard
              icon={<CheckCheck className="w-5 h-5" />}
              label="Retenus"
              value={nbRetenus}
              sub={pct(nbRetenus, nbPresents)}
              color="text-emerald-600"
            />
            <KpiCard
              icon={<GraduationCap className="w-5 h-5" />}
              label="Venu en JO"
              value={nbJO}
              sub={pct(nbJO, nbRetenus)}
              color="text-amber-600"
            />
          </div>

          {/* Sources (avec sous-niveau annonceur/coopteur) */}
          {sources.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase tracking-wide flex items-center justify-between">
                <span>Sources des CV</span>
                {showPerParty && (
                  <span className="text-[10px] normal-case text-gray-400 font-normal">
                    Clique une source pour voir le detail
                  </span>
                )}
              </div>
              <div className="p-4 space-y-3">
                {sources.map((g) => {
                  const pctGroup = nbRdv > 0 ? (g.total / nbRdv) * 100 : 0
                  const isExpanded = expandedSource === g.source
                  const canExpand = showPerParty && g.total > 0
                  return (
                    <div key={g.source}>
                      <button
                        type="button"
                        onClick={() => canExpand && setExpandedSource(isExpanded ? null : g.source)}
                        disabled={!canExpand}
                        className={`w-full text-left ${canExpand ? 'cursor-pointer hover:bg-gray-50 rounded-md px-2 -mx-2 py-1' : 'cursor-default'}`}
                      >
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="flex items-center gap-1 font-semibold text-gray-900">
                            {canExpand && (
                              isExpanded ? (
                                <ChevronDown className="w-3 h-3 text-gray-400" />
                              ) : (
                                <ChevronRight className="w-3 h-3 text-gray-400" />
                              )
                            )}
                            {g.source}
                          </span>
                          <span className="tabular-nums text-gray-500">
                            <span className="font-semibold text-gray-900">{g.total}</span>
                            <span className="ml-1.5 text-gray-400">({pctGroup.toFixed(1)} %)</span>
                          </span>
                        </div>
                        <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-500 transition-all"
                            style={{ width: `${pctGroup}%` }}
                          />
                        </div>
                      </button>

                      {/* Sous-niveau annonceur/coopteur */}
                      {g.sub.length > 0 && (
                        <AnimatePresence initial={false}>
                          {isExpanded && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: 'auto' }}
                              exit={{ opacity: 0, height: 0 }}
                              transition={{ duration: 0.15 }}
                              className="overflow-hidden"
                            >
                              <div className="pl-6 pt-2 pb-1 space-y-1">
                                {g.sub.map((s) => {
                                  const pctSub = g.total > 0 ? (s.nb / g.total) * 100 : 0
                                  return (
                                    <div key={s.nom}>
                                      <div className="flex items-center justify-between text-[11px] mb-0.5">
                                        <span className="text-gray-600 truncate">{s.nom}</span>
                                        <span className="tabular-nums text-gray-500 shrink-0 ml-2">
                                          {s.nb}
                                          <span className="text-gray-400 ml-1">
                                            ({pctSub.toFixed(0)} %)
                                          </span>
                                        </span>
                                      </div>
                                      <div className="w-full h-1 bg-gray-100 rounded-full overflow-hidden">
                                        <div
                                          className="h-full bg-blue-300 transition-all"
                                          style={{ width: `${pctSub}%` }}
                                        />
                                      </div>
                                    </div>
                                  )
                                })}
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Statuts RDV (bars horizontal) */}
          {statuts.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase tracking-wide">
                Statut des RDV Pris
              </div>
              <div className="p-4 space-y-1.5">
                {statuts.map((s) => {
                  const p = maxStatut > 0 ? (s.nb / maxStatut) * 100 : 0
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
                          style={{ width: `${p}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {nbRdv === 0 && (
            <div className="text-center py-10 text-gray-400 text-sm italic">
              Pas de RDV pour ce scope.
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  )
}

function KpiCard({
  icon,
  label,
  value,
  sub,
  color,
}: {
  icon: React.ReactNode
  label: string
  value: number
  sub?: string
  color: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 px-3 py-2.5">
      <div className="flex items-center gap-1.5 text-gray-400">
        {icon}
        <div className="text-[10px] uppercase tracking-wide font-medium">{label}</div>
      </div>
      <div className={`text-xl font-bold tabular-nums mt-0.5 ${color}`}>{value}</div>
      {sub && <div className="text-[10px] text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}
