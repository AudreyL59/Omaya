// Rendu inline des pieces jointes dans les bulles de message.
// - Images : miniature cliquable -> modal fullscreen
// - Audio  : lecteur natif
// - Videos : miniature avec bouton play -> modal fullscreen (video native)
// - Autres : icone typee par extension + telechargement authentifie
//
// Toutes les URLs sont protegees par Bearer token : on fetch en blob puis
// createObjectURL, sinon <img>/<audio>/<video> se prennent un 401.

import { useEffect, useState } from 'react'
import {
  Download, File, FileArchive, FileAudio, FileImage, FileSpreadsheet,
  FileText, FileVideo, Play, X,
} from 'lucide-react'

import { AuthImage } from '../ui/AuthImage'
import { fichierUrl } from './api'
import type { DialoguePJ } from './types'

type Ctx = { apiBase: string; getToken: () => string | null }

// ---------------------------------------------------------------------------
//  Type de fichier + icone
// ---------------------------------------------------------------------------

type Kind = 'image' | 'audio' | 'video' | 'pdf' | 'doc' | 'xls' | 'ppt'
          | 'archive' | 'text' | 'other'

const kindOf = (name: string): Kind => {
  const ext = (name.split('.').pop() || '').toLowerCase()
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext)) return 'image'
  if (['mp3', 'wav', 'm4a', 'aac', 'ogg', 'webm', 'flac'].includes(ext)) return 'audio'
  if (['mp4', 'mov', 'avi', 'mkv', 'webm', 'wmv', 'flv'].includes(ext)) return 'video'
  if (ext === 'pdf') return 'pdf'
  if (['doc', 'docx', 'odt', 'rtf'].includes(ext)) return 'doc'
  if (['xls', 'xlsx', 'ods', 'csv'].includes(ext)) return 'xls'
  if (['ppt', 'pptx', 'odp'].includes(ext)) return 'ppt'
  if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) return 'archive'
  if (['txt', 'log', 'md', 'json', 'xml'].includes(ext)) return 'text'
  return 'other'
}

const iconFor = (k: Kind) => {
  const cls = 'w-4 h-4'
  switch (k) {
    case 'image': return <FileImage className={`${cls} text-blue-600`} />
    case 'audio': return <FileAudio className={`${cls} text-purple-600`} />
    case 'video': return <FileVideo className={`${cls} text-pink-600`} />
    case 'pdf':   return <FileText className={`${cls} text-red-600`} />
    case 'doc':   return <FileText className={`${cls} text-blue-700`} />
    case 'xls':   return <FileSpreadsheet className={`${cls} text-green-600`} />
    case 'ppt':   return <FileText className={`${cls} text-orange-600`} />
    case 'archive': return <FileArchive className={`${cls} text-gray-600`} />
    case 'text':  return <FileText className={`${cls} text-gray-500`} />
    default:      return <File className={`${cls} text-gray-500`} />
  }
}

// ---------------------------------------------------------------------------
//  Hook : fetch blob authentifie -> object URL
// ---------------------------------------------------------------------------

function useAuthBlob(url: string, getToken: () => string | null) {
  const [blobUrl, setBlobUrl] = useState<string>('')
  const [error, setError] = useState(false)
  useEffect(() => {
    let cancelled = false
    let current = ''
    setError(false); setBlobUrl('')
    void (async () => {
      try {
        const r = await fetch(url, {
          headers: { Authorization: `Bearer ${getToken()}` },
        })
        if (!r.ok) throw new Error(String(r.status))
        const b = await r.blob()
        if (cancelled) return
        current = URL.createObjectURL(b)
        setBlobUrl(current)
      } catch {
        if (!cancelled) setError(true)
      }
    })()
    return () => {
      cancelled = true
      if (current) URL.revokeObjectURL(current)
    }
  }, [url, getToken])
  return { blobUrl, error }
}

// ---------------------------------------------------------------------------
//  Modal fullscreen (image / video)
// ---------------------------------------------------------------------------

