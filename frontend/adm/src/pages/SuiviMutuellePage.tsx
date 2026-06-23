/**
 * Fen_SuiviMutuelle (WinDev) - Salariés -> Adhésion mutuelle entreprise.
 *
 * 2 onglets : Actifs / Sortants. Tableau avec 5 checkboxes par ligne
 * (Dossier, Att SS, RIB, Doc envoyés, Récep certif).
 * Toggle d'une checkbox -> PUT /suivi-mutuelle/{id} immédiat.
 * Quand 'Doc envoyés' = true -> le salarié sort de la liste (filtre
 * backend).
 */

import { useCallback, useEffect, useState } from 'react'
import { HeartPulse, Loader2 } from 'lucide-react'
import { getToken } from '@/api'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { showToast } from '@shared/ui/dialog'

interface MutuelleRow {
  id_salarie: string
  nom: string
  prenom: string
  date_debut: string
  id_ste: number
  rs_interne: string
  lib_poste: string
  en_pause: boolean
  mutuelle_dossier: boolean
  mutuelle_att_ss: boolean
  mutuelle_rib: boolean
  mutuelle_doc_envoyes: boolean
  mutuelle_recep_certif: boolean
}

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

function fmtDate(s: string): string {
  if (!s || s.length < 10) return ''
  return `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}`
}

type Tab = 'actifs' | 'sortants'

