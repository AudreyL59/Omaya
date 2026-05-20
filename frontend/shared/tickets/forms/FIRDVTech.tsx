import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, Loader2 } from 'lucide-react'

import type { FIProps } from './index'

// FI_RDVTech (type 19) — Retour RDV Tech FIBRE.
// Lecture INFOS CLIENT + CONTRAT, choix d'un statut RDV (+ Info Cplt),
// « Je valide ce retour » -> append InfoVenteSFR + clôture ticket.
export default function FIRDVTech({ apiBase, getToken, idTicket }: FIProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [newDateRdv, setNewDateRdv] = useState('')
  const [clearDate, setClearDate] = useState(false)

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
        Aucun retour RDV Tech pour ce ticket.
      </div>
    )
  }

  const cl = data.client || {}
  const ct = data.contrat || {}
  const isReschedule = Number(data.id_statut_rdv_choisi) === 8

  const valider = async () => {
    if (!data.id_statut_rdv_choisi) {
      window.alert('Choisis un statut RDV.')
      return
    }
    if (
      !window.confirm(
        'Vous êtes sur le point de valider ce retour RDV technicien.\n' +
          'Le ticket sera clôturé. Continuer ?',
      )
    )
      return
    const payload: any = {
      action: 'valider',
      id_statut_rdv: data.id_statut_rdv_choisi,
      info_cplt: data.info_cplt,
    }
    if (isReschedule) {
      payload.new_date_rdv = clearDate ? 'clear' : newDateRdv
    }
    const r = await post(payload)
    if (r) {
      window.alert('Retour validé. Ticket terminé.')
      reload()
    }
  }

  return (
    <div className="space-y-3">
      {/* Bloc haut : Num BS + Statut RDV + Info Cplt */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Field label="Num BS" value={data.num_bs || ct.num_bs} />
          <div className="flex items-center gap-2 text-sm">
            <span className="text-c-ink-soft w-28 shrink-0">Statut RDV</span>
            <select
              value={data.id_statut_rdv_choisi || 0}
              onChange={(e) =>
                set('id_statut_rdv_choisi', Number(e.target.value))
              }
              className="flex-1 px-2 py-1 border border-c-line-strong rounded-md text-sm bg-white"
            >
              <option value={0}>— Statut —</option>
              {(data.statuts_rdv || []).map((s: any) => (
                <option key={s.id} value={s.id}>{s.lib}</option>
              ))}
            </select>
          </div>
          {isReschedule && (
            <div className="space-y-1 border-l-2 border-c-brand pl-2">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="date"
                  value={newDateRdv}
                  onChange={(e) => {
                    setNewDateRdv(e.target.value)
                    setClearDate(false)
                  }}
                  disabled={clearDate}
                  className="px-2 py-1 border border-c-line-strong rounded-md text-xs"
                />
                <span className="text-c-ink-soft">Nouvelle date de RDV</span>
              </label>
              <label className="flex items-center gap-2 text-xs text-c-ink-soft cursor-pointer">
                <input
                  type="checkbox"
                  checked={clearDate}
                  onChange={(e) => {
                    setClearDate(e.target.checked)
                    if (e.target.checked) setNewDateRdv('')
                  }}
                  className="w-4 h-4 accent-c-brand"
                />
                Le client n'a pas encore eu de nouvelle date
              </label>
            </div>
          )}
          <button
            onClick={valider}
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50 mt-2"
          >
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <CheckCircle2 className="w-4 h-4" />
            )}
            Je valide ce retour
          </button>
        </div>

        <div>
          <label className="block text-sm">
            <span className="text-c-ink-soft">Info Cplt</span>
            <textarea
              value={data.info_cplt || ''}
              onChange={(e) => set('info_cplt', e.target.value)}
              className="mt-1 w-full min-h-[140px] px-2 py-1 border border-c-line-strong rounded-md text-sm resize-none"
            />
          </label>
        </div>
      </div>

      {/* 2 colonnes lecture */}
      <div className="grid grid-cols-2 gap-6">
        <div className="space-y-1.5">
          <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide">
            Infos client
          </h3>
          <Field label="Nom" value={cl.nom} />
          <Field label="Prénom" value={cl.prenom} />
          <Field label="Adresse 1" value={cl.adresse1} />
          <Field label="Adresse 2" value={cl.adresse2} />
          <div className="grid grid-cols-3 gap-2">
            <Field label="CP" value={cl.cp} />
            <div className="col-span-2">
              <Field label="Ville" value={cl.ville} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Tél" value={cl.tel} />
            <Field label="Mobile" value={cl.mobile} />
          </div>
          <Field label="Mail" value={cl.mail} />
        </div>

        <div className="space-y-1.5">
          <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide">
            Infos contrat
          </h3>
          <Field label="Date Signature" value={ct.date_signature} />
          <Field
            label="Date RDV Tech"
            value={`${ct.date_rdv_tech || ''}  (${ct.periode_rdv_lib || ''})`.trim()}
          />
          <Field label="Type Vente" value={ct.type_vente_lib} />
          <Field label="Cluster" value={ct.cluster_lib} />
          <Field label="État vente Vendeur" value={ct.etat_vendeur_lib} />
          <Field label="État vente SFR" value={String(ct.id_etat_sfr || '')} />
          <Field label="Offre" value={ct.offre_lib} />
        </div>
      </div>
    </div>
  )
}

function Field({ label, value }: { label: string; value?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-c-ink-soft w-28 shrink-0">{label}</span>
      <input
        readOnly
        value={value || ''}
        className="flex-1 px-2 py-1 border border-c-line-strong rounded-md text-sm bg-c-surface-soft text-c-ink"
      />
    </div>
  )
}
