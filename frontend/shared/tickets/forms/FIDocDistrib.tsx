import { useCallback, useEffect, useState } from 'react'
import {
  Building2, CheckCircle2, ExternalLink, Loader2, Send, User, XCircle,
} from 'lucide-react'

import type { FIProps } from './index'
import { showConfirm, showToast } from '../../ui/dialog'

// FI_DocDistrib (type 31) — Réclamation Documents distributeur.
export default function FIDocDistrib({
  apiBase, getToken, idTicket, onClose,
}: FIProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [motif, setMotif] = useState('')

  const reload = useCallback(() => {
    setLoading(true)
    fetch(`${apiBase}/tickets/${idTicket}/form`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d) => {
        const dd = d?.data?.found ? d.data : null
        setData(dd)
        if (dd) setMotif(dd.motif_refus || '')
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
      if (!resp.ok || j?.ok === false) {
        showToast(`Erreur : ${j?.error || j?.detail || resp.status}`, 'error')
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

  const ouvrirDoc = async () => {
    if (!data?.lien_fichier) return
    try {
      const resp = await fetch(
        `${apiBase}/tickets/${idTicket}/form/file?name=${encodeURIComponent(data.lien_fichier)}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!resp.ok) {
        showToast('Document introuvable.', 'error')
        return
      }
      const blob = await resp.blob()
      window.open(URL.createObjectURL(blob), '_blank')
    } catch {
      showToast('Erreur réseau (document).', 'error')
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
        Aucune réclamation de document pour ce ticket.
      </div>
    )
  }

  const conforme = async () => {
    if (!data.a_fichier) {
      showToast('Aucun document fourni à valider.', 'success')
      return
    }
    if (
      !(await showConfirm({
        message:
          `Valider le document « ${data.lib_doc} » ?\n` +
          'Il sera classé et le ticket clôturé.',
        variant: 'danger',
        confirmLabel: 'Valider',
      }))
    )
      return
    const r = await post({ action: 'conforme' })
    if (r) {
      showToast('Document validé. ' + (r.mail_result || ''), 'success')
      setTimeout(() => onClose?.(), 1500)
    }
  }

  const nonConforme = async () => {
    if (!motif.trim()) {
      showToast('Merci de saisir un motif de refus.', 'error')
      return
    }
    if (
      !(await showConfirm({
        message: 'Refuser ce document ? Le gérant recevra un SMS.',
        variant: 'danger',
        confirmLabel: 'Refuser',
      }))
    )
      return
    const r = await post({ action: 'non_conforme', motif_refus: motif })
    if (r) {
      showToast('Document refusé. SMS : ' + (r.sms_result || 'envoyé'), 'success')
      setTimeout(() => onClose?.(), 1500)
    }
  }

  const relanceSms = async () => {
    const r = await post({ action: 'relance_sms' })
    if (r) showToast('SMS de relance : ' + (r.sms_result || 'envoyé'), 'success')
  }

  return (
    <div className="space-y-4">
      {/* En-tête société / gérant / document */}
      <div className="space-y-1">
        <div className="flex items-center gap-2 text-sm">
          <Building2 className="w-4 h-4 text-c-ink-icon" />
          <span className="text-c-ink font-semibold">{data.lib_ste || '—'}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <User className="w-4 h-4 text-c-ink-icon" />
          <span className="text-c-ink">{data.lib_gerant || '—'}</span>
        </div>
        <div className="text-sm text-c-ink-soft">
          Document attendu :{' '}
          <span className="text-c-brand-strong font-medium">{data.lib_doc || '—'}</span>
        </div>
      </div>

      {/* Aperçu du document fourni */}
      {data.a_fichier ? (
        <button
          onClick={ouvrirDoc}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong text-sm hover:bg-c-brand-soft"
        >
          <ExternalLink className="w-4 h-4 text-c-brand" />
          Ouvrir le document fourni ({data.lien_fichier})
        </button>
      ) : (
        <div className="text-sm bg-amber-50 text-amber-700 border border-amber-200 rounded-lg px-3 py-2">
          Aucun document n'a encore été fourni par le distributeur.
        </div>
      )}

      {/* Le document est conforme */}
      <button
        onClick={conforme}
        disabled={saving || !data.a_fichier}
        className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
      >
        <CheckCircle2 className="w-4 h-4" />
        Le document est conforme
      </button>

      {/* Motif de refus + non conforme */}
      <div className="border-t border-c-line pt-3 space-y-2">
        <label className="block text-sm">
          <span className="text-c-ink-soft">Motif de Refus</span>
          <textarea
            value={motif}
            onChange={(e) => setMotif(e.target.value)}
            className="mt-1 w-full min-h-[80px] px-2 py-1 border border-c-line-strong rounded-md text-sm resize-none"
          />
        </label>
        <button
          onClick={nonConforme}
          disabled={saving}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-red-200 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
        >
          <XCircle className="w-4 h-4" />
          Le document n'est pas conforme
        </button>
      </div>

      {/* Relance SMS */}
      <button
        onClick={relanceSms}
        disabled={saving}
        className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong text-sm text-c-brand hover:bg-c-brand-soft disabled:opacity-50"
      >
        <Send className="w-4 h-4" />
        Relance SMS
      </button>
    </div>
  )
}
