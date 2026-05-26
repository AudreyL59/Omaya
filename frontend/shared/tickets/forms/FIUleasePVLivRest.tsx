import { useCallback, useEffect, useState } from 'react'
import { Loader2, Star, Trash2 } from 'lucide-react'

import type { FIProps } from './index'
import { showConfirm, showToast } from '../../ui/dialog'

// FI_UleasePVLivRest (type 35) — PV Livraison/Restitution ULEASE.
export default function FIUleasePVLivRest({
  apiBase, getToken, idTicket, onClose,
}: FIProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [plan, setPlan] = useState(1)
  const [obs, setObs] = useState('')
  const [sel, setSel] = useState<any | null>(null)
  const [imgModele, setImgModele] = useState('')
  const [imgFournie, setImgFournie] = useState('')
  const [imgLoading, setImgLoading] = useState(false)
  const [pdfUrl, setPdfUrl] = useState('')
  const [pdfLoading, setPdfLoading] = useState(false)

  const reload = useCallback(() => {
    setLoading(true)
    fetch(`${apiBase}/tickets/${idTicket}/form`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d) => {
        const dd = d?.data?.found ? d.data : null
        setData(dd)
        if (dd) setObs(dd.observations || '')
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

  const fetchImg = async (name: string): Promise<string> => {
    try {
      const resp = await fetch(
        `${apiBase}/tickets/${idTicket}/form/file?name=${encodeURIComponent(name)}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!resp.ok) return ''
      const blob = await resp.blob()
      return URL.createObjectURL(blob)
    } catch {
      return ''
    }
  }

  const selectPhoto = async (p: any) => {
    setSel(p)
    setImgModele('')
    setImgFournie('')
    setImgLoading(true)
    const [m, f] = await Promise.all([
      fetchImg(`m${p.id_type_photo}`),
      fetchImg(`f${p.id}`),
    ])
    setImgModele(m)
    setImgFournie(f)
    setImgLoading(false)
  }

  // Plan 2 : génère + affiche le PDF
  useEffect(() => {
    if (plan !== 2) return
    let revoked = ''
    setPdfLoading(true)
    fetch(`${apiBase}/tickets/${idTicket}/form/print`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const blob = await r.blob()
        const u = URL.createObjectURL(blob)
        revoked = u
        setPdfUrl(u)
      })
      .catch(() => setPdfUrl(''))
      .finally(() => setPdfLoading(false))
    return () => {
      if (revoked) URL.revokeObjectURL(revoked)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plan, apiBase, idTicket])

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
        Aucun PV ULEASE pour ce ticket.
      </div>
    )
  }

  const photos: any[] = data.photos || []

  const noter = async (note: number) => {
    if (!sel) return
    const r = await post({ action: 'note_photo', id_photo: sel.id, note })
    if (r) {
      setData((d: any) => ({
        ...d,
        photos: d.photos.map((p: any) =>
          p.id === sel.id ? { ...p, note } : p,
        ),
        nb_notees: d.photos.filter((p: any) =>
          (p.id === sel.id ? note : p.note) > 0,
        ).length,
      }))
      setSel((s: any) => (s ? { ...s, note } : s))
    }
  }

  const photoNonRecevable = async () => {
    if (!sel) return
    if (
      !(await showConfirm({
        message: 'Vous êtes sur le point de supprimer cette photo.\nVoulez-vous continuer ?',
        variant: 'danger',
        confirmLabel: 'Supprimer',
      }))
    )
      return
    const r = await post({ action: 'del_photo', id_photo: sel.id })
    if (r) {
      setImgFournie('')
      setData((d: any) => ({
        ...d,
        photos: d.photos.map((p: any) =>
          p.id === sel.id ? { ...p, note: 0 } : p,
        ),
      }))
      setSel((s: any) => (s ? { ...s, note: 0 } : s))
    }
  }

  const passerEtape = async () => {
    const toutes = photos.length > 0 && photos.every((p) => p.note > 0)
    if (!toutes) {
      showToast('Toutes les photos doivent être notées.', 'error')
      return
    }
    const r = await post({ action: 'save_obs', observations: obs })
    if (!r) return
    // pré-charge le cache des photos côté serveur (PDF rapide ensuite)
    await post({ action: 'prepare' })
    setPlan(2)
  }

  const nbNotees = photos.filter((p) => p.note > 0).length
  const toutesNotees = photos.length > 0 && nbNotees === photos.length

  // ---- Plan 2 : aperçu PDF + validation ----
  if (plan === 2) {
    return (
      <div className="flex gap-4 h-full">
        <div className="flex-1 min-h-[520px] border border-c-line rounded-lg bg-c-surface-soft flex flex-col overflow-hidden">
          {pdfLoading ? (
            <span className="flex-1 flex items-center justify-center gap-2 text-c-ink-faint text-sm">
              <Loader2 className="w-5 h-5 animate-spin" />
              Génération du PV (peut prendre ~30 s)…
            </span>
          ) : pdfUrl ? (
            <iframe src={pdfUrl} title="PV ULEASE" className="w-full flex-1 border-0" />
          ) : (
            <span className="flex-1 flex items-center justify-center text-c-ink-faint text-sm">
              Impossible de générer le PV.
            </span>
          )}
        </div>
        <div className="w-60 shrink-0 space-y-2 text-sm">
          <div className="text-c-ink-soft">{data.lib_pv}</div>
          <div className="text-c-ink font-medium">{data.vehicule}</div>
          <div className="text-c-ink">{data.conducteur}</div>
          <hr className="border-c-line my-2" />
          <button
            onClick={() => setPlan(1)}
            className="w-full px-3 py-2 rounded-lg border border-c-line-strong text-sm hover:bg-c-surface-soft"
          >
            ← Retour
          </button>
          <button
            onClick={async () => {
              if (
                !(await showConfirm({
                  title: 'Valider le PV',
                  message: 'Valider ce document ? Il sera déposé dans le dossier véhicule et envoyé au salarié.',
                  confirmLabel: 'Valider',
                }))
              )
                return
              const cloturer = await showConfirm({
                message: 'Souhaitez-vous clôturer le ticket ?',
                confirmLabel: 'Clôturer',
                cancelLabel: 'Non',
              })
              const r = await post({ action: 'valider_signe', cloturer })
              if (r) {
                showToast('PV déposé et envoyé au salarié.', 'success')
                setTimeout(() => onClose?.(), 1500)
              }
            }}
            disabled={saving || pdfLoading}
            className="w-full px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
          >
            Ce document est valide
          </button>
        </div>
      </div>
    )
  }

  // ---- Plan 1 : photos + notation ----
  return (
    <div className="space-y-3">
      <div className="flex items-baseline gap-3 text-sm">
        <span className="font-semibold text-c-brand-strong">{data.lib_pv}</span>
        <span className="text-c-ink">{data.vehicule}</span>
        <span className="text-c-ink-soft">— {data.conducteur}</span>
        <span className="ml-auto text-xs text-c-ink-faint">
          {nbNotees}/{photos.length} photos notées
        </span>
      </div>

      <div className="flex gap-4">
        {/* Liste des photos */}
        <div className="w-72 shrink-0 border border-c-line rounded-lg overflow-auto max-h-[460px]">
          <table className="w-full text-sm">
            <thead className="bg-c-surface-soft text-c-ink-soft text-left sticky top-0">
              <tr>
                <th className="px-2 py-2">Photo</th>
                <th className="px-2 py-2 w-24 text-center">Note</th>
              </tr>
            </thead>
            <tbody>
              {photos.map((p) => (
                <tr
                  key={p.id}
                  onClick={() => selectPhoto(p)}
                  className={
                    'border-t border-c-line cursor-pointer ' +
                    (sel?.id === p.id ? 'bg-c-brand-soft' : 'hover:bg-c-surface-soft')
                  }
                >
                  <td className="px-2 py-1.5">{p.lib_photo}</td>
                  <td className="px-2 py-1.5">
                    <div className="flex justify-center gap-0.5">
                      {[1, 2, 3, 4, 5].map((n) => (
                        <Star
                          key={n}
                          className={
                            'w-3 h-3 ' +
                            (n <= p.note
                              ? 'fill-amber-400 text-amber-400'
                              : 'text-c-line-strong')
                          }
                        />
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Panneau photo sélectionnée */}
        <div className="flex-1 min-w-0">
          {!sel ? (
            <div className="h-full flex items-center justify-center text-c-ink-faint text-sm border border-dashed border-c-line rounded-lg min-h-[300px]">
              Sélectionne une photo dans la liste.
            </div>
          ) : (
            <div className="space-y-3">
              <div className="font-medium text-c-ink">{sel.lib_photo}</div>
              {imgLoading ? (
                <div className="flex items-center justify-center min-h-[200px]">
                  <Loader2 className="w-5 h-5 animate-spin text-c-ink-icon" />
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="text-xs text-c-ink-soft mb-1">Photo à fournir (modèle)</div>
                    {imgModele ? (
                      <img src={imgModele} alt="modèle" className="w-full rounded-lg border border-c-line object-contain max-h-56" />
                    ) : (
                      <div className="text-xs text-c-ink-faint">—</div>
                    )}
                  </div>
                  <div>
                    <div className="text-xs text-c-ink-soft mb-1">Photo fournie</div>
                    {imgFournie ? (
                      <img src={imgFournie} alt="fournie" className="w-full rounded-lg border border-c-line object-contain max-h-56" />
                    ) : (
                      <div className="text-xs text-amber-600">Aucune / non recevable</div>
                    )}
                  </div>
                </div>
              )}

              {/* Notation */}
              <div className="flex items-center gap-3">
                <span className="text-sm text-c-ink-soft">Note état :</span>
                <div className="flex gap-1">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button key={n} onClick={() => noter(n)} disabled={saving}>
                      <Star
                        className={
                          'w-6 h-6 transition-colors ' +
                          (n <= (sel.note || 0)
                            ? 'fill-amber-400 text-amber-400'
                            : 'text-c-line-strong hover:text-amber-300')
                        }
                      />
                    </button>
                  ))}
                </div>
                <button
                  onClick={photoNonRecevable}
                  disabled={saving}
                  className="ml-auto flex items-center gap-1 text-sm text-red-600 hover:underline"
                >
                  <Trash2 className="w-4 h-4" /> Photo non recevable
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Observation + passer à l'étape suivante */}
      <label className="block text-sm">
        <span className="text-c-ink-soft">Observation générale</span>
        <textarea
          value={obs}
          onChange={(e) => setObs(e.target.value)}
          className="mt-1 w-full min-h-[70px] px-2 py-1 border border-c-line-strong rounded-md text-sm resize-none"
        />
      </label>
      <button
        onClick={passerEtape}
        disabled={saving || !toutesNotees}
        title={toutesNotees ? '' : 'Toutes les photos doivent être notées'}
        className="w-full px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
      >
        Passer à l'étape suivante
      </button>
    </div>
  )
}
