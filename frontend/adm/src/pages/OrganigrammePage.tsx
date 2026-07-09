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
  UserCog,
  Send,
  Check,
  Plus,
  Pencil,
  MoveRight,
  Trash2,
  Save,
  Copy,
  UserPlus,
} from 'lucide-react'
import OrgaTreePickerModal from '@/components/OrgaTreePickerModal'
import PersonnePicker, { type SalarieItem } from '@/components/PersonnePicker'
import { showConfirm, showToast } from '@shared/ui/dialog'
import { getToken } from '@/api'
import { useAuth } from '@/hooks/useAuth'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PageHeader from '@/components/PageHeader'
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
  useDocumentTitle('Organigramme')
  const { user } = useAuth()
  const droits = user?.droits || []
  const [search, setSearch] = useState('')
  const [zoom, setZoom] = useState(1)
  const [selectedSalarie, setSelectedSalarie] = useState<Salarie | null>(null)
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  // Orga CRUD (droit GestionOrga)
  const canGestionOrga = droits.includes('GestionOrga')
  const [addUnder, setAddUnder] = useState<OrgaNode | null>(null)
  const [editing, setEditing] = useState<OrgaNode | null>(null)
  const [moving, setMoving] = useState<OrgaNode | null>(null)
  const [copying, setCopying] = useState<OrgaNode | null>(null)
  const [addingSalarie, setAddingSalarie] = useState<OrgaNode | null>(null)
  // Etape 2 : quand on a choisi le salarie, on demande la date
  const [deplacerModal, setDeplacerModal] = useState<{
    node: OrgaNode; salarie: SalarieItem
  } | null>(null)
  const [roots, setRoots] = useState<OrgaNode[]>([])
  const [selectedRootId, setSelectedRootId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  // Compteur incremente a la fermeture de FicheSalarieModal pour declencher
  // un rechargement de l'organigramme (icones a jour : en pause, agenda, etc.).
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    fetch('/api/adm/organigramme', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((data) => {
        const list = Array.isArray(data) ? data : []
        setRoots(list)
        if (list.length > 0 && !selectedRootId) {
          setSelectedRootId(list[0].id)
        }

        // Au premier chargement uniquement : collapse les noeuds depth >= 1
        // (les recharges suivantes preservent l'etat d'ouverture utilisateur).
        if (reloadKey === 0) {
          const collapseSet = new Set<string>()
          const walk = (n: OrgaNode, depth: number) => {
            if (depth >= 1 && n.children.length > 0) collapseSet.add(n.id)
            n.children.forEach((c) => walk(c, depth + 1))
          }
          list.forEach((r) => walk(r, 0))
          setCollapsed(collapseSet)
        }
      })
      .catch(() => setRoots([]))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadKey])

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

  // Auto-deplie les ancetres des noeuds qui matchent la recherche + scroll vers
  // le premier match. Se declenche a chaque changement de search ou de root.
  useEffect(() => {
    if (!searchLower || !selectedRoot) return

    const ancestorsToExpand = new Set<string>()
    let firstMatchId: string | null = null

    const walk = (node: OrgaNode, ancestors: string[]): boolean => {
      const nodeMatches = node.lib.toLowerCase().includes(searchLower)
      const salarieMatches = node.salaries.some((s) =>
        `${s.nom} ${s.prenom}`.toLowerCase().includes(searchLower),
      )
      let childHasMatch = false
      for (const c of node.children) {
        if (walk(c, [...ancestors, node.id])) childHasMatch = true
      }
      const hasMatch = nodeMatches || salarieMatches || childHasMatch
      if (hasMatch) {
        ancestors.forEach((a) => ancestorsToExpand.add(a))
        if ((nodeMatches || salarieMatches) && !firstMatchId) {
          firstMatchId = node.id
        }
      }
      return hasMatch
    }
    walk(selectedRoot, [])

    // Deplie les ancetres (retire du Set collapsed)
    setCollapsed((prev) => {
      let changed = false
      const next = new Set(prev)
      ancestorsToExpand.forEach((id) => {
        if (next.delete(id)) changed = true
      })
      return changed ? next : prev
    })

    // Scroll vers le premier match apres que le DOM se soit reorganise
    if (firstMatchId) {
      const targetId = firstMatchId
      window.setTimeout(() => {
        const el = document.getElementById(`orga-node-${targetId}`)
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' })
        }
      }, 150)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchLower, selectedRoot])

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
      <PageHeader
        icon={Network}
        title="Organigramme"
        subtitle={`${stats.total} salariés · ${stats.orgas} organisations`}
      />

      {/* Toolbar */}
      <div className="bg-white rounded-[10px] border border-[#E5DDDC] p-3 mt-6 flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-64 max-w-md">
          <Search className="w-4 h-4 text-[#A68D8A]/80 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Rechercher un salarié ou une orga..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-[#E5DDDC] rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-[#E5DDDC]"
          />
        </div>

        <div className="h-6 w-px bg-[#E5DDDC]" />
        <div className="flex items-center gap-1 bg-white rounded-lg p-1">
          <button
            onClick={() => setZoom((z) => Math.max(0.5, z - 0.1))}
            className="p-1.5 rounded-md hover:bg-white text-[#4E1D17]/80"
            title="Zoom out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <div className="text-xs font-medium text-[#4E1D17]/80 w-12 text-center tabular-nums">
            {Math.round(zoom * 100)}%
          </div>
          <button
            onClick={() => setZoom((z) => Math.min(1.5, z + 0.1))}
            className="p-1.5 rounded-md hover:bg-white text-[#4E1D17]/80"
            title="Zoom in"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom(1)}
            className="p-1.5 rounded-md hover:bg-white text-[#4E1D17]/80"
            title="Reset"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center gap-3 text-xs text-[#A68D8A] ml-auto">
          <LegendItem color="bg-gradient-to-r from-gray-900 to-gray-700" label="Société" />
          <LegendItem color="bg-gradient-to-r from-indigo-600 to-blue-600" label="Région" />
          <LegendItem color="bg-gradient-to-r from-emerald-500 to-teal-500" label="Agence" />
          <LegendItem color="bg-gradient-to-r from-amber-500 to-orange-500" label="Équipe" />
        </div>
      </div>

      {/* Sélecteur de racine (si plus d'une racine) */}
      {roots.length > 1 && (
        <div className="mt-3 flex items-center gap-2 flex-wrap">
          <span className="text-xs text-[#A68D8A] uppercase tracking-wide font-medium">
            Racine :
          </span>
          {roots.map((r) => (
            <button
              key={r.id}
              onClick={() => setSelectedRootId(r.id)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                selectedRootId === r.id
                  ? 'bg-[#17494E] text-white shadow-sm'
                  : 'bg-white text-[#4E1D17]/80 border border-[#E5DDDC] hover:bg-[#EFE9E7]'
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
          <StatCard label="Effectif" value={stats.total} accent="text-[#4E1D17]" />
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
                accent="text-[#17494E]"
              />
            ))}
        </div>
      )}

      {/* Canvas */}
      <div className="flex-1 bg-gradient-to-br from-slate-50 via-white to-slate-50 rounded-[10px] border border-[#E5DDDC] mt-4 overflow-hidden relative">
        <div className="h-full overflow-auto relative">
          {loading ? (
            <div className="flex items-center justify-center py-24">
              <Loader2 className="w-8 h-8 text-[#E5DDDC] animate-spin" />
            </div>
          ) : roots.length === 0 ? (
            <div className="text-center py-24 text-[#A68D8A]/80 text-sm italic">
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
                canGestionOrga={canGestionOrga}
                onAddChild={(n) => setAddUnder(n)}
                onEdit={(n) => setEditing(n)}
                onMove={(n) => setMoving(n)}
                onDelete={handleDeleteOrga}
                onCopy={(n) => setCopying(n)}
                onAddSalarie={(n) => setAddingSalarie(n)}
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
            onFicheClosed={() => setReloadKey((k) => k + 1)}
          />
        )}
      </AnimatePresence>

      {addUnder && (
        <OrgaEditModal
          mode="add"
          idParent={addUnder.id}
          parentLib={addUnder.lib}
          onClose={() => setAddUnder(null)}
          onSaved={() => {
            setAddUnder(null)
            setReloadKey((k) => k + 1)
          }}
        />
      )}
      {editing && (
        <OrgaEditModal
          mode="edit"
          idOrga={editing.id}
          initialLib={editing.lib}
          initialIdTypeNiveau={editing.id_type_niveau}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null)
            setReloadKey((k) => k + 1)
          }}
        />
      )}
      {moving && (
        <OrgaTreePickerModal
          title={`Déplacer "${moving.lib}" vers…`}
          onClose={() => setMoving(null)}
          onSelect={async (idNew) => {
            await handleMoveOrga(moving.id, idNew)
            setMoving(null)
          }}
        />
      )}

      {copying && (
        <OrgaCopierModal
          node={copying}
          onClose={() => setCopying(null)}
          onDone={() => {
            setCopying(null)
            setReloadKey((k) => k + 1)
          }}
        />
      )}

      {addingSalarie && (
        <PersonnePicker
          title={`Ajouter un salarié à "${addingSalarie.lib}"`}
          onClose={() => setAddingSalarie(null)}
          onSelect={(s) => {
            const node = addingSalarie
            setAddingSalarie(null)
            setDeplacerModal({ node, salarie: s })
          }}
        />
      )}

      {deplacerModal && (
        <DeplacerSalarieModal
          orga={deplacerModal.node}
          salarie={deplacerModal.salarie}
          onClose={() => setDeplacerModal(null)}
          onDone={() => {
            setDeplacerModal(null)
            setReloadKey((k) => k + 1)
          }}
        />
      )}
    </div>
  )

  async function handleDeleteOrga(node: OrgaNode) {
    if (!await showConfirm({
      title: 'Supprimer',
      message: `Supprimer le bloc "${node.lib}" ?`,
    })) return
    const r = await fetch(`/api/adm/organigramme/${node.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    const d = await r.json()
    if (d.ok) {
      showToast('Bloc supprimé', 'success')
      setReloadKey((k) => k + 1)
    } else {
      showToast(d.err || 'Erreur', 'error')
    }
  }

  async function handleMoveOrga(idOrga: string, idParentNew: string) {
    const r = await fetch(`/api/adm/organigramme/${idOrga}/move`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ id_parent_new: idParentNew }),
    })
    const d = await r.json()
    if (d.ok) {
      showToast('Bloc déplacé', 'success')
      setReloadKey((k) => k + 1)
    } else {
      showToast(d.err || 'Erreur', 'error')
    }
  }
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
    <div className="bg-white rounded-[10px] border border-[#E5DDDC] px-4 py-2.5">
      <div className={`text-xl font-bold tabular-nums ${accent}`}>{value}</div>
      <div className="text-[10px] text-[#A68D8A] uppercase tracking-wide mt-0.5 truncate">
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

interface OrgaTreeProps {
  node: OrgaNode
  depth: number
  searchLower: string
  collapsed: Set<string>
  onToggle: (id: string) => void
  onSelectSalarie: (s: Salarie) => void
  canGestionOrga: boolean
  onAddChild: (n: OrgaNode) => void
  onEdit: (n: OrgaNode) => void
  onMove: (n: OrgaNode) => void
  onDelete: (n: OrgaNode) => void
  onCopy: (n: OrgaNode) => void
  onAddSalarie: (n: OrgaNode) => void
}

function OrgaTree({
  node,
  depth,
  searchLower,
  collapsed,
  onToggle,
  onSelectSalarie,
  canGestionOrga,
  onAddChild,
  onEdit,
  onMove,
  onDelete,
  onCopy,
  onAddSalarie,
}: OrgaTreeProps) {
  const isCollapsed = collapsed.has(node.id)
  const hasChildren = node.children.length > 0

  const nodeMatches = searchLower && node.lib.toLowerCase().includes(searchLower)
  const salarieMatches = node.salaries.some((s) =>
    `${s.nom} ${s.prenom}`.toLowerCase().includes(searchLower)
  )
  const highlight = !!searchLower && (nodeMatches || salarieMatches)

  return (
    <div id={`orga-node-${node.id}`} className="flex flex-col items-center">
      <OrgaCard
        node={node}
        depth={depth}
        highlight={highlight}
        searchLower={searchLower}
        collapsed={isCollapsed}
        hasChildren={hasChildren}
        onToggle={() => onToggle(node.id)}
        onSelectSalarie={onSelectSalarie}
        canGestionOrga={canGestionOrga}
        onAddChild={onAddChild}
        onEdit={onEdit}
        onMove={onMove}
        onDelete={onDelete}
        onCopy={onCopy}
        onAddSalarie={onAddSalarie}
      />

      {hasChildren && !isCollapsed && (
        <>
          <div className="w-px h-6 bg-[#E5DDDC]" />
          <div className="relative flex items-start gap-6">
            {node.children.length > 1 && (
              <div
                className="absolute top-0 h-px bg-[#E5DDDC]"
                style={{ left: '10%', right: '10%' }}
              />
            )}
            {node.children.map((child) => (
              <div key={child.id} className="flex flex-col items-center">
                <div className="w-px h-6 bg-[#E5DDDC]" />
                <OrgaTree
                  node={child}
                  depth={depth + 1}
                  searchLower={searchLower}
                  collapsed={collapsed}
                  onToggle={onToggle}
                  onSelectSalarie={onSelectSalarie}
                  canGestionOrga={canGestionOrga}
                  onAddChild={onAddChild}
                  onEdit={onEdit}
                  onMove={onMove}
                  onDelete={onDelete}
                  onCopy={onCopy}
                  onAddSalarie={onAddSalarie}
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
  canGestionOrga,
  onAddChild,
  onEdit,
  onMove,
  onDelete,
  onCopy,
  onAddSalarie,
}: {
  node: OrgaNode
  depth: number
  highlight: boolean
  searchLower: string
  collapsed: boolean
  hasChildren: boolean
  onToggle: () => void
  onSelectSalarie: (s: Salarie) => void
  canGestionOrga: boolean
  onAddChild: (n: OrgaNode) => void
  onEdit: (n: OrgaNode) => void
  onMove: (n: OrgaNode) => void
  onDelete: (n: OrgaNode) => void
  onCopy: (n: OrgaNode) => void
  onAddSalarie: (n: OrgaNode) => void
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
          {canGestionOrga && (
            <div className="flex items-center gap-0.5">
              <button
                onClick={(e) => { e.stopPropagation(); onAddChild(node) }}
                className="p-1 rounded-md hover:bg-white/20"
                title="Ajouter un sous-bloc">
                <Plus className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onAddSalarie(node) }}
                className="p-1 rounded-md hover:bg-white/20"
                title="Ajouter / déplacer un salarié ici">
                <UserPlus className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onEdit(node) }}
                className="p-1 rounded-md hover:bg-white/20"
                title="Éditer">
                <Pencil className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onCopy(node) }}
                className="p-1 rounded-md hover:bg-white/20"
                title="Dupliquer">
                <Copy className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onMove(node) }}
                className="p-1 rounded-md hover:bg-white/20"
                title="Déplacer">
                <MoveRight className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onDelete(node) }}
                className="p-1 rounded-md hover:bg-white/20"
                title="Supprimer">
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
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
            <div className="text-[10px] font-medium text-[#A68D8A] uppercase tracking-wide">
              {node.salaries.length} direct
              {nbTotal > node.salaries.length && (
                <span className="text-[#A68D8A]/80"> · {nbTotal} total</span>
              )}
            </div>
            <AvatarStack people={others} max={4} />
          </div>
        )}

        {/* Liste des salariés (hors manager) */}
        {others.length > 0 && (
          <div className="space-y-1 border-t border-[#E5DDDC] pt-2">
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
                className="w-full text-center text-[10px] font-medium text-[#A68D8A] hover:text-[#4E1D17] hover:bg-[#EFE9E7] rounded py-1 mt-1 transition-colors"
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
            : 'hover:bg-[#EFE9E7]'
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
              nonProd ? 'text-[#993636]' : 'text-[#4E1D17]'
            }`}
            title={nonProd ? 'Vendeur non productif' : undefined}
          >
            {s.nom}{' '}
            <span
              className={`font-normal ${nonProd ? 'text-red-500' : 'text-[#4E1D17]'}`}
            >
              {s.prenom.charAt(0).toUpperCase() + s.prenom.slice(1).toLowerCase()}
            </span>
          </span>
          {s.is_resp && (
            <Crown
              className="w-3 h-3 text-red-600 shrink-0"
              aria-label="Responsable"
            />
          )}
          {s.is_resp_adjoint && (
            <Crown
              className="w-3 h-3 text-orange-500 shrink-0"
              aria-label="Responsable adjoint"
            />
          )}
        </div>
        <div className={`${featured ? 'text-xs' : 'text-[10px]'} text-[#A68D8A] truncate`}>
          {s.poste || '—'}
        </div>
        {/* Ancienneté / productivité */}
        <div className="text-[10px] text-[#A68D8A]/80 truncate">
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
                color="bg-red-100 text-[#993636] border-red-200"
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
                color="bg-emerald-100 text-[#17494E] border-[#17494E]/25"
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
        <div className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold text-[#4E1D17]/80 bg-[#EFE9E7] border-2 border-white shadow-sm">
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
  onFicheClosed,
}: {
  salarie: Salarie
  droits: string[]
  onClose: () => void
  /** Appele quand la FicheSalarieModal se ferme - permet au parent
   *  (OrganigrammePage) de recharger l'organigramme pour mettre a jour
   *  les icones (en_pause, en_activite, agenda_actif, etc.). */
  onFicheClosed?: () => void
}) {
  const has = (d: string) => droits.includes(d)
  const [showFiche, setShowFiche] = useState(false)
  // Intranet ADM : seule la Fiche Salarié est exposée ici (les autres
  // actions - declaratifs, ADF, bilan, etc. sont accessibles depuis les
  // ecrans dedies de l'ADM et n'ont pas leur place dans cette popup).
  const actions: {
    label: string
    icon: React.ReactNode
    visible: boolean
    onClick?: () => void
  }[] = [
    {
      label: 'Fiche Salarié',
      icon: <IdCard className="w-4 h-4 text-[#A68D8A]" />,
      visible: has('FicheVend'),
      onClick: () => setShowFiche(true),
    },
  ]
  const visibleActions = actions.filter((a) => a.visible)

  // --- Flags rapides (Pause / Resp Equipe / Resp Adjoint / Chauffeur) --
  // Cf. WinDev menu contextuel salarie -> bascule les booleens
  // pgt_salarie_embauche.
  const [flags, setFlags] = useState({
    en_pause: !!salarie.en_pause,
    resp_equipe: !!salarie.is_resp,
    resp_adjoint: !!salarie.is_resp_adjoint,
    chauffeur: !!salarie.chauffeur,
  })
  const [pendingFlag, setPendingFlag] = useState<string | null>(null)

  const toggleFlag = async (
    field: 'en_pause' | 'resp_equipe' | 'resp_adjoint' | 'chauffeur',
  ) => {
    const nextVal = !flags[field]
    setPendingFlag(field)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${salarie.id_salarie}/toggle-flag`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ field, value: nextVal }),
        },
      )
      const d = await r.json()
      if (d.ok) {
        setFlags((f) => ({ ...f, [field]: nextVal }))
        onFicheClosed?.()
      } else {
        showToast(d.err || 'Erreur', 'error')
      }
    } finally { setPendingFlag(null) }
  }

  // --- Actions Sortie RH / Distrib (ADM uniquement) --------------------
  // Cf. WinDev sortirSalarie(TypeSortie) + sortirDistrib.
  // 1=Annul DUE, 2=FPE Salarie, 3=FPE Entreprise, 4=Demission,
  // 5=Licenciement (autres codes possibles cote backend).
  const canSortieRH = has('TkSortieRH')
  const [pendingSortie, setPendingSortie] = useState<string | null>(null)
  const [profilOmayaOpen, setProfilOmayaOpen] = useState(false)

  const doSortieRH = async (typeSortie: number, lib: string) => {
    if (!await showConfirm({
      title: `Sortir en ${lib}`,
      message: `Confirmer la ${lib} de ${salarie.nom} ${salarie.prenom} ?`,
    })) return
    setPendingSortie(lib)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${salarie.id_salarie}/sortie`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ type_sortie: typeSortie }),
        },
      )
      const d = await r.json()
      if (d.ok) {
        showToast(
          `${lib} enregistrée${d.mail_envoye ? ' + mail envoyé' : ''}`,
          'success',
        )
        onFicheClosed?.()
        onClose()
      } else {
        showToast('Erreur', 'error')
      }
    } finally { setPendingSortie(null) }
  }

  const doSortieDistrib = async () => {
    if (!await showConfirm({
      title: 'Sortie DISTRIB',
      message: `Confirmer la sortie DISTRIB de ${salarie.nom} ${salarie.prenom} ?`,
    })) return
    setPendingSortie('Distrib')
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${salarie.id_salarie}/sortie-distrib`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
        },
      )
      const d = await r.json()
      if (d.ok) {
        showToast('Sortie DISTRIB enregistrée', 'success')
        onFicheClosed?.()
        onClose()
      } else {
        showToast('Erreur', 'error')
      }
    } finally { setPendingSortie(null) }
  }

  const sortieButtons = [
    { type: 1, lib: 'Annul DUE' },
    { type: 3, lib: 'FPE Entreprise' },
    { type: 4, lib: 'Démission' },
    { type: 2, lib: 'FPE Salarié' },
    { type: 5, lib: 'Licenciement' },
  ]
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
            className="p-1 rounded-lg hover:bg-[#EFE9E7] text-[#A68D8A]/80 hover:text-[#4E1D17]"
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
            <h2 className="text-lg font-bold text-[#4E1D17]">
              {salarie.nom} {salarie.prenom}
            </h2>
            {salarie.is_resp && <Crown className="w-4 h-4 text-red-600" />}
          </div>
          <p className="text-sm text-[#A68D8A] mt-0.5">{salarie.poste}</p>

          <div className="mt-5 space-y-2 text-left">
            {salarie.gsm && (
              <a
                href={`tel:${salarie.gsm}`}
                className="flex items-center gap-2 px-3 py-2 bg-white hover:bg-[#EFE9E7] rounded-lg text-sm text-[#4E1D17]"
              >
                <Phone className="w-4 h-4 text-[#A68D8A]/80" />
                {salarie.gsm}
              </a>
            )}
            {salarie.mail && (
              <a
                href={`mailto:${salarie.mail}`}
                className="flex items-center gap-2 px-3 py-2 bg-white hover:bg-[#EFE9E7] rounded-lg text-sm text-[#4E1D17]"
              >
                <Mail className="w-4 h-4 text-[#A68D8A]/80" />
                {salarie.mail}
              </a>
            )}
          </div>

          {visibleActions.length > 0 && (
            <div className="mt-5 pt-4 border-t border-[#E5DDDC] grid grid-cols-2 gap-2">
              {visibleActions.map((a) => (
                <button
                  key={a.label}
                  onClick={a.onClick}
                  className="flex items-center gap-2 px-3 py-2 bg-white hover:bg-[#EFE9E7] rounded-lg text-xs text-[#4E1D17] text-left transition-colors"
                >
                  {a.icon}
                  <span className="truncate">{a.label}</span>
                </button>
              ))}
            </div>
          )}

          {/* Flags rapides (Pause / Resp Equipe / Resp Adjoint / Chauffeur) */}
          <div className="mt-5 pt-4 border-t border-[#E5DDDC] text-left">
            <FlagRow
              label="Pause" icon={<Pause className="w-4 h-4 text-white" />}
              color="bg-gray-500" checked={flags.en_pause}
              loading={pendingFlag === 'en_pause'}
              onToggle={() => toggleFlag('en_pause')}
            />
            <FlagRow
              label="Responsable d'équipe"
              icon={<Crown className="w-4 h-4 text-white" />}
              color="bg-red-600" checked={flags.resp_equipe}
              loading={pendingFlag === 'resp_equipe'}
              onToggle={() => toggleFlag('resp_equipe')}
            />
            <FlagRow
              label="Responsable Adjoint"
              icon={<Crown className="w-4 h-4 text-white" />}
              color="bg-orange-500" checked={flags.resp_adjoint}
              loading={pendingFlag === 'resp_adjoint'}
              onToggle={() => toggleFlag('resp_adjoint')}
            />
            <FlagRow
              label="Chauffeur" icon={<Car className="w-4 h-4 text-white" />}
              color="bg-purple-600" checked={flags.chauffeur}
              loading={pendingFlag === 'chauffeur'}
              onToggle={() => toggleFlag('chauffeur')}
            />
          </div>

          {/* Section Omaya (2 actions) */}
          <div className="mt-4 pt-4 border-t border-[#E5DDDC] text-left">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-[#A68D8A] mb-2">
              Omaya
            </div>
            <button
              onClick={() => setProfilOmayaOpen(true)}
              className="w-full flex items-center gap-2 px-3 py-2 bg-white hover:bg-[#EFE9E7] rounded-lg text-xs text-[#4E1D17] transition-colors mb-1.5">
              <UserCog className="w-4 h-4 text-[#A68D8A]" />
              <span>Attribuer Profil Omaya</span>
            </button>
            <button
              onClick={() => showToast(
                "Renvoyer les Codes OMAYA : à implémenter (envoie le TXT WinDev)",
                'info',
              )}
              className="w-full flex items-center gap-2 px-3 py-2 bg-white hover:bg-[#EFE9E7] rounded-lg text-xs text-[#4E1D17] transition-colors">
              <Send className="w-4 h-4 text-[#A68D8A]" />
              <span>Renvoyer les Codes OMAYA</span>
            </button>
          </div>

          {canSortieRH && (
            <>
              <div className="mt-5 pt-4 border-t border-[#E5DDDC]">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-[#A68D8A] mb-2 text-left">
                  Sortie RH
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {sortieButtons.map((b) => (
                    <button
                      key={b.type}
                      onClick={() => doSortieRH(b.type, b.lib)}
                      disabled={!!pendingSortie}
                      className="flex items-center gap-2 px-3 py-2 bg-white hover:bg-red-50 rounded-lg text-xs text-[#7A2419] text-left transition-colors disabled:opacity-50">
                      {pendingSortie === b.lib
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <UserX className="w-4 h-4" />}
                      <span className="truncate">{b.lib}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-3">
                <button
                  onClick={doSortieDistrib}
                  disabled={!!pendingSortie}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-white hover:bg-red-50 rounded-lg text-xs text-[#7A2419] border border-[#E5DDDC] transition-colors disabled:opacity-50">
                  {pendingSortie === 'Distrib'
                    ? <Loader2 className="w-4 h-4 animate-spin" />
                    : <UserX className="w-4 h-4" />}
                  Sortie DISTRIB
                </button>
              </div>
            </>
          )}
        </div>
      </motion.div>

      <AnimatePresence>
        {showFiche && (
          <FicheSalarieModal
            idSalarie={salarie.id_salarie}
            nom={salarie.nom}
            prenom={salarie.prenom}
            onClose={() => {
              setShowFiche(false)
              onFicheClosed?.()
            }}
          />
        )}
      </AnimatePresence>

      {profilOmayaOpen && (
        <ChoisirProfilOmayaModal
          idSalarie={salarie.id_salarie}
          onClose={() => setProfilOmayaOpen(false)}
          onDone={() => setProfilOmayaOpen(false)}
        />
      )}
    </motion.div>
  )
}

// --- Modal Ajout/Edition d'un bloc orga ----------------------------------

interface OrgaCombo { id: number; lib: string }

interface OrgaEditModalProps {
  mode: 'add' | 'edit'
  idParent?: string
  parentLib?: string
  idOrga?: string
  initialLib?: string
  initialIdTypeNiveau?: number
  onClose: () => void
  onSaved: () => void
}

function OrgaEditModal(p: OrgaEditModalProps) {
  const [lib, setLib] = useState(p.initialLib || '')
  const [idTypeNiveau, setIdTypeNiveau] = useState<number>(
    p.initialIdTypeNiveau || 0,
  )
  const [ville, setVille] = useState('')
  const [secteur, setSecteur] = useState('')
  const [memo, setMemo] = useState('')
  const [invPodium, setInvPodium] = useState(false)
  const [invEffectif, setInvEffectif] = useState(false)
  const [types, setTypes] = useState<OrgaCombo[]>([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetch('/api/adm/organigramme/types-niveau', {
      headers: { Authorization: `Bearer ${getToken()}` },
    }).then((r) => r.json()).then(setTypes).catch(() => setTypes([]))
  }, [])

  const save = async () => {
    if (!lib.trim()) { showToast('Libellé requis', 'error'); return }
    setSaving(true)
    try {
      const body = {
        id_parent: p.idParent || '',
        lib_orga: lib.trim(),
        id_type_niveau_orga: idTypeNiveau,
        ville: ville.trim(),
        secteur: secteur.trim(),
        memo: memo.trim(),
        invisible_podium: invPodium,
        invisible_effectif: invEffectif,
      }
      const r = p.mode === 'add'
        ? await fetch('/api/adm/organigramme', {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${getToken()}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
          })
        : await fetch(`/api/adm/organigramme/${p.idOrga}`, {
            method: 'PUT',
            headers: {
              Authorization: `Bearer ${getToken()}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
          })
      const d = await r.json()
      if (d.ok) {
        showToast(p.mode === 'add' ? 'Bloc créé' : 'Bloc modifié', 'success')
        p.onSaved()
      } else { showToast(d.err || 'Erreur', 'error') }
    } finally { setSaving(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
         onClick={p.onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-5"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-[#4E1D17]">
            {p.mode === 'add' ? 'Ajouter un sous-bloc' : 'Éditer le bloc'}
          </h3>
          <button onClick={p.onClose}
                  className="p-1 rounded-md hover:bg-[#EFE9E7] text-[#A68D8A]">
            <X className="w-4 h-4" />
          </button>
        </div>

        {p.mode === 'add' && p.parentLib && (
          <div className="text-xs text-[#A68D8A] mb-3">
            Sous : <b>{p.parentLib}</b>
          </div>
        )}

        <div className="space-y-3">
          <label className="block text-xs">
            <span className="text-[#A68D8A] font-medium">Libellé *</span>
            <input type="text" value={lib}
                   onChange={(e) => setLib(e.target.value)}
                   className="w-full mt-1 px-2 py-1.5 border border-[#E5DDDC] rounded" />
          </label>

          <label className="block text-xs">
            <span className="text-[#A68D8A] font-medium">Type de niveau</span>
            <select value={idTypeNiveau}
                    onChange={(e) => setIdTypeNiveau(Number(e.target.value))}
                    className="w-full mt-1 px-2 py-1.5 border border-[#E5DDDC] rounded">
              <option value={0}>
                {p.mode === 'add' ? '(automatique : parent + 1)' : '(inchangé)'}
              </option>
              {types.map((t) => (
                <option key={t.id} value={t.id}>{t.lib}</option>
              ))}
            </select>
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label className="block text-xs">
              <span className="text-[#A68D8A] font-medium">Ville</span>
              <input type="text" value={ville}
                     onChange={(e) => setVille(e.target.value)}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5DDDC] rounded" />
            </label>
            <label className="block text-xs">
              <span className="text-[#A68D8A] font-medium">Secteur</span>
              <input type="text" value={secteur}
                     onChange={(e) => setSecteur(e.target.value)}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5DDDC] rounded" />
            </label>
          </div>

          <label className="block text-xs">
            <span className="text-[#A68D8A] font-medium">Mémo</span>
            <textarea rows={2} value={memo}
                      onChange={(e) => setMemo(e.target.value)}
                      className="w-full mt-1 px-2 py-1.5 border border-[#E5DDDC] rounded" />
          </label>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={invPodium}
                     onChange={(e) => setInvPodium(e.target.checked)}
                     className="accent-[#4E1D17]" />
              <span className="text-[#4E1D17]">Invisible podium</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={invEffectif}
                     onChange={(e) => setInvEffectif(e.target.checked)}
                     className="accent-[#4E1D17]" />
              <span className="text-[#4E1D17]">Invisible effectif</span>
            </label>
          </div>
        </div>

        <div className="flex gap-2 mt-5">
          <button onClick={save} disabled={saving}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded bg-[#4E1D17] text-white hover:bg-[#3A1510] disabled:opacity-50 text-sm">
            {saving
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <Save className="w-4 h-4" />}
            Enregistrer
          </button>
          <button onClick={p.onClose}
                  className="flex-1 px-3 py-2 rounded border border-[#A68D8A] text-[#A68D8A] hover:bg-[#EFE9E7] text-sm">
            Annuler
          </button>
        </div>
      </div>
    </div>
  )
}


