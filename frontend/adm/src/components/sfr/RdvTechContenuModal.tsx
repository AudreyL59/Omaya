/**
 * Modal 'Contenu ticket RDV Tech' — cf WinDev
 * OuvreSoeur(Fen_ContenuTicketCallSFR, id_tk_liste, "RDVTech").
 *
 * Different de TicketCallContenuModal (qui affiche un ticket de vente
 * SFR avec client + panier) : ici on affiche un ticket de retour RDV
 * Technicien FIBRE - pas de client, pas de panier, juste les infos
 * du retour + du contrat SFR associe.
 */
import { useEffect, useState } from 'react'
import { X, CalendarClock, FileText, Save, Loader2 } from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'

const API_BASE = '/api/adm'

interface Props {
  row: {
    id_tk_liste: string; id_contrat: string
    id_tk_retour_rdv_tech_fibre: string
    date_crea: string; date_cloture: string; cloturee: boolean
    lib_statut: string; vendeur: string
    num_bs: string; num_bs_sfr: string
    date_rdv_tech: string; periode_rdv_tech: string
    date_signature: string
    id_fibre_statut_rdv: number; lib_statut_rdv: string
    info_cplt: string
  }
  onClose: () => void
  onChanged?: () => void
}

interface StatutRdv { id_sfr_statut_rdv: number; lib_statut: string }

const shortDate = (iso: string): string =>
  !iso || iso.length < 10 ? '' : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

export default function RdvTechContenuModal({ row, onClose, onChanged }: Props) {
  const [statuts, setStatuts] = useState<StatutRdv[]>([])
  const [idStatut, setIdStatut] = useState<number>(row.id_fibre_statut_rdv)
  const [info, setInfo] = useState<string>(row.info_cplt ?? '')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetch(`${API_BASE}/suivi-sfr/rdv-tech/statuts`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then((d: StatutRdv[]) => setStatuts(Array.isArray(d) ? d : []))
  }, [])

  const save = async () => {
    setSaving(true)
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/rdv-tech/${row.id_tk_retour_rdv_tech_fibre}`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            id_fibre_statut_rdv: idStatut,
            info_cplt: info,
          }),
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      showToast('Enregistré', 'success')
      onChanged?.()
      onClose()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setSaving(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
         onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-[900px] max-w-full max-h-[90vh] flex flex-col"
           onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-c-line">
          <h2 className="text-sm font-bold flex items-center gap-2">
            <CalendarClock className="w-4 h-4 text-c-brand" />
            Contenu ticket RDV Tech
            <span className="text-xs text-c-ink-faint-2 font-normal">
              — {row.id_tk_liste}
            </span>
          </h2>
          <button onClick={onClose}
            className="p-1 hover:bg-c-surface-soft rounded text-c-ink-faint">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Barre infos ticket */}
        <div className="px-4 py-2 border-b border-c-line-soft bg-c-surface-soft text-xs text-c-ink-soft flex flex-wrap items-center gap-x-4 gap-y-1">
          <span><b>Créé le :</b> {shortDate(row.date_crea)}</span>
          <span><b>Statut :</b> {row.lib_statut}</span>
          <span><b>Créé par :</b> {row.vendeur}</span>
          {row.cloturee && (
            <span className="text-red-600"><b>Clôturé le :</b> {shortDate(row.date_cloture)}</span>
          )}
        </div>

        {/* Corps */}
        <div className="flex-1 overflow-auto p-4 space-y-4">
          {/* Bloc contrat SFR */}
          <section className="border border-c-line rounded-lg p-3">
            <h3 className="text-xs font-bold text-c-ink-faint uppercase tracking-wide mb-2 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5" /> Contrat SFR associé
            </h3>
            <div className="grid grid-cols-4 gap-3 text-xs">
              <InfoField label="NumBS Contrat" value={row.num_bs_sfr} />
              <InfoField label="Date Signature" value={shortDate(row.date_signature)} />
              <InfoField label="Date RDV Tech" value={shortDate(row.date_rdv_tech)} />
              <InfoField label="Période RDV" value={row.periode_rdv_tech} />
            </div>
          </section>

          {/* Bloc retour RDV Tech (edition) */}
          <section className="border border-c-line rounded-lg p-3">
            <h3 className="text-xs font-bold text-c-ink-faint uppercase tracking-wide mb-2 flex items-center gap-1.5">
              <CalendarClock className="w-3.5 h-3.5" /> Retour RDV Tech
            </h3>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-[10px] text-c-ink-faint">NumBS Retour</label>
                <div className="px-2 py-1 border border-c-line rounded bg-c-surface-soft h-7 flex items-center">
                  {row.num_bs || '—'}
                </div>
              </div>
              <div>
                <label className="text-[10px] text-c-ink-faint">Statut RDV</label>
                <select value={idStatut}
                  onChange={e => setIdStatut(parseInt(e.target.value, 10) || 0)}
                  className="w-full px-2 py-1 border border-c-line rounded text-xs h-7">
                  <option value={0}>— Non défini —</option>
                  {statuts.map(s => (
                    <option key={s.id_sfr_statut_rdv} value={s.id_sfr_statut_rdv}>
                      {s.lib_statut}
                    </option>
                  ))}
                </select>
              </div>
              <div className="col-span-2">
                <label className="text-[10px] text-c-ink-faint">Info complémentaire</label>
                <textarea value={info} onChange={e => setInfo(e.target.value)}
                  rows={4}
                  className="w-full px-2 py-1 border border-c-line rounded text-xs" />
              </div>
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-4 py-3 border-t border-c-line">
          <button type="button" onClick={onClose}
            className="px-3 py-1.5 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft">
            Fermer
          </button>
          <button type="button" onClick={save} disabled={saving}
            className="flex items-center gap-2 px-3 py-1.5 rounded bg-c-brand text-white text-xs font-medium hover:opacity-90 disabled:opacity-50">
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                     : <Save className="w-3.5 h-3.5" />}
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  )
}

function InfoField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <label className="text-[10px] text-c-ink-faint block">{label}</label>
      <div className="px-2 py-1 border border-c-line rounded bg-c-surface-soft h-7 flex items-center truncate">
        {value || '—'}
      </div>
    </div>
  )
}
