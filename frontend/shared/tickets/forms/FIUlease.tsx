import { useCallback, useEffect, useState } from 'react'
import { Loader2, RefreshCw, UserPlus } from 'lucide-react'

import type { FIProps } from './index'
import SearchPicker, { type PickerItem } from './SearchPicker'
import { showConfirm, showToast } from '../../ui/dialog'

// FI_DocUlease (type 34) — Signature Doc ULEASE (même principe que CttW).
export default function FIUlease({ apiBase, getToken, idTicket, onClose }: FIProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [pickDA, setPickDA] = useState(false)
  const [signedPdfUrl, setSignedPdfUrl] = useState('')
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfError, setPdfError] = useState('')
  const [pdfNonce, setPdfNonce] = useState(0)

  // Plan 2 : régénère + charge le PDF signé (docx + soffice + fusion)
  useEffect(() => {
    if (!data || data.plan !== 2 || !data.has_signed_pdf) return
    let revoked = ''
    setPdfLoading(true)
    setPdfError('')
    fetch(`${apiBase}/tickets/${idTicket}/form/print`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(async (r) => {
        if (!r.ok) {
          const e = await r.json().catch(() => null)
          throw new Error(e?.detail || `HTTP ${r.status}`)
        }
        const blob = await r.blob()
        const u = URL.createObjectURL(blob)
        revoked = u
        setSignedPdfUrl(u)
      })
      .catch((err) => {
        setSignedPdfUrl('')
        setPdfError(String(err?.message || err))
      })
      .finally(() => setPdfLoading(false))
    return () => {
      if (revoked) URL.revokeObjectURL(revoked)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.plan, data?.has_signed_pdf, apiBase, idTicket, pdfNonce])

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

  const set = (k: string, v: any) =>
    setData((d: any) => (d ? { ...d, [k]: v } : d))

  const post = async (body: any) => {
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
      if (!resp.ok) {
        const e = await resp.json().catch(() => null)
        showToast(`Erreur : ${e?.detail || resp.status}`, 'error')
        return false
      }
      reload()
      return true
    } catch {
      showToast('Erreur réseau.', 'error')
      return false
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
        Ticket non synchronisé — merci de patienter.
      </div>
    )
  }

  // ---- Plan 2 : document validé (+ signé) ----
  if (data.plan === 2) {
    return (
      <div className="flex gap-4 h-full">
        <div className="flex-1 min-h-[520px] border border-c-line rounded-lg bg-c-surface-soft flex flex-col text-center text-c-ink-faint text-sm overflow-hidden">
          {pdfLoading ? (
            <span className="flex-1 flex items-center justify-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin" />
              Régénération du document signé…
            </span>
          ) : signedPdfUrl ? (
            <iframe
              src={signedPdfUrl}
              title="Document ULEASE signé"
              className="w-full flex-1 border-0"
            />
          ) : !data.has_signed_pdf ? (
            <span className="flex-1 flex items-center justify-center p-6">
              Document <strong>validé</strong>, en attente de la signature
              du salarié sur l'appli Omaya.
            </span>
          ) : (
            <span className="flex-1 flex flex-col items-center justify-center p-6">
              Document <strong>signé</strong> le {data.date_signature || '—'}.
              <br />
              Impossible de régénérer le PDF signé.
              {pdfError && (
                <span className="text-red-600 text-xs break-all mt-1">
                  {pdfError}
                </span>
              )}
            </span>
          )}
        </div>
        <div className="w-72 shrink-0 space-y-2 text-sm">
          <Info label="Salarié" value={data.salarie_nom} />
          <Info label="DA" value={data.da_nom} />
          <Info label="Titre" value={data.titre_contrat} />
          <Info label="Type" value={data.type_cttw} />
          <Info label="Signé le" value={data.date_signature} />

          {data.has_signed_pdf && (
            <button
              onClick={() => setPdfNonce((n) => n + 1)}
              disabled={pdfLoading}
              className="w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg border border-c-line-strong text-sm text-c-brand hover:bg-c-brand-soft disabled:opacity-50"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Rafraîchir
            </button>
          )}

          <hr className="border-c-line my-2" />
          <p className="text-xs font-semibold text-c-ink">
            Problème avec le contrat ?
          </p>
          <Chk label="Pb avec la signature et/ou la photo" k="pb_sign" data={data} set={set} />
          <Chk label="Pb avec la paraphe" k="pb_paraphe" data={data} set={set} />
          <Chk label="Pb avec Mention « Lu et approuvé »" k="pb_mention" data={data} set={set} />
          <button
            onClick={async () => {
              if (
                !(await showConfirm({
                  title: 'Renvoyer en signature',
                  message:
                    'Vous êtes sur le point de refuser ce document.\nSouhaitez-vous continuer ?',
                  variant: 'danger',
                  confirmLabel: 'Refuser',
                }))
              )
                return
              const ok = await post({
                action: 'refuser',
                pb_sign: !!data.pb_sign,
                pb_paraphe: !!data.pb_paraphe,
                pb_mention: !!data.pb_mention,
              })
              if (ok) {
                showToast('Document renvoyé en signature. Le DA a été notifié.', 'success')
                setTimeout(() => onClose?.(), 1500)
              }
            }}
            disabled={saving || (!data.pb_sign && !data.pb_paraphe && !data.pb_mention)}
            className="w-full px-3 py-2 rounded-lg border border-red-300 text-red-600 text-sm font-semibold hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Renvoyer ce document en signature
          </button>

          <button
            onClick={async () => {
              if (
                !(await showConfirm({
                  title: 'Valider le document',
                  message:
                    'Valider ce document ? Il sera déposé dans le dossier et '
                    + 'envoyé par mail au salarié.',
                  confirmLabel: 'Valider',
                }))
              )
                return
              const cloturer = await showConfirm({
                message: 'Souhaitez-vous clôturer le ticket ?',
                confirmLabel: 'Clôturer',
                cancelLabel: 'Non',
              })
              const ok = await post({ action: 'valider_signe', cloturer })
              if (ok) {
                showToast('Document déposé et envoyé par mail au salarié.', 'success')
                setTimeout(() => onClose?.(), 1500)
              }
            }}
            disabled={saving}
            className="w-full px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50 transition-all"
          >
            Ce document est valide
          </button>
        </div>
      </div>
    )
  }

  // ---- Plan 1 : document non validé ----
  return (
    <div className="flex gap-4 h-full">
      {/* Aperçu du doc à signer */}
      <div className="flex-1 min-h-[520px] border border-c-line rounded-lg overflow-hidden bg-c-surface-soft">
        {data.pdf_non_signe_url ? (
          <iframe
            src={data.pdf_non_signe_url}
            title="Document ULEASE (à signer)"
            className="w-full h-full border-0"
          />
        ) : (
          <div className="h-full flex items-center justify-center text-c-ink-faint text-sm">
            Aperçu indisponible.
          </div>
        )}
      </div>

      {/* Panneau droit : salarié + DA + valider */}
      <div className="w-80 shrink-0 space-y-3">
        <Info label="Vendeur" value={data.salarie_nom} />
        <Info label="Titre" value={data.titre_contrat} />

        <hr className="border-c-line" />

        <button
          onClick={() => setPickDA(true)}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong bg-white text-sm text-c-ink hover:bg-c-brand-soft transition-colors"
        >
          <UserPlus className="w-4 h-4 text-c-brand shrink-0" />
          <span className="truncate">{data.da_nom || 'Choisir le DA'}</span>
        </button>

        <button
          onClick={async () => {
            if (
              !(await showConfirm({
                title: 'Valider pour signature',
                message:
                  'Vous êtes sur le point de valider ce document.\nSouhaitez-vous continuer ?',
                confirmLabel: 'Valider',
              }))
            )
              return
            const ok = await post({ action: 'valider' })
            if (ok) showToast('Document validé. Le DA a été notifié par SMS.', 'success')
          }}
          disabled={saving}
          className="w-full px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50 transition-all"
        >
          Valider document pour signature
        </button>
      </div>

      {pickDA && (
        <SearchPicker
          apiBase={apiBase}
          getToken={getToken}
          title="Choisir le DA"
          path="/tickets/salaries/search"
          mapItem={(s) => ({
            id: s.id_salarie,
            label: `${s.nom} ${cap(s.prenom)}`,
            sublabel: [s.poste, s.lib_societe].filter(Boolean).join(' · '),
          })}
          onClose={() => setPickDA(false)}
          onPick={async (it: PickerItem) => {
            setPickDA(false)
            await post({ action: 'da', id_da: it.id })
          }}
        />
      )}
    </div>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-sm">
      <span className="text-c-ink-faint">{label} : </span>
      <span className="text-c-ink">{value || '—'}</span>
    </div>
  )
}

function Chk({
  label, k, data, set,
}: {
  label: string
  k: string
  data: any
  set: (k: string, v: any) => void
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-c-ink cursor-pointer">
      <input
        type="checkbox"
        checked={!!data[k]}
        onChange={(e) => set(k, e.target.checked)}
        className="w-4 h-4 cursor-pointer accent-c-brand"
      />
      {label}
    </label>
  )
}

function cap(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : ''
}
