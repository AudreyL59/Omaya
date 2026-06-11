/**
 * Onglet 'Mutuelle' de la fiche salarie ADM.
 *
 * Transposition de la fenetre WinDev FI_SalarieMutuelle :
 *  - Formulaire : combo Mutuelle + checklists (Adhesion / Dossier /
 *    Att SS / RIB / Doc Envoyes / Recep. Certif) + statuts speciaux
 *    (N'adhere pas + jusqu'au, Resilie + le).
 *  - Tableau historique des tickets Demande Mutuelle.
 *  - Bouton Enregistrer (tooltip 'Derniere modif le X par Y').
 */

import { useCallback, useEffect, useState } from 'react'
import { Info, Loader2, Save } from 'lucide-react'

import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import CheckMark from '../CheckMark'
import {
  AdmCheckbox,
  COLOR_BG_SOFT,
  COLOR_BRUN,
  COLOR_PRIMARY,
} from '@shared/fiche/EmbaucheTab'

interface MutuelleRef {
  id_mutuelle: number
  lib_mutuelle: string
}

interface TicketRow {
  id_tk_liste: string
  date_crea: string
  op_lib: string
  cloturee: boolean
  demande_affiliation: boolean
  demande_affiliation_date: string
  info_cplt: string
}

interface MutuelleData {
  adhesion: boolean
  adhesion_date: string
  id_mutuelle: number
  mutuelle_dossier: boolean
  mutuelle_att_ss: boolean
  mutuelle_rib: boolean
  mutuelle_doc_envoyes: boolean
  mutuelle_recep_certif: boolean
  mutuelle_pas_adhesion: boolean
  mutuelle_pas_adhesion_jusquau: string
  mutuelle_resilie: boolean
  mutuelle_resilie_date: string
  modif_date: string
  modif_op_lib: string
  mutuelles: MutuelleRef[]
  tickets: TicketRow[]
}

interface Props {
  idSalarie: string
}

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

function fmtDateTime(iso: string): string {
  if (!iso || iso.length < 10) return ''
  const d = fmtDate(iso)
  if (iso.length < 16) return d
  return `${d} ${iso.slice(11, 16)}`
}

