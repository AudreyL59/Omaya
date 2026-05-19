import { useCallback, useEffect, useState } from 'react'
import { Loader2, Save, UserPlus, Search, Send } from 'lucide-react'

import type { FIProps } from './index'
import SearchPicker, { type PickerItem } from './SearchPicker'

// FI_SOSBO (type 11) — SOS BO (multi-mode selon type de problème).
type Mode = {
  benef: string
  ref: string
  ref_kind: string
  pbcall: boolean
  contrats: boolean
  modif_vendeur: boolean
  modif_etat: boolean
  desactivation: boolean
}

// Mirroir de _MODES backend (afficherTypeDem WinDev)
const MODES: Record<number, Mode> = {
  1: { benef: 'Demandeur', ref: 'Date et Heure', ref_kind: 'text', pbcall: true, contrats: false, modif_vendeur: false, modif_etat: false, desactivation: false },
  2: { benef: 'Choisir le bon VRP', ref: 'Num Ctt', ref_kind: 'text', pbcall: false, contrats: true, modif_vendeur: true, modif_etat: false, desactivation: false },
  3: { benef: 'Vendeur concerné', ref: 'Adresse Mail', ref_kind: 'email', pbcall: false, contrats: false, modif_vendeur: false, modif_etat: false, desactivation: false },
  4: { benef: 'Vendeur concerné', ref: 'Num Ctt', ref_kind: 'text', pbcall: false, contrats: true, modif_vendeur: false, modif_etat: true, desactivation: false },
  5: { benef: 'Demandeur', ref: 'Num Ctt', ref_kind: 'text', pbcall: true, contrats: false, modif_vendeur: false, modif_etat: false, desactivation: false },
  6: { benef: 'Vendeur concerné', ref: 'Adresse Mail', ref_kind: 'email', pbcall: false, contrats: false, modif_vendeur: false, modif_etat: false, desactivation: true },
}
const DEFAULT_MODE: Mode = { benef: 'Bénéficiaire', ref: 'Référence', ref_kind: 'text', pbcall: false, contrats: false, modif_vendeur: false, modif_etat: false, desactivation: false }

