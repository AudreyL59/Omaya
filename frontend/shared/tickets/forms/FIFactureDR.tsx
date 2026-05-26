import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ExternalLink, FileText, Loader2, Send, Upload, User,
} from 'lucide-react'

import type { FIProps } from './index'
import { showConfirm, showToast } from '../../ui/dialog'

// FI_FactureDR (type 33) — Facture BO (demande de facture / remboursement).
export default function FIFactureDR({
  apiBase, getToken, idTicket,
}: FIProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const [enseigne, setEnseigne] = useState('')
  const [numCommande, setNumCommande] = useState('')
  const [descriptif, setDescriptif] = useState('')
  const [montant, setMontant] = useState(0)
  const [dateAchat, setDateAchat] = useState('')
  const [idSte, setIdSte] = useState('')
  const [modePaiement, setModePaiement] = useState('')
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
          setEnseigne(dd.enseigne || '')
          setNumCommande(dd.num_commande || '')
          setDescriptif(dd.descriptif || '')
          setMontant(Number(dd.montant || 0))
          setDateAchat(dd.date_achat || '')
          setIdSte(dd.id_ste || '')
          setModePaiement((dd.modes_paiement || [])[0] || '')
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

  const openPath = async (chemin: string) => {
    if (!chemin) return
    try {
      const resp = await fetch(
        `${apiBase}/tickets/${idTicket}/form/file?name=${encodeURIComponent(chemin)}`,
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

  const uploadPreuve = async (file: File) => {
    setSaving(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const resp = await fetch(`${apiBase}/tickets/${idTicket}/form/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      })
      const j = await resp.json().catch(() => null)
      if (!resp.ok || j?.ok === false) {
        showToast(`Erreur : ${j?.error || j?.detail || resp.status}`, 'error')
        return
      }
      showToast('Preuve de virement chargée.', 'success')
      reload()
    } catch {
      showToast('Erreur réseau (upload).', 'error')
    } finally {
      setSaving(false)
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
        Aucune demande de facture pour ce ticket.
      </div>
    )
  }

  const societes: any[] = data.societes || []
  const modes: string[] = data.modes_paiement || []
  const transferee = !!data.transferee

  const transferer = async () => {
    if (
      !(await showConfirm({
        message:
          'Vous êtes sur le point de transférer cette facture dans le module ' +
          'de suivi des factures. Continuer ?',
      }))
    )
      return
    const r = await post({
      action: 'transferer',
      enseigne, num_commande: numCommande, descriptif, montant,
      date_achat: dateAchat, id_salarie: data.id_salarie,
      id_ste: idSte, mode_paiement: modePaiement,
    })
    if (r) {
      showToast('Facture transférée dans le module factures.', 'success')
      reload()
    }
  }

  return (
    <div className="space-y-4">
      {/* Vendeur */}
      <div className="flex items-center gap-2 text-sm text-c-ink-soft">
        <User className="w-4 h-4 text-c-ink-icon" />
        Vendeur : <span className="text-c-ink font-medium">{data.vendeur_nom || '—'}</span>
      </div>

      {transferee ? (
        /* Déjà transférée → voir la fiche facture (TODO module factures) */
        <>
          <div className="text-sm bg-c-brand-soft text-c-brand-strong rounded-lg px-3 py-2">
            ✓ Facture transférée dans le module factures (Commande{' '}
            {data.id_commande}).
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span className="text-c-ink-soft">Enseigne : </span>{data.enseigne}</div>
            <div><span className="text-c-ink-soft">N° Commande : </span>{data.num_commande}</div>
            <div><span className="text-c-ink-soft">Montant : </span>{Number(data.montant).toFixed(2)} €</div>
            <div><span className="text-c-ink-soft">Date Achat : </span>{data.date_achat}</div>
          </div>
          {data.chemin_facture && (
            <button
              onClick={() => openPath(data.chemin_facture)}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong text-sm hover:bg-c-brand-soft"
            >
              <ExternalLink className="w-4 h-4 text-c-brand" />
              Ouvrir la facture
            </button>
          )}
          <button
            disabled
            title="À venir avec le module de gestion des factures"
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong text-sm text-c-ink-faint cursor-not-allowed"
          >
            <FileText className="w-4 h-4" />
            Voir la fiche Facture
          </button>
        </>
      ) : (
        <>
          {/* Formulaire éditable */}
          <label className="block text-sm">
            <span className="text-c-ink-soft">Enseigne</span>
            <input
              value={enseigne}
              onChange={(e) => setEnseigne(e.target.value)}
              className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
            />
          </label>
          <label className="block text-sm">
            <span className="text-c-ink-soft">N° Commande</span>
            <input
              value={numCommande}
              onChange={(e) => setNumCommande(e.target.value)}
              className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
            />
          </label>
          <label className="block text-sm">
            <span className="text-c-ink-soft">Descriptif</span>
            <textarea
              value={descriptif}
              onChange={(e) => setDescriptif(e.target.value)}
              className="mt-1 w-full min-h-[70px] px-2 py-1 border border-c-line-strong rounded-md text-sm resize-none"
            />
          </label>
          <div className="flex items-end gap-4">
            <label className="block text-sm">
              <span className="text-c-ink-soft">Montant</span>
              <div className="mt-1 flex items-center gap-2">
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={montant}
                  onChange={(e) => setMontant(Math.max(0, Number(e.target.value)))}
                  className="w-32 px-2 py-1 border border-c-line-strong rounded-md text-sm text-right"
                />
                <span className="text-c-ink-soft text-sm">€</span>
              </div>
            </label>
            <label className="block text-sm">
              <span className="text-c-ink-soft">Date Achat</span>
              <input
                type="date"
                value={dateAchat}
                onChange={(e) => setDateAchat(e.target.value)}
                className="mt-1 block px-2 py-1 border border-c-line-strong rounded-md text-sm"
              />
            </label>
          </div>

          {/* Facture + preuve */}
          <div className="flex flex-col gap-2 border-t border-c-line pt-3">
            {data.chemin_facture && (
              <button
                onClick={() => openPath(data.chemin_facture)}
                className="flex items-center gap-2 text-sm text-c-brand hover:underline"
              >
                <ExternalLink className="w-4 h-4" /> Ouvrir la facture
              </button>
            )}
            {data.chemin_preuve ? (
              <button
                onClick={() => openPath(data.chemin_preuve)}
                className="flex items-center gap-2 text-sm text-c-brand hover:underline"
              >
                <ExternalLink className="w-4 h-4" /> Ouvrir la preuve de virement
              </button>
            ) : (
              <span className="text-xs text-c-ink-faint">
                Aucune preuve de virement chargée.
              </span>
            )}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={saving}
              className="flex items-center gap-2 text-sm text-c-brand hover:underline disabled:opacity-50"
            >
              <Upload className="w-4 h-4" /> Charger la preuve de virement
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*,application/pdf"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) uploadPreuve(f)
              }}
            />
          </div>

          {/* Société + Mode paiement */}
          <div className="grid grid-cols-2 gap-3 border-t border-c-line pt-3">
            <label className="block text-sm">
              <span className="text-c-ink-soft">Société</span>
              <select
                value={idSte}
                onChange={(e) => setIdSte(e.target.value)}
                className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm bg-white"
              >
                <option value="">— Société —</option>
                {societes.map((s) => (
                  <option key={s.id} value={s.id}>{s.lib}</option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="text-c-ink-soft">Mode Paiement</span>
              <select
                value={modePaiement}
                onChange={(e) => setModePaiement(e.target.value)}
                className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm bg-white"
              >
                {modes.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </label>
          </div>

          {/* Transférer */}
          <button
            onClick={transferer}
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
            Transférer dans le module facture
          </button>
        </>
      )}
    </div>
  )
}
