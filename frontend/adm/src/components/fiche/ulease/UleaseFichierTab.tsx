/**
 * Sous-onglet 'Fichier Conducteur' de l'onglet Ulease.
 *
 * Listing FTP /ulease/Conducteurs/{idconducteur}/ + actions :
 *  - Ajouter un fichier (upload)
 *  - Télécharger la sélection (multi)
 *  - Supprimer la sélection (multi)
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { Download, Loader2, Trash2, Upload } from 'lucide-react'

import { getToken } from '@/api'
import { showConfirm, showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'

interface FileItem {
  nom: string
  taille_mo: number
  date_iso: string
}

interface ListResponse {
  ok: boolean
  srv: string
  etat: string
  files: FileItem[]
}

interface Props {
  idConducteur: string
}

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

export default function UleaseFichierTab({ idConducteur }: Props) {
  const [data, setData] = useState<ListResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const inputRef = useRef<HTMLInputElement>(null)

  const reload = useCallback(async () => {
    if (!idConducteur) return
    setLoading(true)
    try {
      const r = await fetch(`/api/adm/fiche-salarie/ulease/${idConducteur}/files`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const j = (await r.json()) as ListResponse
      setData(j)
      setSelected(new Set())
    } catch (e) {
      showToast(`Échec listing FTP : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [idConducteur])

  useEffect(() => {
    void reload()
  }, [reload])

  const toggle = (nom: string) => {
    setSelected((s) => {
      const n = new Set(s)
      if (n.has(nom)) n.delete(nom)
      else n.add(nom)
      return n
    })
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''
    setBusy(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const r = await fetch(`/api/adm/fiche-salarie/ulease/${idConducteur}/files`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      showToast('Fichier envoyé.', 'success')
      await reload()
    } catch (e) {
      showToast(`Échec upload : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleDownload = async () => {
    if (selected.size === 0) {
      showToast('Sélectionner au moins un fichier.', 'info')
      return
    }
    setBusy(true)
    try {
      for (const nom of selected) {
        const r = await fetch(
          `/api/adm/fiche-salarie/ulease/${idConducteur}/files/download?filename=${encodeURIComponent(nom)}`,
          { headers: { Authorization: `Bearer ${getToken()}` } },
        )
        if (!r.ok) {
          showToast(`Échec téléchargement ${nom} : ${r.status}`, 'error')
          continue
        }
        const blob = await r.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = nom
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
      }
    } finally {
      setBusy(false)
    }
  }

  const handleDelete = async () => {
    if (selected.size === 0) {
      showToast('Sélectionner au moins un fichier.', 'info')
      return
    }
    const ok = await showConfirm({
      title: `Supprimer ${selected.size} fichier(s) ?`,
      message: 'Voulez-vous supprimer les fichiers sélectionnés ?',
      confirmLabel: 'Supprimer',
      variant: 'danger',
    })
    if (!ok) return
    setBusy(true)
    try {
      for (const nom of selected) {
        const r = await fetch(
          `/api/adm/fiche-salarie/ulease/${idConducteur}/files?filename=${encodeURIComponent(nom)}`,
          { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
        )
        if (!r.ok) {
          showToast(`Échec suppression ${nom} : ${r.status}`, 'error')
        }
      }
      await reload()
      showToast('Fichiers supprimés.', 'success')
    } finally {
      setBusy(false)
    }
  }

  const template = '40px 1fr 110px 130px'

  return (
    <div className="flex flex-col gap-2 h-full">
      <div className="flex items-center gap-2 flex-shrink-0">
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          onChange={(e) => void handleUpload(e)}
        />
        <ToolBtn
          icon={Upload}
          label="Ajouter un fichier"
          onClick={() => inputRef.current?.click()}
          primary
          disabled={busy}
        />
        <ToolBtn
          icon={Download}
          label="Télécharger la sélection"
          onClick={() => void handleDownload()}
          disabled={busy || selected.size === 0}
        />
        <ToolBtn
          icon={Trash2}
          label="Supprimer la sélection"
          onClick={() => void handleDelete()}
          disabled={busy || selected.size === 0}
          danger
        />
        {(loading || busy) && (
          <Loader2 className="w-4 h-4 animate-spin ml-2" style={{ color: COLOR_PRIMARY }} />
        )}
      </div>

      <div
        className="flex-1 border rounded overflow-hidden flex flex-col"
        style={{ borderColor: COLOR_BG_SOFT }}
      >
        <div
          className="grid items-center gap-2 px-3 py-2 text-xs font-semibold border-b"
          style={{
            gridTemplateColumns: template,
            color: COLOR_BRUN,
            backgroundColor: COLOR_BG_SOFT,
            borderColor: COLOR_BG_SOFT,
          }}
        >
          <div />
          <div>Nom fichier</div>
          <div className="text-right">Taille (Mo)</div>
          <div>Date</div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {!loading && (data?.files?.length || 0) === 0 && (
            <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
              Aucun fichier dans le dossier.
            </div>
          )}
          {(data?.files || []).map((f) => (
            <div
              key={f.nom}
              className="grid items-center gap-2 px-3 py-1.5 text-xs border-b cursor-pointer"
              style={{
                gridTemplateColumns: template,
                borderColor: COLOR_BG_SOFT,
                color: COLOR_BRUN,
                backgroundColor: selected.has(f.nom) ? COLOR_BG_SOFT : 'white',
              }}
              onClick={() => toggle(f.nom)}
            >
              <div>
                <input
                  type="checkbox"
                  checked={selected.has(f.nom)}
                  onChange={() => toggle(f.nom)}
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
              <div className="truncate" title={f.nom}>
                {f.nom}
              </div>
              <div className="text-right">{f.taille_mo.toFixed(2)}</div>
              <div>{fmtDate(f.date_iso.slice(0, 10))}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Pied : Srv / Etat */}
      <div className="text-xs flex-shrink-0" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
        <div>Srv : {data?.srv || '-'}</div>
        <div>État Connexion : {data?.etat || '-'}</div>
      </div>
    </div>
  )
}

function ToolBtn({
  icon: Icon,
  label,
  onClick,
  disabled,
  primary,
  danger,
}: {
  icon: typeof Upload
  label: string
  onClick: () => void
  disabled?: boolean
  primary?: boolean
  danger?: boolean
}) {
  const color = primary ? 'white' : danger ? '#B91C1C' : COLOR_PRIMARY
  const bg = primary ? COLOR_PRIMARY : 'white'
  const border = primary ? COLOR_PRIMARY : danger ? '#B91C1C' : COLOR_PRIMARY
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded border disabled:opacity-40"
      style={{ backgroundColor: bg, color, borderColor: border }}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  )
}