export default function MutuelleTab({ idSalarie }: Props) {
  const [data, setData] = useState<MutuelleData | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const reload = useCallback(async () => {
    if (!idSalarie) return
    setLoading(true)
    try {
      const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/mutuelle`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const j = (await r.json()) as MutuelleData
      setData(j)
    } catch (e) {
      showToast(`Échec chargement : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [idSalarie])

  useEffect(() => {
    void reload()
  }, [reload])

  const update = (patch: Partial<MutuelleData>) => {
    setData((prev) => (prev ? { ...prev, ...patch } : prev))
  }

  const handleSave = async () => {
    if (!data) return
    setSaving(true)
    try {
      const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/mutuelle`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          adhesion: data.adhesion,
          adhesion_date: data.adhesion_date,
          id_mutuelle: data.id_mutuelle,
          mutuelle_dossier: data.mutuelle_dossier,
          mutuelle_att_ss: data.mutuelle_att_ss,
          mutuelle_rib: data.mutuelle_rib,
          mutuelle_doc_envoyes: data.mutuelle_doc_envoyes,
          mutuelle_recep_certif: data.mutuelle_recep_certif,
          mutuelle_pas_adhesion: data.mutuelle_pas_adhesion,
          mutuelle_pas_adhesion_jusquau: data.mutuelle_pas_adhesion_jusquau,
          mutuelle_resilie: data.mutuelle_resilie,
          mutuelle_resilie_date: data.mutuelle_resilie_date,
        }),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      showToast('Informations enregistrées.', 'success')
      await reload()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading && !data) {
    return (
      <div className="flex items-center gap-2 text-sm" style={{ color: COLOR_BRUN }}>
        <Loader2 className="w-4 h-4 animate-spin" /> Chargement…
      </div>
    )
  }
  if (!data) return null

  const tooltipModif =
    data.modif_date
      ? `Dernière modif le ${fmtDateTime(data.modif_date)}` +
        (data.modif_op_lib ? ` par ${data.modif_op_lib}` : '')
      : ''

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Formulaire */}
      <div
        className="border rounded p-4"
        style={{ borderColor: COLOR_BG_SOFT, backgroundColor: '#FBF9F8' }}
      >
        <div className="grid grid-cols-2 gap-x-8 gap-y-3">
          {/* Col gauche */}
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <AdmCheckbox
                checked={data.adhesion}
                onChange={(v) => update({ adhesion: v })}
              />
              <span className="text-sm" style={{ color: COLOR_BRUN }}>
                Adhésion à la mutuelle
              </span>
              <select
                value={data.id_mutuelle}
                onChange={(e) => update({ id_mutuelle: Number(e.target.value) || 0 })}
                className="ml-auto px-2 py-1 border rounded text-sm bg-white"
                style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN, minWidth: 180 }}
              >
                <option value={0}>—</option>
                {data.mutuelles.map((m) => (
                  <option key={m.id_mutuelle} value={m.id_mutuelle}>
                    {m.lib_mutuelle}
                  </option>
                ))}
              </select>
            </div>
            <Field label="Depuis le">
              <input
                type="date"
                value={data.adhesion_date}
                onChange={(e) => update({ adhesion_date: e.target.value })}
                disabled={!data.adhesion}
                className="px-2 py-1 border rounded text-sm bg-white disabled:opacity-50"
                style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
              />
            </Field>

            <div className="flex items-center gap-2 pt-2">
              <AdmCheckbox
                checked={data.mutuelle_dossier}
                onChange={(v) => update({ mutuelle_dossier: v })}
              />
              <span className="text-sm" style={{ color: COLOR_BRUN }}>Dossier</span>
            </div>
            <div className="flex items-center gap-2">
              <AdmCheckbox
                checked={data.mutuelle_att_ss}
                onChange={(v) => update({ mutuelle_att_ss: v })}
              />
              <span className="text-sm" style={{ color: COLOR_BRUN }}>
                Attestation de sécu. Sociale
              </span>
            </div>
            <div className="flex items-center gap-2">
              <AdmCheckbox
                checked={data.mutuelle_rib}
                onChange={(v) => update({ mutuelle_rib: v })}
              />
              <span className="text-sm" style={{ color: COLOR_BRUN }}>RIB</span>
            </div>
            <div className="flex items-center gap-2">
              <AdmCheckbox
                checked={data.mutuelle_doc_envoyes}
                onChange={(v) => update({ mutuelle_doc_envoyes: v })}
              />
              <span className="text-sm" style={{ color: COLOR_BRUN }}>Doc Envoyés</span>
            </div>
            <div className="flex items-center gap-2">
              <AdmCheckbox
                checked={data.mutuelle_recep_certif}
                onChange={(v) => update({ mutuelle_recep_certif: v })}
              />
              <span className="text-sm" style={{ color: COLOR_BRUN }}>
                Récep. du Certificat
              </span>
            </div>
          </div>

          {/* Col droite */}
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <AdmCheckbox
                checked={data.mutuelle_pas_adhesion}
                onChange={(v) => update({ mutuelle_pas_adhesion: v })}
              />
              <span className="text-sm" style={{ color: COLOR_BRUN }}>N'adhère pas</span>
              <span className="text-sm ml-2" style={{ color: COLOR_BRUN }}>jusqu'au</span>
              <input
                type="date"
                value={data.mutuelle_pas_adhesion_jusquau}
                onChange={(e) =>
                  update({ mutuelle_pas_adhesion_jusquau: e.target.value })
                }
                disabled={!data.mutuelle_pas_adhesion}
                className="px-2 py-1 border rounded text-sm bg-white disabled:opacity-50"
                style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
              />
            </div>
            <div className="flex items-center gap-3">
              <AdmCheckbox
                checked={data.mutuelle_resilie}
                onChange={(v) => update({ mutuelle_resilie: v })}
              />
              <span className="text-sm" style={{ color: COLOR_BRUN }}>Résilié</span>
              <span className="text-sm ml-2" style={{ color: COLOR_BRUN }}>le</span>
              <input
                type="date"
                value={data.mutuelle_resilie_date}
                onChange={(e) => update({ mutuelle_resilie_date: e.target.value })}
                disabled={!data.mutuelle_resilie}
                className="px-2 py-1 border rounded text-sm bg-white disabled:opacity-50"
                style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
              />
            </div>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-3">
          {tooltipModif && (
            <span
              className="text-xs flex items-center gap-1"
              style={{ color: COLOR_BRUN, opacity: 0.7 }}
              title={tooltipModif}
            >
              <Info className="w-3.5 h-3.5" />
              {tooltipModif}
            </span>
          )}
          <div className="flex-1" />
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded text-white disabled:opacity-40"
            style={{ backgroundColor: COLOR_PRIMARY }}
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Enregistrer
          </button>
        </div>
      </div>

      {/* Historique tickets */}
      <div className="flex-1 flex flex-col gap-2 overflow-hidden">
        <h3 className="text-xs uppercase tracking-wider font-semibold" style={{ color: COLOR_BRUN }}>
          Historique des tickets Demande Mutuelle
        </h3>
        <div className="flex-1 border rounded overflow-hidden flex flex-col" style={{ borderColor: COLOR_BG_SOFT }}>
          <div
            className="grid items-center gap-2 px-3 py-2 text-xs font-semibold border-b"
            style={{
              gridTemplateColumns: '140px 160px 80px 110px 100px 1fr',
              color: COLOR_BRUN,
              backgroundColor: COLOR_BG_SOFT,
              borderColor: COLOR_BG_SOFT,
            }}
          >
            <div>Date créa Ticket</div>
            <div>Par</div>
            <div className="text-center">Clôturé</div>
            <div className="text-center">Affiliation</div>
            <div>Le</div>
            <div>InfoCplt</div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {(data.tickets || []).length === 0 && (
              <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
                Aucun ticket Demande Mutuelle.
              </div>
            )}
            {data.tickets.map((t) => (
              <div
                key={t.id_tk_liste}
                className="grid items-center gap-2 px-3 py-1.5 text-xs border-b"
                style={{
                  gridTemplateColumns: '140px 160px 80px 110px 100px 1fr',
                  borderColor: COLOR_BG_SOFT,
                  color: COLOR_BRUN,
                }}
              >
                <div>{fmtDateTime(t.date_crea)}</div>
                <div className="truncate" title={t.op_lib}>
                  {t.op_lib}
                </div>
                <div className="text-center"><CheckMark active={t.cloturee} /></div>
                <div className="text-center"><CheckMark active={t.demande_affiliation} /></div>
                <div>{fmtDate(t.demande_affiliation_date)}</div>
                <div className="truncate whitespace-pre-wrap" title={t.info_cplt}>
                  {t.info_cplt}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm w-24" style={{ color: COLOR_BRUN }}>
        {label}
      </span>
      {children}
    </div>
  )
}
