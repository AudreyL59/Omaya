import { useState, useEffect, useMemo, useRef, type KeyboardEvent } from 'react'
import { motion } from 'framer-motion'
import {
  Loader2,
  Search,
  X,
  ChevronLeft,
  ChevronRight,
  Upload,
  ArrowUpDown,
} from 'lucide-react'
import { getToken } from '@/api'
import ClusterCard, { type ClusterData } from '@/components/ClusterCard'
import SousClustersModal from '@/components/SousClustersModal'

interface GroupementItem {
  id: string
  label: string
}

type SortMode = 'ratio' | 'cluster' | 'equipe'

const MONTHS = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
]

function monthKey(m: number, a: number): number {
  return a * 12 + (m - 1)
}

function MonthPicker({
  value,
  onChange,
  label,
}: {
  value: { m: number; a: number }
  onChange: (v: { m: number; a: number }) => void
  label: string
}) {
  const [open, setOpen] = useState(false)
  const [viewYear, setViewYear] = useState(value.a)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [open])

  return (
    <div className="relative" ref={ref}>
      <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
      <button
        onClick={() => {
          setViewYear(value.a)
          setOpen(!open)
        }}
        className="px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 hover:border-gray-400 transition-colors min-w-[130px] text-left"
      >
        {MONTHS[value.m - 1]} {value.a}
      </button>
      {open && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute top-full left-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 p-3 z-20 w-64"
        >
          <div className="flex items-center justify-between mb-3">
            <button
              onClick={() => setViewYear(viewYear - 1)}
              className="p-1 hover:bg-gray-100 rounded text-gray-500"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-semibold text-sm text-gray-900">{viewYear}</span>
            <button
              onClick={() => setViewYear(viewYear + 1)}
              className="p-1 hover:bg-gray-100 rounded text-gray-500"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
          <div className="grid grid-cols-3 gap-1.5">
            {MONTHS.map((name, idx) => {
              const m = idx + 1
              const selected = value.m === m && value.a === viewYear
              return (
                <button
                  key={m}
                  onClick={() => {
                    onChange({ m, a: viewYear })
                    setOpen(false)
                  }}
                  className={`px-2 py-1.5 text-xs rounded transition-colors ${
                    selected
                      ? 'bg-gray-900 text-white'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {name.slice(0, 3)}
                </button>
              )
            })}
          </div>
        </motion.div>
      )}
    </div>
  )
}

export default function ClustersPage() {
  const now = new Date()
  const [du, setDu] = useState({ m: now.getMonth() + 1, a: now.getFullYear() })
  const [au, setAu] = useState({ m: now.getMonth() + 1, a: now.getFullYear() })
  const [jetons, setJetons] = useState<string[]>([])
  const [input, setInput] = useState('')
  const [groupements, setGroupements] = useState<GroupementItem[]>([])
  const [clusters, setClusters] = useState<ClusterData[]>([])
  const [loading, setLoading] = useState(false)
  const [sortMode, setSortMode] = useState<SortMode>('cluster')
  const [detailCluster, setDetailCluster] = useState<ClusterData | null>(null)

  // Correction si Du > Au
  useEffect(() => {
    if (monthKey(du.m, du.a) > monthKey(au.m, au.a)) {
      setAu(du)
    }
  }, [du, au])

  // Chargement groupements (une fois)
  useEffect(() => {
    fetch('/api/vendeur/clusters/groupements', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d: GroupementItem[]) => setGroupements(Array.isArray(d) ? d : []))
      .catch(() => setGroupements([]))
  }, [])

  // Chargement clusters à chaque changement
  const jetonsKey = useMemo(() => jetons.join('|'), [jetons])

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams({
      mois_du: String(du.m),
      annee_du: String(du.a),
      mois_au: String(au.m),
      annee_au: String(au.a),
    })
    jetons.forEach((j) => params.append('jetons', j))

    fetch(`/api/vendeur/clusters?${params.toString()}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d: ClusterData[]) => setClusters(Array.isArray(d) ? d : []))
      .catch(() => setClusters([]))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [du.m, du.a, au.m, au.a, jetonsKey])

  const addJeton = (value: string) => {
    const v = value.trim()
    if (!v) return
    if (jetons.some((j) => j.toLowerCase() === v.toLowerCase())) return
    setJetons([...jetons, v])
    setInput('')
  }

  const removeJeton = (idx: number) => {
    setJetons(jetons.filter((_, i) => i !== idx))
  }

  const handleInputKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addJeton(input)
    } else if (e.key === 'Backspace' && !input && jetons.length) {
      setJetons(jetons.slice(0, -1))
    }
  }

  const sortedClusters = useMemo(() => {
    const arr = [...clusters]
    if (sortMode === 'ratio') {
      arr.sort((a, b) => b.ratio_reel - a.ratio_reel)
    } else if (sortMode === 'equipe') {
      arr.sort(
        (a, b) =>
          a.exp_lib.localeCompare(b.exp_lib, 'fr') ||
          a.code_vad_full.localeCompare(b.code_vad_full),
      )
    } else {
      arr.sort((a, b) => a.code_vad_full.localeCompare(b.code_vad_full))
    }
    return arr
  }, [clusters, sortMode])

  return (
    <div className="p-8">
      {/* En-tête */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between gap-4 flex-wrap"
      >
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Mes clusters</h1>
          <p className="text-gray-500 mt-1">
            Suivi des objectifs SFR par département
          </p>
        </div>
        <button
          disabled
          className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          title="À venir : import Excel des objectifs"
        >
          <Upload className="w-4 h-4" />
          Éditer les Objectifs
        </button>
      </motion.div>

      {/* Période */}
      <div className="mt-6 flex items-end gap-3 flex-wrap">
        <MonthPicker value={du} onChange={setDu} label="Du" />
        <MonthPicker value={au} onChange={setAu} label="Au" />
        {loading && (
          <Loader2 className="w-5 h-5 text-gray-400 animate-spin ml-2 mb-2" />
        )}
      </div>

      {/* Filtre (chips + input) */}
      <div className="mt-6">
        <label className="block text-xs font-medium text-gray-500 mb-1.5">
          Filtre
        </label>
        <div className="flex items-center flex-wrap gap-1.5 px-3 py-2 bg-white border border-gray-300 rounded-lg focus-within:border-gray-500 transition-colors min-h-[44px]">
          <Search className="w-4 h-4 text-gray-400 shrink-0" />
          {jetons.map((j, i) => (
            <motion.span
              key={j + i}
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.85 }}
              className="inline-flex items-center gap-1 px-2.5 py-1 bg-gray-900 text-white text-xs font-medium rounded-full"
            >
              {j}
              <button
                onClick={() => removeJeton(i)}
                className="p-0.5 hover:bg-white/20 rounded-full"
              >
                <X className="w-3 h-3" />
              </button>
            </motion.span>
          ))}
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleInputKey}
            placeholder={jetons.length ? '' : 'Rechercher (Entrée pour ajouter)…'}
            className="flex-1 min-w-[120px] bg-transparent outline-none text-sm"
          />
        </div>
      </div>

      {/* Barre horizontale groupements */}
      {groupements.length > 0 && (
        <div className="mt-4 overflow-x-auto scrollbar-thin pb-1">
          <div className="flex items-center gap-2 min-w-max">
            {groupements.map((g) => {
              const active = jetons.some(
                (j) => j.toLowerCase() === g.label.toLowerCase(),
              )
              return (
                <button
                  key={g.id}
                  onClick={() => {
                    if (active) {
                      setJetons(
                        jetons.filter(
                          (j) => j.toLowerCase() !== g.label.toLowerCase(),
                        ),
                      )
                    } else {
                      addJeton(g.label)
                    }
                  }}
                  className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                    active
                      ? 'bg-gray-900 text-white'
                      : 'bg-white border border-gray-300 text-gray-700 hover:border-gray-400'
                  }`}
                >
                  {g.label}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Tris */}
      <div className="mt-6 flex items-center gap-2 text-sm">
        <span className="text-gray-500 mr-2 inline-flex items-center gap-1">
          <ArrowUpDown className="w-4 h-4" />
          Trier par :
        </span>
        {([
          ['ratio', 'Ratio'],
          ['cluster', 'Cluster'],
          ['equipe', 'Équipe'],
        ] as const).map(([k, label]) => (
          <button
            key={k}
            onClick={() => setSortMode(k)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              sortMode === k
                ? 'bg-gray-900 text-white'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Grille de cartes */}
      <div className="mt-6">
        {loading && clusters.length === 0 ? (
          <div className="flex items-center justify-center h-48">
            <Loader2 className="w-6 h-6 text-gray-300 animate-spin" />
          </div>
        ) : sortedClusters.length === 0 ? (
          <div className="text-center py-16 text-gray-400 text-sm border border-dashed border-gray-300 rounded-xl">
            Aucun cluster sur cette période avec ces filtres.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {sortedClusters.map((c) => (
              <ClusterCard
                key={c.code_vad_full}
                cluster={c}
                onTeamClick={() => setDetailCluster(c)}
              />
            ))}
          </div>
        )}
      </div>

      <SousClustersModal
        open={!!detailCluster}
        onClose={() => setDetailCluster(null)}
        parent={detailCluster}
        moisDu={du.m}
        anneeDu={du.a}
        moisAu={au.m}
        anneeAu={au.a}
        jetons={jetons}
      />
    </div>
  )
}
