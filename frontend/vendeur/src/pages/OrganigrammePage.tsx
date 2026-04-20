import { useState, useMemo } from 'react'
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
} from 'lucide-react'

// --- Types ---------------------------------------------------------------

interface Salarie {
  id: string
  nom: string
  prenom: string
  poste: string
  photo?: string
  is_resp?: boolean
  gsm?: string
  mail?: string
}

type OrgaType = 'societe' | 'region' | 'agence' | 'equipe'

interface OrgaNode {
  id: string
  lib: string
  type: OrgaType
  salaries: Salarie[]
  children: OrgaNode[]
}

// --- Mock ----------------------------------------------------------------

const S = (nom: string, prenom: string, poste: string, is_resp = false): Salarie => ({
  id: `${nom}-${prenom}`,
  nom: nom.toUpperCase(),
  prenom,
  poste,
  is_resp,
  gsm: '06 12 34 56 78',
  mail: `${prenom.toLowerCase()}.${nom.toLowerCase()}@omaya.fr`,
})

const MOCK_TREE: OrgaNode = {
  id: 'root',
  lib: 'Omaya Groupe',
  type: 'societe',
  salaries: [
    S('LOUDIEUX', 'Audrey', 'Directrice', true),
    S('MARTIN', 'Jean', 'DRH'),
    S('BERNARD', 'Claire', 'DAF'),
  ],
  children: [
    {
      id: 'nord',
      lib: 'Région Nord',
      type: 'region',
      salaries: [
        S('DUPONT', 'Marc', 'Resp Région', true),
        S('LEROY', 'Sophie', 'Assistante'),
      ],
      children: [
        {
          id: 'lille',
          lib: 'Agence Lille',
          type: 'agence',
          salaries: [
            S('PETIT', 'Paul', 'Resp Agence', true),
            S('MOREAU', 'Marie', 'Commerciale'),
          ],
          children: [
            {
              id: 'eq-lille-1',
              lib: 'Équipe Énergie',
              type: 'equipe',
              salaries: [
                S('ROUX', 'Thomas', 'Chef d\'équipe', true),
                S('BLANC', 'Lisa', 'Vendeur'),
                S('NOIR', 'Marc', 'Vendeur'),
                S('VERT', 'Julie', 'Vendeur'),
                S('BLEU', 'Pierre', 'Vendeur'),
                S('JAUNE', 'Emma', 'Vendeur'),
              ],
              children: [],
            },
            {
              id: 'eq-lille-2',
              lib: 'Équipe Fibre',
              type: 'equipe',
              salaries: [
                S('DURAND', 'Luc', 'Chef d\'équipe', true),
                S('LAMBERT', 'Alice', 'Commercial Fibre'),
                S('GIRARD', 'Hugo', 'Commercial Fibre'),
              ],
              children: [],
            },
          ],
        },
        {
          id: 'roubaix',
          lib: 'Agence Roubaix',
          type: 'agence',
          salaries: [
            S('BERNARD', 'Thomas', 'Resp Agence', true),
          ],
          children: [
            {
              id: 'eq-rbx-1',
              lib: 'Équipe Multi-Produits',
              type: 'equipe',
              salaries: [
                S('GARCIA', 'Paul', 'Chef d\'équipe', true),
                S('ROBERT', 'Sophie', 'Vendeur'),
                S('RICHARD', 'Maxime', 'Vendeur'),
              ],
              children: [],
            },
          ],
        },
      ],
    },
    {
      id: 'idf',
      lib: 'Région Île-de-France',
      type: 'region',
      salaries: [
        S('MASSON', 'Julien', 'Resp Région', true),
      ],
      children: [
        {
          id: 'paris',
          lib: 'Agence Paris',
          type: 'agence',
          salaries: [S('FAURE', 'Camille', 'Resp Agence', true)],
          children: [
            {
              id: 'eq-par-1',
              lib: 'Équipe Commerciale',
              type: 'equipe',
              salaries: [
                S('DUBOIS', 'Léo', 'Chef', true),
                S('CHEVALIER', 'Anna', 'Vendeur'),
                S('MOULIN', 'Pierre', 'Vendeur'),
                S('GUERIN', 'Zoé', 'Vendeur'),
              ],
              children: [],
            },
          ],
        },
      ],
    },
  ],
}

