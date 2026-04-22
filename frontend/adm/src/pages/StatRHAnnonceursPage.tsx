import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  ChevronLeft,
  Calendar as CalendarIcon,
  Play,
  Loader2,
  AlertCircle,
  Eye,
  RotateCw,
  Check,
  Megaphone,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import { getToken } from '@/api'
import ExportButton from '@/components/ExportButton'
import PdfExportButton from '@/components/PdfExportButton'
import { exportToCSV, csvDate } from '@/utils/csvExport'

type TabKey = 'resume' | 'saisis'

interface AnnonceurItem {
  id_annonceur: string
  lib_annonceur: string
}

interface CvSaisiAnnonceurRow {
  id_cvtheque: string
  id_annonceur: string
  lib_annonceur: string
  ope_id: string
  ope_nom: string
  date_traitement: string
  est_reactivation: boolean
  nom_prenom: string
  commune: string
  tel: string
  statut_actuel: string
  id_statut_actuel: number
  statut_rdv: string
  fiche_reac: boolean
  dpae: boolean
  cv_traite: boolean
  has_rdv: boolean
  is_present: boolean
  is_retenu: boolean
}

interface AnnonceurResumeRow {
  id_annonceur: string
  lib_annonceur: string
  nb_cv_saisis: number
  nb_cv_traites: number
  nb_rdv: number
  nb_presents: number
  nb_retenus: number
  nb_jo: number
}

interface StatAnnonceursResponse {
  saisis: CvSaisiAnnonceurRow[]
  resume: AnnonceurResumeRow[]
}

function toYmd(d: Date): string {
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
}

function pct(n: number, d: number): string {
  return d > 0 ? `${((n / d) * 100).toFixed(1)} %` : '0.0 %'
}

