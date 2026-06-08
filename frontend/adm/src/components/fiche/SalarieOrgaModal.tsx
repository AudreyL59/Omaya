/**
 * Popup "Rattachement du salarie" (transposition Fen_salarieOrga WinDev).
 *
 * - Navigation arborescente dans pgt_organigramme (chargement lazy : on
 *   ne demande les enfants que quand un noeud est deplie).
 * - Champs : date debut / date fin / actif.
 * - Si idSalarieOrga != '' : preremplit l'enregistrement existant et fait
 *   une modification (PUT). Sinon : creation (POST) -> le backend ferme
 *   automatiquement l'ancien suivi 'changement d'equipe' et en cree un
 *   nouveau.
 */

import { useCallback, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown, ChevronRight, Loader2, Save, Users, X } from 'lucide-react'

import { ADM_API, getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'

interface TreeNode {
  id_organigramme: string
  lib_orga: string
  has_children: boolean
  children?: TreeNode[]
  expanded?: boolean
  loading?: boolean
}

interface Props {
  idSalarie: string
  idSalarieOrga: string // '' = creation
  onClose: () => void
  onSaved: () => void
}

export default function SalarieOrgaModal({
  idSalarie,
  idSalarieOrga,
  onClose,
  onSaved,
}: Props) {
  const [tree, setTree] = useState<TreeNode[]>([])
  const [selected, setSelected] = useState<string>('') // id_organigramme
  const [selectedLib, setSelectedLib] = useState<string>('')
  const [showOrga, setShowOrga] = useState(false)
  const [dateDebut, setDateDebut] = useState('')
  const [dateFin, setDateFin] = useState('')
  const [actif, setActif] = useState(true)
  const [saving, setSaving] = useState(false)
  const [loadingInit, setLoadingInit] = useState(false)

  // Chargement initial : si modification, recupere les valeurs existantes
  useEffect(() => {
    if (!idSalarieOrga) return
    let cancelled = false
    setLoadingInit(true)
    // On recharge via la liste complete et on filtre cote front (l'endpoint
    // /orga renvoie deja tous les rattachements du salarie).
    fetch(`${ADM_API}/fiche-salarie/${idSalarie}/orga`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((j) => {
        if (cancelled) return
        const item = (j.organigrammes || []).find(
          (o: { id_salarie_organigramme: string }) =>
            o.id_salarie_organigramme === idSalarieOrga,
        )
        if (item) {
          setSelected(item.id_organigramme)
          setSelectedLib(item.lib_orga)
          setDateDebut(item.date_debut || '')
          setDateFin(item.date_fin || '')
          setActif(!!item.aff_actif)
        }
      })
      .catch(() => {})
      .finally(() => !cancelled && setLoadingInit(false))
    return () => {
      cancelled = true
    }
  }, [idSalarie, idSalarieOrga])

  // Chargement de la racine de l'arbre a l'ouverture
  const loadChildren = useCallback(async (idParent: string): Promise<TreeNode[]> => {
    const r = await fetch(
      `${ADM_API}/fiche-salarie/orga/tree?id_parent=${idParent || 0}`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
    if (!r.ok) throw new Error(String(r.status))
    const j = (await r.json()) as { items: TreeNode[] }
    return j.items
  }, [])

  const toggleOrga = async () => {
    if (showOrga) {
      setShowOrga(false)
      return
    }
    setShowOrga(true)
    if (tree.length === 0) {
      try {
        const items = await loadChildren('0')
        setTree(items.map((it) => ({ ...it, expanded: false })))
      } catch {
        showToast('Échec chargement de l\'organigramme', 'error')
      }
    }
  }

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

  const handleSave = async () => {
    if (!selected) {
      showToast('Sélectionner un organigramme dans l\'arborescence.', 'error')
      return
    }
    setSaving(true)
    try {
      const url = idSalarieOrga
        ? `${ADM_API}/fiche-salarie/orga/${idSalarieOrga}`
        : `${ADM_API}/fiche-salarie/${idSalarie}/orga`
      const method = idSalarieOrga ? 'PUT' : 'POST'
      const r = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id_organigramme: selected,
          date_debut: dateDebut,
          date_fin: dateFin,
          aff_actif: actif,
        }),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      showToast('Rattachement enregistré.', 'success')
      onSaved()
    } catch (e) {
      showToast(`Échec enregistrement : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
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
          <div
            className="flex items-center justify-between px-5 py-3 border-b"
            style={{ borderColor: COLOR_BG_SOFT }}
          >
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5" style={{ color: COLOR_PRIMARY }} />
              <h2 className="text-base font-semibold" style={{ color: COLOR_BRUN }}>
                Rattachement du salarié
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded hover:bg-[#EFE9E7]"
              style={{ color: COLOR_BRUN }}
              title="Fermer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-4">
            {loadingInit && (
              <div className="flex items-center gap-2 text-sm" style={{ color: COLOR_BRUN }}>
                <Loader2 className="w-4 h-4 animate-spin" /> Chargement…
              </div>
            )}

            {/* Toggle organigramme */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={toggleOrga}
                className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded border"
                style={{ borderColor: COLOR_PRIMARY, color: COLOR_PRIMARY }}
              >
                <span
                  className="inline-block w-8 h-4 rounded-full relative transition"
                  style={{
                    backgroundColor: showOrga ? COLOR_PRIMARY : '#D4D4D4',
                  }}
                >
                  <span
                    className="absolute top-0.5 w-3 h-3 rounded-full bg-white transition"
                    style={{ left: showOrga ? 18 : 2 }}
                  />
                </span>
                Afficher l'organigramme
              </button>
              {selectedLib && (
                <span className="text-sm" style={{ color: COLOR_BRUN }}>
                  Sélection : <strong>{selectedLib}</strong>
                </span>
              )}
            </div>

            {/* Arbre */}
            {showOrga && (
              <div
                className="border rounded p-3 max-h-[300px] overflow-y-auto"
                style={{ borderColor: COLOR_BG_SOFT }}
              >
                <div className="text-xs font-semibold mb-2" style={{ color: COLOR_BRUN }}>
                  Réseau
                </div>
                {tree.length === 0 && (
                  <div className="text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
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

            {/* Champs */}
            <div className="grid grid-cols-2 gap-4">
              <Field label="Date de début">
                <input
                  type="date"
                  value={dateDebut}
                  onChange={(e) => setDateDebut(e.target.value)}
                  className="w-full px-2 py-1 border rounded text-sm"
                  style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
                />
              </Field>
              <Field label="Date de fin">
                <input
                  type="date"
                  value={dateFin}
                  onChange={(e) => setDateFin(e.target.value)}
                  className="w-full px-2 py-1 border rounded text-sm"
                  style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
                />
              </Field>
              <Field label="Actif">
                <label className="inline-flex items-center gap-2 text-sm" style={{ color: COLOR_BRUN }}>
                  <input
                    type="checkbox"
                    checked={actif}
                    onChange={(e) => setActif(e.target.checked)}
                  />
                  Rattachement actif
                </label>
              </Field>
            </div>
          </div>

          {/* Footer */}
          <div
            className="px-5 py-3 border-t flex justify-end gap-2"
            style={{ borderColor: COLOR_BG_SOFT }}
          >
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-sm rounded border"
              style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
            >
              Annuler
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !selected}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded text-white disabled:opacity-40"
              style={{ backgroundColor: COLOR_PRIMARY }}
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Enregistrer
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium" style={{ color: COLOR_BRUN }}>
        {label}
      </label>
      {children}
    </div>
  )
}

// --- Arbre lazy ----------------------------------------------------------

function TreeView({
  nodes,
  path,
  selected,
  onSelect,
  onExpand,
  onCollapse,
}: {
  nodes: TreeNode[]
  path: number[]
  selected: string
  onSelect: (n: TreeNode) => void
  onExpand: (path: number[]) => void
  onCollapse: (path: number[]) => void
}) {
  return (
    <ul className="text-sm" style={{ color: COLOR_BRUN }}>
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
                  <button
                    type="button"
                    onClick={() => onCollapse(childPath)}
                    className="text-[10px]"
                  >
                    <ChevronDown className="w-3 h-3" />
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => onExpand(childPath)}
                    className="text-[10px]"
                  >
                    <ChevronRight className="w-3 h-3" />
                  </button>
                )
              ) : (
                <span className="w-3 h-3 inline-block" />
              )}
              <button
                type="button"
                onClick={() => onSelect(n)}
                className="px-1 rounded"
                style={{
                  backgroundColor: isSelected ? COLOR_PRIMARY : 'transparent',
                  color: isSelected ? 'white' : COLOR_BRUN,
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

// --- Helpers immutabilite arbre ------------------------------------------

function findNode(nodes: TreeNode[], path: number[]): TreeNode | null {
  let cur: TreeNode | undefined = nodes[path[0]]
  for (let i = 1; i < path.length; i++) {
    if (!cur?.children) return null
    cur = cur.children[path[i]]
  }
  return cur || null
}

function mutateTree(
  nodes: TreeNode[],
  path: number[],
  mutator: (n: TreeNode) => TreeNode,
): TreeNode[] {
  if (path.length === 0) return nodes
  const [head, ...rest] = path
  return nodes.map((n, i) => {
    if (i !== head) return n
    if (rest.length === 0) return mutator(n)
    return {
      ...n,
      children: n.children ? mutateTree(n.children, rest, mutator) : n.children,
    }
  })
}
