import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, Loader2, Save, Trash2, User, X } from 'lucide-react'

import type { FIProps } from './index'

// FI_AttExoCash (type 25) — Attribution ExoCash.
// Crédite le livret EC d'un salarié (Gain Challenge / Prime / Cde Boutique).
const TYPE_OP_GAIN_CHALLENGE = 1

export default function FIAttExoCash({
  apiBase, getToken, idTicket, onClose,
}: FIProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  // Champs éditables (avant validation)
  const [montant, setMontant] = useState(0)
  const [info, setInfo] = useState('')
  const [typeOp, setTypeOp] = useState(0)
  const [idChallenge, setIdChallenge] = useState('')

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
          setInfo(dd.info_attribution || '')
          setTypeOp(Number(dd.type_operation || 0))
          setIdChallenge(dd.id_challenge || '')
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
        Aucune attribution ExoCash pour ce ticket.
      </div>
    )
  }

  const typeOps: any[] = data.type_operations || []
  const challenges: any[] = data.challenges || []
  const attribuee = !!data.attribuee

  // ExoCash = monnaie virtuelle interne (unité EC, pas €)
  const fmtDate = (iso: string) => {
    if (!iso) return ''
    const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/)
    if (!m) return iso
    return `${m[3]}/${m[2]}/${m[1]} à ${m[4]}:${m[5]}`
  }

  const valider = async () => {
    if (montant <= 0) {
      window.alert('Le montant EC doit être supérieur à 0.')
      return
    }
    if (
      !window.confirm(
        `Attribuer ${montant} EC à ${data.salarie_nom || 'ce salarié'} ?\n` +
          'Le livret ExoCash du salarié sera crédité.',
      )
    )
      return
    const r = await post({
      action: 'valider',
      montant,
      info_attribution: info,
      type_operation: typeOp,
      id_challenge: typeOp === TYPE_OP_GAIN_CHALLENGE ? idChallenge : '',
    })
    if (r) {
      window.alert('Attribution validée. SMS : ' + (r.sms_result || 'envoyé'))
      reload()
    }
  }

  const cloturer = async () => {
    if (
      !window.confirm(
        'Vous êtes sur le point de clôturer le ticket.\nVoulez-vous continuer ?',
      )
    )
      return
    const r = await post({ action: 'cloturer' })
    if (r) {
      onClose?.()
    }
  }

  return (
    <div className="space-y-4">
      {/* Bénéficiaire */}
      {data.salarie_nom && (
        <div className="flex items-center gap-2 text-sm text-c-ink-soft">
          <User className="w-4 h-4 text-c-ink-icon" />
          Bénéficiaire : <span className="text-c-ink font-medium">{data.salarie_nom}</span>
        </div>
      )}

      {/* Montant */}
      <label className="block text-sm">
        <span className="text-c-ink-soft">Montant</span>
        <div className="mt-1 flex items-center gap-2">
          <input
            type="number"
            min={0}
            step="0.01"
            value={montant}
            disabled={attribuee}
            onChange={(e) => setMontant(Math.max(0, Number(e.target.value)))}
            className="w-40 px-2 py-1 border border-c-line-strong rounded-md text-sm text-right disabled:bg-c-surface-soft"
          />
          <span className="text-c-ink-soft text-sm">EC</span>
        </div>
      </label>

      {/* Info Attribution */}
      <label className="block text-sm">
        <span className="text-c-ink-soft">Info Attribution</span>
        <textarea
          value={info}
          disabled={attribuee}
          onChange={(e) => setInfo(e.target.value)}
          className="mt-1 w-full min-h-[120px] px-2 py-1 border border-c-line-strong rounded-md text-sm resize-none disabled:bg-c-surface-soft"
        />
      </label>

      {attribuee ? (
        /* LibInfo : attribution déjà effectuée */
        <div className="text-sm bg-c-brand-soft text-c-brand-strong rounded-lg px-3 py-2">
          ✓ Attribution effectuée le {fmtDate(data.date_attribution)}
          {data.challenge_label && (
            <div className="text-xs mt-1 text-c-ink-soft">
              Challenge : {data.challenge_label}
            </div>
          )}
        </div>
      ) : (
        <>
          {/* À remplir avant validation */}
          <div className="border-t border-c-line pt-3">
            <h3 className="text-sm font-semibold text-c-brand-strong mb-2">
              A remplir avant validation de l'attribution
            </h3>
            <label className="block text-sm">
              <span className="text-c-ink-soft">Type Opération</span>
              <select
                value={typeOp}
                onChange={(e) => setTypeOp(Number(e.target.value))}
                className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm bg-white"
              >
                <option value={0}>— Choisir —</option>
                {typeOps
                  .filter((t) => t.id !== 0)
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.lib}
                    </option>
                  ))}
              </select>
            </label>

            {/* Challenge (uniquement si Gain Challenge) */}
            {typeOp === TYPE_OP_GAIN_CHALLENGE && (
              <div className="mt-2 flex items-end gap-2">
                <label className="block text-sm flex-1">
                  <span className="text-c-ink-soft">Challenge</span>
                  <select
                    value={idChallenge}
                    onChange={(e) => setIdChallenge(e.target.value)}
                    className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm bg-white"
                  >
                    <option value="">— Choisir un challenge —</option>
                    {challenges.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </label>
                {idChallenge && (
                  <button
                    onClick={() => setIdChallenge('')}
                    title="Retirer le challenge"
                    className="p-1.5 rounded-md border border-c-line-strong hover:bg-red-50"
                  >
                    <Trash2 className="w-4 h-4 text-red-600" />
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Valider */}
          <button
            onClick={valider}
            disabled={saving || montant <= 0}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            Valider l'attribution
          </button>
        </>
      )}

      {/* Voir la fiche salarié (TODO : module fiche salarié) */}
      <button
        disabled
        title="À venir avec le module Fiche salarié"
        className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong text-sm text-c-ink-faint disabled:opacity-50 cursor-not-allowed"
      >
        <CheckCircle2 className="w-4 h-4" />
        Voir la fiche salarié
      </button>

      {/* Clôturer le ticket */}
      <button
        onClick={cloturer}
        disabled={saving}
        className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-red-200 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
      >
        <X className="w-4 h-4" />
        Clôturer le ticket
      </button>
    </div>
  )
}
