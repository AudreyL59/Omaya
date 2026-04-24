import { useState, useMemo, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Building2,
  Users,
  ChevronDown,
  ChevronRight,
  Search,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Phone,
  Mail,
  Crown,
  Network,
  X,
  Sparkles,
  Loader2,
  UserX,
  Pause,
  Car,
  GraduationCap,
  Scale,
  HeartPulse,
  IdCard,
  CalendarCheck,
  TrendingUp,
  LineChart,
  FileText,
  ClipboardList,
  FileSignature,
} from 'lucide-react'
import { getToken } from '@/api'
import { useAuth } from '@/hooks/useAuth'
import FicheSalarieModal from '@/components/FicheSalarieModal'

// --- Types ---------------------------------------------------------------

interface Salarie {
  id_salarie: string
  nom: string
  prenom: string
  poste: string
  categorie?: string
  is_resp?: boolean
  is_resp_adjoint?: boolean
  gsm?: string
  mail?: string
  date_debut?: string
  anciennete_jours?: number
  date_dernier_ctt?: string
  cj_envoye?: boolean
  formation_iag?: boolean
  en_pause?: boolean
  chauffeur?: boolean
  mutuelle_adhesion?: boolean
  mutuelle_id?: number
  mutuelle_lib?: string
  mutuelle_fin_date?: string
  absent?: boolean
  absence_type_id?: number
  absence_lib?: string
  absence_date_debut?: string
  absence_date_fin?: string
}

interface OrgaNode {
  id: string
  lib: string
  lib_niveau: string
  id_type_niveau: number
  salaries: Salarie[]
  children: OrgaNode[]
}


// Styles par profondeur : la profondeur 0 = racine (Société), 1 = Région, etc.
// Label = lib_niveau venant de la DB ; on ne fait que styler par niveau.
interface NiveauStyle {
  icon: React.ReactNode
  headerBg: string
  headerText: string
  width: string
}

const NIVEAU_STYLES: NiveauStyle[] = [
  {
    icon: <Sparkles className="w-3.5 h-3.5" />,
    headerBg: 'bg-gradient-to-r from-gray-900 to-gray-700',
    headerText: 'text-white',
    width: 'w-80',
  },
  {
    icon: <Network className="w-3.5 h-3.5" />,
    headerBg: 'bg-gradient-to-r from-indigo-600 to-blue-600',
    headerText: 'text-white',
    width: 'w-72',
  },
  {
    icon: <Building2 className="w-3.5 h-3.5" />,
    headerBg: 'bg-gradient-to-r from-emerald-500 to-teal-500',
    headerText: 'text-white',
    width: 'w-72',
  },
  {
    icon: <Users className="w-3.5 h-3.5" />,
    headerBg: 'bg-gradient-to-r from-amber-500 to-orange-500',
    headerText: 'text-white',
    width: 'w-64',
  },
  {
    icon: <Users className="w-3.5 h-3.5" />,
    headerBg: 'bg-gradient-to-r from-slate-500 to-gray-500',
    headerText: 'text-white',
    width: 'w-64',
  },
]

function styleForDepth(depth: number): NiveauStyle {
  return NIVEAU_STYLES[Math.min(depth, NIVEAU_STYLES.length - 1)]
}

function libFontSize(lib: string): string {
  const n = (lib || '').length
  if (n <= 18) return 'text-base'
  if (n <= 26) return 'text-sm'
  if (n <= 36) return 'text-xs'
  return 'text-[11px]'
}

function initials(nom: string, prenom: string): string {
  return ((nom[0] || '') + (prenom[0] || '')).toUpperCase()
}

function formatShortDate(raw: string): string {
  if (!raw) return ''
  const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (iso) return `${iso[3]}/${iso[2]}/${iso[1]}`
  if (raw.length >= 8 && /^\d+$/.test(raw.slice(0, 8))) {
    return `${raw.slice(6, 8)}/${raw.slice(4, 6)}/${raw.slice(0, 4)}`
  }
  return raw
}

