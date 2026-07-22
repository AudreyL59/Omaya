// Editeur/viewer de diagramme (Excalidraw), utilise en modal fullscreen
// dans ProcessPage. Storage : JSON serialise du scene Excalidraw
// (elements + appState + files) dans pgt_process.diagramme_json.
//
// Excalidraw est libre (MIT), pas de licence commerciale requise —
// choix pragmatique apres avoir constate que tldraw v5 exige une
// licence payante en prod.

import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Excalidraw } from '@excalidraw/excalidraw'
import '@excalidraw/excalidraw/index.css'
import { Save, X } from 'lucide-react'

import { showToast } from '../ui/dialog'
import { fetchDiagramme, saveDiagramme } from './api'

type Ctx = { apiBase: string; getToken: () => string | null }

// Type minimal pour l'API imperative Excalidraw. On utilise structural
// typing pour rester tolerant aux petites variations d'API entre
// versions du package.
type ExcalidrawAPI = {
  getSceneElements: () => readonly unknown[]
  getAppState: () => Record<string, unknown>
  getFiles: () => Record<string, unknown>
}


export default function DiagrammeEditor({
  ctx, idProcess, readonly, onClose,
}: {
  ctx: Ctx
  idProcess: string
  readonly: boolean
  onClose: () => void
}) {
  const apiRef = useRef<ExcalidrawAPI | null>(null)
  const dirtyRef = useRef(false)
  const [saving, setSaving] = useState(false)
  const [dirtyTick, setDirtyTick] = useState(0)
  const [initialData, setInitialData] = useState<null | {
    elements: unknown[]
    appState: Record<string, unknown>
    files: Record<string, unknown>
  }>(null)
  const [loading, setLoading] = useState(true)

  // Charge le JSON existant AVANT de monter Excalidraw. initialData
  // n'est pas dynamique — le composant n'est monte qu'apres le fetch.
  useEffect(() => {
    let cancelled = false
    void (async () => {
      const r = await fetchDiagramme(ctx, idProcess)
      if (cancelled) return
      const json = r?.json || ''
      if (json) {
        try {
          const data = JSON.parse(json)
          setInitialData({
            elements: data.elements || [],
            appState: {
              ...(data.appState || {}),
              // Excalidraw exige que collaborators soit un Map, pas un
              // objet plain — le JSON.parse le remet en obj, on reset.
              collaborators: new Map(),
            },
            files: data.files || {},
          })
        } catch (e) {
          console.warn('diagramme JSON invalide', e)
          setInitialData({ elements: [], appState: {}, files: {} })
        }
      } else {
        setInitialData({ elements: [], appState: {}, files: {} })
      }
      setLoading(false)
    })()
    return () => { cancelled = true }
  }, [ctx, idProcess])

  // ESC = close (confirmation si dirty)
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
    const api = apiRef.current
    console.log('[Diagramme] save clicked', { hasApi: !!api, saving, dirty: dirtyRef.current })
    if (!api) {
      showToast("API Excalidraw non initialisée", 'error')
      return
    }
    if (saving) return
    setSaving(true)
    try {
      const appState = { ...api.getAppState() }
      delete (appState as Record<string, unknown>).collaborators
      const payload = {
        elements: api.getSceneElements(),
        appState,
        files: api.getFiles(),
      }
      const jsonStr = JSON.stringify(payload)
      console.log('[Diagramme] payload size', jsonStr.length, 'chars')
      const r = await saveDiagramme(ctx, idProcess, jsonStr)
      console.log('[Diagramme] save response', r)
      if (r?.ok) {
        dirtyRef.current = false
        setDirtyTick(t => t + 1)
        showToast('Diagramme enregistré', 'success')
      } else {
        showToast('Échec sauvegarde (backend a répondu ' + (r ? 'ok=false' : 'null/erreur HTTP') + ')', 'error')
      }
    } catch (e) {
      console.error('[Diagramme] save exception', e)
      showToast(`Échec: ${e instanceof Error ? e.message : String(e)}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const dirty = dirtyRef.current
  void dirtyTick

  const content = (
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
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center text-c-ink-soft">
            Chargement…
          </div>
        )}
        {!loading && initialData && (
          <Excalidraw
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            initialData={initialData as any}
            viewModeEnabled={readonly}
            excalidrawAPI={(api) => {
              console.log('[Diagramme] excalidrawAPI ready', !!api)
              apiRef.current = api as ExcalidrawAPI
            }}
            onChange={() => {
              if (!dirtyRef.current) {
                console.log('[Diagramme] 1st onChange -> dirty=true')
                dirtyRef.current = true
                setDirtyTick(t => t + 1)
              }
            }}
            UIOptions={{
              canvasActions: {
                saveToActiveFile: false,
                loadScene: false,
                export: { saveFileToDisk: false },
              },
            }}
          />
        )}
      </div>
    </div>
  )

  return createPortal(content, document.body)
}
