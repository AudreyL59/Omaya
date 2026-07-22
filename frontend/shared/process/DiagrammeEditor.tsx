// Editeur/viewer de diagramme (tldraw v5), utilise en modal fullscreen
// dans ProcessPage. Storage : JSON serialise du store tldraw (backend
// stocke dans pgt_process.diagramme_json).

import { useEffect, useMemo, useRef, useState } from 'react'
import { Tldraw, type Editor, getSnapshot, loadSnapshot } from 'tldraw'
// Alias Vite (resolve.alias 'tldraw-assets-vite') pointe vers
// node_modules/@tldraw/assets/imports.vite.js du projet courant.
// Rolldown refuse le sous-import '@tldraw/assets/imports.vite' car le
// package n'a pas de champ "exports" declare — on contourne via alias.
// @ts-expect-error alias resolu au build par Vite
import { getAssetUrlsByImport } from 'tldraw-assets-vite'
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
  // Editor tldraw stocke en ref (pas en state) pour eviter les
  // re-renders qui demontent le canvas apres l'action utilisateur.
  const editorRef = useRef<Editor | null>(null)
  // Dirty flag idem : ref pour tracker cote save, on ne rerender pas
  // pour ca (le badge 'modifie' est mis a jour via forceUpdate ci-dessous).
  const dirtyRef = useRef(false)
  const [saving, setSaving] = useState(false)
  const [dirtyTick, setDirtyTick] = useState(0)  // force UI refresh du badge

  // Assets tldraw servis en local (bundle) — evite le CDN unpkg.
  // Memoise pour ne pas re-generer les URLs a chaque render.
  const assetUrls = useMemo(() => getAssetUrlsByImport(), [])

  const handleMount = (editor: Editor) => {
    editorRef.current = editor
    // Charge le snapshot existant
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
      // Ecoute des changements user pour flag dirty (via ref, PAS de
      // state qui rerender). On ne veut le badge visible qu'a la 1re
      // modif, donc un tick suffit.
      editor.store.listen(() => {
        if (!dirtyRef.current) {
          dirtyRef.current = true
          setDirtyTick(t => t + 1)
        }
      }, { source: 'user', scope: 'document' })
    })()
  }

  // ESC = close (avec confirmation si dirty)
  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      if (dirtyRef.current && !readonly
          && !window.confirm('Fermer sans enregistrer ?')) return
      onClose()
    }
    window.addEventListener('keydown', onEsc)
    return () => window.removeEventListener('keydown', onEsc)
  }, [onClose, readonly])

  const save = async () => {
    const editor = editorRef.current
    if (!editor || saving) return
    setSaving(true)
    try {
      const snap = getSnapshot(editor.store)
      const json = JSON.stringify(snap)
      const r = await saveDiagramme(ctx, idProcess, json)
      if (r?.ok) {
        dirtyRef.current = false
        setDirtyTick(t => t + 1)
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

  const dirty = dirtyRef.current
  // dirtyTick sert uniquement à forcer le re-render du header
  void dirtyTick

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 95,
                  display: 'flex', flexDirection: 'column',
                  background: '#fff' }}>
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
          if (dirtyRef.current && !readonly
              && !window.confirm('Fermer sans enregistrer ?')) return
          onClose()
        }} className="p-2 rounded hover:bg-gray-100">
          <X className="w-4 h-4" />
        </button>
      </header>
      {/* Tldraw doit avoir un container avec dimensions non-nulles.
          On utilise position:absolute plutot que flex-1 pour eviter les
          bugs de calcul de layout au re-render. */}
      <div style={{ position: 'relative', flex: 1 }}>
        <div style={{ position: 'absolute', inset: 0 }}>
          <Tldraw onMount={handleMount} assetUrls={assetUrls} />
        </div>
      </div>
    </div>
  )
}
