// Editeur/viewer d'UN diagramme (Excalidraw) d'un process.
// Un diagramme = 1 fichier .excalidraw dans pgt_process_fichier (N par
// process). Stockage : JSON serialise (elements + appState + files)
// dans contenu_fichier bytea.

import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Excalidraw } from '@excalidraw/excalidraw'
import '@excalidraw/excalidraw/index.css'
import { Save, X } from 'lucide-react'

import { showConfirm, showToast } from '../ui/dialog'
import { fetchDiagramme, saveDiagramme } from './api'

type Ctx = { apiBase: string; getToken: () => string | null }

type ExcalidrawAPI = {
  getSceneElements: () => readonly unknown[]
  getAppState: () => Record<string, unknown>
  getFiles: () => Record<string, unknown>
}


export default function DiagrammeEditor({
  ctx, idProcess, idDiagramme, initialTitre, readonly, onClose, onSaved,
}: {
  ctx: Ctx
  idProcess: string
  idDiagramme: string   // '0' si nouveau diagramme
  initialTitre: string  // pour un nouveau : titre par defaut ('Nouveau diagramme')
  readonly: boolean
  onClose: () => void
  onSaved?: (idDiagramme: string) => void
}) {
  const apiRef = useRef<ExcalidrawAPI | null>(null)
  const dirtyRef = useRef(false)
  const savedSigRef = useRef<string>('')
  const [saving, setSaving] = useState(false)
  const [dirtyTick, setDirtyTick] = useState(0)
  const [titre, setTitre] = useState(initialTitre)
  const [idDiaCur, setIdDiaCur] = useState(idDiagramme)
  const [initialData, setInitialData] = useState<null | {
    elements: unknown[]
    appState: Record<string, unknown>
    files: Record<string, unknown>
  }>(null)
  const [loading, setLoading] = useState(true)

  // Charge le JSON existant AVANT de monter Excalidraw.
  useEffect(() => {
    let cancelled = false
    void (async () => {
      // Nouveau diagramme (id = '0') : pas de fetch
      if (!idDiagramme || idDiagramme === '0') {
        if (!cancelled) {
          setInitialData({ elements: [], appState: {}, files: {} })
          setLoading(false)
        }
        return
      }
      const d = await fetchDiagramme(ctx, idDiagramme)
      if (cancelled) return
      if (d?.Titre) setTitre(d.Titre)
      const json = d?.ContenuJson || ''
      if (json) {
        try {
          const data = JSON.parse(json)
          setInitialData({
            elements: data.elements || [],
            appState: {
              ...(data.appState || {}),
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
  }, [ctx, idDiagramme])

  const tryClose = async () => {
    if (dirtyRef.current && !readonly) {
      const ok = await showConfirm({
        title: 'Fermer sans enregistrer ?',
        message: 'Les modifications non sauvegardées seront perdues.',
        confirmLabel: 'Fermer', cancelLabel: 'Annuler',
        variant: 'danger',
      })
      if (!ok) return
    }
    onClose()
  }

  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      void tryClose()
    }
    window.addEventListener('keydown', onEsc)
    return () => window.removeEventListener('keydown', onEsc)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [readonly])

  const save = async () => {
    const api = apiRef.current
    if (!api) {
      showToast("API Excalidraw non initialisée", 'error')
      return
    }
    if (saving) return
    const t = (titre || '').trim() || 'Diagramme'
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
      const r = await saveDiagramme(ctx, {
        IDProcessDiagramme: idDiaCur || '0',
        IDProcess: idProcess,
        Titre: t,
        ContenuJson: jsonStr,
      })
      if (r?.IDProcessDiagramme) {
        savedSigRef.current = elementsSig(payload.elements)
        dirtyRef.current = false
        setDirtyTick(x => x + 1)
        // Si c'etait une creation, on bascule sur l'id retourne pour
        // que les prochains save fassent un UPDATE et non un nouvel INSERT
        if (idDiaCur === '0' || !idDiaCur) setIdDiaCur(r.IDProcessDiagramme)
        onSaved?.(r.IDProcessDiagramme)
        showToast('Diagramme enregistré', 'success')
      } else {
        showToast('Échec sauvegarde', 'error')
      }
    } catch (e) {
      console.warn('[Diagramme] save exception', e)
      showToast(`Échec: ${e instanceof Error ? e.message : String(e)}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const dirty = dirtyRef.current
  void dirtyTick

  function elementsSig(elements: readonly unknown[]): string {
    return (elements || []).map(e => {
      const el = e as { id?: string; version?: number }
      return `${el.id || '?'}:${el.version ?? 0}`
    }).join(',')
  }

  const content = (
    <div style={{ position: 'fixed', inset: 0, zIndex: 95,
                  display: 'flex', flexDirection: 'column',
                  background: '#fff' }}>
      <header className="bg-white border-b border-c-line-soft px-3 py-2 flex items-center gap-2 shrink-0">
        <div className="flex-1 min-w-0 flex items-center gap-2">
          {readonly ? (
            <div className="text-sm font-semibold truncate">
              {titre} <span className="text-xs italic text-c-ink-soft">(lecture seule)</span>
            </div>
          ) : (
            <input value={titre} onChange={e => setTitre(e.target.value)}
              placeholder="Titre du diagramme"
              className="text-sm font-semibold border border-c-line rounded px-2 py-1 bg-white min-w-[240px]" />
          )}
          {dirty && !readonly && (
            <span className="text-xs text-amber-600 italic shrink-0">
              modifications non enregistrées
            </span>
          )}
        </div>
        {!readonly && (
          <button onClick={save} disabled={saving}
            className={`flex items-center gap-1 px-3 py-1.5 rounded text-sm font-semibold ${
              saving
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-c-brand text-white hover:brightness-110'}`}>
            <Save className="w-4 h-4" /> Enregistrer
          </button>
        )}
        <button onClick={() => void tryClose()}
          className="p-2 rounded hover:bg-gray-100">
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
              savedSigRef.current = elementsSig(api.getSceneElements())
            }}
            onChange={(elements) => {
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
