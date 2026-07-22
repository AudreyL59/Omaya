// Editeur/viewer de diagramme (tldraw v5), utilise en modal fullscreen
// dans ProcessPage. Storage : JSON serialise du store tldraw (backend
// stocke dans pgt_process.diagramme_json).

import { memo, useEffect, useMemo, useRef, useState } from 'react'
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

// Composant tldraw fige : monte une fois et ne rerend JAMAIS, meme si
// le parent rerender. Sans ca, chaque event du store declenchait un
// setState quelque part -> React demontait le canvas -> ecran blanc.
const StableTldraw = memo(function StableTldraw({
  onMount, assetUrls,
}: {
  onMount: (editor: Editor) => void
  assetUrls: object
}) {
  return <Tldraw onMount={onMount} assetUrls={assetUrls} />
}, () => true)  // <-- always return true (equal) -> jamais de rerender


export default function DiagrammeEditor({
  ctx, idProcess, readonly, onClose,
}: {
  ctx: Ctx
  idProcess: string
  readonly: boolean
  onClose: () => void
}) {
  // Editor + dirty flag en ref pour ne PAS declencher de rerender.
  const editorRef = useRef<Editor | null>(null)
  const dirtyRef = useRef(false)

  // Ces states peuvent rerender le parent (Tldraw reste stable grace
  // au memo).
  const [saving, setSaving] = useState(false)
  const [dirtyTick, setDirtyTick] = useState(0)

  // Assets tldraw servis en local (bundle) — evite le CDN unpkg.
  const assetUrls = useMemo(() => getAssetUrlsByImport(), [])

  // Callback mount memoise pour rester la meme reference toute la vie
  // du composant (au cas ou React aurait envie de dire "prop change").
  const handleMount = useMemo(() => (editor: Editor) => {
    editorRef.current = editor
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
      // Ecoute les modifs user : uniquement le 1er tick met le badge
      // 'modifications non enregistrees' visible. Ensuite le ref reste
      // a true, on ne re-render plus le parent inutilement.
      editor.store.listen(() => {
        if (!dirtyRef.current) {
          dirtyRef.current = true
          setDirtyTick(t => t + 1)
        }
      }, { source: 'user', scope: 'document' })
    })()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
  void dirtyTick  // dependance pour le render du header

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
      <div style={{ position: 'relative', flex: 1 }}>
        <div style={{ position: 'absolute', inset: 0 }}>
          <StableTldraw onMount={handleMount} assetUrls={assetUrls} />
        </div>
      </div>
    </div>
  )
}
