import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Building2, ClipboardPaste, Download, FolderOpen, Loader2, Save, Send,
  Upload, User,
} from 'lucide-react'

import type { FIProps } from './index'

// FI_FactDistrib (type 28) — Facturation Distrib.
export default function FIFactDistrib({
  apiBase, getToken, idTicket, onClose,
}: FIProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const [montant, setMontant] = useState(0)
  const [dateVirement, setDateVirement] = useState('')
  const [memo, setMemo] = useState('')
  const [preuveFile, setPreuveFile] = useState<File | null>(null)
  const [preuveUrl, setPreuveUrl] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const reload = useCallback(() => {
    setLoading(true)
    fetch(`${apiBase}/tickets/${idTicket}/form`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d) => {
        const dd = d?.data?.found ? d.data : null
        setData(dd)
        if (dd) {
          setMontant(Number(dd.montant || 0))
          setDateVirement(dd.date_virement || '')
        }
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase, idTicket])

  useEffect(() => {
    reload()
  }, [reload])

  const post = async (body: any): Promise<any> => {
    setSaving(true)
    try {
      const resp = await fetch(`${apiBase}/tickets/${idTicket}/form`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(body),
      })
      const j = await resp.json().catch(() => null)
      if (!resp.ok) {
        window.alert(`Erreur : ${j?.detail || resp.status}`)
        return null
      }
      return j ?? {}
    } catch {
      window.alert('Erreur réseau.')
      return null
    } finally {
      setSaving(false)
    }
  }

  const fetchBlob = async (nom: string): Promise<Blob | null> => {
    try {
      const resp = await fetch(
        `${apiBase}/tickets/${idTicket}/form/file?name=${encodeURIComponent(nom)}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!resp.ok) {
        window.alert(`Fichier introuvable : ${nom}`)
        return null
      }
      return await resp.blob()
    } catch {
      window.alert('Erreur réseau (fichier).')
      return null
    }
  }

  const setPreuve = (file: File | null) => {
    setPreuveFile(file)
    setPreuveUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return file ? URL.createObjectURL(file) : ''
    })
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-c-ink-icon animate-spin" />
      </div>
    )
  }
  if (!data) {
    return (
      <div className="h-full flex items-center justify-center text-c-ink-faint text-sm">
        Aucune demande de facturation pour ce ticket.
      </div>
    )
  }

  const suivi: any[] = data.suivi_adm || []
  const fmt = (n: number) =>
    `${(n || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`
  const fmtDate = (iso: string) => {
    if (!iso) return ''
    const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/)
    if (m) return `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}`
    if (iso.length >= 10) return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
    return iso
  }

  const enregistrer = async () => {
    const r = await post({
      action: 'enregistrer', montant, date_virement: dateVirement,
    })
    if (r) window.alert('Informations enregistrées')
  }

  const ouvrirFacture = async () => {
    if (!data.fic_facture) {
      window.alert('Aucune facture.')
      return
    }
    const blob = await fetchBlob(data.fic_facture)
    if (blob) window.open(URL.createObjectURL(blob), '_blank')
  }

  const ouvrirPreuve = async () => {
    if (!data.fic_preuve) return
    const blob = await fetchBlob(data.fic_preuve)
    if (blob) window.open(URL.createObjectURL(blob), '_blank')
  }

  const collerScreen = async () => {
    try {
      const items = await (navigator.clipboard as any).read()
      for (const item of items) {
        const type = item.types.find((t: string) => t.startsWith('image/'))
        if (type) {
          const blob = await item.getType(type)
          const ext = type.split('/')[1] || 'png'
          setPreuve(new File([blob], `screen.${ext}`, { type }))
          return
        }
      }
      window.alert('Aucune image dans le presse-papier.')
    } catch {
      window.alert(
        'Impossible de lire le presse-papier. Utilisez « Choisir un fichier » ' +
          'ou collez (Ctrl+V) dans la zone d\'aperçu.',
      )
    }
  }

  const chargerPreuve = async () => {
    if (!dateVirement) {
      window.alert('La date de virement est obligatoire.')
      return
    }
    if (!preuveFile) {
      window.alert('Sélectionnez ou collez une preuve de virement.')
      return
    }
    if (
      !window.confirm(
        'Charger la preuve de virement clôturera le ticket. Continuer ?',
      )
    )
      return
    // 1. Enregistre montant + date avant l'upload (cf. SaveTicket WinDev)
    const r1 = await post({
      action: 'enregistrer', montant, date_virement: dateVirement,
    })
    if (!r1) return
    // 2. Upload de la preuve (→ FTP + clôture côté backend)
    setSaving(true)
    try {
      const fd = new FormData()
      fd.append('file', preuveFile)
      const resp = await fetch(`${apiBase}/tickets/${idTicket}/form/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      })
      const j = await resp.json().catch(() => null)
      if (!resp.ok || j?.ok === false) {
        window.alert(`Erreur : ${j?.error || j?.detail || resp.status}`)
        return
      }
      window.alert('Preuve chargée, ticket clôturé.')
      onClose?.()
    } catch {
      window.alert('Erreur réseau (upload).')
    } finally {
      setSaving(false)
    }
  }

  const ajouterMemo = async () => {
    if (!memo.trim()) return
    const r = await post({ action: 'add_memo', message: memo })
    if (r) {
      setMemo('')
      setData((d: any) => ({ ...d, suivi_adm: r.suivi_adm || d.suivi_adm }))
      if (r.mail_result) window.alert(r.mail_result)
    }
  }

  return (
    <div className="space-y-4">
      {/* En-tête société / gérant */}
      <div className="space-y-1">
        <div className="flex items-center gap-2 text-sm">
          <Building2 className="w-4 h-4 text-c-ink-icon" />
          <span className="text-c-ink font-semibold">{data.lib_ste || '—'}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <User className="w-4 h-4 text-c-ink-icon" />
          <span className="text-c-ink">{data.lib_gerant || '—'}</span>
        </div>
      </div>

      {/* Montant + Date de virement */}
      <div className="flex items-end gap-4 flex-wrap">
        <label className="block text-sm">
          <span className="text-c-ink-soft">Montant</span>
          <div className="mt-1 flex items-center gap-2">
            <input
              type="number"
              min={0}
              step="0.01"
              value={montant}
              onChange={(e) => setMontant(Math.max(0, Number(e.target.value)))}
              className="w-36 px-2 py-1 border border-c-line-strong rounded-md text-sm text-right"
            />
            <span className="text-c-ink-soft text-sm">€</span>
          </div>
        </label>
        <label className="block text-sm">
          <span className="text-c-ink-soft">Date de Virement</span>
          <input
            type="date"
            value={dateVirement}
            onChange={(e) => setDateVirement(e.target.value)}
            className="mt-1 block px-2 py-1 border border-c-line-strong rounded-md text-sm"
          />
        </label>
        <button
          onClick={enregistrer}
          disabled={saving}
          className="ml-auto flex items-center gap-2 px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          Enregistrer les infos ticket
        </button>
      </div>

      {/* Facture + preuve de virement */}
      <div className="flex gap-4 flex-wrap items-start border-t border-c-line pt-3">
        <div className="flex flex-col gap-2">
          <button
            onClick={ouvrirFacture}
            className="flex items-center gap-2 text-sm text-c-brand hover:underline"
          >
            <FolderOpen className="w-4 h-4" />
            Ouvrir la facture
          </button>

          {data.a_preuve ? (
            <button
              onClick={ouvrirPreuve}
              className="flex items-center gap-2 text-sm text-c-brand hover:underline"
            >
              <Download className="w-4 h-4" />
              Ouvrir la preuve de virement
            </button>
          ) : (
            <>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center gap-2 text-sm text-c-brand hover:underline"
              >
                <Upload className="w-4 h-4" />
                Choisir un fichier
              </button>
              <button
                onClick={collerScreen}
                className="flex items-center gap-2 text-sm text-c-brand hover:underline"
              >
                <ClipboardPaste className="w-4 h-4" />
                Coller le screen
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,application/pdf"
                className="hidden"
                onChange={(e) => setPreuve(e.target.files?.[0] || null)}
              />
            </>
          )}
        </div>

        {/* Aperçu de la preuve (zone de paste) */}
        {data.a_preuve ? (
          <div className="flex-1 min-w-[200px] text-sm bg-c-brand-soft text-c-brand-strong rounded-lg px-3 py-2">
            ✓ Preuve de virement chargée — ticket clôturé.
          </div>
        ) : (
          <div
            onPaste={(e) => {
              const f = e.clipboardData.files?.[0]
              if (f) setPreuve(f)
            }}
            className="flex-1 min-w-[200px] min-h-[120px] border-2 border-dashed border-c-line-strong rounded-lg flex items-center justify-center overflow-hidden"
          >
            {preuveUrl ? (
              <img src={preuveUrl} alt="preuve" className="max-h-[200px] object-contain" />
            ) : (
              <span className="text-c-ink-faint text-sm px-2 text-center">
                Aperçu de la preuve (Ctrl+V pour coller une image)
              </span>
            )}
          </div>
        )}
      </div>

      {!data.a_preuve && (
        <button
          onClick={chargerPreuve}
          disabled={saving || !preuveFile}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
        >
          <Download className="w-4 h-4" />
          Charger la preuve de virement (clôture le ticket)
        </button>
      )}

      {/* Suivi ADM */}
      <div className="border-t border-c-line pt-3">
        <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide mb-2">
          Suivi ADM
        </h3>
        <div className="border border-c-line rounded-lg overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-c-surface-soft text-c-ink-soft text-left">
              <tr>
                <th className="px-2 py-2 w-36">Déposé le</th>
                <th className="px-2 py-2 w-40">Par</th>
                <th className="px-2 py-2">Message</th>
              </tr>
            </thead>
            <tbody>
              {suivi.length === 0 ? (
                <tr>
                  <td colSpan={3} className="px-2 py-3 text-center text-c-ink-faint">
                    Aucun mémo.
                  </td>
                </tr>
              ) : (
                suivi.map((s) => (
                  <tr key={s.id} className="border-t border-c-line align-top">
                    <td className="px-2 py-1.5 whitespace-nowrap">{fmtDate(s.depose_le)}</td>
                    <td className="px-2 py-1.5">{s.par}</td>
                    <td className="px-2 py-1.5 whitespace-pre-wrap">{s.message}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Saisie d'un nouveau mémo */}
        <div className="flex items-end gap-2 mt-2">
          <label className="block text-sm flex-1">
            <span className="text-c-ink-soft">Saisir un nouveau mémo</span>
            <input
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') ajouterMemo()
              }}
              className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
            />
          </label>
          <button
            onClick={ajouterMemo}
            disabled={saving || !memo.trim()}
            title="Déposer le mémo"
            className="p-2 rounded-md bg-c-brand text-white hover:brightness-110 disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