const TYPE_CONFIG: Record<
  OrgaType,
  {
    label: string
    icon: React.ReactNode
    // Gradient du bandeau d'en-tête
    headerBg: string
    // Couleur du texte sur le bandeau
    headerText: string
    // Couleur d'accent (ring + barre latérale)
    accent: string
    // Taille de la card
    width: string
  }
> = {
  societe: {
    label: 'Société',
    icon: <Sparkles className="w-3.5 h-3.5" />,
    headerBg: 'bg-gradient-to-r from-gray-900 to-gray-700',
    headerText: 'text-white',
    accent: 'bg-gray-900',
    width: 'w-80',
  },
  region: {
    label: 'Région',
    icon: <Network className="w-3.5 h-3.5" />,
    headerBg: 'bg-gradient-to-r from-indigo-600 to-blue-600',
    headerText: 'text-white',
    accent: 'bg-blue-600',
    width: 'w-72',
  },
  agence: {
    label: 'Agence',
    icon: <Building2 className="w-3.5 h-3.5" />,
    headerBg: 'bg-gradient-to-r from-emerald-500 to-teal-500',
    headerText: 'text-white',
    accent: 'bg-emerald-500',
    width: 'w-72',
  },
  equipe: {
    label: 'Équipe',
    icon: <Users className="w-3.5 h-3.5" />,
    headerBg: 'bg-gradient-to-r from-amber-500 to-orange-500',
    headerText: 'text-white',
    accent: 'bg-amber-500',
    width: 'w-64',
  },
}

function initials(nom: string, prenom: string): string {
  return ((nom[0] || '') + (prenom[0] || '')).toUpperCase()
}

function colorForName(name: string): string {
  const colors = ['bg-rose-400', 'bg-amber-400', 'bg-emerald-400', 'bg-blue-400', 'bg-violet-400', 'bg-pink-400', 'bg-cyan-400', 'bg-teal-400']
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h + name.charCodeAt(i)) % colors.length
  return colors[h]
}

// --- Page ----------------------------------------------------------------

