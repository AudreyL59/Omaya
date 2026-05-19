import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Loader2, Save, UserPlus, Trash2, Upload, FileText, Send, X,
} from 'lucide-react'

import type { FIProps } from './index'
import SearchPicker, { type PickerItem } from './SearchPicker'

// FI_Resa (type 9) — Réservation (hébergement / transport / salle).
export default function FIResa({ apiBase, getToken, idTicket }: FIProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [pick, setPick] = useState<'' | 'main' | 'supp'>('')
  const [busyFile, setBusyFile] = useState('')
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
        window.alert(`Erreur : ${j?.detail || resp.status}`)
        return null
      }
      return j?.data ?? j ?? {}
    } catch {
      window.alert('Erreur réseau.')
      return null
    } finally {
      setSaving(false)
    }
  }

  const openFile = async (nom: string) => {
    setBusyFile(nom)
    try {
      const r = await fetch(
        `${apiBase}/tickets/${idTicket}/form/file?name=${encodeURIComponent(nom)}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) {
        const e = await r.json().catch(() => null)
        window.alert(`Document indisponible : ${e?.detail || r.status}`)
        return
      }
      const blob = await r.blob()
      window.open(URL.createObjectURL(blob), '_blank', 'noopener')
    } catch {
      window.alert('Erreur réseau.')
    } finally {
      setBusyFile('')
    }
  }

  const doUpload = async (f: File) => {
    setBusyFile('__up__')
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
        window.alert(`Upload échoué : ${j?.detail || j?.error || r.status}`)
        return
      }
      reload()
    } catch {
      window.alert('Erreur réseau.')
    } finally {
      setBusyFile('')
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
        Aucune réservation pour ce ticket.
      </div>
    )
  }

  const L = data.labels || {}
  const benefs: any[] = data.beneficiaires || []
  const sousFam: any[] = (data.sous_familles || []).filter(
    (s: any) => !data.id_type_resa || s.id_type_resa === data.id_type_resa,
  )

  const removeBenef = (id: string) => {
    set(
      'beneficiaires',
      benefs.filter((b) => b.id_salarie !== id),
    )
    if (data.benef_id === id) set('benef_id', '')
  }

  const saveAll = () =>
    post({
      action: 'enregistrer',
      id_ss_fam: data.id_ss_fam,
      ville_dep: data.ville_dep,
      ville_arr: data.ville_arr,
      jour_dep: data.jour_dep,
      jour_arr: data.jour_arr,
      heure_dep: data.heure_dep,
      heure_arr: data.heure_arr,
      ar: data.ar,
      jourr_dep: data.jourr_dep,
      jourr_arr: data.jourr_arr,
      heurer_dep: data.heurer_dep,
      heurer_arr: data.heurer_arr,
      benef_id: data.benef_id,
      supp_ids: benefs
        .filter((b) => b.id_salarie !== data.benef_id)
        .map((b) => b.id_salarie),
      info_cplt: data.info_cplt,
    }).then((r) => r && reload())

  return (
    <div className="flex gap-4 h-full">
      {/* Colonne principale */}
      <div className="flex-1 min-w-0 overflow-y-auto pr-1 space-y-3">
        {/* Bénéficiaire + mobile demandeur */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setPick('main')}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong bg-white text-sm text-c-ink hover:bg-c-brand-soft transition-colors"
          >
            <UserPlus className="w-4 h-4 text-c-brand shrink-0" />
            <span className="truncate max-w-[220px]">
              {data.benef_nom || 'Choisir le Bénéficiaire'}
            </span>
          </button>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-c-ink-soft">Mobile demandeur</span>
            <input
              readOnly
              value={data.mobile_demandeur || ''}
              className="px-2 py-1 border border-c-line-strong rounded-md text-sm bg-c-surface-soft w-40"
            />
          </div>
        </div>

        {/* Catégorie / Type Resa / AR */}
        <div className="grid grid-cols-2 gap-3">
          <Field label="Catégorie">
            <select
              value={data.id_type_resa || 0}
              onChange={(e) => {
                set('id_type_resa', Number(e.target.value))
                set('id_ss_fam', 0)
              }}
              className="w-full px-2 py-1 border border-c-line-strong rounded-md text-sm bg-white"
            >
              <option value={0}>— Catégorie —</option>
              {(data.categories || []).map((c: any) => (
                <option key={c.id} value={c.id}>{c.lib}</option>
              ))}
            </select>
          </Field>
          <Field label="Type Resa">
            <select
              value={data.id_ss_fam || 0}
              onChange={(e) => set('id_ss_fam', Number(e.target.value))}
              className="w-full px-2 py-1 border border-c-line-strong rounded-md text-sm bg-white"
            >
              <option value={0}>— Type —</option>
              {sousFam.map((s: any) => (
                <option key={s.id} value={s.id}>{s.lib}</option>
              ))}
            </select>
          </Field>
          <Field label={L.lib_ville_dep || 'À'}>
            <input
              value={data.ville_dep || ''}
              onChange={(e) => set('ville_dep', e.target.value)}
              className="w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
            />
          </Field>
          {L.show_ville_arr !== false && (
            <Field label="Vers">
              <input
                value={data.ville_arr || ''}
                onChange={(e) => set('ville_arr', e.target.value)}
                className="w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
              />
            </Field>
          )}
          <label className="flex items-center gap-2 text-sm text-c-ink cursor-pointer">
            <input
              type="checkbox"
              checked={!!data.ar}
              onChange={(e) => set('ar', e.target.checked)}
              className="w-4 h-4 accent-c-brand cursor-pointer"
            />
            Aller-Retour
          </label>
        </div>

        {/* Dates aller */}
        <div className="border border-c-line rounded-lg p-3 space-y-2">
          <DateTime
            label={L.lib_dep || 'Départ le'}
            dateK="jour_dep" timeK="heure_dep" data={data} set={set}
          />
          <DateTime
            label={L.lib_arr || 'Arrivée le'}
            dateK="jour_arr" timeK="heure_arr" data={data} set={set}
          />
          {L.show_retour && (
            <>
              <DateTime
                label="Retour : Départ le"
                dateK="jourr_dep" timeK="heurer_dep" data={data} set={set}
              />
              <DateTime
                label="Retour : Arrivée le"
                dateK="jourr_arr" timeK="heurer_arr" data={data} set={set}
              />
            </>
          )}
        </div>

        {/* Liste des bénéficiaires */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide">
              Liste des bénéficiaires
            </h3>
            <button
              onClick={() => setPick('supp')}
              className="flex items-center gap-1 text-xs text-c-brand hover:underline"
            >
              <UserPlus className="w-3.5 h-3.5" /> Ajouter
            </button>
          </div>
          <div className="border border-c-line rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-c-surface-soft text-c-ink-soft text-left">
                <tr>
                  <th className="px-3 py-2">Nom</th>
                  <th className="px-3 py-2">Mobile</th>
                  <th className="px-3 py-2">Mail</th>
                  <th className="px-3 py-2 w-8" />
                </tr>
              </thead>
              <tbody>
                {benefs.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-3 py-4 text-center text-c-ink-faint">
                      Aucun bénéficiaire.
                    </td>
                  </tr>
                ) : (
                  benefs.map((b) => (
                    <tr key={b.id_salarie} className="border-t border-c-line">
                      <td className="px-3 py-2 text-c-ink">
                        {b.nom}
                        {b.principal && (
                          <span className="ml-1 text-[10px] text-c-brand">
                            (principal)
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2">{b.mobile || '—'}</td>
                      <td className="px-3 py-2">{b.mail || '—'}</td>
                      <td className="px-3 py-2">
                        <button
                          onClick={() => removeBenef(b.id_salarie)}
                          className="text-c-ink-faint hover:text-red-600"
                          title="Retirer"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pièces jointes */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide">
              Pièces jointes
            </h3>
            <div className="flex items-center gap-2">
              <input
                ref={fileInput}
                type="file"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) doUpload(f)
                  e.target.value = ''
                }}
              />
              <button
                onClick={() => fileInput.current?.click()}
                disabled={busyFile === '__up__'}
                className="flex items-center gap-1 text-xs text-c-brand hover:underline disabled:opacity-50"
              >
                {busyFile === '__up__' ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Upload className="w-3.5 h-3.5" />
                )}
                Ajouter une PJ
              </button>
            </div>
          </div>
          <div className="border border-c-line rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-c-surface-soft text-c-ink-soft text-left">
                <tr>
                  <th className="px-3 py-2">Nom Fichier</th>
                  <th className="px-3 py-2 w-20">Taille</th>
                  <th className="px-3 py-2 w-40">Date</th>
                  <th className="px-3 py-2 w-20" />
                </tr>
              </thead>
              <tbody>
                {(data.fichiers || []).length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-3 py-4 text-center text-c-ink-faint">
                      Aucune pièce jointe.
                    </td>
                  </tr>
                ) : (
                  (data.fichiers || []).map((f: any) => (
                    <tr key={f.nom} className="border-t border-c-line">
                      <td
                        className="px-3 py-2 text-c-ink cursor-pointer hover:text-c-brand"
                        onClick={() => openFile(f.nom)}
                      >
                        <span className="flex items-center gap-1">
                          {busyFile === f.nom ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <FileText className="w-3.5 h-3.5 shrink-0" />
                          )}
                          {f.nom}
                        </span>
                      </td>
                      <td className="px-3 py-2">{f.taille}</td>
                      <td className="px-3 py-2">{f.date}</td>
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() =>
                              post({ action: 'sms', nom_fichier: f.nom }).then(
                                (r: any) =>
                                  r &&
                                  window.alert(
                                    'SMS envoyé :\n' +
                                      ((r.envois || []).join('\n') || 'OK'),
                                  ),
                              )
                            }
                            disabled={saving}
                            title="Envoyer le lien de cette PJ par SMS"
                            className="text-c-ink-faint hover:text-c-brand"
                          >
                            <Send className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => {
                              if (!window.confirm(`Supprimer ${f.nom} ?`)) return
                              post({
                                action: 'delete_pj',
                                nom_fichier: f.nom,
                              }).then((r: any) => r && reload())
                            }}
                            disabled={saving}
                            title="Supprimer"
                            className="text-c-ink-faint hover:text-red-600"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Colonne droite : info complémentaire + actions */}
      <div className="w-72 shrink-0 flex flex-col gap-3">
        <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide">
          Info Complémentaire
        </h3>
        <textarea
          value={data.info_cplt || ''}
          onChange={(e) => set('info_cplt', e.target.value)}
          className="flex-1 min-h-[180px] px-2 py-1 border border-c-line-strong rounded-md text-sm resize-none"
        />
        <button
          onClick={saveAll}
          disabled={saving}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50 transition-all"
        >
          {saving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          Enregistrer
        </button>
      </div>

      {pick && (
        <SearchPicker
          apiBase={apiBase}
          getToken={getToken}
          title={pick === 'main' ? 'Choisir le Bénéficiaire' : 'Ajouter un bénéficiaire'}
          path="/tickets/salaries/search"
          mapItem={(s) => ({
            id: s.id_salarie,
            label: `${s.nom} ${cap(s.prenom)}`,
            sublabel: [s.poste, s.lib_societe].filter(Boolean).join(' · '),
          })}
          onClose={() => setPick('')}
          onPick={(it: PickerItem) => {
            const mode = pick
            setPick('')
            if (benefs.some((b) => b.id_salarie === it.id) && mode === 'supp')
              return
            const entry = {
              id_salarie: it.id,
              nom: it.label,
              mobile: '',
              mail: '',
              principal: mode === 'main',
            }
            if (mode === 'main') {
              set('benef_id', it.id)
              set('benef_nom', it.label)
              set('beneficiaires', [
                entry,
                ...benefs.filter((b) => !b.principal && b.id_salarie !== it.id),
              ])
            } else {
              set('beneficiaires', [...benefs, entry])
            }
          }}
        />
      )}
    </div>
  )
}

function Field({
  label, children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-c-ink-soft w-24 shrink-0">{label}</span>
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  )
}

function DateTime({
  label, dateK, timeK, data, set,
}: {
  label: string
  dateK: string
  timeK: string
  data: any
  set: (k: string, v: any) => void
}) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-c-ink-soft w-40 shrink-0 text-right">{label}</span>
      <input
        type="date"
        value={data[dateK] || ''}
        onChange={(e) => set(dateK, e.target.value)}
        className="px-2 py-1 border border-c-line-strong rounded-md text-xs"
      />
      <span className="text-c-ink-soft">à</span>
      <input
        type="time"
        value={data[timeK] || ''}
        onChange={(e) => set(timeK, e.target.value)}
        className="px-2 py-1 border border-c-line-strong rounded-md text-xs"
      />
    </div>
  )
}

function cap(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : ''
}
