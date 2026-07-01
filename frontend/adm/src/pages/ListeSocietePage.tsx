/**
 * Fen_ListeSociete - Sociétés (icône building du header).
 *
 * Tableau des sociétés avec 2 filtres :
 *   - Toggle Interne (id_type_orga=1) / Distributeur (id_type_orga=3)
 *   - Toggle 'Afficher les STE archivées' (is_actif=False si activé)
 *
 * Boutons haut : Nouveau / Dupliquer / Supprimer / Modifier / Archiver
 * (placeholders pour l'instant en attente du code WinDev de chaque
 * bouton — la liste reste fonctionnelle en lecture).
 */
import { useCallback, useEffect, useState } from 'react'
import {
  ArrowLeft, Building2, Plus, Copy, Trash2, Pencil, Archive,
  Loader2,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  useTableSortFilter, SortableTh, FilterInput,
} from '@shared/production/_tableHelpers'
import FicheSocieteModal from '@/components/societe/FicheSocieteModal'

const API_BASE = '/api/adm'

interface Societe {
  id_societe_auto: string; id_ste: string
  id_type_orga: number
  raison_sociale: string; rs_interne: string; siret: string
  is_actif: boolean; modif_date: string
  id_gerant: number; num_orias: string; date_creation: string
}

const shortDate = (iso: string): string =>
  !iso || iso.length < 10 ? '' : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
const typeLabel = (id: number): string =>
  id === 1 ? 'Interne' : id === 3 ? 'Distributeur' : String(id)

