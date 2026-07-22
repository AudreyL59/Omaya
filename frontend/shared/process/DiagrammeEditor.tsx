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
  // Signature (id:version) des elements au dernier save. Sert a distinguer
  // les vrais onChange (elements modifies par l'utilisateur) des onChange
  // internes d'Excalidraw (viewport, recalibrage, etc.) qui suivent parfois
  // le save et remettaient a tort dirty=true.
  const savedSigRef = useRef<string>('')
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
      const r = await saveDiagramme(ctx, idProcess, jsonStr)
      if (r?.ok) {
        savedSigRef.current = elementsSig(payload.elements)
        dirtyRef.current = false
        setDirtyTick(t => t + 1)
        showToast('Diagramme enregistré', 'success')
      } else {
        showToast('Échec sauvegarde (backend a répondu ' + (r ? 'ok=false' : 'null/erreur HTTP') + ')', 'error')
      }
    } catch (e) {
      console.warn('[Diagramme] save exception', e)
      showToast(`Échec: ${e instanceof Error ? e.message : String(e)}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  // Signature stable des elements Excalidraw : detecte les vraies
  // modifs (add/remove/edit) via id + numero de version. Ignore les
  // onChange 'a vide' (viewport, hover, etc.) qui n'ont pas touche
  // aux elements du dessin.
  function elementsSig(elements: readonly unknown[]): string {
    return (elements || []).map(e => {
      const el = e as { id?: string; version?: number }
      return `${el.id || '?'}:${el.version ?? 0}`
    }).join(',')
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
              apiRef.current = api as ExcalidrawAPI
              // Signature initiale des elements charges (post-load)
              savedSigRef.current = elementsSig(api.getSceneElements())
            }}
            onChange={(elements) => {
              // Ignore les onChange internes d'Excalidraw : on ne
              // marque dirty QUE si la signature (id:version) des
              // elements a change vs la derniere sauvegarde.
              const sig = elementsSig(elements)
              if (sig === savedSigRef.current) return
              if (!dirtyRef.current) {
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
