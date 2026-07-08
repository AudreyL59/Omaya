/**
 * Modal de selection d'une equipe / agence via l'arborescence de
 * l'organigramme (comme la popup Rattachement du salarie).
 *
 * Navigation lazy : chaque noeud charge ses enfants a l'expand.
 * Endpoint utilise : /api/adm/fiche-salarie/orga/tree?id_parent=X
 */
import { useCallback, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown, ChevronRight, Loader2, Users, X, Check } from 'lucide-react'

import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'

interface TreeNode {
  id_organigramme: string
  lib_orga: string
  has_children: boolean
  children?: TreeNode[]
  expanded?: boolean
  loading?: boolean
}

interface Props {
  onClose: () => void
  onSelect: (idOrga: string, libOrga: string) => void
  title?: string
}

export default function OrgaTreePickerModal({
  onClose,
  onSelect,
  title = 'Choisir une équipe / agence',
}: Props) {
  const [tree, setTree] = useState<TreeNode[]>([])
  const [showOrga, setShowOrga] = useState(true)
  const [selected, setSelected] = useState<string>('')
  const [selectedLib, setSelectedLib] = useState<string>('')

  const loadChildren = useCallback(async (idParent: string): Promise<TreeNode[]> => {
    const r = await fetch(
      `/api/adm/fiche-salarie/orga/tree?id_parent=${idParent || 0}`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
    if (!r.ok) throw new Error(String(r.status))
    const j = (await r.json()) as { items: TreeNode[] }
    return j.items
  }, [])

  // Charge la racine a l'ouverture
  useEffect(() => {
    let cancelled = false
    loadChildren('0')
      .then((items) => {
        if (!cancelled) {
          setTree(items.map((it) => ({ ...it, expanded: false })))
        }
      })
      .catch(() => {
        if (!cancelled) showToast('Échec chargement de l\'organigramme', 'error')
      })
    return () => { cancelled = true }
  }, [loadChildren])

  const expandNode = async (path: number[]) => {
    setTree((prev) => mutateTree(prev, path, (n) => ({ ...n, loading: true })))
    try {
      const target = findNode(tree, path)
      const items = target ? await loadChildren(target.id_organigramme) : []
      setTree((prev) =>
        mutateTree(prev, path, (n) => ({
          ...n,
          loading: false,
          expanded: true,
          children: items.map((it) => ({ ...it, expanded: false })),
        })),
      )
    } catch {
      setTree((prev) => mutateTree(prev, path, (n) => ({ ...n, loading: false })))
      showToast('Échec chargement des enfants', 'error')
    }
  }

  const collapseNode = (path: number[]) => {
    setTree((prev) => mutateTree(prev, path, (n) => ({ ...n, expanded: false })))
  }

  const onSelectNode = (n: TreeNode) => {
    setSelected(n.id_organigramme)
    setSelectedLib(n.lib_orga)
  }

  const handleValider = () => {
    if (!selected) {
      showToast('Sélectionne une équipe/agence dans l\'arborescence', 'info')
      return
    }
    onSelect(selected, selectedLib)
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4"
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white rounded-2xl shadow-2xl w-[900px] max-w-[95vw] max-h-[85vh] flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-3 border-b border-[#F0EDE5]">
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-[#17494E]" />
              <h2 className="text-base font-semibold text-[#17494E]">{title}</h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded hover:bg-[#EFE9E7] text-[#17494E]"
              title="Fermer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-4">
            {/* Toggle organigramme + selection courante */}
            <div className="flex items-center gap-3 flex-wrap">
              <button
                type="button"
                onClick={() => setShowOrga((v) => !v)}
                className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded border border-[#17494E] text-[#17494E]"
              >
                <span
                  className="inline-block w-8 h-4 rounded-full relative transition"
                  style={{ backgroundColor: showOrga ? '#17494E' : '#D4D4D4' }}
                >
                  <span
                    className="absolute top-0.5 w-3 h-3 rounded-full bg-white transition"
                    style={{ left: showOrga ? 18 : 2 }}
                  />
                </span>
                Afficher l'organigramme
              </button>
              {selectedLib && (
                <span className="text-sm text-[#8B7355]">
                  Sélection : <strong className="text-[#17494E]">{selectedLib}</strong>
                </span>
              )}
            </div>

            {/* Arbre */}
            {showOrga && (
              <div className="border border-[#F0EDE5] rounded p-3 max-h-[400px] overflow-y-auto">
                <div className="text-xs font-semibold mb-2 text-[#8B7355]">Réseau</div>
                {tree.length === 0 && (
                  <div className="text-xs italic text-[#8B7355]/60">
                    <Loader2 className="w-3 h-3 animate-spin inline mr-1" />
                    Chargement…
                  </div>
                )}
                <TreeView
                  nodes={tree}
                  path={[]}
                  selected={selected}
                  onSelect={onSelectNode}
                  onExpand={expandNode}
                  onCollapse={collapseNode}
                />
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-5 py-3 border-t border-[#F0EDE5] flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-sm rounded border border-[#F0EDE5] text-[#8B7355] hover:bg-[#ECF1F2]"
            >
              Annuler
            </button>
            <button
              type="button"
              onClick={handleValider}
              disabled={!selected}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded bg-[#17494E] text-white disabled:opacity-40 hover:bg-[#0F3438]"
            >
              <Check className="w-4 h-4" />
              Sélectionner
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

// --- Arbre lazy ------------------------------------------------------

function TreeView({
  nodes, path, selected, onSelect, onExpand, onCollapse,
}: {
  nodes: TreeNode[]
  path: number[]
  selected: string
  onSelect: (n: TreeNode) => void
  onExpand: (path: number[]) => void
  onCollapse: (path: number[]) => void
}) {
  return (
    <ul className="text-sm text-[#17494E]">
      {nodes.map((n, idx) => {
        const childPath = [...path, idx]
        const isSelected = selected === n.id_organigramme
        return (
          <li key={n.id_organigramme} className="leading-7">
            <div className="flex items-center gap-1">
              {n.has_children ? (
                n.loading ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : n.expanded ? (
                  <button type="button" onClick={() => onCollapse(childPath)}>
                    <ChevronDown className="w-3 h-3" />
                  </button>
                ) : (
                  <button type="button" onClick={() => onExpand(childPath)}>
                    <ChevronRight className="w-3 h-3" />
                  </button>
                )
              ) : (
                <span className="w-3 h-3 inline-block" />
              )}
              <button
                type="button"
                onClick={() => onSelect(n)}
                className="px-1 rounded transition-colors"
                style={{
                  backgroundColor: isSelected ? '#17494E' : 'transparent',
                  color: isSelected ? 'white' : undefined,
                }}
              >
                {n.lib_orga}
              </button>
            </div>
            {n.expanded && n.children && n.children.length > 0 && (
              <div className="pl-4">
                <TreeView
                  nodes={n.children}
                  path={childPath}
                  selected={selected}
                  onSelect={onSelect}
                  onExpand={onExpand}
                  onCollapse={onCollapse}
                />
              </div>
            )}
          </li>
        )
      })}
    </ul>
  )
}

// --- Helpers arbre ---------------------------------------------------

function mutateTree(
  nodes: TreeNode[],
  path: number[],
  fn: (n: TreeNode) => TreeNode,
): TreeNode[] {
  if (path.length === 0) return nodes
  const [head, ...rest] = path
  return nodes.map((n, i) => {
    if (i !== head) return n
    if (rest.length === 0) return fn(n)
    return { ...n, children: mutateTree(n.children || [], rest, fn) }
  })
}

function findNode(nodes: TreeNode[], path: number[]): TreeNode | null {
  let current: TreeNode | undefined = nodes[path[0]]
  for (let i = 1; i < path.length; i++) {
    if (!current?.children) return null
    current = current.children[path[i]]
  }
  return current || null
}