// --- FlagRow (bascule inline dans SalariePopup) --------------------------

function FlagRow(
  { label, icon, color, checked, loading, onToggle }:
    {
      label: string; icon: React.ReactNode; color: string
      checked: boolean; loading: boolean; onToggle: () => void
    },
) {
  return (
    <label className="flex items-center gap-2.5 py-1.5 cursor-pointer">
      <div className={`w-7 h-7 rounded-full flex items-center justify-center ${color}`}>
        {icon}
      </div>
      <input type="checkbox" checked={checked} disabled={loading}
             onChange={onToggle}
             className="accent-[#4E1D17] w-4 h-4" />
      <span className={`text-sm ${checked ? 'text-[#4E1D17] font-medium' : 'text-[#A68D8A]'}`}>
        {label}
      </span>
      {loading && <Loader2 className="w-3 h-3 animate-spin text-[#A68D8A] ml-auto" />}
    </label>
  )
}


// --- Modal Choisir Profil Omaya -----------------------------------------

function ChoisirProfilOmayaModal(
  { idSalarie, onClose, onDone }:
    {
      idSalarie: string
      onClose: () => void
      onDone: () => void
    },
) {
  const [profils, setProfils] = useState<string[]>([])
  const [choix, setChoix] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetch('/api/adm/fiche-salarie/droit-acces/profils', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((j) => setProfils(Array.isArray(j.items) ? j.items : []))
      .catch(() => setProfils([]))
  }, [])

  const attribuer = async () => {
    if (!choix) { showToast('Sélectionner un profil.', 'info'); return }
    if (!await showConfirm({
      title: 'Attribuer ce profil ?',
      message: `Vous êtes sur le point d'attribuer le profil "${choix}". Continuer ?`,
      confirmLabel: 'Attribuer',
    })) return
    setSaving(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/droit-acces/profil`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({ categorie: choix }),
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const j = (await r.json()) as { nb_inserted: number; nb_updated: number }
      showToast(
        `Profil appliqué : ${j.nb_inserted} ajouté(s), ${j.nb_updated} mis à jour.`,
        'success',
      )
      onDone()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally { setSaving(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4"
         onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-5"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-[#4E1D17]">
            Attribuer un profil Omaya
          </h3>
          <button onClick={onClose}
                  className="p-1 rounded-md hover:bg-[#EFE9E7] text-[#A68D8A]">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[#4E1D17]">Profil :</span>
          <select value={choix}
                  onChange={(e) => setChoix(e.target.value)}
                  className="flex-1 px-2 py-1.5 border rounded text-sm bg-white border-[#E5DDDC] text-[#4E1D17]">
            <option value="">—</option>
            {profils.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <button
            type="button"
            onClick={attribuer}
            disabled={saving || !choix}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded border border-[#17494E] text-[#17494E] hover:bg-[#EFE9E7] disabled:opacity-40">
            {saving
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <Check className="w-4 h-4" />}
            Choisir ce profil
          </button>
        </div>
      </div>
    </div>
  )
}


// --- Modal Copier bloc ---------------------------------------------------

function OrgaCopierModal(
  { node, onClose, onDone }:
    { node: OrgaNode; onClose: () => void; onDone: () => void },
) {
  const [pickerOpen, setPickerOpen] = useState(true)
  const [target, setTarget] = useState<{ id: string; lib: string } | null>(null)
  const [deep1, setDeep1] = useState(true)
  const [deep2, setDeep2] = useState(false)
  const [saving, setSaving] = useState(false)

  const doCopy = async () => {
    if (!target) return
    setSaving(true)
    try {
      const r = await fetch(`/api/adm/organigramme/${node.id}/copier`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_parent_new: target.id,
          include_children_deep_1: deep1,
          include_children_deep_2: deep1 && deep2,
        }),
      })
      const d = await r.json()
      if (d.ok) {
        showToast('Bloc dupliqué', 'success')
        onDone()
      } else {
        showToast(d.err || 'Erreur', 'error')
      }
    } finally { setSaving(false) }
  }

  if (pickerOpen) {
    return (
      <OrgaTreePickerModal
        title={`Copier "${node.lib}" sous…`}
        onClose={onClose}
        onSelect={(id, lib) => {
          setTarget({ id, lib })
          setPickerOpen(false)
        }}
      />
    )
  }
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
         onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-5"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-[#4E1D17]">
            Dupliquer un bloc
          </h3>
          <button onClick={onClose}
                  className="p-1 rounded-md hover:bg-[#EFE9E7] text-[#A68D8A]">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="text-sm text-[#4E1D17] mb-3">
          Copier <b>{node.lib}</b> sous <b>{target?.lib || 'Racine'}</b>
        </div>
        <div className="space-y-2 mb-4 text-xs">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={deep1}
                   onChange={(e) => setDeep1(e.target.checked)}
                   className="accent-[#4E1D17]" />
            <span className="text-[#4E1D17]">Copier aussi les sous-blocs directs</span>
          </label>
          <label className="flex items-center gap-2 ml-5">
            <input type="checkbox" checked={deep2} disabled={!deep1}
                   onChange={(e) => setDeep2(e.target.checked)}
                   className="accent-[#4E1D17]" />
            <span className={deep1 ? 'text-[#4E1D17]' : 'text-gray-400'}>
              …et leurs propres sous-blocs (2 niveaux)
            </span>
          </label>
        </div>
        <div className="flex gap-2">
          <button onClick={doCopy} disabled={!target || saving}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded bg-[#4E1D17] text-white hover:bg-[#3A1510] disabled:opacity-50 text-sm">
            {saving
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <Copy className="w-4 h-4" />}
            Dupliquer
          </button>
          <button onClick={onClose}
                  className="flex-1 px-3 py-2 rounded border border-[#A68D8A] text-[#A68D8A] hover:bg-[#EFE9E7] text-sm">
            Annuler
          </button>
        </div>
      </div>
    </div>
  )
}


// --- Modal Deplacer salarie ---------------------------------------------

function DeplacerSalarieModal(
  { orga, salarie, onClose, onDone }:
    {
      orga: OrgaNode; salarie: SalarieItem
      onClose: () => void; onDone: () => void
    },
) {
  const [date, setDate] = useState(
    salarie.date_embauche || new Date().toISOString().slice(0, 10),
  )
  const [saving, setSaving] = useState(false)

  const doMove = async () => {
    if (!date) { showToast('Date requise', 'error'); return }
    setSaving(true)
    try {
      const r = await fetch('/api/adm/organigramme/deplacer-salarie', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_salarie: salarie.id_salarie,
          id_orga_cible: orga.id,
          date_changement: date,
        }),
      })
      const d = await r.json()
      if (d.ok) {
        showToast('Salarié déplacé', 'success')
        onDone()
      } else { showToast(d.err || 'Erreur', 'error') }
    } finally { setSaving(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
         onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-5"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-[#4E1D17]">
            Transfert de {salarie.nom} {salarie.prenom}
          </h3>
          <button onClick={onClose}
                  className="p-1 rounded-md hover:bg-[#EFE9E7] text-[#A68D8A]">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="text-sm text-[#4E1D17] mb-4">
          Vers : <b>{orga.lib}</b>
        </div>
        <label className="block text-xs mb-4">
          <span className="text-[#A68D8A] font-medium">
            Date de changement d'équipe
          </span>
          <input type="date" value={date}
                 onChange={(e) => setDate(e.target.value)}
                 className="w-full mt-1 px-2 py-1.5 border border-[#E5DDDC] rounded" />
        </label>
        <div className="flex gap-2">
          <button onClick={doMove} disabled={saving}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded bg-[#4E1D17] text-white hover:bg-[#3A1510] disabled:opacity-50 text-sm">
            {saving
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <UserPlus className="w-4 h-4" />}
            Confirmer le transfert
          </button>
          <button onClick={onClose}
                  className="flex-1 px-3 py-2 rounded border border-[#A68D8A] text-[#A68D8A] hover:bg-[#EFE9E7] text-sm">
            Annuler
          </button>
        </div>
      </div>
    </div>
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