export default function StatRHAnnonceursPage() {
  const navigate = useNavigate()

  const today = toYmd(new Date())
  const [dateDu, setDateDu] = useState<string>(today)
  const [dateAu, setDateAu] = useState<string>(today)
  const [idAnnonceur, setIdAnnonceur] = useState<string>('')  // '' = tous
  const [tab, setTab] = useState<TabKey>('resume')

  const [annonceurs, setAnnonceurs] = useState<AnnonceurItem[]>([])
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<StatAnnonceursResponse | null>(null)
  const [error, setError] = useState<string>('')
  const [detail, setDetail] = useState<{
    annonceur: AnnonceurResumeRow
    saisis: CvSaisiAnnonceurRow[]
  } | null>(null)

  // Charger liste annonceurs au mount
  useEffect(() => {
    fetch('/api/adm/annonceurs/list', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((list: AnnonceurItem[]) => setAnnonceurs(list || []))
      .catch(() => setAnnonceurs([]))
  }, [])

  const runCalcul = () => {
    setError('')
    setLoading(true)
    const params = new URLSearchParams({
      date_du: dateDu,
      date_au: dateAu,
    })
    if (idAnnonceur) params.set('id_annonceur', idAnnonceur)
    fetch(`/api/adm/stat-rh/annonceurs?${params.toString()}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => {
        if (!r.ok) throw new Error(`Erreur API (${r.status})`)
        return r.json()
      })
      .then((res: StatAnnonceursResponse) => setData(res))
      .catch((e) => setError(e.message || 'Erreur'))
      .finally(() => setLoading(false))
  }

  return (
    <div className="p-8">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <button
          onClick={() => navigate('/stat-rh')}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 mb-3"
        >
          <ChevronLeft className="w-4 h-4" />
          Retour Stats RH
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Stats RH Annonceurs</h1>
        <p className="text-gray-500 mt-1">
          Performance des annonceurs : CV saisis, RDV, presents, retenus, JO.
        </p>
      </motion.div>

      {/* Filtres */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mt-6 flex flex-wrap items-center gap-3">
        <DateField label="Du" value={dateDu} onChange={setDateDu} />
        <DateField label="Au" value={dateAu} onChange={setDateAu} />

        <div className="h-6 w-px bg-gray-200" />

        <label className="flex items-center gap-2 px-3 py-1.5 border border-gray-200 rounded-lg text-sm">
          <Megaphone className="w-4 h-4 text-gray-400" />
          <span className="text-gray-500">Annonceur</span>
          <select
            value={idAnnonceur}
            onChange={(e) => setIdAnnonceur(e.target.value)}
            className="outline-none bg-transparent font-medium text-gray-900 max-w-[200px]"
          >
            <option value="">--- Tous ---</option>
            {annonceurs.map((a) => (
              <option key={a.id_annonceur} value={a.id_annonceur}>
                {a.lib_annonceur}
              </option>
            ))}
          </select>
        </label>

        <div className="flex-1" />

        <button
          onClick={runCalcul}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50 shadow-sm"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          Demarrer le calcul
        </button>
      </div>

      {error && (
        <div className="mt-3 flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 px-4 py-2.5 rounded-lg text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Onglets */}
      <div className="mt-4 border-b border-gray-200 flex gap-1">
        <TabButton active={tab === 'resume'} onClick={() => setTab('resume')} label="Resume" />
        <TabButton
          active={tab === 'saisis'}
          onClick={() => setTab('saisis')}
          label={`CV Saisis${data ? ` (${data.saisis.length})` : ''}`}
        />
      </div>

      {/* Contenu */}
      <div className="mt-4">
        <AnimatePresence mode="wait">
          {tab === 'resume' && (
            <motion.div key="resume" initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }}>
              <ResumeTable
                rows={data?.resume || []}
                loading={loading}
                onDetail={(ann) => {
                  const saisis = (data?.saisis || []).filter(
                    (s) => s.id_annonceur === ann.id_annonceur
                  )
                  setDetail({ annonceur: ann, saisis })
                }}
                onDetailTotal={(totalRow) => {
                  setDetail({
                    annonceur: totalRow,
                    saisis: data?.saisis || [],
                  })
                }}
              />
            </motion.div>
          )}
          {tab === 'saisis' && (
            <motion.div key="saisis" initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }}>
              <SaisisTable rows={data?.saisis || []} loading={loading} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {detail && (
          <AnnonceurDetailModal
            annonceur={detail.annonceur}
            saisis={detail.saisis}
            onClose={() => setDetail(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

// --- Sous-composants ------------------------------------------------------

function DateField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  const inputValue =
    value.length === 8
      ? `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`
      : value
  return (
    <label className="flex items-center gap-2 px-3 py-1.5 border border-gray-200 rounded-lg text-sm">
      <CalendarIcon className="w-4 h-4 text-gray-400" />
      <span className="text-gray-500">{label}</span>
      <input
        type="date"
        value={inputValue}
        onChange={(e) => onChange(e.target.value.replace(/-/g, ''))}
        className="outline-none bg-transparent font-medium text-gray-900 w-32"
      />
    </label>
  )
}

function TabButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
        active
          ? 'border-gray-900 text-gray-900'
          : 'border-transparent text-gray-500 hover:text-gray-700'
      }`}
    >
      {label}
    </button>
  )
}

function ResumeTable({
  rows,
  loading,
  onDetail,
  onDetailTotal,
}: {
  rows: AnnonceurResumeRow[]
  loading: boolean
  onDetail: (r: AnnonceurResumeRow) => void
  onDetailTotal: (totalRow: AnnonceurResumeRow) => void
}) {
  if (loading) return <TableLoader />
  if (rows.length === 0) return <EmptyState label="Pas de donnees. Demarre le calcul." />

  const total = rows.reduce(
    (acc, r) => ({
      saisis: acc.saisis + r.nb_cv_saisis,
      traites: acc.traites + r.nb_cv_traites,
      rdv: acc.rdv + r.nb_rdv,
      pres: acc.pres + r.nb_presents,
      ret: acc.ret + r.nb_retenus,
      jo: acc.jo + r.nb_jo,
    }),
    { saisis: 0, traites: 0, rdv: 0, pres: 0, ret: 0, jo: 0 }
  )

  const handleExport = () => {
    exportToCSV(
      'stats-annonceurs-resume',
      [
        'Annonceur',
        'CV Saisis',
        'CV Traites',
        '% Traites',
        'RDV',
        '% RDV',
        'Presents',
        '% Pres',
        'Retenus',
        '% Ret',
        'JO',
        '% JO',
      ],
      [
        ...rows.map((r) => [
          r.lib_annonceur,
          r.nb_cv_saisis,
          r.nb_cv_traites,
          pct(r.nb_cv_traites, r.nb_cv_saisis),
          r.nb_rdv,
          pct(r.nb_rdv, r.nb_cv_traites),
          r.nb_presents,
          pct(r.nb_presents, r.nb_rdv),
          r.nb_retenus,
          pct(r.nb_retenus, r.nb_presents),
          r.nb_jo,
          pct(r.nb_jo, r.nb_retenus),
        ]),
        [
          'TOTAL',
          total.saisis,
          total.traites,
          pct(total.traites, total.saisis),
          total.rdv,
          pct(total.rdv, total.traites),
          total.pres,
          pct(total.pres, total.rdv),
          total.ret,
          pct(total.ret, total.pres),
          total.jo,
          pct(total.jo, total.ret),
        ],
      ]
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-end">
        <ExportButton onClick={handleExport} />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Annonceur</th>
              <th className="text-right py-2 px-3 text-xs font-medium text-gray-500 uppercase">CV Saisis</th>
              <th className="text-right py-2 px-3 text-xs font-medium text-gray-500 uppercase">CV Traites</th>
              <th className="text-right py-2 px-3 text-xs font-medium text-gray-500 uppercase">RDV</th>
              <th className="text-right py-2 px-3 text-xs font-medium text-gray-500 uppercase">Presents</th>
              <th className="text-right py-2 px-3 text-xs font-medium text-gray-500 uppercase">Retenus</th>
              <th className="text-right py-2 px-3 text-xs font-medium text-gray-500 uppercase">JO</th>
              <th className="w-12 py-2 px-2 text-xs font-medium text-gray-500 uppercase text-center">Detail</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id_annonceur} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                <td className="py-2 px-3 font-medium text-gray-900 whitespace-nowrap">{r.lib_annonceur}</td>
                <td className="py-2 px-3 text-right tabular-nums">{r.nb_cv_saisis}</td>
                <td className="py-2 px-3 text-right tabular-nums">
                  {r.nb_cv_traites}
                  <span className="text-gray-400 ml-1 text-xs">({pct(r.nb_cv_traites, r.nb_cv_saisis)})</span>
                </td>
                <td className="py-2 px-3 text-right tabular-nums">
                  {r.nb_rdv}
                  <span className="text-gray-400 ml-1 text-xs">({pct(r.nb_rdv, r.nb_cv_traites)})</span>
                </td>
                <td className="py-2 px-3 text-right tabular-nums">
                  {r.nb_presents}
                  <span className="text-gray-400 ml-1 text-xs">({pct(r.nb_presents, r.nb_rdv)})</span>
                </td>
                <td className="py-2 px-3 text-right tabular-nums">
                  {r.nb_retenus}
                  <span className="text-gray-400 ml-1 text-xs">({pct(r.nb_retenus, r.nb_presents)})</span>
                </td>
                <td className="py-2 px-3 text-right tabular-nums">
                  {r.nb_jo}
                  <span className="text-gray-400 ml-1 text-xs">({pct(r.nb_jo, r.nb_retenus)})</span>
                </td>
                <td className="py-1 px-2 text-center">
                  <button
                    onClick={() => onDetail(r)}
                    title={`Detail ${r.lib_annonceur}`}
                    className="p-1.5 rounded-md text-gray-400 hover:text-gray-900 hover:bg-white border border-transparent hover:border-gray-200"
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            ))}
            <tr className="bg-gray-50 font-semibold border-t-2 border-gray-300">
              <td className="py-2 px-3 text-gray-900">TOTAL</td>
              <td className="py-2 px-3 text-right tabular-nums">{total.saisis}</td>
              <td className="py-2 px-3 text-right tabular-nums">
                {total.traites}
                <span className="text-gray-400 ml-1 text-xs">({pct(total.traites, total.saisis)})</span>
              </td>
              <td className="py-2 px-3 text-right tabular-nums">
                {total.rdv}
                <span className="text-gray-400 ml-1 text-xs">({pct(total.rdv, total.traites)})</span>
              </td>
              <td className="py-2 px-3 text-right tabular-nums">
                {total.pres}
                <span className="text-gray-400 ml-1 text-xs">({pct(total.pres, total.rdv)})</span>
              </td>
              <td className="py-2 px-3 text-right tabular-nums">
                {total.ret}
                <span className="text-gray-400 ml-1 text-xs">({pct(total.ret, total.pres)})</span>
              </td>
              <td className="py-2 px-3 text-right tabular-nums">
                {total.jo}
                <span className="text-gray-400 ml-1 text-xs">({pct(total.jo, total.ret)})</span>
              </td>
              <td className="py-1 px-2 text-center">
                <button
                  onClick={() =>
                    onDetailTotal({
                      id_annonceur: '',
                      lib_annonceur: 'TOTAL',
                      nb_cv_saisis: total.saisis,
                      nb_cv_traites: total.traites,
                      nb_rdv: total.rdv,
                      nb_presents: total.pres,
                      nb_retenus: total.ret,
                      nb_jo: total.jo,
                    })
                  }
                  title="Detail Total"
                  className="p-1.5 rounded-md text-gray-400 hover:text-gray-900 hover:bg-white border border-transparent hover:border-gray-200"
                >
                  <Eye className="w-3.5 h-3.5" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SaisisTable({ rows, loading }: { rows: CvSaisiAnnonceurRow[]; loading: boolean }) {
  if (loading) return <TableLoader />
  if (rows.length === 0) return <EmptyState label="Pas de CV saisi sur cette periode." />

  const handleExport = () => {
    exportToCSV(
      'stats-annonceurs-saisis',
      [
        'Ope saisie',
        'Date saisie',
        'Reactivation',
        'Candidat',
        'Commune',
        'Tel',
        'Statut actuel',
        'Annonceur',
        'DPAE',
        'Fiche reac',
      ],
      rows.map((r) => [
        r.ope_nom,
        csvDate(r.date_traitement),
        r.est_reactivation,
        r.nom_prenom,
        r.commune,
        r.tel,
        r.statut_actuel,
        r.lib_annonceur,
        r.dpae,
        r.fiche_reac,
      ])
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-end">
        <ExportButton onClick={handleExport} />
      </div>
      <div className="overflow-x-auto max-h-[calc(100vh-400px)] overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200 sticky top-0">
            <tr>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase whitespace-nowrap min-w-[160px]">
                Ope saisie
              </th>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase whitespace-nowrap">
                Date
              </th>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Candidat</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Commune</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Tel</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Statut actuel</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Annonceur</th>
              <th className="text-center py-2 px-3 text-xs font-medium text-gray-500 uppercase">DPAE</th>
              <th className="text-center py-2 px-3 text-xs font-medium text-gray-500 uppercase">Fiche Reac</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={`${r.id_cvtheque}-${i}`} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                <td className="py-2 px-3 text-gray-600 whitespace-nowrap">{r.ope_nom}</td>
                <td className="py-2 px-3 text-gray-600 whitespace-nowrap">
                  {csvDate(r.date_traitement)}
                  {r.est_reactivation && (
                    <RotateCw className="inline w-3 h-3 ml-1 text-amber-500" aria-label="Reactivation" />
                  )}
                </td>
                <td className="py-2 px-3 font-medium text-gray-900 truncate max-w-xs">{r.nom_prenom}</td>
                <td className="py-2 px-3 text-gray-600 truncate max-w-xs">{r.commune}</td>
                <td className="py-2 px-3 text-gray-600">{r.tel}</td>
                <td className="py-2 px-3 text-gray-600">{r.statut_actuel || '—'}</td>
                <td className="py-2 px-3 text-gray-600 whitespace-nowrap">{r.lib_annonceur}</td>
                <td className="py-2 px-3 text-center">
                  {r.dpae ? <Check className="inline w-4 h-4 text-emerald-600" /> : '—'}
                </td>
                <td className="py-2 px-3 text-center">
                  {r.fiche_reac ? <Check className="inline w-4 h-4 text-blue-600" /> : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function AnnonceurDetailModal({
  annonceur,
  saisis,
  onClose,
}: {
  annonceur: AnnonceurResumeRow
  saisis: CvSaisiAnnonceurRow[]
  onClose: () => void
}) {
  // Funnel (summary) + accessor pour determiner si chaque CV compte dans une etape
  type StepKey = 'saisis' | 'traites' | 'rdv' | 'presents' | 'retenus' | 'jo'
  const stepMatch: Record<StepKey, (r: CvSaisiAnnonceurRow) => boolean> = {
    saisis: () => true,
    traites: (r) => r.cv_traite,
    rdv: (r) => r.has_rdv,
    presents: (r) => r.is_present,
    retenus: (r) => r.is_retenu,
    jo: (r) => r.dpae,
  }
  const steps: {
    key: StepKey
    label: string
    value: number
    base: number
    color: string
  }[] = [
    { key: 'saisis', label: 'CV Saisis', value: annonceur.nb_cv_saisis, base: annonceur.nb_cv_saisis, color: 'bg-gray-900' },
    { key: 'traites', label: 'CV Traites', value: annonceur.nb_cv_traites, base: annonceur.nb_cv_saisis, color: 'bg-indigo-500' },
    { key: 'rdv', label: 'RDV', value: annonceur.nb_rdv, base: annonceur.nb_cv_traites, color: 'bg-blue-500' },
    { key: 'presents', label: 'Presents', value: annonceur.nb_presents, base: annonceur.nb_rdv, color: 'bg-teal-500' },
    { key: 'retenus', label: 'Retenus', value: annonceur.nb_retenus, base: annonceur.nb_presents, color: 'bg-emerald-500' },
    { key: 'jo', label: 'JO', value: annonceur.nb_jo, base: annonceur.nb_retenus, color: 'bg-amber-500' },
  ]

  const [expandedStep, setExpandedStep] = useState<StepKey | null>(null)
  const [expandedStatut, setExpandedStatut] = useState<string | null>(null)
  const contentRef = useRef<HTMLDivElement>(null)

  // Breakdown par annonceur (utile surtout pour le TOTAL)
  const annonceurMap = new Map<string, number>()
  for (const r of saisis) {
    const lib = r.lib_annonceur || 'Non renseigne'
    annonceurMap.set(lib, (annonceurMap.get(lib) || 0) + 1)
  }
  const breakdownAnnonceurs = [...annonceurMap.entries()]
    .map(([lib, nb]) => ({ lib, nb }))
    .sort((a, b) => b.nb - a.nb)
  const showAnnonceurBreakdown = breakdownAnnonceurs.length > 1

  // Breakdown des statuts : logique WinDev
  // - IdStatut >= 100 : "Entretien planifie" (groupe parent) + Statut_actuel (sub)
  // - Sinon : Statut_actuel au niveau racine
  const groups = new Map<string, { total: number; sub: Map<string, number> }>()
  const ensureGroup = (label: string) => {
    if (!groups.has(label)) groups.set(label, { total: 0, sub: new Map() })
    return groups.get(label)!
  }

  for (const r of saisis) {
    const lib = r.statut_actuel || 'Non renseigne'
    if (r.id_statut_actuel >= 100) {
      const g = ensureGroup('Entretien planifie')
      g.total += 1
      g.sub.set(lib, (g.sub.get(lib) || 0) + 1)
    } else {
      const g = ensureGroup(lib)
      g.total += 1
    }
  }

  const breakdown = [...groups.entries()]
    .map(([label, v]) => ({
      label,
      total: v.total,
      sub: [...v.sub.entries()]
        .map(([lib, nb]) => ({ lib, nb }))
        .sort((a, b) => b.nb - a.nb),
    }))
    .sort((a, b) => b.total - a.total)

  const totalSaisis = saisis.length

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
            <h2 className="text-lg font-bold text-gray-900">{annonceur.lib_annonceur}</h2>
            <p className="text-xs text-gray-500 mt-0.5">Funnel + repartition des statuts</p>
          </div>
          <div className="flex items-center gap-2">
            <PdfExportButton
              targetRef={contentRef}
              filename={`detail-annonceur-${annonceur.lib_annonceur.toLowerCase().replace(/\s+/g, '-')}`}
              title={`${annonceur.lib_annonceur} - Detail Annonceur`}
            />
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div ref={contentRef} className="p-6 space-y-6">
          {/* Funnel cliquable */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase tracking-wide flex items-center justify-between">
              <span>Funnel de conversion</span>
              {showAnnonceurBreakdown && (
                <span className="text-[10px] normal-case text-gray-400 font-normal">
                  Clique une etape pour voir par annonceur
                </span>
              )}
            </div>
            <div className="p-4 space-y-2">
              {steps.map((s, i) => {
                const p = s.base > 0 ? (s.value / s.base) * 100 : i === 0 ? 100 : 0
                const isExpanded = expandedStep === s.key
                const canExpand = showAnnonceurBreakdown && s.value > 0

                // Breakdown par annonceur pour l'etape courante
                const perAnn = canExpand && isExpanded
                  ? (() => {
                      const map = new Map<string, number>()
                      for (const r of saisis) {
                        if (!stepMatch[s.key](r)) continue
                        const lib = r.lib_annonceur || 'Non renseigne'
                        map.set(lib, (map.get(lib) || 0) + 1)
                      }
                      return [...map.entries()]
                        .map(([lib, nb]) => ({ lib, nb }))
                        .sort((a, b) => b.nb - a.nb)
                    })()
                  : []

                return (
                  <div key={s.label}>
                    <button
                      type="button"
                      onClick={() => canExpand && setExpandedStep(isExpanded ? null : s.key)}
                      disabled={!canExpand}
                      className={`w-full text-left ${canExpand ? 'cursor-pointer hover:bg-gray-50 rounded-md px-2 -mx-2 py-1' : 'cursor-default'}`}
                    >
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="flex items-center gap-1 text-gray-700 font-medium">
                          {canExpand && (
                            isExpanded ? (
                              <ChevronDown className="w-3 h-3 text-gray-400" />
                            ) : (
                              <ChevronRight className="w-3 h-3 text-gray-400" />
                            )
                          )}
                          {s.label}
                        </span>
                        <span className="tabular-nums text-gray-500">
                          <span className="font-semibold text-gray-900">{s.value}</span>
                          {i > 0 && (
                            <span className="ml-1.5 text-gray-400">
                              ({p.toFixed(1)} % vs {steps[i - 1].label})
                            </span>
                          )}
                        </span>
                      </div>
                      <div className="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${s.color} transition-all`}
                          style={{ width: `${Math.min(100, p)}%` }}
                        />
                      </div>
                    </button>

                    {/* Accordion : repartition par annonceur pour cette etape */}
                    <AnimatePresence initial={false}>
                      {isExpanded && perAnn.length > 0 && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          transition={{ duration: 0.15 }}
                          className="overflow-hidden"
                        >
                          <div className="pl-6 pt-2 pb-1 space-y-1">
                            {perAnn.map((a) => {
                              const pa = s.value > 0 ? (a.nb / s.value) * 100 : 0
                              return (
                                <div key={a.lib}>
                                  <div className="flex items-center justify-between text-[11px] mb-0.5">
                                    <span className="text-gray-600 truncate">{a.lib}</span>
                                    <span className="tabular-nums text-gray-500 shrink-0 ml-2">
                                      {a.nb}
                                      <span className="text-gray-400 ml-1">
                                        ({pa.toFixed(1)} %)
                                      </span>
                                    </span>
                                  </div>
                                  <div className="w-full h-1 bg-gray-100 rounded-full overflow-hidden">
                                    <div
                                      className={`h-full ${s.color} opacity-60 transition-all`}
                                      style={{ width: `${pa}%` }}
                                    />
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Repartition par annonceur (seulement quand il y en a plusieurs, ex. TOTAL) */}
          {showAnnonceurBreakdown && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase tracking-wide">
                Repartition par annonceur (CV Saisis)
              </div>
              <div className="p-4 space-y-1.5">
                {breakdownAnnonceurs.map((a) => {
                  const p = totalSaisis > 0 ? (a.nb / totalSaisis) * 100 : 0
                  return (
                    <div key={a.lib}>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-medium text-gray-700">{a.lib}</span>
                        <span className="tabular-nums text-gray-500">
                          <span className="font-semibold text-gray-900">{a.nb}</span>
                          <span className="ml-1.5 text-gray-400">({p.toFixed(1)} %)</span>
                        </span>
                      </div>
                      <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-sky-500 transition-all"
                          style={{ width: `${p}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Breakdown des statuts actuels (cliquable pour breakdown par annonceur) */}
          {breakdown.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase tracking-wide flex items-center justify-between">
                <span>Repartition des statuts actuels</span>
                {showAnnonceurBreakdown && (
                  <span className="text-[10px] normal-case text-gray-400 font-normal">
                    Clique un statut pour voir par annonceur
                  </span>
                )}
              </div>
              <div className="p-4 space-y-2">
                {breakdown.map((g) => {
                  const pctGroup = totalSaisis > 0 ? (g.total / totalSaisis) * 100 : 0
                  const isExpanded = expandedStatut === g.label
                  const canExpand = showAnnonceurBreakdown && g.total > 0

                  // Filtrer les saisis correspondant a ce groupe
                  const matchGroup = (r: CvSaisiAnnonceurRow) => {
                    if (g.label === 'Entretien planifie') {
                      return r.id_statut_actuel >= 100
                    }
                    return r.id_statut_actuel < 100 && (r.statut_actuel || 'Non renseigne') === g.label
                  }

                  const perAnn = canExpand && isExpanded
                    ? (() => {
                        const map = new Map<string, number>()
                        for (const r of saisis) {
                          if (!matchGroup(r)) continue
                          const lib = r.lib_annonceur || 'Non renseigne'
                          map.set(lib, (map.get(lib) || 0) + 1)
                        }
                        return [...map.entries()]
                          .map(([lib, nb]) => ({ lib, nb }))
                          .sort((a, b) => b.nb - a.nb)
                      })()
                    : []

                  return (
                    <div key={g.label}>
                      <button
                        type="button"
                        onClick={() => canExpand && setExpandedStatut(isExpanded ? null : g.label)}
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
                            {g.label}
                          </span>
                          <span className="tabular-nums text-gray-500">
                            <span className="font-semibold text-gray-900">{g.total}</span>
                            <span className="ml-1.5 text-gray-400">
                              ({pctGroup.toFixed(1)} %)
                            </span>
                          </span>
                        </div>
                        <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-violet-400 transition-all"
                            style={{ width: `${pctGroup}%` }}
                          />
                        </div>
                      </button>

                      {/* Sous-statuts (nouvelle ligne pour "Entretien planifie" : Pas Retenu, Absent, etc.) */}
                      {g.sub.length > 0 && !isExpanded && (
                        <div className="pl-4 mt-1.5 space-y-1">
                          {g.sub.map((s) => {
                            const pctSub = g.total > 0 ? (s.nb / g.total) * 100 : 0
                            return (
                              <div key={s.lib}>
                                <div className="flex items-center justify-between text-[11px] mb-0.5">
                                  <span className="text-gray-600 truncate">{s.lib}</span>
                                  <span className="tabular-nums text-gray-500 shrink-0 ml-2">
                                    {s.nb}
                                    <span className="text-gray-400 ml-1">
                                      ({pctSub.toFixed(0)} %)
                                    </span>
                                  </span>
                                </div>
                                <div className="w-full h-1 bg-gray-100 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-violet-300 transition-all"
                                    style={{ width: `${pctSub}%` }}
                                  />
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      )}

                      {/* Accordion : repartition par annonceur pour ce statut */}
                      <AnimatePresence initial={false}>
                        {isExpanded && perAnn.length > 0 && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.15 }}
                            className="overflow-hidden"
                          >
                            <div className="pl-6 pt-2 pb-1 space-y-1">
                              {perAnn.map((a) => {
                                const pa = g.total > 0 ? (a.nb / g.total) * 100 : 0
                                return (
                                  <div key={a.lib}>
                                    <div className="flex items-center justify-between text-[11px] mb-0.5">
                                      <span className="text-gray-600 truncate">{a.lib}</span>
                                      <span className="tabular-nums text-gray-500 shrink-0 ml-2">
                                        {a.nb}
                                        <span className="text-gray-400 ml-1">
                                          ({pa.toFixed(1)} %)
                                        </span>
                                      </span>
                                    </div>
                                    <div className="w-full h-1 bg-gray-100 rounded-full overflow-hidden">
                                      <div
                                        className="h-full bg-violet-400 opacity-70 transition-all"
                                        style={{ width: `${pa}%` }}
                                      />
                                    </div>
                                  </div>
                                )
                              })}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  )
}

function TableLoader() {
  return (
    <div className="flex items-center justify-center py-20 bg-white rounded-xl border border-gray-200">
      <Loader2 className="w-6 h-6 text-gray-300 animate-spin" />
    </div>
  )
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="text-center py-20 text-gray-400 text-sm italic bg-white rounded-xl border border-gray-200">
      {label}
    </div>
  )
}