export default function OrganigrammePage() {
  const [search, setSearch] = useState('')
  const [zoom, setZoom] = useState(1)
  const [selectedSalarie, setSelectedSalarie] = useState<Salarie | null>(null)
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())

  // Comptage récursif des salariés
  const stats = useMemo(() => countStats(MOCK_TREE), [])

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

      {/* Canvas */}
      <div className="flex-1 bg-gradient-to-br from-slate-50 via-white to-slate-50 rounded-xl border border-gray-200 mt-4 overflow-hidden relative">
        <div className="h-full overflow-auto relative">
          <div
            className="min-w-max min-h-full p-10 flex items-start justify-center"
            style={{ transform: `scale(${zoom})`, transformOrigin: 'top center' }}
          >
            <OrgaTree
              node={MOCK_TREE}
              searchLower={searchLower}
              collapsed={collapsed}
              onToggle={toggleCollapse}
              onSelectSalarie={setSelectedSalarie}
            />
          </div>
        </div>
      </div>

      <AnimatePresence>
        {selectedSalarie && (
          <SalariePopup
            salarie={selectedSalarie}
            onClose={() => setSelectedSalarie(null)}
          />
        )}
      </AnimatePresence>
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
  searchLower,
  collapsed,
  onToggle,
  onSelectSalarie,
}: {
  node: OrgaNode
  searchLower: string
  collapsed: Set<string>
  onToggle: (id: string) => void
  onSelectSalarie: (s: Salarie) => void
}) {
  const isCollapsed = collapsed.has(node.id)
  const hasChildren = node.children.length > 0

  // Match search : la node match si son lib matche OU un de ses salariés matche
  const nodeMatches = searchLower && node.lib.toLowerCase().includes(searchLower)
  const salarieMatches = node.salaries.some((s) =>
    `${s.nom} ${s.prenom}`.toLowerCase().includes(searchLower)
  )
  const highlight = !!searchLower && (nodeMatches || salarieMatches)

  return (
    <div className="flex flex-col items-center">
      <OrgaCard
        node={node}
        highlight={highlight}
        searchLower={searchLower}
        collapsed={isCollapsed}
        hasChildren={hasChildren}
        onToggle={() => onToggle(node.id)}
        onSelectSalarie={onSelectSalarie}
      />

      {hasChildren && !isCollapsed && (
        <>
          {/* Ligne verticale depuis le parent */}
          <div className="w-px h-6 bg-gray-300" />

          {/* Ligne horizontale sur les enfants */}
          <div className="relative flex items-start gap-6">
            {/* Barre horizontale */}
            {node.children.length > 1 && (
              <div
                className="absolute top-0 h-px bg-gray-300"
                style={{ left: '10%', right: '10%' }}
              />
            )}
            {node.children.map((child) => (
              <div key={child.id} className="flex flex-col items-center">
                {/* Ligne verticale vers l'enfant */}
                <div className="w-px h-6 bg-gray-300" />
                <OrgaTree
                  node={child}
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
  highlight,
  searchLower,
  collapsed,
  hasChildren,
  onToggle,
  onSelectSalarie,
}: {
  node: OrgaNode
  highlight: boolean
  searchLower: string
  collapsed: boolean
  hasChildren: boolean
  onToggle: () => void
  onSelectSalarie: (s: Salarie) => void
}) {
  const cfg = TYPE_CONFIG[node.type]
  const nbTotal = countStats(node).total
  const manager = node.salaries.find((s) => s.is_resp) || null
  const others = node.salaries.filter((s) => s.id !== manager?.id)

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`relative bg-white rounded-2xl overflow-hidden ${cfg.width} transition-all ${
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
            {cfg.label}
          </div>
          <div className="flex-1" />
          {hasChildren && (
            <button
              onClick={onToggle}
              className="p-1 rounded-md hover:bg-white/20 transition-colors"
              title={collapsed ? 'Déplier' : 'Replier'}
            >
              {collapsed ? (
                <ChevronRight className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>
          )}
        </div>
        <div className="font-bold text-base mt-1 truncate">{node.lib}</div>
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
            {others.slice(0, 4).map((s) => (
              <SalarieRow
                key={s.id}
                s={s}
                searchLower={searchLower}
                onClick={() => onSelectSalarie(s)}
              />
            ))}
            {others.length > 4 && (
              <div className="text-center text-[10px] text-gray-400 pt-1">
                + {others.length - 4} autres
              </div>
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

  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 p-1.5 rounded-lg text-left transition-all ${
        matches
          ? 'bg-yellow-50 ring-1 ring-yellow-300'
          : featured
            ? 'bg-gradient-to-r from-gray-50 to-transparent hover:from-gray-100'
            : 'hover:bg-gray-50'
      }`}
    >
      <div
        className={`${featured ? 'w-10 h-10 text-xs' : 'w-7 h-7 text-[10px]'} rounded-full flex items-center justify-center font-bold text-white shadow-sm ${colorForName(s.id)}`}
      >
        {initials(s.nom, s.prenom)}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1">
          <span
            className={`${featured ? 'text-sm' : 'text-xs'} font-semibold text-gray-900 truncate`}
          >
            {s.nom}{' '}
            <span className="font-normal text-gray-700">
              {s.prenom.charAt(0).toUpperCase() + s.prenom.slice(1).toLowerCase()}
            </span>
          </span>
          {s.is_resp && <Crown className="w-3 h-3 text-amber-500 shrink-0" />}
        </div>
        <div className={`${featured ? 'text-xs' : 'text-[10px]'} text-gray-500 truncate`}>
          {s.poste}
        </div>
      </div>
    </button>
  )
}

function AvatarStack({ people, max }: { people: Salarie[]; max: number }) {
  const shown = people.slice(0, max)
  const extra = people.length - max
  return (
    <div className="flex items-center -space-x-2">
      {shown.map((s) => (
        <div
          key={s.id}
          className={`w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold text-white border-2 border-white shadow-sm ${colorForName(s.id)}`}
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
  onClose,
}: {
  salarie: Salarie
  onClose: () => void
}) {
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
            className={`w-20 h-20 mx-auto rounded-full flex items-center justify-center text-xl font-bold text-white ${colorForName(salarie.id)}`}
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
        </div>
      </motion.div>
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