function colorForName(name: string): string {
  const colors = ['bg-rose-400', 'bg-amber-400', 'bg-emerald-400', 'bg-blue-400', 'bg-violet-400', 'bg-pink-400', 'bg-cyan-400', 'bg-teal-400']
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h + name.charCodeAt(i)) % colors.length
  return colors[h]
}

// --- Page ----------------------------------------------------------------

export default function OrganigrammePage() {
  const { user } = useAuth()
  const droits = user?.droits || []
  const [search, setSearch] = useState('')
  const [zoom, setZoom] = useState(1)
  const [selectedSalarie, setSelectedSalarie] = useState<Salarie | null>(null)
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  const [roots, setRoots] = useState<OrgaNode[]>([])
  const [selectedRootId, setSelectedRootId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/adm/organigramme', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((data) => {
        const list = Array.isArray(data) ? data : []
        setRoots(list)
        if (list.length > 0) setSelectedRootId(list[0].id)

        // Par défaut : ne déplie que les 2 premiers niveaux
        // → on collapse tous les nœuds à depth >= 1 (leurs enfants depth >= 2 sont cachés)
        const collapseSet = new Set<string>()
        const walk = (n: OrgaNode, depth: number) => {
          if (depth >= 1 && n.children.length > 0) collapseSet.add(n.id)
          n.children.forEach((c) => walk(c, depth + 1))
        }
        list.forEach((r) => walk(r, 0))
        setCollapsed(collapseSet)
      })
      .catch(() => setRoots([]))
      .finally(() => setLoading(false))
  }, [])

  const selectedRoot = useMemo(
    () => roots.find((r) => r.id === selectedRootId) || null,
    [roots, selectedRootId]
  )

  // Stats avancées sur la racine sélectionnée
  const stats = useMemo(() => {
    if (!selectedRoot) {
      return {
        total: 0,
        orgas: 0,
        managers: 0,
        dir_agence: 0,
        vendeurs: 0,
        vendeurs_productifs: 0,
        par_categorie: {} as Record<string, number>,
      }
    }
    const all: Salarie[] = []
    const walk = (n: OrgaNode) => {
      for (const s of n.salaries) all.push(s)
      n.children.forEach(walk)
    }
    walk(selectedRoot)

    // Dédup par id_salarie (un salarié peut apparaître dans plusieurs orgas)
    const seen = new Set<string>()
    const uniq: Salarie[] = []
    for (const s of all) {
      if (seen.has(s.id_salarie)) continue
      seen.add(s.id_salarie)
      uniq.push(s)
    }

    const EXCLUDED_CATS = new Set([
      'Autre',
      'STAFF',
      'CALL',
      'CALLRH',
      'FDV MAN',
      'FDV DA',
      'FDV DR',
      '',
    ])
    const par_categorie: Record<string, number> = {}
    let managers = 0
    let dir_agence = 0
    let vendeurs = 0
    let vendeurs_productifs = 0
    for (const s of uniq) {
      const rawCat = s.categorie || ''
      const cat = rawCat === 'FDV VRP' ? 'Vendeur' : rawCat
      if (rawCat === 'FDV MAN' && s.is_resp) managers++
      if (rawCat === 'FDV DA' && s.is_resp) dir_agence++
      if (rawCat === 'FDV VRP') {
        vendeurs++
        if (s.date_dernier_ctt) vendeurs_productifs++
      }
      if (!EXCLUDED_CATS.has(rawCat)) {
        par_categorie[cat] = (par_categorie[cat] || 0) + 1
      }
    }
    const orgas = countStats(selectedRoot).orgas
    return {
      total: uniq.length,
      orgas,
      managers,
      dir_agence,
      vendeurs,
      vendeurs_productifs,
      par_categorie,
    }
  }, [selectedRoot])

  const searchLower = search.trim().toLowerCase()

  const toggleCollapse = (id: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="p-8 h-[calc(100vh-4rem)] flex flex-col">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Organigramme</h1>
            <p className="text-gray-500 mt-1">
              {stats.total} salariés · {stats.orgas} organisations
            </p>
          </div>
        </div>
      </motion.div>

      {/* Toolbar */}
      <div className="bg-white rounded-xl border border-gray-200 p-3 mt-6 flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-64 max-w-md">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Rechercher un salarié ou une orga..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-gray-300"
          />
        </div>

        <div className="h-6 w-px bg-gray-200" />
        <div className="flex items-center gap-1 bg-gray-50 rounded-lg p-1">
          <button
            onClick={() => setZoom((z) => Math.max(0.5, z - 0.1))}
            className="p-1.5 rounded-md hover:bg-white text-gray-600"
            title="Zoom out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <div className="text-xs font-medium text-gray-600 w-12 text-center tabular-nums">
            {Math.round(zoom * 100)}%
          </div>
          <button
            onClick={() => setZoom((z) => Math.min(1.5, z + 0.1))}
            className="p-1.5 rounded-md hover:bg-white text-gray-600"
            title="Zoom in"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom(1)}
            className="p-1.5 rounded-md hover:bg-white text-gray-600"
            title="Reset"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center gap-3 text-xs text-gray-500 ml-auto">
          <LegendItem color="bg-gradient-to-r from-gray-900 to-gray-700" label="Société" />
          <LegendItem color="bg-gradient-to-r from-indigo-600 to-blue-600" label="Région" />
          <LegendItem color="bg-gradient-to-r from-emerald-500 to-teal-500" label="Agence" />
          <LegendItem color="bg-gradient-to-r from-amber-500 to-orange-500" label="Équipe" />
        </div>
      </div>

      {/* Sélecteur de racine (si plus d'une racine) */}
      {roots.length > 1 && (
        <div className="mt-3 flex items-center gap-2 flex-wrap">
          <span className="text-xs text-gray-500 uppercase tracking-wide font-medium">
            Racine :
          </span>
          {roots.map((r) => (
            <button
              key={r.id}
              onClick={() => setSelectedRootId(r.id)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                selectedRootId === r.id
                  ? 'bg-gray-900 text-white shadow-sm'
                  : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
              }`}
            >
              {r.lib}
            </button>
          ))}
        </div>
      )}

      {/* Dashboard stats */}
      {selectedRoot && (
        <div className="mt-3 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <StatCard label="Effectif" value={stats.total} accent="text-gray-900" />
          <StatCard
            label="Dir Agence"
            value={stats.dir_agence}
            accent="text-purple-600"
          />
          <StatCard label="Managers" value={stats.managers} accent="text-amber-600" />
          <StatCard
            label="Vendeur Productif"
            value={stats.vendeurs_productifs}
            accent="text-blue-600"
          />
          {Object.entries(stats.par_categorie)
            .sort(([, a], [, b]) => b - a)
            .map(([cat, n]) => (
              <StatCard
                key={cat}
                label={cat}
                value={n}
                accent="text-emerald-600"
              />
            ))}
        </div>
      )}

      {/* Canvas */}
      <div className="flex-1 bg-gradient-to-br from-slate-50 via-white to-slate-50 rounded-xl border border-gray-200 mt-4 overflow-hidden relative">
        <div className="h-full overflow-auto relative">
          {loading ? (
            <div className="flex items-center justify-center py-24">
              <Loader2 className="w-8 h-8 text-gray-300 animate-spin" />
            </div>
          ) : roots.length === 0 ? (
            <div className="text-center py-24 text-gray-400 text-sm italic">
              Aucune organisation accessible
            </div>
          ) : selectedRoot ? (
            <div
              className="min-w-max min-h-full p-10 flex items-start justify-center"
              style={{ transform: `scale(${zoom})`, transformOrigin: 'top center' }}
            >
              <OrgaTree
                key={selectedRoot.id}
                node={selectedRoot}
                depth={0}
                searchLower={searchLower}
                collapsed={collapsed}
                onToggle={toggleCollapse}
                onSelectSalarie={setSelectedSalarie}
              />
            </div>
          ) : null}
        </div>
      </div>

      <AnimatePresence>
        {selectedSalarie && (
          <SalariePopup
            salarie={selectedSalarie}
            droits={droits}
            onClose={() => setSelectedSalarie(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string
  value: number
  accent: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 px-4 py-2.5">
      <div className={`text-xl font-bold tabular-nums ${accent}`}>{value}</div>
      <div className="text-[10px] text-gray-500 uppercase tracking-wide mt-0.5 truncate">
        {label}
      </div>
    </div>
  )
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className={`w-2 h-2 rounded-full ${color}`} />
      {label}
    </div>
  )
}

// --- Tree (recursive) ----------------------------------------------------

function OrgaTree({
  node,
  depth,
  searchLower,
  collapsed,
  onToggle,
  onSelectSalarie,
}: {
  node: OrgaNode
  depth: number
  searchLower: string
  collapsed: Set<string>
  onToggle: (id: string) => void
  onSelectSalarie: (s: Salarie) => void
}) {
  const isCollapsed = collapsed.has(node.id)
  const hasChildren = node.children.length > 0

  const nodeMatches = searchLower && node.lib.toLowerCase().includes(searchLower)
  const salarieMatches = node.salaries.some((s) =>
    `${s.nom} ${s.prenom}`.toLowerCase().includes(searchLower)
  )
  const highlight = !!searchLower && (nodeMatches || salarieMatches)

  return (
    <div className="flex flex-col items-center">
      <OrgaCard
        node={node}
        depth={depth}
        highlight={highlight}
        searchLower={searchLower}
        collapsed={isCollapsed}
        hasChildren={hasChildren}
        onToggle={() => onToggle(node.id)}
        onSelectSalarie={onSelectSalarie}
      />

      {hasChildren && !isCollapsed && (
        <>
          <div className="w-px h-6 bg-gray-300" />
          <div className="relative flex items-start gap-6">
            {node.children.length > 1 && (
              <div
                className="absolute top-0 h-px bg-gray-300"
                style={{ left: '10%', right: '10%' }}
              />
            )}
            {node.children.map((child) => (
              <div key={child.id} className="flex flex-col items-center">
                <div className="w-px h-6 bg-gray-300" />
                <OrgaTree
                  node={child}
                  depth={depth + 1}
                  searchLower={searchLower}
                  collapsed={collapsed}
                  onToggle={onToggle}
                  onSelectSalarie={onSelectSalarie}
                />
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function OrgaCard({
  node,
  depth,
  highlight,
  searchLower,
  collapsed,
  hasChildren,
  onToggle,
  onSelectSalarie,
}: {
  node: OrgaNode
  depth: number
  highlight: boolean
  searchLower: string
  collapsed: boolean
  hasChildren: boolean
  onToggle: () => void
  onSelectSalarie: (s: Salarie) => void
}) {
  const cfg = styleForDepth(depth)
  const nbTotal = countStats(node).total
  const manager = node.salaries.find((s) => s.is_resp) || null
  const others = node.salaries.filter((s) => s.id_salarie !== manager?.id_salarie)
  const [showAll, setShowAll] = useState(false)
  const INITIAL_LIMIT = 4
  const visible = showAll ? others : others.slice(0, INITIAL_LIMIT)

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={hasChildren ? onToggle : undefined}
      className={`relative bg-white rounded-2xl overflow-hidden ${cfg.width} transition-all ${
        hasChildren ? 'cursor-pointer' : ''
      } ${
        highlight
          ? 'ring-2 ring-offset-2 ring-yellow-400 shadow-xl'
          : 'shadow-md hover:shadow-lg shadow-gray-200/60'
      }`}
    >
      {/* Header gradient */}
      <div className={`${cfg.headerBg} ${cfg.headerText} px-4 py-3 relative`}>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/20 backdrop-blur-sm text-[10px] font-semibold uppercase tracking-wider">
            {cfg.icon}
            {node.lib_niveau || `Niveau ${depth + 1}`}
          </div>
          <div className="flex-1" />
          {hasChildren && (
            <div className="p-1 rounded-md">
              {collapsed ? (
                <ChevronRight className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </div>
          )}
        </div>
        <div
          className={`font-bold mt-1 leading-tight break-words ${libFontSize(node.lib)}`}
          title={node.lib}
        >
          {node.lib}
        </div>
      </div>

      {/* Body */}
      <div className="p-4 space-y-3">
        {/* Manager en vedette */}
        {manager && (
          <SalarieRow
            s={manager}
            searchLower={searchLower}
            onClick={() => onSelectSalarie(manager)}
            featured
          />
        )}

        {/* Compteur + avatar stack */}
        {(others.length > 0 || nbTotal > node.salaries.length) && (
          <div className="flex items-center justify-between">
            <div className="text-[10px] font-medium text-gray-500 uppercase tracking-wide">
              {node.salaries.length} direct
              {nbTotal > node.salaries.length && (
                <span className="text-gray-400"> · {nbTotal} total</span>
              )}
            </div>
            <AvatarStack people={others} max={4} />
          </div>
        )}

        {/* Liste des salariés (hors manager) */}
        {others.length > 0 && (
          <div className="space-y-1 border-t border-gray-100 pt-2">
            {visible.map((s) => (
              <SalarieRow
                key={s.id_salarie}
                s={s}
                searchLower={searchLower}
                onClick={() => onSelectSalarie(s)}
              />
            ))}
            {others.length > INITIAL_LIMIT && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setShowAll((v) => !v)
                }}
                className="w-full text-center text-[10px] font-medium text-gray-500 hover:text-gray-900 hover:bg-gray-50 rounded py-1 mt-1 transition-colors"
              >
                {showAll
                  ? '− Réduire'
                  : `+ Voir les ${others.length - INITIAL_LIMIT} autres`}
              </button>
            )}
          </div>
        )}
      </div>
    </motion.div>
  )
}

function SalarieRow({
  s,
  searchLower,
  onClick,
  featured = false,
}: {
  s: Salarie
  searchLower: string
  onClick: () => void
  featured?: boolean
}) {
  const matches =
    searchLower && `${s.nom} ${s.prenom}`.toLowerCase().includes(searchLower)
  const nonProd = s.categorie === 'FDV VRP' && !s.date_dernier_ctt

  return (
    <button
      onClick={(e) => {
        e.stopPropagation()
        onClick()
      }}
      className={`w-full flex items-center gap-3 p-1.5 rounded-lg text-left transition-all ${
        matches
          ? 'bg-yellow-50 ring-1 ring-yellow-300'
          : featured
            ? 'bg-gradient-to-r from-gray-50 to-transparent hover:from-gray-100'
            : 'hover:bg-gray-50'
      }`}
    >
      <div
        className={`${featured ? 'w-10 h-10 text-xs' : 'w-7 h-7 text-[10px]'} rounded-full flex items-center justify-center font-bold text-white shadow-sm ${colorForName(s.id_salarie)}`}
      >
        {initials(s.nom, s.prenom)}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1 flex-wrap">
          <span
            className={`${featured ? 'text-sm' : 'text-xs'} font-semibold truncate ${
              nonProd ? 'text-red-600' : 'text-gray-900'
            }`}
            title={nonProd ? 'Vendeur non productif' : undefined}
          >
            {s.nom}{' '}
            <span
              className={`font-normal ${nonProd ? 'text-red-500' : 'text-gray-700'}`}
            >
              {s.prenom.charAt(0).toUpperCase() + s.prenom.slice(1).toLowerCase()}
            </span>
          </span>
          {s.is_resp && (
            <Crown
              className="w-3 h-3 text-amber-500 shrink-0"
              aria-label="Responsable"
            />
          )}
          {s.is_resp_adjoint && (
            <span
              className="inline-flex items-center px-1 py-px rounded-full text-[8px] font-bold text-blue-700 bg-blue-100 border border-blue-200"
              title="Responsable adjoint"
            >
              ADJ
            </span>
          )}
        </div>
        <div className={`${featured ? 'text-xs' : 'text-[10px]'} text-gray-500 truncate`}>
          {s.poste || '—'}
        </div>
        {/* Ancienneté / productivité */}
        <div className="text-[10px] text-gray-400 truncate">
          {s.date_dernier_ctt ? (
            <span>Dernier ctt : {formatShortDate(s.date_dernier_ctt)}</span>
          ) : s.anciennete_jours !== undefined && s.anciennete_jours > 0 ? (
            <span>
              {formatShortDate(s.date_debut || '')} · {s.anciennete_jours} j
            </span>
          ) : null}
        </div>
        {/* Badges (pictos) */}
        {(s.cj_envoye ||
          s.formation_iag ||
          s.en_pause ||
          s.chauffeur ||
          s.mutuelle_adhesion ||
          s.absent) && (
          <div className="flex items-center gap-1 mt-1 flex-wrap">
            {s.absent && (
              <MiniBadge
                icon={<UserX className="w-3 h-3" />}
                title={s.absence_lib || 'Absent'}
                color="bg-red-100 text-red-700 border-red-200"
              />
            )}
            {s.en_pause && (
              <MiniBadge
                icon={<Pause className="w-3 h-3" />}
                title="En pause"
                color="bg-orange-100 text-orange-700 border-orange-200"
              />
            )}
            {s.chauffeur && (
              <MiniBadge
                icon={<Car className="w-3 h-3" />}
                title="Chauffeur"
                color="bg-violet-100 text-violet-700 border-violet-200"
              />
            )}
            {s.formation_iag && (
              <MiniBadge
                icon={<GraduationCap className="w-3 h-3" />}
                title="Formation IAG"
                color="bg-teal-100 text-teal-700 border-teal-200"
              />
            )}
            {s.cj_envoye && (
              <MiniBadge
                icon={<Scale className="w-3 h-3" />}
                title="Casier judiciaire envoyé"
                color="bg-emerald-100 text-emerald-700 border-emerald-200"
              />
            )}
            {s.mutuelle_adhesion && (
              <MiniBadge
                icon={<HeartPulse className="w-3 h-3" />}
                title={s.mutuelle_lib || 'Mutuelle'}
                color="bg-sky-100 text-sky-700 border-sky-200"
              />
            )}
          </div>
        )}
      </div>
    </button>
  )
}

function MiniBadge({
  icon,
  title,
  color,
}: {
  icon: React.ReactNode
  title: string
  color: string
}) {
  return (
    <span
      title={title}
      className={`inline-flex items-center justify-center w-5 h-5 rounded border ${color}`}
    >
      {icon}
    </span>
  )
}

function AvatarStack({ people, max }: { people: Salarie[]; max: number }) {
  const shown = people.slice(0, max)
  const extra = people.length - max
  return (
    <div className="flex items-center -space-x-2">
      {shown.map((s) => (
        <div
          key={s.id_salarie}
          className={`w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold text-white border-2 border-white shadow-sm ${colorForName(s.id_salarie)}`}
          title={`${s.nom} ${s.prenom}`}
        >
          {initials(s.nom, s.prenom)}
        </div>
      ))}
      {extra > 0 && (
        <div className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold text-gray-600 bg-gray-100 border-2 border-white shadow-sm">
          +{extra}
        </div>
      )}
    </div>
  )
}

// --- Popup salarié -------------------------------------------------------

function SalariePopup({
  salarie,
  droits,
  onClose,
}: {
  salarie: Salarie
  droits: string[]
  onClose: () => void
}) {
  const has = (d: string) => droits.includes(d)
  const [showFiche, setShowFiche] = useState(false)
  const actions: {
    label: string
    icon: React.ReactNode
    visible: boolean
    onClick?: () => void
  }[] = [
    {
      label: 'Fiche Salarié',
      icon: <IdCard className="w-4 h-4 text-gray-500" />,
      visible: has('FicheVend'),
      onClick: () => setShowFiche(true),
    },
    {
      label: 'Déclaratif de présence',
      icon: <CalendarCheck className="w-4 h-4 text-gray-500" />,
      visible: has('TkSortieRH'),
    },
    {
      label: 'Déclaratif de prod',
      icon: <TrendingUp className="w-4 h-4 text-gray-500" />,
      visible: true,
    },
    {
      label: "Bilan d'évolution",
      icon: <LineChart className="w-4 h-4 text-gray-500" />,
      visible: has('ProgEvo'),
    },
    {
      label: 'ADF',
      icon: <FileText className="w-4 h-4 text-gray-500" />,
      visible: has('ProgEvo'),
    },
    {
      label: 'Feuille de pointe',
      icon: <ClipboardList className="w-4 h-4 text-gray-500" />,
      visible: true,
    },
    {
      label: 'Demander un Ctt W',
      icon: <FileSignature className="w-4 h-4 text-gray-500" />,
      visible: has('Tk_DemCttW'),
    },
  ]
  const visibleActions = actions.filter((a) => a.visible)
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
        className="bg-white rounded-2xl shadow-2xl w-full max-w-sm"
      >
        <div className="flex items-center justify-end px-4 pt-3">
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="px-6 pb-6 text-center">
          <div
            className={`w-20 h-20 mx-auto rounded-full flex items-center justify-center text-xl font-bold text-white ${colorForName(salarie.id_salarie)}`}
          >
            {initials(salarie.nom, salarie.prenom)}
          </div>
          <div className="mt-3 flex items-center justify-center gap-1.5">
            <h2 className="text-lg font-bold text-gray-900">
              {salarie.nom} {salarie.prenom}
            </h2>
            {salarie.is_resp && <Crown className="w-4 h-4 text-amber-500" />}
          </div>
          <p className="text-sm text-gray-500 mt-0.5">{salarie.poste}</p>

          <div className="mt-5 space-y-2 text-left">
            {salarie.gsm && (
              <a
                href={`tel:${salarie.gsm}`}
                className="flex items-center gap-2 px-3 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm text-gray-700"
              >
                <Phone className="w-4 h-4 text-gray-400" />
                {salarie.gsm}
              </a>
            )}
            {salarie.mail && (
              <a
                href={`mailto:${salarie.mail}`}
                className="flex items-center gap-2 px-3 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm text-gray-700"
              >
                <Mail className="w-4 h-4 text-gray-400" />
                {salarie.mail}
              </a>
            )}
          </div>

          {visibleActions.length > 0 && (
            <div className="mt-5 pt-4 border-t border-gray-100 grid grid-cols-2 gap-2">
              {visibleActions.map((a) => (
                <button
                  key={a.label}
                  onClick={a.onClick}
                  className="flex items-center gap-2 px-3 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg text-xs text-gray-700 text-left transition-colors"
                >
                  {a.icon}
                  <span className="truncate">{a.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </motion.div>

      <AnimatePresence>
        {showFiche && (
          <FicheSalarieModal
            idSalarie={salarie.id_salarie}
            nom={salarie.nom}
            prenom={salarie.prenom}
            onClose={() => setShowFiche(false)}
          />
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// --- Helpers -------------------------------------------------------------

function countStats(node: OrgaNode): { total: number; orgas: number } {
  let total = node.salaries.length
  let orgas = 1
  for (const c of node.children) {
    const s = countStats(c)
    total += s.total
    orgas += s.orgas
  }
  return { total, orgas }
}
