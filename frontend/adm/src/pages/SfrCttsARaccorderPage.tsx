/**
 * Fen_SFRCttaRacc - Suivi SFR > Ctts à raccorder.
 *
 * Liste les contrats SFR entre Du et Au avec un état planifié/payé,
 * pre-coche les contrats à relancer (Choix=1 si pas encore envoye OU
 * envoye > 7j) puis permet d'envoyer un mail demande RDV technicien
 * au BO SFR de chaque cluster en lot.
 */
import { useState } from 'react'
import {
  Search, Send, Loader2, ArrowLeft, CheckCircle2, XCircle, FileDown,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

const API_BASE = '/api/adm'

interface Ligne {
  id_contrat: string; num_bs: string
  nom: string; prenom: string; cp: string; ville: string
  code_vad: string; nom_cluster: string
  nom_sa: string; prenom_sa: string
  date_signature: string; date_validation: string
  date_raccordement: string; date_rdv_tech: string
  lib_etat: string; type_etat: number; type_install: number
  type_offre: number; type_vente: number; technologie: number
  option_dec: string; box8: boolean; nb_pts_payes: number
  mail_bo_envoye: boolean; mail_bo_date_envoi: string
  choix: number
}

interface SendResult {
  id_contrat: string; num_bs: string; ok: boolean; message: string
}

const todayIso = (): string => new Date().toISOString().slice(0, 10)
const monthAgoIso = (): string => {
  const d = new Date(); d.setMonth(d.getMonth() - 3)
  return d.toISOString().slice(0, 10)
}
const shortDate = (iso: string): string =>
  !iso || iso.length < 10 ? '' : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

export default function SfrCttsARaccorderPage() {
  useDocumentTitle('Ctts SFR à raccorder')
  const [du, setDu] = useState(monthAgoIso())
  const [au, setAu] = useState(todayIso())
  const [lignes, setLignes] = useState<Ligne[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [results, setResults] = useState<Map<string, SendResult>>(new Map())
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [testMode, setTestMode] = useState(false)

  const rechercher = async () => {
    if (du > au) { showToast('Dates incohérentes', 'error'); return }
    setLoading(true)
    setResults(new Map())
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/ctts-a-raccorder?du=${du}&au=${au}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const d: Ligne[] = await r.json()
      setLignes(d)
      // Preselectionne les lignes choix=1
      setSelected(new Set(d.filter(l => l.choix === 1).map(l => l.id_contrat)))
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }

  const toggleAll = () => {
    if (selected.size === lignes.length) setSelected(new Set())
    else setSelected(new Set(lignes.map(l => l.id_contrat)))
  }
  const toggle = (id: string) => {
    const s = new Set(selected)
    if (s.has(id)) s.delete(id); else s.add(id)
    setSelected(s)
  }

  const envoyerMails = async () => {
    if (selected.size === 0) {
      showToast('Aucune ligne sélectionnée.', 'info'); return
    }
    const ok = await showConfirm({
      title: `Envoyer ${selected.size} mail(s) ${testMode ? '(MODE TEST)' : 'aux BOs SFR'}`,
      message: testMode
        ? "En mode TEST, tous les mails partent à a.loudieux@exosphere.fr. Continuer ?"
        : `Vous allez envoyer ${selected.size} mail(s) aux BOs SFR. Continuer ?`,
    })
    if (!ok) return
    setSending(true)
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/ctts-a-raccorder/send-mails`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            ids_contrats: Array.from(selected).map(s => parseInt(s, 10)),
            test_mode: testMode,
          }),
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      const d: SendResult[] = await r.json()
      const m = new Map<string, SendResult>()
      for (const res of d) m.set(res.id_contrat, res)
      setResults(m)
      const okCount = d.filter(x => x.ok).length
      showToast(`${okCount}/${d.length} mail(s) envoyé(s)`,
        okCount === d.length ? 'success' : 'info')
      // Met à jour les lignes pour refléter l'envoi
      setLignes(prev => prev.map(l => {
        const r = m.get(l.id_contrat)
        if (r?.ok) {
          return { ...l, mail_bo_envoye: true,
                   mail_bo_date_envoi: new Date().toISOString().slice(0, 10) }
        }
        return l
      }))
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setSending(false) }
  }

  const exportXlsx = async () => {
    const { exportRowsToXlsx } = await import('@shared/production/_tableHelpers')
    exportRowsToXlsx(
      [
        { key: 'num_bs', label: 'NUM Ctt' },
        { key: 'date_signature', label: 'Date Signature' },
        { key: 'date_validation', label: 'Date Validation' },
        { key: 'date_raccordement', label: 'Date Raccordement' },
        { key: 'date_rdv_tech', label: 'Date RDV Tech' },
        { key: 'lib_etat', label: 'État' },
        { key: 'nom', label: 'Nom Client' },
        { key: 'prenom', label: 'Prénom Client' },
        { key: 'cp', label: 'CP' },
        { key: 'ville', label: 'Ville' },
        { key: 'nom_sa', label: 'Nom Vendeur' },
        { key: 'prenom_sa', label: 'Prénom Vendeur' },
        { key: 'nom_cluster', label: 'Cluster' },
        { key: 'code_vad', label: 'Code VAD' },
        { key: 'nb_pts_payes', label: 'nbPts Payés' },
      ],
      lignes as unknown as Array<Record<string, unknown>>,
      'ctts-sfr-a-raccorder', 'Ctts à raccorder',
    )
  }

  const rowBg = (l: Ligne): string => {
    const r = results.get(l.id_contrat)
    if (r?.ok) return 'bg-green-50'
    if (r && !r.ok) return 'bg-red-50'
    return 'hover:bg-c-surface-soft'
  }

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-110px)] text-c-ink">
      <div className="flex items-center gap-2 mb-3">
        <Link to=".." relative="path"
          className="p-1.5 hover:bg-c-surface-soft rounded text-c-ink-faint-2">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-lg font-bold flex-1">Contrats à raccorder</h1>
      </div>

      {/* Filtres */}
      <div className="flex items-end gap-3 mb-3 bg-white p-3 rounded-xl border border-c-line text-sm flex-wrap">
        <div>
          <label className="text-[10px] text-c-ink-faint">Du</label>
          <input type="date" value={du}
            onChange={e => setDu(e.target.value)}
            className="block px-2 py-1 border border-c-line rounded text-xs" />
        </div>
        <div>
          <label className="text-[10px] text-c-ink-faint">Au</label>
          <input type="date" value={au}
            onChange={e => setAu(e.target.value)}
            className="block px-2 py-1 border border-c-line rounded text-xs" />
        </div>
        <button type="button" onClick={rechercher} disabled={loading}
          className="flex items-center gap-2 px-4 py-1.5 bg-c-brand text-white rounded text-sm font-medium hover:opacity-90 disabled:opacity-50 h-8">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" />
                   : <Search className="w-4 h-4" />}
          Rechercher
        </button>

        <div className="flex-1" />

        <label className="flex items-center gap-1.5 text-xs text-c-ink-soft">
          <input type="checkbox" checked={testMode}
            onChange={e => setTestMode(e.target.checked)} />
          Mode test (mails vers Audrey)
        </label>

        <button type="button" onClick={envoyerMails}
          disabled={sending || selected.size === 0}
          className="flex items-center gap-2 px-4 py-1.5 bg-c-brand text-white rounded text-sm font-medium hover:opacity-90 disabled:opacity-50 h-8">
          {sending ? <Loader2 className="w-4 h-4 animate-spin" />
                   : <Send className="w-4 h-4" />}
          Envoyer {selected.size > 0 ? `(${selected.size})` : ''}
        </button>

        {lignes.length > 0 && (
          <button type="button" onClick={exportXlsx}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft h-8">
            <FileDown className="w-3.5 h-3.5" /> XLSX
          </button>
        )}
      </div>

      {/* Tableau */}
      <div className="bg-white rounded-xl border border-c-line overflow-hidden flex-1 flex flex-col">
        <div className="px-3 py-1.5 border-b border-c-line-soft text-xs text-c-ink-faint">
          {lignes.length} contrat(s) | {selected.size} sélectionné(s)
          {results.size > 0 && (
            <span className="ml-3">
              · OK : {Array.from(results.values()).filter(r => r.ok).length}
              · KO : {Array.from(results.values()).filter(r => !r.ok).length}
            </span>
          )}
        </div>
        <div className="flex-1 overflow-auto">
          <table className="w-full text-xs">
            <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0 z-10">
              <tr>
                <th className="px-2 py-2 text-center w-10">
                  <input type="checkbox"
                    checked={lignes.length > 0 && selected.size === lignes.length}
                    onChange={toggleAll} />
                </th>
                <th className="px-2 py-2 text-center w-10">Mail</th>
                <th className="px-2 py-2 text-left">Envoyé le</th>
                <th className="px-2 py-2 text-left">NUM Ctt</th>
                <th className="px-2 py-2 text-left">Signature</th>
                <th className="px-2 py-2 text-left">Validation</th>
                <th className="px-2 py-2 text-left">Raccord.</th>
                <th className="px-2 py-2 text-left">RDV Tech</th>
                <th className="px-2 py-2 text-left">État</th>
                <th className="px-2 py-2 text-left">Client</th>
                <th className="px-2 py-2 text-left">Ville</th>
                <th className="px-2 py-2 text-left">Vendeur</th>
                <th className="px-2 py-2 text-left">Cluster</th>
                <th className="px-2 py-2 text-right">nbPts</th>
                <th className="px-2 py-2 text-center w-6"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-c-line-soft">
              {lignes.length === 0 ? (
                <tr>
                  <td colSpan={15} className="text-center py-12 text-c-ink-faint-2 italic">
                    Aucun résultat — choisis dates puis Rechercher.
                  </td>
                </tr>
              ) : lignes.map(l => {
                const r = results.get(l.id_contrat)
                return (
                  <tr key={l.id_contrat} className={rowBg(l)}>
                    <td className="px-2 py-1.5 text-center">
                      <input type="checkbox"
                        checked={selected.has(l.id_contrat)}
                        onChange={() => toggle(l.id_contrat)} />
                    </td>
                    <td className="px-2 py-1.5 text-center">
                      {l.mail_bo_envoye && <CheckCircle2 className="w-3.5 h-3.5 text-c-brand inline" />}
                    </td>
                    <td className="px-2 py-1.5">{shortDate(l.mail_bo_date_envoi)}</td>
                    <td className="px-2 py-1.5 tabular-nums">{l.num_bs}</td>
                    <td className="px-2 py-1.5">{shortDate(l.date_signature)}</td>
                    <td className="px-2 py-1.5">{shortDate(l.date_validation)}</td>
                    <td className="px-2 py-1.5">{shortDate(l.date_raccordement)}</td>
                    <td className="px-2 py-1.5">{shortDate(l.date_rdv_tech)}</td>
                    <td className="px-2 py-1.5 max-w-[260px] truncate" title={l.lib_etat}>{l.lib_etat}</td>
                    <td className="px-2 py-1.5">{l.nom} {l.prenom}</td>
                    <td className="px-2 py-1.5">{l.cp} {l.ville}</td>
                    <td className="px-2 py-1.5">{l.nom_sa} {l.prenom_sa}</td>
                    <td className="px-2 py-1.5">{l.nom_cluster}</td>
                    <td className="px-2 py-1.5 text-right tabular-nums">{l.nb_pts_payes.toFixed(2)}</td>
                    <td className="px-2 py-1.5 text-center" title={r?.message}>
                      {r?.ok && <CheckCircle2 className="w-4 h-4 text-c-brand inline" />}
                      {r && !r.ok && <XCircle className="w-4 h-4 text-red-600 inline" />}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
