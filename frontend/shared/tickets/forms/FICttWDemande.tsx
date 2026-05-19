import { useCallback, useEffect, useState } from 'react'
import { Download, FileText, Loader2, Save } from 'lucide-react'

import type { FIProps } from './index'

// FI_CttW_Demande (type 40) — Contrat W : Demande.
// Gauche « Documents Fournis » : casier (lecture) + infos mutuelle
// (même bloc que FI_CttW Plan 1). Droite « Documents à Fournir » :
// table tk_demandecttw_doc, aperçu FTP au clic.
export default function FICttWDemande({ apiBase, getToken, idTicket }: FIProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [openingDoc, setOpeningDoc] = useState('')

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
    setData((d: any) => ({ ...d, [k]: v }))

  const post = async (body: any): Promise<boolean> => {
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
        window.alert(`Erreur : ${e?.detail || resp.status}`)
        return false
      }
      reload()
      return true
    } catch {
      window.alert('Erreur réseau.')
      return false
    } finally {
      setSaving(false)
    }
  }

  const openDoc = async (nom: string) => {
    if (!nom) return
    setOpeningDoc(nom)
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
      setOpeningDoc('')
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
        Aucune demande de contrat W pour ce ticket.
      </div>
    )
  }

  const docs: any[] = data.documents || []

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Type de Contrat demandé */}
      <div className="flex items-center gap-3 shrink-0">
        <span className="text-sm font-semibold text-c-ink shrink-0">
          Type de Contrat demandé
        </span>
        <input
          readOnly
          value={data.type_contrat || ''}
          className="flex-1 px-2 py-1 border border-c-line-strong rounded-md text-sm bg-c-surface-soft text-c-ink"
        />
      </div>

      <div className="flex gap-6 flex-1 min-h-0">
        {/* Documents Fournis */}
        <div className="w-80 shrink-0 space-y-2 overflow-y-auto pr-1">
          <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide">
            Documents Fournis
          </h3>

          <Chk
            label="Casier judiciaire"
            checked={!!data.casier_judiciaire}
            readOnly
          />

          {data.mutuelle_found === false ? (
            <div className="text-sm text-c-ink-faint">
              Pas de fiche mutuelle pour ce salarié.
            </div>
          ) : (
            <>
              <Chk
                label="Adhésion à la mutuelle"
                checked={!!data.adhesion}
                onChange={(v) => set('adhesion', v)}
              />
              <DateF
                label="Date d'adhésion"
                value={data.adhesion_date}
                onChange={(v) => set('adhesion_date', v)}
              />
              <select
                value={data.id_mutuelle || 0}
                onChange={(e) => set('id_mutuelle', Number(e.target.value))}
                className="w-full px-2 py-1 border border-c-line-strong rounded-md text-sm bg-white"
              >
                <option value={0}>— Mutuelle —</option>
                {(data.mutuelles || []).map((m: any) => (
                  <option key={m.id} value={m.id}>{m.lib}</option>
                ))}
              </select>
              <Chk
                label="Mutuelle Dossier"
                checked={!!data.mutuelle_dossier}
                onChange={(v) => set('mutuelle_dossier', v)}
              />
              <Chk
                label="Att SS"
                checked={!!data.att_ss}
                onChange={(v) => set('att_ss', v)}
              />
              <Chk
                label="RIB"
                checked={!!data.rib}
                onChange={(v) => set('rib', v)}
              />
              <Chk
                label="Docs Envoyés"
                checked={!!data.docs_envoyes}
                onChange={(v) => set('docs_envoyes', v)}
              />
              <Chk
                label="Récep. Certificat"
                checked={!!data.recep_certif}
                onChange={(v) => set('recep_certif', v)}
              />
              <Chk
                label="N'adhère pas"
                checked={!!data.pas_adhesion}
                onChange={(v) => set('pas_adhesion', v)}
              />
              <DateF
                label="Jusqu'au"
                value={data.pas_adhesion_jusquau}
                onChange={(v) => set('pas_adhesion_jusquau', v)}
              />
              <Chk
                label="Résilié"
                checked={!!data.resilie}
                onChange={(v) => set('resilie', v)}
              />
              <DateF
                label="Le"
                value={data.resilie_date}
                onChange={(v) => set('resilie_date', v)}
              />

              <button
                onClick={() =>
                  post({
                    action: 'mutuelle',
                    id_salarie: data.id_salarie,
                    adhesion: data.adhesion,
                    adhesion_date: data.adhesion_date,
                    id_mutuelle: data.id_mutuelle,
                    mutuelle_dossier: data.mutuelle_dossier,
                    att_ss: data.att_ss,
                    rib: data.rib,
                    docs_envoyes: data.docs_envoyes,
                    recep_certif: data.recep_certif,
                    pas_adhesion: data.pas_adhesion,
                    pas_adhesion_jusquau: data.pas_adhesion_jusquau,
                    resilie: data.resilie,
                    resilie_date: data.resilie_date,
                  })
                }
                disabled={saving}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50 transition-all"
              >
                {saving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                Enregistrer les infos mutuelle
              </button>
            </>
          )}

          <hr className="border-c-line" />

          <button
            disabled
            title="Dépend du module « Génération doc / Ajout salarié » (Fen_SalariéDocRH non encore transposée)"
            className="w-full px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold opacity-40 cursor-not-allowed"
          >
            Générer le contrat de travail
          </button>
          <p className="text-[11px] text-c-ink-faint leading-tight">
            Génération à venir : dépend du module « Ajout d'un salarié »
            (fenêtre WinDev Fen_SalariéDocRH non encore fournie).
          </p>
        </div>

        {/* Documents à Fournir */}
        <div className="flex-1 min-w-0 flex flex-col min-h-0">
          <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide mb-2 shrink-0">
            Documents à Fournir
          </h3>
          <div className="flex-1 min-h-0 border border-c-line rounded-lg overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-c-surface-soft sticky top-0">
                <tr className="text-left text-c-ink-soft">
                  <th className="px-3 py-2 w-16 text-center">Envoyé</th>
                  <th className="px-3 py-2">Document</th>
                  <th className="px-3 py-2 w-10" />
                </tr>
              </thead>
              <tbody>
                {docs.length === 0 ? (
                  <tr>
                    <td
                      colSpan={3}
                      className="px-3 py-6 text-center text-c-ink-faint"
                    >
                      Aucun document.
                    </td>
                  </tr>
                ) : (
                  docs.map((d) => {
                    const clickable = !!d.nom_fichier
                    return (
                      <tr
                        key={d.id}
                        onClick={() => clickable && openDoc(d.nom_fichier)}
                        className={
                          'border-t border-c-line ' +
                          (clickable
                            ? 'cursor-pointer hover:bg-c-brand-soft'
                            : 'text-c-ink-faint')
                        }
                      >
                        <td className="px-3 py-2 text-center">
                          <input
                            type="checkbox"
                            checked={!!d.present}
                            readOnly
                            className="w-4 h-4 accent-c-brand"
                          />
                        </td>
                        <td className="px-3 py-2 text-c-ink">
                          {d.type_doc || d.nom_fichier || '—'}
                        </td>
                        <td className="px-3 py-2 text-c-ink-icon">
                          {clickable &&
                            (openingDoc === d.nom_fichier ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <FileText className="w-4 h-4" />
                            ))}
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] text-c-ink-faint mt-1 flex items-center gap-1 shrink-0">
            <Download className="w-3 h-3" />
            Cliquer une ligne pour ouvrir le document fourni.
          </p>
        </div>
      </div>
    </div>
  )
}

function Chk({
  label,
  checked,
  onChange,
  readOnly,
}: {
  label: string
  checked: boolean
  onChange?: (v: boolean) => void
  readOnly?: boolean
}) {
  return (
    <label
      className={
        'flex items-center gap-2 text-sm text-c-ink ' +
        (readOnly ? '' : 'cursor-pointer')
      }
    >
      <input
        type="checkbox"
        checked={checked}
        readOnly={readOnly}
        onChange={(e) => onChange && onChange(e.target.checked)}
        className={
          'w-4 h-4 accent-c-brand ' +
          (readOnly ? '' : 'cursor-pointer')
        }
      />
      {label}
    </label>
  )
}

function DateF({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-c-ink-soft w-28 shrink-0">{label}</span>
      <input
        type="date"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        className="flex-1 px-2 py-1 border border-c-line-strong rounded-md text-xs"
      />
    </div>
  )
}
