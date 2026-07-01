/**
 * Fen_SocieteDocCourtage - Generer le contrat de courtage.
 *
 * Partie 1 (ce commit) : liste des docs de courtage disponibles
 * (regroupes par groupe operateur) + filtres Secteur + Date signature
 * + boutons Ticket Omaya / Export PDF (placeholders : le publipostage
 * DOCX + PDF + FTP + creation ticket TK_Liste arrivera en commit 2).
 *
 * cf Fen_SalarieDocRH (meme principe pour les documents RH salaries).
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  X, Loader2, Ticket, FileDown, FileText, Star,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'

const API_BASE = '/api/adm'

interface Doc {
  id_doc_courtage: string
  titre: string; info_cpl: string
  id_groupe_operateur: number; lib_groupe_operateur: string
  prioritaire: boolean
  id_ste: string; rs_interne_ste: string
  datecrea: string; modif_date: string
}

interface Props {
  idDistrib: string
  idGerant: number
  onClose: () => void
}

const shortDate = (iso: string): string =>
  !iso || iso.length < 10 ? '' : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

export default function GenerationContratModal({
  idDistrib, idGerant, onClose,
}: Props) {
  const [docs, setDocs] = useState<Doc[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string>('')
  const [secteur, setSecteur] = useState('')
  const [dateSign, setDateSign] = useState(new Date().toISOString().slice(0, 10))

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/distrib-courtage/${idDistrib}/docs-courtage`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      setDocs(await r.json())
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }, [idDistrib])

  useEffect(() => { void load() }, [load])

  // Regroupement par groupe_operateur (cf structure WinDev)
  const docsByGroup = useMemo(() => {
    const map: Record<string, Doc[]> = {}
    for (const d of docs) {
      const key = d.lib_groupe_operateur || '(sans groupe)'
      if (!map[key]) map[key] = []
      map[key].push(d)
    }
    return map
  }, [docs])

  const sel = docs.find(d => d.id_doc_courtage === selected)

  const [generating, setGenerating] = useState(false)

  const ticketOmaya = async () => {
    if (!sel) { showToast('Sélectionne un document.', 'info'); return }
    // Cf WinDev : secteur obligatoire sauf pour groupe 'Autre' (id 281474976710657)
    const GROUPE_AUTRE = 281474976710657
    if (!secteur.trim() && sel.id_groupe_operateur !== GROUPE_AUTRE) {
      showToast('Merci de renseigner les secteurs de prospection.', 'error')
      return
    }
    if (!dateSign) {
      showToast('Merci de renseigner une date de signature valide.', 'error')
      return
    }

    setGenerating(true)
    try {
      const r = await fetch(
        `${API_BASE}/distrib-courtage/generate-contrat`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            id_doc_courtage: parseInt(sel.id_doc_courtage, 10),
            id_distrib: 0,
            id_gerant: idGerant,
            secteur, date_signature: dateSign,
            date_avenant: '',
            creer_suivi: true,
          }).replace(
            // Hack : id_distrib bigint > 2^53, envoyer en string non JSON parsable
            '"id_distrib":0', `"id_distrib":${idDistrib}`,
          ),
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const cd = r.headers.get('content-disposition') || ''
      const m = /filename="?([^";]+)"?/.exec(cd)
      a.download = m ? m[1] : `contrat-${sel.id_doc_courtage}-${dateSign}.docx`
      document.body.appendChild(a); a.click()
      document.body.removeChild(a); URL.revokeObjectURL(url)
      showToast('Contrat généré et suivi enregistré', 'success')
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setGenerating(false) }
  }

  const exportPdf = () => {
    if (!sel) { showToast('Sélectionne un document.', 'info'); return }
    showToast('Export PDF : à venir (Fen_EditionDocCourtage)', 'info')
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-[70] flex items-center justify-center p-4"
         onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-[1000px] max-w-full max-h-[95vh] flex flex-col"
           onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-c-line">
          <h2 className="text-sm font-bold flex items-center gap-2">
            <FileText className="w-4 h-4 text-c-brand" />
            Liste des contrats de courtage disponibles
          </h2>
          <button onClick={onClose}
            className="p-1 hover:bg-c-surface-soft rounded text-c-ink-faint">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Filtres + actions */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-c-line-soft bg-c-surface-soft flex-wrap">
          <label className="text-c-ink-faint text-xs">Secteur</label>
          <input type="text" value={secteur} onChange={e => setSecteur(e.target.value)}
            placeholder="Secteurs de prospection"
            className="px-2 py-1 border border-c-line rounded text-xs h-7 min-w-[180px]" />
          <label className="text-c-ink-faint text-xs ml-2">Date de signature</label>
          <input type="date" value={dateSign} onChange={e => setDateSign(e.target.value)}
            className="px-2 py-1 border border-c-line rounded text-xs h-7" />
          <div className="flex-1" />
          <button type="button" onClick={ticketOmaya} disabled={!sel || generating}
            className="flex items-center gap-1.5 px-3 py-1 rounded bg-c-brand text-white text-xs hover:opacity-90 disabled:opacity-30">
            {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        : <Ticket className="w-3.5 h-3.5" />}
            Ticket Omaya
          </button>
          <button type="button" onClick={exportPdf} disabled={!sel}
            className="flex items-center gap-1.5 px-3 py-1 rounded border border-c-line text-c-ink-soft text-xs hover:bg-c-surface-soft disabled:opacity-30">
            <FileDown className="w-3.5 h-3.5" /> Export PDF
          </button>
        </div>

        {/* Liste des docs */}
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-5 h-5 animate-spin text-c-brand" />
            </div>
          ) : docs.length === 0 ? (
            <div className="text-center py-12 text-c-ink-faint-2 italic text-xs">
              Aucun document de courtage disponible.
            </div>
          ) : (
            <table className="w-full text-xs">
              <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0 z-10">
                <tr>
                  <th className="px-2 py-2 text-left w-8"></th>
                  <th className="px-2 py-2 text-left">Titre</th>
                  <th className="px-2 py-2 text-left w-64">Info Cplt</th>
                  <th className="px-2 py-2 text-left w-40">Société</th>
                  <th className="px-2 py-2 text-center w-20">Prioritaire</th>
                  <th className="px-2 py-2 text-left w-24">Modif</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(docsByGroup).map(([grp, list]) => (
                  <>
                    <tr key={`h-${grp}`} className="bg-c-brand/5 border-t border-c-line-soft">
                      <td colSpan={6} className="px-3 py-1 text-xs font-bold text-c-brand flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5" /> {grp}
                      </td>
                    </tr>
                    {list.map(d => (
                      <tr key={d.id_doc_courtage}
                        onClick={() => setSelected(d.id_doc_courtage)}
                        className={`cursor-pointer border-t border-c-line-soft ${
                          selected === d.id_doc_courtage
                            ? 'bg-c-brand/10' : 'hover:bg-c-surface-soft'
                        }`}>
                        <td className="px-2 py-1.5 text-center">
                          <input type="radio" checked={selected === d.id_doc_courtage}
                            onChange={() => setSelected(d.id_doc_courtage)} />
                        </td>
                        <td className="px-2 py-1.5 font-medium">{d.titre}</td>
                        <td className="px-2 py-1.5 truncate max-w-[300px]" title={d.info_cpl}>
                          {d.info_cpl || '—'}
                        </td>
                        <td className="px-2 py-1.5">{d.rs_interne_ste || '—'}</td>
                        <td className="px-2 py-1.5 text-center">
                          {d.prioritaire && (
                            <Star className="w-3.5 h-3.5 text-yellow-500 inline" fill="currentColor" />
                          )}
                        </td>
                        <td className="px-2 py-1.5">{shortDate(d.modif_date)}</td>
                      </tr>
                    ))}
                  </>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
