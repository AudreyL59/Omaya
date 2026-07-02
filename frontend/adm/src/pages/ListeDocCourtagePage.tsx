/**
 * Fen_ListeDocCourtage - Liste des documents de courtage (templates).
 *
 * Page menu ADM 'Liste des Contrats de Courtage'.
 * Toggle 'Afficher les doc archives' (inverse doc_actif).
 * Boutons : Nouveau / Dupliquer / Supprimer / Modifier / Archiver.
 * Double-clic ligne = Modifier.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  ArrowLeft, FileText, Plus, Copy, Trash2, Pencil, Archive,
  Loader2, Star,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  useTableSortFilter, SortableTh, FilterInput,
} from '@shared/production/_tableHelpers'
import DocCourtageEditModal from '@/components/societe/DocCourtageEditModal'

const API_BASE = '/api/adm'

interface Doc {
  id_doc_courtage: string
  id_groupe_operateur: number; lib_groupe_operateur: string
  titre: string; info_cpl: string
  id_ste: string; rs_interne_ste: string
  doc_actif: boolean; prioritaire: boolean
  modif_date: string
}

const shortDate = (iso: string): string =>
  !iso || iso.length < 10 ? '' : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

export default function ListeDocCourtagePage() {
  useDocumentTitle('Liste des Contrats de Courtage')
  const [archives, setArchives] = useState(false)
  const [rows, setRows] = useState<Doc[]>([])
  const [selected, setSelected] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [fiche, setFiche] = useState<{ open: boolean; id: string | null }>({
    open: false, id: null,
  })

  const load = useCallback(async () => {
    setLoading(true); setSelected('')
    try {
      const r = await fetch(
        `${API_BASE}/doc-courtage?archives=${archives}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      setRows(await r.json())
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }, [archives])

  useEffect(() => { void load() }, [load])

  const tsf = useTableSortFilter(
    rows as unknown as Array<Record<string, unknown>>,
    { key: 'lib_groupe_operateur', dir: 'asc' },
    (r) => [
      r.titre, r.info_cpl, r.lib_groupe_operateur, r.rs_interne_ste,
    ].join(' '),
  )
  const visible = tsf.rows as unknown as Doc[]

  const sel = visible.find(r => r.id_doc_courtage === selected)

  // Regroupement visuel par groupe operateur
  const groupedByGrp: Record<string, Doc[]> = {}
  for (const r of visible) {
    const key = r.lib_groupe_operateur || '(sans groupe)'
    if (!groupedByGrp[key]) groupedByGrp[key] = []
    groupedByGrp[key].push(r)
  }

  const onNouveau = () => setFiche({ open: true, id: null })
  const onModifier = () => {
    if (!sel) { showToast('Sélectionne un document.', 'info'); return }
    setFiche({ open: true, id: sel.id_doc_courtage })
  }

  const doAction = async (
    label: string, url: string, method: 'POST' | 'DELETE', ask: string,
  ) => {
    if (!sel) { showToast('Sélectionne un document.', 'info'); return }
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

  const onDupliquer = () => sel && doAction(
    'Dupliquer',
    `${API_BASE}/doc-courtage/${sel.id_doc_courtage}/duplicate`,
    'POST',
    'Vous êtes sur le point de dupliquer ce document. Voulez-vous continuer ?',
  )
  const onSupprimer = () => sel && doAction(
    'Supprimer',
    `${API_BASE}/doc-courtage/${sel.id_doc_courtage}`,
    'DELETE',
    'Vous êtes sur le point de supprimer ce document. Voulez-vous continuer ?',
  )
  const onArchiver = () => sel && doAction(
    'Archiver',
    `${API_BASE}/doc-courtage/${sel.id_doc_courtage}/archive`,
    'POST',
    'Vous êtes sur le point d\'archiver ce document. Voulez-vous continuer ?',
  )

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-110px)] text-c-ink">
      <div className="flex items-center gap-2 mb-3">
        <Link to=".." relative="path"
          className="p-1.5 hover:bg-c-surface-soft rounded text-c-ink-faint-2">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-lg font-bold flex items-center gap-2">
          <FileText className="w-4 h-4 text-c-brand" />
          Liste des documents de courtage
        </h1>
      </div>

      {/* Barre d'action */}
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
        <div className="flex-1" />
        <label className="flex items-center gap-2 text-xs cursor-pointer">
          <input type="checkbox" checked={archives}
            onChange={e => setArchives(e.target.checked)} />
          Afficher les doc archivés
        </label>
        <FilterInput value={tsf.filter} onChange={tsf.setFilter}
          placeholder="Filtrer…" />
      </div>

      {/* Tableau */}
      <div className="bg-white rounded-xl border border-c-line overflow-hidden flex-1 flex flex-col">
        <div className="px-3 py-1.5 border-b border-c-line-soft text-xs text-c-ink-faint">
          {visible.length} / {rows.length} document(s) {archives ? 'archivé(s)' : 'actif(s)'}
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
                  <SortableTh label="Groupe" sortKey="lib_groupe_operateur" sort={tsf.sort} onSort={tsf.toggleSort} />
                  <SortableTh label="Titre" sortKey="titre" sort={tsf.sort} onSort={tsf.toggleSort} />
                  <SortableTh label="Info Cplt" sortKey="info_cpl" sort={tsf.sort} onSort={tsf.toggleSort} />
                  <SortableTh label="Société" sortKey="rs_interne_ste" sort={tsf.sort} onSort={tsf.toggleSort} />
                  <SortableTh label="Prioritaire" sortKey="prioritaire" sort={tsf.sort} onSort={tsf.toggleSort} align="center" />
                  <SortableTh label="Dernière modif" sortKey="modif_date" sort={tsf.sort} onSort={tsf.toggleSort} />
                </tr>
              </thead>
              <tbody>
                {Object.keys(groupedByGrp).length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-c-ink-faint-2 italic">
                      Aucun document.
                    </td>
                  </tr>
                ) : Object.entries(groupedByGrp).map(([grp, list]) => (
                  <>
                    <tr key={`h-${grp}`} className="bg-c-brand/5 border-t border-c-line-soft">
                      <td colSpan={6} className="px-3 py-1 text-xs font-bold text-c-brand">
                        — {grp} —
                      </td>
                    </tr>
                    {list.map(r => (
                      <tr key={r.id_doc_courtage}
                        onClick={() => setSelected(r.id_doc_courtage)}
                        onDoubleClick={() => setFiche({ open: true, id: r.id_doc_courtage })}
                        className={`cursor-pointer border-t border-c-line-soft ${
                          selected === r.id_doc_courtage
                            ? 'bg-c-brand/10' : 'hover:bg-c-surface-soft'
                        }`}>
                        <td className="px-2 py-1.5">{r.lib_groupe_operateur}</td>
                        <td className="px-2 py-1.5 font-medium">{r.titre}</td>
                        <td className="px-2 py-1.5 truncate max-w-[280px]" title={r.info_cpl}>
                          {r.info_cpl}
                        </td>
                        <td className="px-2 py-1.5">{r.rs_interne_ste}</td>
                        <td className="px-2 py-1.5 text-center">
                          {r.prioritaire && (
                            <Star className="w-3.5 h-3.5 text-yellow-500 inline" fill="currentColor" />
                          )}
                        </td>
                        <td className="px-2 py-1.5">{shortDate(r.modif_date)}</td>
                      </tr>
                    ))}
                  </>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {fiche.open && (
        <DocCourtageEditModal
          idDocCourtage={fiche.id ?? ''}
          onClose={() => setFiche({ open: false, id: null })}
          onSaved={() => { void load(); setFiche({ open: false, id: null }) }} />
      )}
    </div>
  )
}
