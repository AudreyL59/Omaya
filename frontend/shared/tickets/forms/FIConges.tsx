import { useCallback, useEffect, useRef, useState } from 'react'
import { Eraser, Loader2, Save } from 'lucide-react'

import type { FIProps } from './index'

// FI_Congés (type 13) — Demande de congés (avec signature manuscrite).
export default function FIConges({ apiBase, getToken, idTicket }: FIProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [signatureB64, setSignatureB64] = useState('')
  const [approved, setApproved] = useState(false)

  const reload = useCallback(() => {
    setLoading(true)
    fetch(`${apiBase}/tickets/${idTicket}/form`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d) => {
        const dd = d?.data?.found ? d.data : null
        setData(dd)
        if (dd && typeof dd.activite_salarie === 'boolean')
          setData((cur: any) => ({
            ...cur,
            envoyer_sms: dd.activite_salarie,
          }))
      })
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
        Aucune demande de congés pour ce ticket.
      </div>
    )
  }

  const valider = async () => {
    if (!signatureB64) {
      window.alert('Signe avant de valider.')
      return
    }
    const r = await post({
      action: 'valider',
      type_conges: data.type_conges,
      id_type_absence: data.id_type_absence,
      periode_conges: data.periode_conges,
      date_debut: data.date_debut,
      date_fin: data.date_fin,
      motif: data.motif,
      envoyer_sms: !!data.envoyer_sms,
      signature_b64: signatureB64,
    })
    if (r) {
      window.alert('Demande de congés validée. Ticket terminé.')
      reload()
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="text-lg font-semibold text-c-ink">
        {data.salarie_nom || '—'}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <label className="text-sm">
          <span className="text-c-ink-soft">
            Type Congés (maladie, CP …)
          </span>
          <input
            type="text"
            value={data.type_conges || ''}
            onChange={(e) => set('type_conges', e.target.value)}
            className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
          />
          <p className="text-[10px] text-c-ink-faint mt-0.5">
            Infos affichées sur le PDF de demande de congé.
          </p>
        </label>

        <label className="text-sm">
          <span className="text-c-ink-soft">Absence pour Omaya</span>
          <select
            value={data.id_type_absence || 0}
            onChange={(e) => set('id_type_absence', Number(e.target.value))}
            className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm bg-white"
          >
            <option value={0}>— Type —</option>
            {(data.types_absence || []).map((t: any) => (
              <option key={t.id} value={t.id}>{t.lib}</option>
            ))}
          </select>
          <p className="text-[10px] text-c-ink-faint mt-0.5">
            Type utilisé pour générer l'absence sur la fiche salarié.
          </p>
        </label>

        <label className="text-sm">
          <span className="text-c-ink-soft">
            PériodeCongés (Période / Journée / AM / PM)
          </span>
          <select
            value={data.periode_conges || ''}
            onChange={(e) => set('periode_conges', e.target.value)}
            className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm bg-white"
          >
            <option value="">—</option>
            <option value="Période">Période</option>
            <option value="Journée">Journée</option>
            <option value="AM">AM</option>
            <option value="PM">PM</option>
          </select>
        </label>

        <div className="grid grid-cols-2 gap-2">
          <label className="text-sm">
            <span className="text-c-ink-soft">Date Début</span>
            <input
              type="date"
              value={data.date_debut || ''}
              onChange={(e) => set('date_debut', e.target.value)}
              className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
            />
          </label>
          <label className="text-sm">
            <span className="text-c-ink-soft">Date Fin</span>
            <input
              type="date"
              value={data.date_fin || ''}
              onChange={(e) => set('date_fin', e.target.value)}
              className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
            />
          </label>
        </div>
      </div>

      <label className="block text-sm">
        <span className="text-c-ink-soft">Motif</span>
        <textarea
          value={data.motif || ''}
          onChange={(e) => set('motif', e.target.value)}
          className="mt-1 w-full min-h-[80px] px-2 py-1 border border-c-line-strong rounded-md text-sm resize-none"
        />
      </label>

      {/* Signature du demandeur (lecture) */}
      {data.signature_demandeur_url && (
        <div className="border border-c-line rounded-lg p-3">
          <div className="text-sm font-semibold text-c-brand-strong mb-1">
            Signature du demandeur
          </div>
          <img
            src={data.signature_demandeur_url}
            alt="Signature du demandeur"
            className="max-h-32 mx-auto"
          />
        </div>
      )}

      {/* J'approuve + signature manuscrite */}
      <label className="flex items-center gap-2 text-sm text-c-ink cursor-pointer">
        <input
          type="checkbox"
          checked={approved}
          onChange={(e) => setApproved(e.target.checked)}
          className="w-4 h-4 accent-c-brand cursor-pointer"
        />
        J'approuve la demande de congé
      </label>

      {approved && (
        <div className="border border-c-line rounded-lg p-3 space-y-2">
          <div className="text-sm font-semibold text-c-brand-strong">
            Signer dans l'encadrer ci-dessous :
          </div>
          <SignaturePad value={signatureB64} onChange={setSignatureB64} />
          <label className="flex items-center gap-2 text-sm text-c-ink cursor-pointer">
            <input
              type="checkbox"
              checked={!!data.envoyer_sms}
              onChange={(e) => set('envoyer_sms', e.target.checked)}
              disabled={!data.activite_salarie}
              className="w-4 h-4 accent-c-brand cursor-pointer disabled:opacity-50"
            />
            Envoyer le SMS au salarié
            {!data.activite_salarie && (
              <span className="text-[10px] text-c-ink-faint">
                (salarié inactif → SMS désactivé)
              </span>
            )}
          </label>
          <button
            onClick={valider}
            disabled={saving || !signatureB64}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
          >
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Validation finale
          </button>
        </div>
      )}
    </div>
  )
}

