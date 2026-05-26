import { useCallback, useEffect, useRef, useState } from 'react'
import { Loader2, Save, Upload, UserRound } from 'lucide-react'

import type { FIProps } from './index'
import { showConfirm, showToast } from '../../ui/dialog'

// FI_Avance (type 10) — Demande d'avance sur salaire.
export default function FIAvance({ apiBase, getToken, idTicket }: FIProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const reload = useCallback(() => {
    setLoading(true)
    fetch(`${apiBase}/tickets/${idTicket}/form`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d) => setData(d?.data?.found ? d.data : null))
      .catch(() => setData(null))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase, idTicket])

  useEffect(() => {
    reload()
  }, [reload])

  const set = (k: string, v: any) => setData((d: any) => ({ ...d, [k]: v }))

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
        showToast(`Erreur : ${j?.detail || resp.status}`, 'error')
        return null
      }
      return j ?? {}
    } catch {
      showToast('Erreur réseau.', 'error')
      return null
    } finally {
      setSaving(false)
    }
  }

  const doUpload = async (f: File) => {
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', f)
      const r = await fetch(`${apiBase}/tickets/${idTicket}/form/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      })
      const j = await r.json().catch(() => null)
      if (!r.ok || j?.ok === false) {
        showToast(
          `Upload échoué (HTTP ${r.status}) : ` +
            `${j?.detail || j?.error || 'réponse inattendue'}`,
          'error',
        )
        return
      }
      reload()
    } catch (err) {
      showToast(`Erreur réseau : ${String((err as any)?.message || err)}`, 'error')
    } finally {
      setUploading(false)
    }
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
        Aucune demande d'avance pour ce ticket.
      </div>
    )
  }

  const validerVirement = async () => {
    if (!data.mois_paiement) {
      showToast('Le mois de paiement est obligatoire.', 'error')
      return
    }
    if (!data.has_preuve) {
      if (
        !(await showConfirm({
          message:
            "Vous n'avez pas ajouté de preuve de virement.\n" +
            'Celle-ci est IMPORTANTE pour le suivi du virement !\n' +
            'Poursuivre la validation sans la preuve ?',
        }))
      )
        return
    }
    const r = await post({
      action: 'virement',
      montant: data.montant,
      mois_paiement: data.mois_paiement,
      date_virement: data.date_virement,
    })
    if (r) {
      showToast('Virement validé. Ticket terminé.', 'success')
      reload()
    }
  }

  return (
    <div className="max-w-xl mx-auto space-y-4">
      {/* Bénéficiaire */}
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-c-line bg-c-surface-soft">
        <UserRound className="w-4 h-4 text-c-brand shrink-0" />
        <span className="text-sm text-c-ink-soft">Bénéficiaire :</span>
        <span className="text-sm font-medium text-c-ink">
          {data.benef_nom || '—'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <label className="text-sm">
          <span className="text-c-ink-soft">Montant (€)</span>
          <input
            type="number"
            step="0.01"
            value={data.montant ?? 0}
            onChange={(e) => set('montant', e.target.value)}
            className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
          />
        </label>
        <label className="text-sm">
          <span className="text-c-ink-soft">Mois de Paiement</span>
          <input
            type="text"
            placeholder="MM-AAAA"
            value={data.mois_paiement || ''}
            onChange={(e) => set('mois_paiement', e.target.value)}
            className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
          />
        </label>
        <label className="text-sm col-span-2">
          <span className="text-c-ink-soft">
            Date du virement{' '}
            <em className="text-c-ink-faint not-italic">
              (à renseigner pour mettre à jour le Tb salarié)
            </em>
          </span>
          <input
            type="date"
            value={data.date_virement || ''}
            onChange={(e) => set('date_virement', e.target.value)}
            className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
          />
        </label>
      </div>

      {/* Preuve de virement */}
      <div className="border border-c-line rounded-lg p-3 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-c-brand-strong">
            Preuve de virement
          </span>
          <input
            ref={fileInput}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) doUpload(f)
              e.target.value = ''
            }}
          />
          <button
            onClick={() => fileInput.current?.click()}
            disabled={uploading}
            className="flex items-center gap-1 text-xs text-c-brand hover:underline disabled:opacity-50"
          >
            {uploading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Upload className="w-3.5 h-3.5" />
            )}
            Charger la preuve de virement
          </button>
        </div>
        {data.preuve_url ? (
          <img
            src={data.preuve_url}
            alt="Preuve de virement"
            className="max-h-72 rounded border border-c-line mx-auto"
          />
        ) : (
          <div className="text-sm text-c-ink-faint text-center py-6">
            Aucune preuve de virement chargée.
          </div>
        )}
      </div>

      <button
        onClick={validerVirement}
        disabled={saving || data.demande_validee}
        className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50 transition-all"
      >
        {saving ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Save className="w-4 h-4" />
        )}
        {data.demande_validee ? 'Virement déjà validé' : 'Virement effectué'}
      </button>
    </div>
  )
}
