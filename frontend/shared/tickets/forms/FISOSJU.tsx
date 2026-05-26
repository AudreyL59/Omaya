import { useCallback, useEffect, useState } from 'react'
import { Loader2, Pencil, Save } from 'lucide-react'

import type { FIProps } from './index'
import SearchPicker, { type PickerItem } from './SearchPicker'
import { showToast } from '../../ui/dialog'

// FI_SOSJU (type 17) — SOS Juridique.
// UI pilotée par TK_TypeSOS_JU.TypeForm :
//   Salarie  -> picker salarié (crayon)
//   Poste    -> select TypePoste
//   Societe  -> select societe
//   Vehicule -> RefDemande "Immatriculation"
//   autres   -> RefDemande libre (label "Montant" si IDTK_TypeSOS_JU=1)
export default function FISOSJU({ apiBase, getToken, idTicket }: FIProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [pickSal, setPickSal] = useState(false)

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
        Aucune demande SOS Juridique pour ce ticket.
      </div>
    )
  }

  // Type form du type sélectionné (recalcule live au changement de type)
  const selType = (data.types || []).find(
    (t: any) => t.id === Number(data.id_type),
  )
  const typeForm: string = (selType?.type_form || '').trim()
  const isSalarie = typeForm === 'Salarie'
  const isPoste = typeForm === 'Poste'
  const isSociete = typeForm === 'Societe'
  const isVehicule = typeForm === 'Vehicule'
  const showPour = isSalarie || isPoste || isSociete
  const showRef = !showPour
  const refLabel = isVehicule
    ? 'Immatriculation'
    : Number(data.id_type) === 1
      ? 'Montant'
      : 'Référence'

  const enregistrer = async () => {
    const r = await post({
      action: 'enregistrer',
      id_type: data.id_type,
      id_elem: showPour ? data.id_elem : 0,
      ref_demande: showRef ? data.ref_demande : '',
      descriptif: data.descriptif,
    })
    if (r) {
      showToast('Modifications enregistrées.', 'success')
      reload()
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-3">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-c-ink-soft w-32 shrink-0">Type demande</span>
        <select
          value={data.id_type || 0}
          onChange={(e) => {
            set('id_type', Number(e.target.value))
            // reset Pour/Ref quand le type change
            set('id_elem', '')
            set('pour_name', '')
            set('ref_demande', '')
          }}
          className="flex-1 px-2 py-1 border border-c-line-strong rounded-md text-sm bg-white"
        >
          <option value={0}>— Type —</option>
          {(data.types || []).map((t: any) => (
            <option key={t.id} value={t.id}>{t.lib}</option>
          ))}
        </select>
      </div>

      {showPour && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-c-ink-soft w-32 shrink-0">Pour</span>
          {isSalarie ? (
            <>
              <input
                readOnly
                value={data.pour_name || ''}
                className="flex-1 px-2 py-1 border border-c-line-strong rounded-md text-sm bg-c-surface-soft"
              />
              <button
                onClick={() => setPickSal(true)}
                title="Choisir un salarié"
                className="p-1.5 rounded-md border border-c-line-strong hover:bg-c-brand-soft"
              >
                <Pencil className="w-4 h-4 text-c-brand" />
              </button>
            </>
          ) : isPoste ? (
            <select
              value={data.id_elem || 0}
              onChange={(e) => {
                const id = Number(e.target.value)
                set('id_elem', id)
                const p = (data.postes || []).find((x: any) => x.id === id)
                set('pour_name', p?.lib || '')
              }}
              className="flex-1 px-2 py-1 border border-c-line-strong rounded-md text-sm bg-white"
            >
              <option value={0}>— Poste —</option>
              {(data.postes || []).map((p: any) => (
                <option key={p.id} value={p.id}>{p.lib}</option>
              ))}
            </select>
          ) : (
            <select
              value={data.id_elem || 0}
              onChange={(e) => {
                const id = Number(e.target.value)
                set('id_elem', id)
                const s = (data.societes || []).find((x: any) => x.id === id)
                set('pour_name', s?.lib || '')
              }}
              className="flex-1 px-2 py-1 border border-c-line-strong rounded-md text-sm bg-white"
            >
              <option value={0}>— Société —</option>
              {(data.societes || []).map((s: any) => (
                <option key={s.id} value={s.id}>{s.lib}</option>
              ))}
            </select>
          )}
        </div>
      )}

      {showRef && (
        <div className="border border-c-line rounded-lg p-3">
          <div className="text-sm font-semibold text-c-brand-strong mb-1">
            {refLabel === 'Montant' ? 'Immat-Montant' : refLabel}
          </div>
          <input
            type={refLabel === 'Montant' ? 'number' : 'text'}
            step={refLabel === 'Montant' ? '0.01' : undefined}
            value={data.ref_demande || ''}
            onChange={(e) => set('ref_demande', e.target.value)}
            placeholder={refLabel}
            className="w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
          />
        </div>
      )}

      <label className="block text-sm">
        <span className="text-c-ink-soft">Descriptif</span>
        <textarea
          value={data.descriptif || ''}
          onChange={(e) => set('descriptif', e.target.value)}
          className="mt-1 w-full min-h-[180px] px-2 py-1 border border-c-line-strong rounded-md text-sm resize-none"
        />
      </label>

      <button
        onClick={enregistrer}
        disabled={saving}
        className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
      >
        {saving ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Save className="w-4 h-4" />
        )}
        Enregistrer
      </button>

      {pickSal && (
        <SearchPicker
          apiBase={apiBase}
          getToken={getToken}
          title="Choisir un salarié"
          path="/tickets/salaries/search"
          mapItem={(s) => ({
            id: s.id_salarie,
            label: `${s.nom} ${cap(s.prenom)}`,
            sublabel: [s.poste, s.lib_societe].filter(Boolean).join(' · '),
          })}
          onClose={() => setPickSal(false)}
          onPick={(it: PickerItem) => {
            setPickSal(false)
            set('id_elem', it.id)
            set('pour_name', it.label)
          }}
        />
      )}
    </div>
  )
}

function cap(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : ''
}
