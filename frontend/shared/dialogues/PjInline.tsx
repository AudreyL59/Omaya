// Rendu inline des pieces jointes dans les bulles de message.
//
// Les fichiers sont exposes en HTTP statique par IIS a l'URL
// DOCS_URL/DocConv/{idDialogue}/{nomFic} (backend renseigne pj.Url).
// Pas d'auth Bearer necessaire : <img>/<audio>/<video> chargent
// directement l'URL.
//
// Types de rendu :
// - Image : miniature cliquable -> modal fullscreen
// - Audio : lecteur natif
// - Video : miniature avec bouton play -> modal fullscreen
// - Autres : icone typee par extension + telechargement

import { useEffect, useState } from 'react'
import {
  Download, File, FileArchive, FileAudio, FileImage, FileSpreadsheet,
  FileText, FileVideo, Play, X,
} from 'lucide-react'

import { fichierUrl } from './api'
import type { DialoguePJ } from './types'

type Ctx = { apiBase: string; getToken: () => string | null }

// URL a utiliser : celle du backend (statique) si presente, sinon
// endpoint authentifie de fallback.
const resolveUrl = (pj: DialoguePJ, ctx: Ctx, idDialogue: string) =>
  pj.Url || fichierUrl(ctx, idDialogue, pj.NomFic)

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
//  Modal fullscreen (image / video)
// ---------------------------------------------------------------------------

function PreviewModal({ url, filename, kind, onClose }: {
  url: string; filename: string; kind: 'image' | 'video'; onClose: () => void
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
      <div className="absolute top-4 left-4 text-white text-sm bg-black/40 px-3 py-1 rounded max-w-[70%] truncate">
        {filename}
      </div>
      {kind === 'image' ? (
        <img src={url} alt={filename}
          className="max-w-full max-h-full object-contain"
          onClick={e => e.stopPropagation()} />
      ) : (
        <video src={url} controls autoPlay
          className="max-w-full max-h-full"
          onClick={e => e.stopPropagation()} />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
//  Vignette image
// ---------------------------------------------------------------------------

function ImageThumb({ url, filename, onOpen }: {
  url: string; filename: string; onOpen: () => void
}) {
  const [error, setError] = useState(false)
  if (error) {
    return (
      <button onClick={onOpen}
        className="inline-flex items-center gap-2 px-2 py-1.5 text-xs bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 max-w-full">
        <FileImage className="w-5 h-5 text-blue-600 shrink-0" />
        <div className="min-w-0 text-left">
          <div className="truncate max-w-[240px] font-medium" title={filename}>{filename}</div>
          <div className="text-[10px] text-c-ink-soft">Image · introuvable</div>
        </div>
      </button>
    )
  }
  return (
    <button onClick={onOpen} className="block max-w-full text-left group">
      <img src={url} alt={filename} onError={() => setError(true)}
        className="max-h-48 rounded border border-c-line-soft cursor-zoom-in
                   group-hover:brightness-95 transition" />
    </button>
  )
}

// ---------------------------------------------------------------------------
//  Vignette video
// ---------------------------------------------------------------------------

function VideoThumb({ url, filename, onOpen }: {
  url: string; filename: string; onOpen: () => void
}) {
  return (
    <button onClick={onOpen}
      className="relative group max-w-full block rounded overflow-hidden border border-c-line-soft bg-gray-900">
      <video src={url} preload="metadata" title={filename}
        className="max-h-48 w-auto max-w-full block" />
      <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/40 transition">
        <Play className="w-12 h-12 text-white drop-shadow-lg" fill="currentColor" />
      </div>
    </button>
  )
}

// ---------------------------------------------------------------------------
//  Lien telechargement
// ---------------------------------------------------------------------------

function DownloadLink({ url, filename, kind }: {
  url: string; filename: string; kind: Kind
}) {
  return (
    <a href={url} download={filename} target="_blank" rel="noreferrer"
      className="inline-flex items-center gap-1.5 px-2 py-1 text-xs bg-white border border-c-line rounded hover:bg-gray-50 max-w-full">
      {iconFor(kind)}
      <span className="truncate max-w-[240px]" title={filename}>{filename}</span>
      <Download className="w-3 h-3 text-c-ink-soft" />
    </a>
  )
}

// ---------------------------------------------------------------------------
//  Composant principal (utilise par DialoguesPage)
// ---------------------------------------------------------------------------

export function PjInline({ pj, ctx, idDialogue }: {
  pj: DialoguePJ; ctx: Ctx; idDialogue: string
}) {
  const url = resolveUrl(pj, ctx, idDialogue)
  const kind = kindOf(pj.NomFic)
  const [preview, setPreview] = useState<null | 'image' | 'video'>(null)

  if (kind === 'image') {
    return (
      <>
        <ImageThumb url={url} filename={pj.NomFic}
          onOpen={() => setPreview('image')} />
        {preview === 'image' && (
          <PreviewModal url={url} filename={pj.NomFic}
            kind="image" onClose={() => setPreview(null)} />
        )}
      </>
    )
  }

  if (kind === 'audio') {
    return <audio controls src={url} className="max-w-full h-8" />
  }

  if (kind === 'video') {
    return (
      <>
        <VideoThumb url={url} filename={pj.NomFic}
          onOpen={() => setPreview('video')} />
        {preview === 'video' && (
          <PreviewModal url={url} filename={pj.NomFic}
            kind="video" onClose={() => setPreview(null)} />
        )}
      </>
    )
  }

  return <DownloadLink url={url} filename={pj.NomFic} kind={kind} />
}