function PreviewModal({ blobUrl, filename, kind, onClose }: {
  blobUrl: string; filename: string; kind: 'image' | 'video'; onClose: () => void
}) {
  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onEsc)
    return () => window.removeEventListener('keydown', onEsc)
  }, [onClose])
  return (
    <div className="fixed inset-0 z-[100] bg-black/80 flex items-center justify-center p-4"
      onClick={onClose}>
      <button onClick={onClose}
        className="absolute top-4 right-4 text-white hover:bg-white/10 rounded p-2">
        <X className="w-6 h-6" />
      </button>
      <div className="absolute top-4 left-4 text-white text-sm bg-black/40 px-3 py-1 rounded">
        {filename}
      </div>
      {kind === 'image' ? (
        <img src={blobUrl} alt={filename}
          className="max-w-full max-h-full object-contain"
          onClick={e => e.stopPropagation()} />
      ) : (
        <video src={blobUrl} controls autoPlay
          className="max-w-full max-h-full"
          onClick={e => e.stopPropagation()} />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
//  Vignette image (avec fallback carte-icone si fetch echoue)
// ---------------------------------------------------------------------------

function ImageThumb({ url, filename, getToken, onOpen }: {
  url: string; filename: string
  getToken: () => string | null
  onOpen: () => void
}) {
  const { blobUrl, error } = useAuthBlob(url, getToken)
  // Chargement en cours
  if (!blobUrl && !error) {
    return (
      <div className="inline-flex items-center gap-2 px-2 py-1 text-xs bg-white border border-c-line-soft rounded">
        <FileImage className="w-4 h-4 text-blue-600" />
        <span className="text-c-ink-soft">Chargement…</span>
      </div>
    )
  }
  // Vignette OK
  if (blobUrl) {
    return (
      <button onClick={onOpen}
        className="block max-w-full text-left group relative">
        <img src={blobUrl} alt={filename}
          className="max-h-48 rounded border border-c-line-soft cursor-zoom-in
                     group-hover:brightness-95 transition" />
      </button>
    )
  }
  // Erreur fetch : carte cliquable qui tente quand meme d'ouvrir le modal
  return (
    <button onClick={onOpen}
      className="inline-flex items-center gap-2 px-2 py-1.5 text-xs bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 max-w-full">
      <FileImage className="w-5 h-5 text-blue-600 shrink-0" />
      <div className="min-w-0 text-left">
        <div className="truncate max-w-[240px] font-medium" title={filename}>{filename}</div>
        <div className="text-[10px] text-c-ink-soft">Image · introuvable sur le serveur</div>
      </div>
    </button>
  )
}

// ---------------------------------------------------------------------------
//  Vignette video (poster derriere un play button)
// ---------------------------------------------------------------------------

function VideoThumb({ url, getToken, onOpen }: {
  url: string; getToken: () => string | null; onOpen: () => void
}) {
  const { blobUrl } = useAuthBlob(url, getToken)
  return (
    <button onClick={onOpen}
      className="relative group max-w-full block rounded overflow-hidden border border-c-line-soft bg-gray-900">
      {blobUrl ? (
        <video src={blobUrl} preload="metadata"
          className="max-h-48 w-auto max-w-full block" />
      ) : (
        <div className="h-32 w-56 flex items-center justify-center text-white/50">
          Chargement…
        </div>
      )}
      <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/40 transition">
        <Play className="w-12 h-12 text-white drop-shadow-lg" fill="currentColor" />
      </div>
    </button>
  )
}

// ---------------------------------------------------------------------------
//  Lien telechargement authentifie
// ---------------------------------------------------------------------------

function DownloadLink({ url, filename, kind, getToken }: {
  url: string; filename: string; kind: Kind
  getToken: () => string | null
}) {
  const [busy, setBusy] = useState(false)
  const download = async (e: React.MouseEvent) => {
    e.preventDefault()
    if (busy) return
    setBusy(true)
    try {
      const r = await fetch(url, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const blob = await r.blob()
      const objUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objUrl; a.download = filename
      document.body.appendChild(a); a.click(); document.body.removeChild(a)
      setTimeout(() => URL.revokeObjectURL(objUrl), 1000)
    } catch { /* ignore */ }
    setBusy(false)
  }
  return (
    <a href="#" onClick={download}
      className="inline-flex items-center gap-1.5 px-2 py-1 text-xs bg-white border border-c-line rounded hover:bg-gray-50 max-w-full">
      {iconFor(kind)}
      <span className="truncate max-w-[240px]" title={filename}>{filename}</span>
      <Download className={`w-3 h-3 text-c-ink-soft ${busy ? 'animate-pulse' : ''}`} />
    </a>
  )
}

// ---------------------------------------------------------------------------
//  Composant principal (utilise par DialoguesPage)
// ---------------------------------------------------------------------------

export function PjInline({ pj, ctx, idDialogue }: {
  pj: DialoguePJ; ctx: Ctx; idDialogue: string
}) {
  const url = fichierUrl(ctx, idDialogue, pj.NomFic)
  const kind = kindOf(pj.NomFic)
  const [preview, setPreview] = useState<null | 'image' | 'video'>(null)
  const audio = useAuthBlob(kind === 'audio' ? url : '', ctx.getToken)
  const modalBlob = useAuthBlob(preview ? url : '', ctx.getToken)

  if (kind === 'image') {
    return (
      <>
        <ImageThumb url={url} filename={pj.NomFic}
          getToken={ctx.getToken}
          onOpen={() => setPreview('image')} />
        {preview === 'image' && (
          modalBlob.blobUrl ? (
            <PreviewModal blobUrl={modalBlob.blobUrl} filename={pj.NomFic}
              kind="image" onClose={() => setPreview(null)} />
          ) : modalBlob.error ? (
            <div className="fixed inset-0 z-[100] bg-black/80 flex items-center justify-center p-4"
              onClick={() => setPreview(null)}>
              <div className="bg-white rounded p-4 max-w-sm text-sm text-center">
                <p className="mb-2">Impossible de charger l'image.</p>
                <p className="text-xs text-c-ink-soft break-all">{pj.NomFic}</p>
                <button onClick={() => setPreview(null)}
                  className="mt-3 px-3 py-1 bg-gray-900 text-white rounded text-xs">Fermer</button>
              </div>
            </div>
          ) : null
        )}
      </>
    )
  }

  if (kind === 'audio') {
    return audio.blobUrl
      ? <audio controls src={audio.blobUrl} className="max-w-full h-8" />
      : <span className="text-xs text-c-ink-faint">Chargement audio…</span>
  }

  if (kind === 'video') {
    return (
      <>
        <VideoThumb url={url} getToken={ctx.getToken}
          onOpen={() => setPreview('video')} />
        {preview === 'video' && modalBlob.blobUrl && (
          <PreviewModal blobUrl={modalBlob.blobUrl} filename={pj.NomFic}
            kind="video" onClose={() => setPreview(null)} />
        )}
      </>
    )
  }

  // Autre : icone + telechargement
  return <DownloadLink url={url} filename={pj.NomFic} kind={kind}
                       getToken={ctx.getToken} />
}
