/**
 * Slot d'image pour une societe (logo / guimmick / cachet_cial /
 * gerant_paraphe / gerant_signature).
 *
 * Cf boutons WinDev Logo/Guimmick/Cachet Cial/Paraphe/Signature :
 * fSelecteurImage + confirmation 'Voulez-vous associer cette image ?'
 * -> UPDATE colonne bytea.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { ImageIcon, Loader2, Upload } from 'lucide-react'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'

const API_BASE = '/api/adm'

type Champ =
  | 'logo' | 'guimmick' | 'cachet_cial'
  | 'gerant_paraphe' | 'gerant_signature'

interface Props {
  idSociete: string        // bigint WinDev -> string pour eviter perte precision JS
  champ: Champ
  label: string
  hasImage: boolean
  disabled?: boolean       // ex: modal en creation (id_societe=0)
  onChanged?: () => void   // callback refresh parent
}

const LABEL_TITRES: Record<Champ, string> = {
  logo: 'Nouveau LOGO',
  guimmick: 'Nouveau GUIMMICK',
  cachet_cial: 'Nouveau Cachet Cial',
  gerant_paraphe: 'Nouvelle PARAPHE',
  gerant_signature: 'Nouvelle SIGNATURE',
}

export default function SocieteImageSlot({
  idSociete, champ, label, hasImage, disabled, onChanged,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [rev, setRev] = useState(0)   // busts cache apres upload
  const [blobUrl, setBlobUrl] = useState<string>('')

  // Charge l'image via fetch() authentifie (JWT dans header Authorization)
  // et cree un blob URL local. <img src=...> ne peut pas envoyer de
  // header Authorization tout seul, donc si on met l'URL API en direct
  // le serveur repond 401 et le browser affiche un defi Basic Auth.
  const loadImage = useCallback(async () => {
    if (!hasImage && rev === 0) { setBlobUrl(''); return }
    try {
      const r = await fetch(
        `${API_BASE}/societes/${idSociete}/image/${champ}?v=${rev}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) { setBlobUrl(''); return }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      setBlobUrl(prev => { if (prev) URL.revokeObjectURL(prev); return url })
    } catch {
      setBlobUrl('')
    }
  }, [idSociete, champ, hasImage, rev])

  useEffect(() => {
    void loadImage()
    return () => {
      setBlobUrl(prev => { if (prev) URL.revokeObjectURL(prev); return '' })
    }
  }, [loadImage])

  const upload = async (file: File) => {
    const ok = await showConfirm({
      title: LABEL_TITRES[champ],
      message: 'Voulez-vous associer cette image ?',
    })
    if (!ok) return
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const r = await fetch(
        `${API_BASE}/societes/${idSociete}/image/${champ}`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
          body: fd,
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      showToast(`${label} enregistré`, 'success')
      setRev(v => v + 1)
      onChanged?.()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setUploading(false) }
  }

  return (
    <div className="flex flex-col items-center gap-1 p-3 bg-c-surface-soft rounded-lg border border-c-line">
      <div className="text-[10px] text-c-ink-faint uppercase tracking-wide">
        {label}
      </div>
      <div className="w-32 h-24 bg-white border border-c-line rounded flex items-center justify-center overflow-hidden">
        {uploading ? (
          <Loader2 className="w-5 h-5 animate-spin text-c-brand" />
        ) : blobUrl ? (
          <img src={blobUrl} alt={label}
            className="max-w-full max-h-full object-contain" />
        ) : (
          <ImageIcon className="w-8 h-8 text-c-ink-faint-2" />
        )}
      </div>
      <input ref={inputRef} type="file"
        accept="image/*"
        onChange={(e) => {
          const f = e.target.files?.[0]
          if (f) void upload(f)
          e.target.value = ''
        }}
        className="hidden" />
      <button type="button"
        onClick={() => inputRef.current?.click()}
        disabled={disabled || uploading}
        className="flex items-center gap-1 px-2 py-1 rounded text-c-brand hover:bg-c-brand/10 text-[10px] disabled:opacity-30">
        <Upload className="w-3 h-3" />
        {hasImage || rev > 0 ? 'Changer' : 'Ajouter'}
      </button>
    </div>
  )
}
