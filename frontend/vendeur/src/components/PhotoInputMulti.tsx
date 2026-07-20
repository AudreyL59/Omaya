/**
 * Composant : selection d'un ou plusieurs fichiers (images / PDF).
 *
 * Remplace le `showPhotoEditorMulti` de Flutter (qui ouvre la camera
 * multi-cliches + editor). Ici l'utilisateur choisit un ou plusieurs
 * fichiers dans son explorateur (pas d'ouverture camera).
 *
 * Utilise pour : CIN, KBIS, Clarification, Lettre resil, Justif...
 * Cf. docs/tickets_call_screens_analysis.md.
 */

import { useRef, useState } from 'react'
import { Loader2, Paperclip, Trash2 } from 'lucide-react'


export interface PhotoInputMultiProps {
  label?: string
  accept?: string          // default: 'image/*'
  multiple?: boolean       // default: true
  disabled?: boolean
  loading?: boolean
  onChange: (files: File[]) => void
}


export default function PhotoInputMulti({
  label = 'Sélectionner des fichiers',
  accept = 'image/*',
  multiple = true,
  disabled,
  loading,
  onChange,
}: PhotoInputMultiProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<File[]>([])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const list = e.target.files
    if (!list) return
    const arr = Array.from(list)
    setFiles(arr)
    onChange(arr)
  }

  const removeAt = (i: number) => {
    const next = files.filter((_, idx) => idx !== i)
    setFiles(next)
    onChange(next)
  }

  return (
    <div className="space-y-2">
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled || loading}
        onChange={handleChange}
        className="hidden"
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={disabled || loading}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-md
                   bg-gray-900 text-white text-sm font-semibold
                   hover:brightness-110 disabled:opacity-60"
      >
        {loading
          ? <Loader2 className="w-4 h-4 animate-spin" />
          : <Paperclip className="w-4 h-4" />}
        {label}
      </button>
      {files.length > 0 && (
        <ul className="text-xs space-y-1">
          {files.map((f, i) => (
            <li key={i}
                className="flex items-center gap-2 border border-c-line-soft rounded px-2 py-1 bg-white">
              <span className="flex-1 truncate">{f.name}</span>
              <span className="text-c-ink-faint tabular-nums">
                {(f.size / 1024).toFixed(0)} kb
              </span>
              <button
                type="button"
                onClick={() => removeAt(i)}
                disabled={disabled || loading}
                className="text-red-600 hover:text-red-800 disabled:opacity-40">
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
