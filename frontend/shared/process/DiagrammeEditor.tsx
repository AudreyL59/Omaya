// Editeur/viewer de diagramme (tldraw v5), utilise en modal fullscreen
// dans ProcessPage. Storage : JSON serialise du store tldraw (backend
// stocke dans pgt_process.diagramme_json).

import { useEffect, useMemo, useState } from 'react'
import { Tldraw, type Editor, getSnapshot, loadSnapshot } from 'tldraw'
import { getAssetUrlsByImport } from '@tldraw/assets/imports.vite'
import 'tldraw/tldraw.css'
import { Save, X } from 'lucide-react'

import { showToast } from '../ui/dialog'
import { fetchDiagramme, saveDiagramme } from './api'

type Ctx = { apiBase: string; getToken: () => string | null }

export default function DiagrammeEditor({
  ctx, idProcess, readonly, onClose,
}: {
  ctx: Ctx
  idProcess: string
  readonly: boolean
  onClose: () => void
}) {
  const [editor, setEditor] = useState<Editor | null>(null)
  const [initialLoaded, setInitialLoaded] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  // Assets tldraw servis en local (bundle) plutot que depuis unpkg :
  // evite le CDN externe (firewall d'entreprise) qui causait un ecran
  // noir a la 1ere interaction. Memoise pour ne pas re-generer les URLs.
  const assetUrls = useMemo(() => getAssetUrlsByImport(), [])

  // ESC = close (avec confirmation si dirty)
  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      if (dirty && !readonly && !window.confirm('Fermer sans enregistrer ?')) return
      onClose()
    }
    window.addEventListener('keydown', onEsc)
    return () => window.removeEventListener('keydown', onEsc)
  }, [onClose, dirty, readonly])

  // Chargement initial du snapshot depuis le backend
  useEffect(() => {
    if (!editor || initialLoaded) return
    void (async () => {
      const r = await fetchDiagramme(ctx, idProcess)
      const json = r?.json || ''
      if (json) {
        try {
          const snap = JSON.parse(json)
          loadSnapshot(editor.store, snap)
        } catch (e) {
          console.warn('diagramme JSON invalide', e)
        }
      }
      if (readonly) {
        editor.updateInstanceState({ isReadonly: true })
      }
      setInitialLoaded(true)
      // Ecoute des changements pour marquer dirty
      const cleanup = editor.store.listen(
        () => setDirty(true),
        { source: 'user', scope: 'document' },
      )
      // On garde le cleanup dans le closure — inutile de le retourner
      // car le composant se demonte au close.
      void cleanup
    })()
  }, [editor, ctx, idProcess, readonly, initialLoaded])

  const save = async () => {
    if (!editor || saving) return
    setSaving(true)
    try {
      const snap = getSnapshot(editor.store)
      const json = JSON.stringify(snap)
      const r = await saveDiagramme(ctx, idProcess, json)
      if (r?.ok) {
        setDirty(false)
        showToast('Diagramme enregistré', 'success')
      } else {
        showToast('Échec sauvegarde', 'error')
      }
    } catch (e) {
      console.warn('save diagramme', e)
      showToast('Échec sauvegarde', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[95] bg-black/80 flex flex-col">
      <header className="bg-white border-b border-c-line-soft px-3 py-2 flex items-center gap-2 shrink-0">
        <div className="flex-1 text-sm font-semibold">
          Diagramme{readonly ? ' (lecture seule)' : ''}
          {dirty && !readonly && (
            <span className="ml-2 text-xs text-amber-600 italic">
              modifications non enregistrées
            </span>
          )}
        </div>
        {!readonly && (
          <button onClick={save} disabled={saving || !dirty}
            className={`flex items-center gap-1 px-3 py-1.5 rounded text-sm font-semibold ${
              !dirty || saving
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-c-brand text-white hover:brightness-110'}`}>
            <Save className="w-4 h-4" /> Enregistrer
          </button>
        )}
        <button onClick={() => {
          if (dirty && !readonly && !window.confirm('Fermer sans enregistrer ?')) return
          onClose()
        }} className="p-2 rounded hover:bg-gray-100">
          <X className="w-4 h-4" />
        </button>
      </header>
      <div className="flex-1 relative bg-white">
        <Tldraw onMount={setEditor} assetUrls={assetUrls} />
      </div>
    </div>
  )
}