export default function ListeSocietePage() {
  useDocumentTitle('Liste des sociétés')
  const [typeOrga, setTypeOrga] = useState<1 | 3>(1)
  const [archivees, setArchivees] = useState(false)
  const [rows, setRows] = useState<Societe[]>([])
  const [selected, setSelected] = useState<string>('')
  const [loading, setLoading] = useState(false)
  // id_societe_auto est un bigint WinDev (timestamp 17 chiffres) > 2^53
  // -> DOIT rester en string, sinon parseInt perd de la precision et on
  // ouvre la mauvaise fiche.
  const [fiche, setFiche] = useState<{ open: boolean; id: string | null }>({ open: false, id: null })

  const load = useCallback(async () => {
    setLoading(true); setSelected('')
    try {
      const r = await fetch(
        `${API_BASE}/societes?type_orga=${typeOrga}&archivees=${archivees}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      setRows(await r.json())
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }, [typeOrga, archivees])

  useEffect(() => { void load() }, [load])

  const tsf = useTableSortFilter(
    rows as unknown as Array<Record<string, unknown>>,
    { key: 'rs_interne', dir: 'asc' },
    (r) => [r.rs_interne, r.raison_sociale, r.siret, r.num_orias].join(' '),
  )
  const visible = tsf.rows as unknown as Societe[]

  const sel = visible.find(r => r.id_societe_auto === selected)

  const requireSel = (): Societe | null => {
    if (!sel) { showToast('Sélectionne une société d\'abord.', 'info'); return null }
    return sel
  }

  const doAction = async (
    label: string, url: string, method: 'POST' | 'DELETE', ask: string,
  ) => {
    const s = requireSel(); if (!s) return
    const ok = await showConfirm({ title: label, message: ask })
    if (!ok) return
    try {
      const r = await fetch(url, {
        method,
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast(`${label} OK`, 'success')
      await load()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  const onDupliquer = () => {
    const s = sel; if (!s) { showToast('Sélectionne une société d\'abord.', 'info'); return }
    void doAction(
      'Dupliquer',
      `${API_BASE}/societes/${s.id_societe_auto}/duplicate`,
      'POST',
      'Vous êtes sur le point de dupliquer cette société. Voulez-vous continuer ?',
    )
  }
  const onSupprimer = () => {
    const s = sel; if (!s) { showToast('Sélectionne une société d\'abord.', 'info'); return }
    void doAction(
      'Supprimer',
      `${API_BASE}/societes/${s.id_societe_auto}`,
      'DELETE',
      'Vous êtes sur le point de supprimer cette société. Voulez-vous continuer ?',
    )
  }
  const onArchiver = () => {
    const s = sel; if (!s) { showToast('Sélectionne une société d\'abord.', 'info'); return }
    void doAction(
      'Archiver',
      `${API_BASE}/societes/${s.id_societe_auto}/archive`,
      'POST',
      'Vous êtes sur le point d\'archiver cette société. Voulez-vous continuer ?',
    )
  }
  const onNouveau = () => {
    setFiche({ open: true, id: null })
  }
  const onModifier = () => {
    if (!sel) { showToast('Sélectionne une société d\'abord.', 'info'); return }
    setFiche({ open: true, id: sel.id_societe_auto })
  }

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-110px)] text-c-ink">
      <div className="flex items-center gap-2 mb-3">
        <Link to=".." relative="path"
          className="p-1.5 hover:bg-c-surface-soft rounded text-c-ink-faint-2">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-lg font-bold flex items-center gap-2">
          <Building2 className="w-4 h-4 text-c-brand" />
          Liste des sociétés
        </h1>
      </div>

      {/* Barre d'actions */}
      <div className="flex items-center gap-2 mb-3 bg-white p-3 rounded-xl border border-c-line text-sm flex-wrap">
        <button type="button" onClick={onNouveau}
          className="flex items-center gap-1.5 px-3 py-1 rounded text-c-brand hover:bg-c-brand/10 text-xs">
          <Plus className="w-4 h-4" /> Nouveau
        </button>
        <button type="button" onClick={onDupliquer} disabled={!sel}
          className="flex items-center gap-1.5 px-3 py-1 rounded text-c-brand hover:bg-c-brand/10 disabled:opacity-30 text-xs">
          <Copy className="w-4 h-4" /> Dupliquer
        </button>
        <button type="button" onClick={onSupprimer} disabled={!sel}
          className="flex items-center gap-1.5 px-3 py-1 rounded text-red-600 hover:bg-red-50 disabled:opacity-30 text-xs">
          <Trash2 className="w-4 h-4" /> Supprimer
        </button>
        <button type="button" onClick={onModifier} disabled={!sel}
          className="flex items-center gap-1.5 px-3 py-1 rounded text-c-brand hover:bg-c-brand/10 disabled:opacity-30 text-xs">
          <Pencil className="w-4 h-4" /> Modifier
        </button>
        <button type="button" onClick={onArchiver} disabled={!sel}
          className="flex items-center gap-1.5 px-3 py-1 rounded text-c-ink-soft hover:bg-c-surface-soft disabled:opacity-30 text-xs">
          <Archive className="w-4 h-4" /> Archiver
        </button>

        {/* Toggle Interne / Distributeur */}
        <div className="flex gap-0 ml-4">
          {([[1, 'Interne'], [3, 'Distributeur']] as const).map(([val, label], i) => (
            <button key={val} type="button" onClick={() => setTypeOrga(val)}
              className={`px-3 h-7 text-xs border border-c-line ${
                i === 0 ? 'rounded-l' : 'rounded-r'
              } ${
                typeOrga === val
                  ? 'bg-c-brand text-white border-c-brand'
                  : 'bg-white text-c-ink-soft hover:bg-c-surface-soft'
              }`}>
              {label}
            </button>
          ))}
        </div>

        <div className="flex-1" />

        <label className="flex items-center gap-2 text-xs cursor-pointer">
          <input type="checkbox" checked={archivees}
            onChange={e => setArchivees(e.target.checked)} />
          Afficher les STE archivées
        </label>
        <FilterInput value={tsf.filter} onChange={tsf.setFilter}
          placeholder="Filtrer…" />
      </div>

      {/* Tableau */}
      <div className="bg-white rounded-xl border border-c-line overflow-hidden flex-1 flex flex-col">
        <div className="px-3 py-1.5 border-b border-c-line-soft text-xs text-c-ink-faint">
          {visible.length} / {rows.length} société(s) {archivees ? 'archivée(s)' : 'active(s)'}
        </div>
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-5 h-5 animate-spin text-c-brand" />
            </div>
          ) : (
            <table className="w-full text-xs">
              <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0 z-10">
                <tr>
                  <SortableTh label="Société" sortKey="rs_interne" sort={tsf.sort} onSort={tsf.toggleSort} />
                  <SortableTh label="Type Orga" sortKey="id_type_orga" sort={tsf.sort} onSort={tsf.toggleSort} />
                  <SortableTh label="Raison Sociale" sortKey="raison_sociale" sort={tsf.sort} onSort={tsf.toggleSort} />
                  <SortableTh label="Raison Sociale Interne" sortKey="rs_interne" sort={tsf.sort} onSort={tsf.toggleSort} />
                  <SortableTh label="SIRET" sortKey="siret" sort={tsf.sort} onSort={tsf.toggleSort} />
                  <SortableTh label="Visible" sortKey="is_actif" sort={tsf.sort} onSort={tsf.toggleSort} align="center" />
                  <SortableTh label="Date modif" sortKey="modif_date" sort={tsf.sort} onSort={tsf.toggleSort} />
                </tr>
              </thead>
              <tbody className="divide-y divide-c-line-soft">
                {visible.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-c-ink-faint-2 italic">
                      Aucune société.
                    </td>
                  </tr>
                ) : visible.map(r => (
                  <tr key={r.id_societe_auto}
                    onClick={() => setSelected(r.id_societe_auto)}
                    onDoubleClick={() => setFiche({ open: true, id: r.id_societe_auto })}
                    className={`cursor-pointer ${
                      selected === r.id_societe_auto
                        ? 'bg-c-brand/10' : 'hover:bg-c-surface-soft'
                    }`}>
                    <td className="px-2 py-1.5 font-medium">{r.rs_interne}</td>
                    <td className="px-2 py-1.5">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                        r.id_type_orga === 1 ? 'bg-c-brand/10 text-c-brand'
                                              : 'bg-orange-100 text-orange-700'
                      }`}>
                        {typeLabel(r.id_type_orga)}
                      </span>
                    </td>
                    <td className="px-2 py-1.5">{r.raison_sociale}</td>
                    <td className="px-2 py-1.5">{r.rs_interne}</td>
                    <td className="px-2 py-1.5 tabular-nums">{r.siret}</td>
                    <td className="px-2 py-1.5 text-center">{r.is_actif ? '✓' : ''}</td>
                    <td className="px-2 py-1.5">{shortDate(r.modif_date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {fiche.open && (
        <FicheSocieteModal idSocieteAuto={fiche.id}
          onClose={() => setFiche({ open: false, id: null })}
          onSaved={() => { void load() }} />
      )}
    </div>
  )
}