export default function FISOSBO({ apiBase, getToken, idTicket }: FIProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [pick, setPick] = useState(false)
  const [selContrat, setSelContrat] = useState('')
  const [incident, setIncident] = useState<any | null>(null)

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
        Aucune demande SOS BO pour ce ticket.
      </div>
    )
  }

  const mode: Mode = MODES[Number(data.id_type)] || DEFAULT_MODE
  const typeLib =
    (data.types || []).find((t: any) => t.id === Number(data.id_type))?.lib ||
    ''
  const contrats: any[] = data.contrats || []
  const selRow = contrats.find((c) => c.id_contrat === selContrat)

  const enregistrer = () =>
    post({
      action: 'enregistrer',
      benef_id: data.benef_id,
      id_type: data.id_type,
      ref: data.ref,
      info_cplt: data.info_cplt,
    }).then((r) => r && window.alert('Contenu du ticket enregistré.'))

  const rechercher = async () => {
    const r = await post({ action: 'search_contrat', ref: data.ref })
    if (r) set('contrats', r.contrats || [])
  }

  return (
    <div className="flex gap-4 h-full">
      <div className="flex-1 min-w-0 overflow-y-auto pr-1 space-y-3">
        {/* Type de problème */}
        <div className="flex items-center gap-2 text-sm">
          <span className="text-c-ink-soft w-32 shrink-0">
            Type de problème
          </span>
          <select
            value={data.id_type || 0}
            onChange={(e) => {
              set('id_type', Number(e.target.value))
              setSelContrat('')
            }}
            className="flex-1 px-2 py-1 border border-c-line-strong rounded-md text-sm bg-white"
          >
            <option value={0}>— Type —</option>
            {(data.types || []).map((t: any) => (
              <option key={t.id} value={t.id}>{t.lib}</option>
            ))}
          </select>
        </div>

        {/* Bénéficiaire */}
        <div className="flex items-center gap-2 text-sm">
          <span className="text-c-ink-soft w-32 shrink-0">{mode.benef}</span>
          <button
            onClick={() => setPick(true)}
            className="flex-1 flex items-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong bg-white text-c-ink hover:bg-c-brand-soft transition-colors"
          >
            <UserPlus className="w-4 h-4 text-c-brand shrink-0" />
            <span className="truncate">
              {data.benef_nom || 'Choisir le Bénéficiaire'}
            </span>
          </button>
        </div>

        {/* Référence à contrôler */}
        <div className="flex items-center gap-2 text-sm">
          <span className="text-c-ink-soft w-32 shrink-0">{mode.ref}</span>
          <input
            type={mode.ref_kind === 'email' ? 'email' : 'text'}
            value={data.ref || ''}
            onChange={(e) => set('ref', e.target.value)}
            className="flex-1 px-2 py-1 border border-c-line-strong rounded-md text-sm"
          />
          {mode.contrats && (
            <button
              onClick={rechercher}
              disabled={saving}
              className="flex items-center gap-1 px-2 py-1 rounded-md border border-c-line-strong text-xs hover:bg-c-brand-soft disabled:opacity-50"
            >
              <Search className="w-3.5 h-3.5" /> Chercher
            </button>
          )}
        </div>

        {/* Infos complémentaires */}
        <div className="text-sm">
          <span className="text-c-ink-soft">Infos Cplt</span>
          <textarea
            value={data.info_cplt || ''}
            onChange={(e) => set('info_cplt', e.target.value)}
            className="mt-1 w-full min-h-[90px] px-2 py-1 border border-c-line-strong rounded-md text-sm resize-none"
          />
        </div>

        {/* Désactivation code (mode 6) */}
        {mode.desactivation && (
          <div className="border border-c-line rounded-lg p-3 space-y-2">
            <select
              value={data._id_partenaire || 0}
              onChange={(e) => set('_id_partenaire', Number(e.target.value))}
              className="w-full px-2 py-1 border border-c-line-strong rounded-md text-sm bg-white"
            >
              <option value={0}>--- Choisir un partenaire ---</option>
              {(data.partenaires || []).map((p: any) => (
                <option key={p.id} value={p.id}>{p.lib}</option>
              ))}
            </select>
            <button
              onClick={async () => {
                if (!data._id_partenaire) {
                  window.alert('Choisis un partenaire.')
                  return
                }
                const r = await post({
                  action: 'gen_desactivation',
                  id_partenaire: data._id_partenaire,
                })
                if (r)
                  window.alert(
                    'Ticket de désactivation créé (n° ' +
                      (r.id_nouveau_ticket || '?') + ').',
                  )
              }}
              disabled={saving}
              className="w-full px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
            >
              Générer Tk Désactivation Code
            </button>
          </div>
        )}

        {/* PB CALL (modes 1, 5) */}
        {mode.pbcall && (
          <div className="border border-c-line rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-c-brand-strong">
                PB CALL (incident)
              </span>
              <button
                onClick={() =>
                  setIncident({
                    id_incident: 0,
                    debut: '',
                    fin: '',
                    commentaire:
                      `Pb Call remonté par ${data.benef_nom || ''} ` +
                      `le ${new Date().toLocaleDateString('fr-FR')}` +
                      (data.ref ? ` — réf ${data.ref}` : ''),
                  })
                }
                className="text-xs text-c-brand hover:underline"
              >
                + Ajouter un PB CALL
              </button>
            </div>
            {incident && (
              <div className="space-y-2">
                <label className="block text-sm">
                  <span className="text-c-ink-soft">Début de l'incident</span>
                  <input
                    type="datetime-local"
                    value={incident.debut}
                    onChange={(e) =>
                      setIncident({ ...incident, debut: e.target.value })
                    }
                    className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
                  />
                </label>
                <label className="block text-sm">
                  <span className="text-c-ink-soft">Fin de l'incident</span>
                  <input
                    type="datetime-local"
                    value={incident.fin}
                    onChange={(e) =>
                      setIncident({ ...incident, fin: e.target.value })
                    }
                    className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
                  />
                </label>
                <label className="block text-sm">
                  <span className="text-c-ink-soft">Commentaire</span>
                  <textarea
                    value={incident.commentaire}
                    onChange={(e) =>
                      setIncident({
                        ...incident,
                        commentaire: e.target.value,
                      })
                    }
                    className="mt-1 w-full min-h-[70px] px-2 py-1 border border-c-line-strong rounded-md text-sm resize-none"
                  />
                </label>
                <div className="flex gap-2">
                  <button
                    onClick={async () => {
                      const r = await post({
                        action: 'incident_save',
                        ...incident,
                      })
                      if (r) {
                        window.alert('Incident enregistré.')
                        setIncident(null)
                        reload()
                      }
                    }}
                    disabled={saving}
                    className="flex-1 px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
                  >
                    Enregistrer l'incident
                  </button>
                  <button
                    onClick={() => setIncident(null)}
                    className="px-3 py-2 rounded-lg border border-c-line-strong text-sm text-c-ink hover:bg-c-surface-soft"
                  >
                    Annuler
                  </button>
                </div>
              </div>
            )}

            <div className="border border-c-line rounded-lg overflow-auto max-h-56">
              <table className="w-full text-sm">
                <thead className="bg-c-surface-soft text-c-ink-soft text-left sticky top-0">
                  <tr>
                    <th className="px-2 py-2 w-36">Début</th>
                    <th className="px-2 py-2 w-36">Fin</th>
                    <th className="px-2 py-2">Commentaire</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.incidents || []).length === 0 ? (
                    <tr>
                      <td colSpan={3} className="px-2 py-3 text-center text-c-ink-faint">
                        Aucun incident.
                      </td>
                    </tr>
                  ) : (
                    (data.incidents || []).map((it: any) => (
                      <tr
                        key={it.id_incident}
                        onClick={() =>
                          setIncident({
                            id_incident: Number(it.id_incident),
                            debut: (it.debut || '').replace(' ', 'T').slice(0, 16),
                            fin: (it.fin || '').replace(' ', 'T').slice(0, 16),
                            commentaire: it.commentaire || '',
                          })
                        }
                        className="border-t border-c-line cursor-pointer hover:bg-c-surface-soft"
                      >
                        <td className="px-2 py-1.5">{it.debut || '—'}</td>
                        <td className="px-2 py-1.5">{it.fin || '—'}</td>
                        <td className="px-2 py-1.5 truncate max-w-[260px]">
                          {it.commentaire}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Contrats (modes 2, 4) */}
        {mode.contrats && (
          <div>
            <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide mb-1">
              Contrat(s) correspondant au numéro fourni
            </h3>
            <div className="border border-c-line rounded-lg overflow-auto max-h-72">
              <table className="w-full text-sm">
                <thead className="bg-c-surface-soft text-c-ink-soft text-left sticky top-0">
                  <tr>
                    <th className="px-2 py-2">Partenaire</th>
                    <th className="px-2 py-2">N° Contrat</th>
                    <th className="px-2 py-2">Date sign.</th>
                    <th className="px-2 py-2">État</th>
                    <th className="px-2 py-2">Mois Paie.</th>
                    <th className="px-2 py-2">Client</th>
                    <th className="px-2 py-2">Vendeur</th>
                  </tr>
                </thead>
                <tbody>
                  {contrats.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-2 py-4 text-center text-c-ink-faint">
                        Aucun contrat.
                      </td>
                    </tr>
                  ) : (
                    contrats.map((c) => (
                      <tr
                        key={c.partenaire + c.id_contrat}
                        onClick={() => setSelContrat(c.id_contrat)}
                        className={
                          'border-t border-c-line cursor-pointer ' +
                          (selContrat === c.id_contrat
                            ? 'bg-c-brand-soft'
                            : 'hover:bg-c-surface-soft')
                        }
                      >
                        <td className="px-2 py-2">{c.partenaire}</td>
                        <td className="px-2 py-2">{c.n_contrat}</td>
                        <td className="px-2 py-2">{c.date_signature}</td>
                        <td className="px-2 py-2">{c.etat}</td>
                        <td className="px-2 py-2">{c.mois_paiement}</td>
                        <td className="px-2 py-2">{c.nom_client}</td>
                        <td className="px-2 py-2">{c.nom_vendeur}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            {mode.modif_vendeur && (
              <button
                onClick={async () => {
                  if (!selRow) {
                    window.alert('Sélectionne un contrat.')
                    return
                  }
                  if (
                    !window.confirm(
                      `Réattribuer le contrat n° ${selRow.n_contrat} à ` +
                        `${data.benef_nom} ?`,
                    )
                  )
                    return
                  const r = await post({
                    action: 'modif_vendeur_bs',
                    partenaire: selRow.partenaire,
                    id_contrat: selRow.id_contrat,
                    n_contrat: selRow.n_contrat,
                    id_salarie_old: selRow.id_salarie,
                    benef_id: data.benef_id,
                  })
                  if (r) {
                    window.alert('Changement de vendeur effectué.')
                    rechercher()
                  }
                }}
                disabled={saving}
                className="mt-2 w-full px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
              >
                Modifier le vendeur du BS
              </button>
            )}
            {mode.modif_etat && (
              <button
                onClick={async () => {
                  if (!selRow) {
                    window.alert('Sélectionne un contrat.')
                    return
                  }
                  if (
                    !window.confirm(
                      `Remettre le contrat n° ${selRow.n_contrat} en ` +
                        'BS CALL - En cours de traitement opérateur ?',
                    )
                  )
                    return
                  const r = await post({
                    action: 'modif_etat_bs',
                    partenaire: selRow.partenaire,
                    id_contrat: selRow.id_contrat,
                    id_etat_old: selRow.id_etat,
                  })
                  if (r) {
                    window.alert("Changement d'état effectué.")
                    rechercher()
                  }
                }}
                disabled={saving}
                className="mt-2 w-full px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
              >
                Modifier l'état du BS
              </button>
            )}
          </div>
        )}
      </div>

      {/* Colonne droite : actions globales */}
      <div className="w-72 shrink-0 flex flex-col gap-2">
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
          Enregistrer le contenu du ticket
        </button>
        <button
          onClick={async () => {
            const r = await post({
              action: 'sms_traite',
              type_lib: typeLib,
              benef_nom: data.benef_nom,
            })
            if (r)
              window.alert(
                'SMS demandeur : ' + (r.sms_result || 'envoyé'),
              )
          }}
          disabled={saving}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong text-sm text-c-ink hover:bg-c-brand-soft disabled:opacity-50"
        >
          <Send className="w-4 h-4 text-c-brand" />
          Envoyer un SMS « demande traitée »
        </button>
      </div>

      {pick && (
        <SearchPicker
          apiBase={apiBase}
          getToken={getToken}
          title={mode.benef}
          path="/tickets/salaries/search"
          mapItem={(s) => ({
            id: s.id_salarie,
            label: `${s.nom} ${cap(s.prenom)}`,
            sublabel: [s.poste, s.lib_societe].filter(Boolean).join(' · '),
          })}
          onClose={() => setPick(false)}
          onPick={(it: PickerItem) => {
            setPick(false)
            set('benef_id', it.id)
            set('benef_nom', it.label)
          }}
        />
      )}
    </div>
  )
}

function cap(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : ''
}
