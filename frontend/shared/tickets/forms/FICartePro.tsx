import { useCallback, useEffect, useRef, useState } from 'react'
import { Download, Loader2, Printer, Save, Upload } from 'lucide-react'

import type { FIProps } from './index'

interface LigneCartePro {
  id: string
  id_salarie: string
  nom_prenom: string
  date_embauche: string
  entite: string
  num_suivi: string
  photo_data_url: string
}

export default function FICartePro({ apiBase, getToken, idTicket }: FIProps) {
  const [lignes, setLignes] = useState<LigneCartePro[]>([])
  const [loading, setLoading] = useState(true)
  const [selId, setSelId] = useState<string | null>(null)
  const [numSuivi, setNumSuivi] = useState('')
  const [photoUrl, setPhotoUrl] = useState('') // affichée (existante ou nouvelle)
  const [photoB64, setPhotoB64] = useState('') // nouvelle photo à envoyer
  const [saving, setSaving] = useState(false)
  const [printing, setPrinting] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const reload = useCallback(() => {
    setLoading(true)
    fetch(`${apiBase}/tickets/${idTicket}/form`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d) => {
        const ls: LigneCartePro[] = d?.data?.lignes || []
        setLignes(ls)
        if (ls.length > 0) select(ls[0])
        else setSelId(null)
      })
      .catch(() => setLignes([]))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase, idTicket])

  useEffect(() => {
    reload()
  }, [reload])

  const select = (l: LigneCartePro) => {
    setSelId(l.id)
    setNumSuivi(l.num_suivi || '')
    setPhotoUrl(l.photo_data_url || '')
    setPhotoB64('')
  }

  const onPickFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    const reader = new FileReader()
    reader.onload = () => {
      const url = String(reader.result || '')
      setPhotoUrl(url)
      setPhotoB64(url) // data URL ; le backend strip le préfixe
    }
    reader.readAsDataURL(f)
  }

  const enregistrer = async () => {
    if (!selId) return
    setSaving(true)
    try {
      const resp = await fetch(`${apiBase}/tickets/${idTicket}/form`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id_ligne: selId,
          num_suivi: numSuivi,
          photo_b64: photoB64 || undefined,
        }),
      })
      if (!resp.ok) {
        const e = await resp.json().catch(() => null)
        window.alert(`Erreur : ${e?.detail || resp.status}`)
        return
      }
      reload()
    } catch {
      window.alert('Erreur réseau lors de l’enregistrement.')
    } finally {
      setSaving(false)
    }
  }

  const telechargerPhoto = () => {
    if (!photoUrl) return
    const a = document.createElement('a')
    a.href = photoUrl
    a.download = `cartepro_${selId}.jpg`
    a.click()
  }

  const imprimer = async () => {
    if (!selId) return
    setPrinting(true)
    try {
      const resp = await fetch(
        `${apiBase}/tickets/${idTicket}/form/print?id_ligne=${selId}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!resp.ok) {
        const e = await resp.json().catch(() => null)
        window.alert(`Erreur : ${e?.detail || resp.status}`)
        return
      }
      const blob = await resp.blob()
      window.open(URL.createObjectURL(blob), '_blank')
    } catch {
      window.alert('Erreur réseau lors de l’impression.')
    } finally {
      setPrinting(false)
    }
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-c-ink-icon animate-spin" />
      </div>
    )
  }
  if (lignes.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-c-ink-faint text-sm">
        Aucune demande de carte pro pour ce ticket.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="border border-c-line rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-c-surface-soft text-xs text-c-ink-faint uppercase tracking-wide">
            <tr>
              <th className="px-3 py-2 text-left">Nom Prénom</th>
              <th className="px-3 py-2 text-left w-32">Date Embauche</th>
              <th className="px-3 py-2 text-center w-16">Photo</th>
              <th className="px-3 py-2 text-left">Num de Suivi</th>
              <th className="px-3 py-2 text-left">Entité</th>
            </tr>
          </thead>
          <tbody>
            {lignes.map((l) => (
              <tr
                key={l.id}
                onClick={() => select(l)}
                className={`border-t border-c-line-soft cursor-pointer transition-colors ${
                  selId === l.id ? 'bg-c-brand-soft' : 'hover:bg-c-surface-soft'
                }`}
              >
                <td className="px-3 py-2 text-c-ink">{l.nom_prenom}</td>
                <td className="px-3 py-2 tabular-nums text-c-ink-soft">
                  {fmtDate(l.date_embauche)}
                </td>
                <td className="px-3 py-2 text-center">
                  {l.photo_data_url ? (
                    <img
                      src={l.photo_data_url}
                      alt=""
                      className="w-8 h-8 object-cover rounded inline-block"
                    />
                  ) : (
                    <span className="text-c-ink-faint">—</span>
                  )}
                </td>
                <td className="px-3 py-2 text-c-ink-soft">{l.num_suivi}</td>
                <td className="px-3 py-2 text-c-ink-soft">{l.entite}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selId && (
        <div className="flex gap-6">
          {/* Photo */}
          <div className="flex flex-col items-center gap-2">
            <div className="w-40 h-52 border border-c-line rounded-lg bg-c-surface-soft overflow-hidden flex items-center justify-center">
              {photoUrl ? (
                <img
                  src={photoUrl}
                  alt="Carte pro"
                  className="w-full h-full object-cover"
                />
              ) : (
                <span className="text-xs text-c-ink-faint">Aucune photo</span>
              )}
            </div>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              onChange={onPickFile}
              className="hidden"
            />
            <button
              onClick={() => fileRef.current?.click()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-c-line-strong text-xs text-c-ink hover:bg-c-surface-medium transition-colors"
            >
              <Upload className="w-3.5 h-3.5" />
              Changer la photo
            </button>
          </div>

          {/* Champs + actions */}
          <div className="flex-1 space-y-3 max-w-sm">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-c-ink-soft">Num de Suivi</span>
              <input
                value={numSuivi}
                onChange={(e) => setNumSuivi(e.target.value)}
                className="w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
              />
            </div>
            <div className="flex flex-wrap gap-2 pt-1">
              <button
                onClick={enregistrer}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50 transition-all"
              >
                {saving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                Enregistrer
              </button>
              <button
                onClick={telechargerPhoto}
                disabled={!photoUrl}
                className="flex items-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong text-sm text-c-ink hover:bg-c-surface-medium disabled:opacity-40 transition-colors"
              >
                <Download className="w-4 h-4" />
                Télécharger la photo
              </button>
              <button
                onClick={imprimer}
                disabled={printing}
                className="flex items-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong text-sm text-c-ink hover:bg-c-surface-medium disabled:opacity-50 transition-colors"
              >
                {printing ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Printer className="w-4 h-4" />
                )}
                Imprimer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function fmtDate(iso: string): string {
  if (!iso) return ''
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/)
  return m ? `${m[3]}/${m[2]}/${m[1]}` : iso
}