export default function SuiviMutuellePage() {
  useDocumentTitle('Adhésion mutuelle')
  const [tab, setTab] = useState<Tab>('actifs')
  const [rows, setRows] = useState<MutuelleRow[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState('')

  const reload = useCallback(() => {
    setLoading(true)
    const url = tab === 'actifs'
      ? '/api/adm/suivi-mutuelle/actifs'
      : '/api/adm/suivi-mutuelle/sortants'
    fetch(url, { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => (r.ok ? r.json() : []))
      .then((d) => setRows(Array.isArray(d) ? d : []))
      .finally(() => setLoading(false))
  }, [tab])

  useEffect(() => { reload() }, [reload])

  const toggleFlag = async (row: MutuelleRow, flag: keyof MutuelleRow) => {
    const newVal = !row[flag]
    const next = { ...row, [flag]: newVal }
    // Optimistic update
    setRows((rs) => rs.map((r) => r.id_salarie === row.id_salarie ? next : r))
    try {
      const r = await fetch(`/api/adm/suivi-mutuelle/${row.id_salarie}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          mutuelle_dossier: next.mutuelle_dossier,
          mutuelle_att_ss: next.mutuelle_att_ss,
          mutuelle_rib: next.mutuelle_rib,
          mutuelle_doc_envoyes: next.mutuelle_doc_envoyes,
          mutuelle_recep_certif: next.mutuelle_recep_certif,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
      // Si 'docs envoyes' devient TRUE -> le salarie sort de la liste
      if (flag === 'mutuelle_doc_envoyes' && newVal) {
        setRows((rs) => rs.filter((x) => x.id_salarie !== row.id_salarie))
      }
    } catch (e) {
      // Rollback
      setRows((rs) => rs.map((r) => r.id_salarie === row.id_salarie ? row : r))
      showToast(`Échec : ${(e as Error).message}`, 'error')
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto font-normal space-y-4">
      <div className="flex items-center gap-3">
        <HeartPulse className="w-6 h-6" style={{ color: COL_BRUN }} />
        <h1 className="text-xl font-bold flex-1" style={{ color: COL_BRUN }}>
          Adhésion mutuelle entreprise
        </h1>
        <div className="flex items-center rounded overflow-hidden"
             style={{ border: `1px solid ${COL_BORDER}` }}>
          {([
            { v: 'actifs' as Tab, l: 'Actifs' },
            { v: 'sortants' as Tab, l: 'Sortants' },
          ]).map((o) => {
            const active = tab === o.v
            return (
              <button key={o.v} type="button" onClick={() => setTab(o.v)}
                      className="px-4 py-1.5 text-sm"
                      style={{
                        backgroundColor: active ? COL_PRIMARY : 'white',
                        color: active ? 'white' : COL_BRUN,
                        fontWeight: active ? 600 : 400,
                      }}>
                {o.l}
              </button>
            )
          })}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border overflow-hidden"
           style={{ borderColor: COL_BORDER }}>
        {loading ? (
          <div className="p-10 flex justify-center">
            <Loader2 className="w-5 h-5 animate-spin text-[#A68D8A]" />
          </div>
        ) : rows.length === 0 ? (
          <div className="p-10 text-center text-sm italic text-[#A68D8A]">
            Aucun salarié dans cet onglet.
          </div>
        ) : (
          <div className="overflow-auto" style={{ maxHeight: 'calc(85vh - 140px)' }}>
            <table className="w-full text-xs">
              <thead className="sticky top-0" style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                <tr>
                  <th className="px-2 py-2 text-left">Nom Prénom</th>
                  <th className="px-2 py-2 text-left w-28">Date début</th>
                  <th className="px-2 py-2 text-left">Société</th>
                  <th className="px-2 py-2 text-left">Emploi</th>
                  <th className="px-2 py-2 text-center w-16">Dossier</th>
                  <th className="px-2 py-2 text-center w-16">Att SS</th>
                  <th className="px-2 py-2 text-center w-12">RIB</th>
                  <th className="px-2 py-2 text-center w-20">Doc envoyés</th>
                  <th className="px-2 py-2 text-center w-20">Récep certif</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const isSel = selected === r.id_salarie
                  return (
                    <tr key={r.id_salarie}
                        onClick={() => setSelected(r.id_salarie)}
                        className="cursor-pointer border-b"
                        style={{
                          backgroundColor: isSel ? COL_PRIMARY_LIGHT
                            : r.en_pause ? COL_BG_SOFT : 'white',
                          color: isSel ? 'white' : COL_BRUN,
                          borderColor: COL_BORDER,
                        }}>
                      <td className="px-2 py-1 font-semibold">
                        {r.nom} {r.prenom}
                        {r.en_pause && <span className="ml-2 text-xs italic">(en pause)</span>}
                      </td>
                      <td className="px-2 py-1">{fmtDate(r.date_debut)}</td>
                      <td className="px-2 py-1">{r.rs_interne}</td>
                      <td className="px-2 py-1">{r.lib_poste}</td>
                      <td className="px-2 py-1 text-center">
                        <input type="checkbox" checked={r.mutuelle_dossier}
                               onClick={(e) => e.stopPropagation()}
                               onChange={() => toggleFlag(r, 'mutuelle_dossier')} />
                      </td>
                      <td className="px-2 py-1 text-center">
                        <input type="checkbox" checked={r.mutuelle_att_ss}
                               onClick={(e) => e.stopPropagation()}
                               onChange={() => toggleFlag(r, 'mutuelle_att_ss')} />
                      </td>
                      <td className="px-2 py-1 text-center">
                        <input type="checkbox" checked={r.mutuelle_rib}
                               onClick={(e) => e.stopPropagation()}
                               onChange={() => toggleFlag(r, 'mutuelle_rib')} />
                      </td>
                      <td className="px-2 py-1 text-center">
                        <input type="checkbox" checked={r.mutuelle_doc_envoyes}
                               onClick={(e) => e.stopPropagation()}
                               onChange={() => toggleFlag(r, 'mutuelle_doc_envoyes')} />
                      </td>
                      <td className="px-2 py-1 text-center">
                        <input type="checkbox" checked={r.mutuelle_recep_certif}
                               onClick={(e) => e.stopPropagation()}
                               onChange={() => toggleFlag(r, 'mutuelle_recep_certif')} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="text-xs italic" style={{ color: COL_BRUN }}>
        {rows.length} salarié(s) · Cocher 'Doc envoyés' fait sortir le salarié de la liste.
      </div>
    </div>
  )
}