// ----- Signature manuscrite (canvas) -----

function SignaturePad({
  value,
  onChange,
}: {
  value: string
  onChange: (b64: string) => void
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const drawing = useRef(false)
  const last = useRef<{ x: number; y: number } | null>(null)

  // Initialise / efface
  const clearPad = useCallback(() => {
    const c = canvasRef.current
    if (!c) return
    const ctx = c.getContext('2d')
    if (!ctx) return
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, c.width, c.height)
    ctx.lineWidth = 2
    ctx.strokeStyle = '#000'
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    onChange('')
  }, [onChange])

  useEffect(() => {
    clearPad()
  }, [clearPad])

  const pos = (e: React.MouseEvent | React.TouchEvent) => {
    const c = canvasRef.current!
    const rect = c.getBoundingClientRect()
    const sx = c.width / rect.width
    const sy = c.height / rect.height
    let cx = 0
    let cy = 0
    if ('touches' in e) {
      const t = e.touches[0] || e.changedTouches[0]
      cx = t.clientX
      cy = t.clientY
    } else {
      cx = e.clientX
      cy = e.clientY
    }
    return { x: (cx - rect.left) * sx, y: (cy - rect.top) * sy }
  }

  const start = (e: React.MouseEvent | React.TouchEvent) => {
    drawing.current = true
    last.current = pos(e)
  }
  const move = (e: React.MouseEvent | React.TouchEvent) => {
    if (!drawing.current) return
    const c = canvasRef.current!
    const ctx = c.getContext('2d')!
    const p = pos(e)
    const l = last.current!
    ctx.beginPath()
    ctx.moveTo(l.x, l.y)
    ctx.lineTo(p.x, p.y)
    ctx.stroke()
    last.current = p
  }
  const end = () => {
    if (!drawing.current) return
    drawing.current = false
    last.current = null
    const c = canvasRef.current!
    onChange(c.toDataURL('image/jpeg', 0.85))
  }

  return (
    <div>
      <canvas
        ref={canvasRef}
        width={600}
        height={180}
        className="w-full h-44 border border-c-line rounded bg-white cursor-crosshair touch-none"
        onMouseDown={start}
        onMouseMove={move}
        onMouseUp={end}
        onMouseLeave={end}
        onTouchStart={(e) => { e.preventDefault(); start(e) }}
        onTouchMove={(e) => { e.preventDefault(); move(e) }}
        onTouchEnd={(e) => { e.preventDefault(); end() }}
      />
      <div className="flex items-center justify-between mt-1">
        <button
          onClick={clearPad}
          type="button"
          className="flex items-center gap-1 text-xs text-c-ink-faint hover:text-c-brand"
        >
          <Eraser className="w-3.5 h-3.5" /> Effacer
        </button>
        <span className="text-[10px] text-c-ink-faint">
          {value ? 'Signé' : 'Signe avec la souris ou le doigt'}
        </span>
      </div>
    </div>
  )
}
