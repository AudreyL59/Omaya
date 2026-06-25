/**
 * Fen_CVPresaisis (shared) — liste des mails CV recus a traiter.
 *
 * Layout : filtres a gauche + tableau a droite avec actions par ligne
 * (voir contenu / convertir en CV / supprimer le mail). Toolbar du
 * tableau : 'Supprimer la selection'. Footer : compteurs.
 */

import { useCallback, useEffect, useState } from 'react'
import {
  FileSearch, FileText, Filter, Loader2, Mail, Trash2,
} from 'lucide-react'
import { getToken } from '@/api'
import { showConfirm, showToast } from '../ui/dialog'
import CvPresaisiContenuModal from './CvPresaisiContenuModal'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface ComboItem { id: string; label: string }
interface SourceItem { adr: string; id_ste: string; id_cv_poste: string }

interface MailRow {
  id_mail: string
  id_cv: string
  nom_prenom: string
  mail_cand: string
  gsm: string
  ville_cand: string
  cp_cand: string
  mail_source: string
  date_mail: string
  id_ste: string
  id_annonceur: string
  id_cvposte: string
  is_converti: boolean
}

interface ListResult {
  rows: MailRow[]
  nb_a_traiter: number
  nb_convertis: number
}

interface CvPresaisisPageProps {
  apiBase: string
  onOpenFiche: (idCv: string) => void
}

const defaultDeb = (): string => {
  const d = new Date(); d.setDate(d.getDate() - 1)
  return d.toISOString().slice(0, 10)
}

const fmtDateTime = (iso: string): string => {
  if (!iso) return ''
  const [d, t] = iso.split(' ')
  if (!d) return iso
  const [y, m, day] = d.split('-')
  return `${day}/${m}/${y} ${(t || '').slice(0, 5)}`
}

export default function CvPresaisisPage({
  apiBase, onOpenFiche,
}: CvPresaisisPageProps) {
  // Filtres
  const [saisisDeb, setSaisisDeb] = useState(defaultDeb())
  const [saisisFin, setSaisisFin] = useState(new Date().toISOString().slice(0, 10))
  const [idSte, setIdSte] = useState('')
  const [idPoste, setIdPoste] = useState('')
  const [idAnnonceur, setIdAnnonceur] = useState('')
  const [mailSrc, setMailSrc] = useState('')
  const [mode, setMode] = useState<'a_traiter' | 'convertis' | 'supprimes'>('a_traiter')

  // Combos
  const [societes, setSocietes] = useState<ComboItem[]>([])
  const [postes, setPostes] = useState<ComboItem[]>([])
  const [annonceurs, setAnnonceurs] = useState<ComboItem[]>([])
  const [sources, setSources] = useState<SourceItem[]>([])

  // Donnees
  const [data, setData] = useState<ListResult>({
    rows: [], nb_a_traiter: 0, nb_convertis: 0,
  })
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [contentMail, setContentMail] = useState<string>('')   // id_mail dont on affiche le contenu

  // Combos load
  useEffect(() => {
    const h = { headers: { Authorization: `Bearer ${getToken()}` } }
    Promise.all([
      fetch(`${apiBase}/recrutement/cv/combos/societes`, h).then(r => r.json()),
      fetch(`${apiBase}/recrutement/cv/combos/postes`, h).then(r => r.json()),
      fetch(`${apiBase}/recrutement/cv/combos/annonceurs`, h).then(r => r.json()),
      fetch(`${apiBase}/recrutement/cv/cv-presaisis/sources`, h).then(r => r.json()),
    ]).then(([s, p, a, src]) => {
      setSocietes(s || []); setPostes(p || []); setAnnonceurs(a || [])
      setSources(src || [])
    })
  }, [apiBase])

  const search = useCallback(() => {
    setLoading(true)
    const q = new URLSearchParams({
      saisis_deb: saisisDeb, saisis_fin: saisisFin,
      id_ste: idSte, id_cvposte: idPoste, id_elem_source: idAnnonceur,
      adr_mail_rh: mailSrc, mode,
    })
    fetch(`${apiBase}/recrutement/cv/cv-presaisis?${q.toString()}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : { rows: [], nb_a_traiter: 0, nb_convertis: 0 })
      .then(setData)
      .finally(() => setLoading(false))
  }, [apiBase, saisisDeb, saisisFin, idSte, idPoste, idAnnonceur, mailSrc, mode])

  useEffect(() => { search() }, [search])

  const toggleSel = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }
  const toggleAll = () => {
    if (selected.size === data.rows.length) setSelected(new Set())
    else setSelected(new Set(data.rows.map(r => r.id_mail)))
  }

  const deleteMail = async (id: string) => {
    const ok = await showConfirm({
      title: 'Supprimer ce mail ?',
      message: 'Vous êtes sur le point de supprimer ce mail. Souhaitez-vous continuer ?',
      confirmLabel: 'Supprimer',
    })
    if (!ok) return
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/cv-presaisis/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast('Mail supprimé.', 'success')
      search()
    } catch (e) { showToast(`Erreur : ${(e as Error).message}`, 'error') }
  }

  const bulkDelete = async () => {
    if (selected.size === 0) {
      showToast('Sélectionne au moins un mail.', 'info'); return
    }
    const ok = await showConfirm({
      title: 'Supprimer la sélection ?',
      message: `Vous êtes sur le point de supprimer ${selected.size} mail(s). Souhaitez-vous continuer ?`,
      confirmLabel: 'Supprimer',
    })
    if (!ok) return
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/cv-presaisis/bulk-delete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ ids: Array.from(selected) }),
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast(`${selected.size} mail(s) supprimé(s).`, 'success')
      setSelected(new Set()); search()
    } catch (e) { showToast(`Erreur : ${(e as Error).message}`, 'error') }
  }

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-120px)]"
         style={{ color: COL_BRUN }}>
      <h1 className="text-xl font-bold mb-3">Liste des CV pré-saisis</h1>

      <div className="flex-1 flex gap-3 min-h-0">
        {/* Filtres */}
        <div className="w-72 shrink-0 border rounded p-3 space-y-2 overflow-y-auto"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          <Row label="Saisis entre le">
            <input type="date" value={saisisDeb}
                   onChange={e => setSaisisDeb(e.target.value)}
                   className="w-full px-2 py-1.5 rounded border text-sm"
                   style={{ borderColor: COL_BORDER }} />
          </Row>
          <Row label="Et le">
            <input type="date" value={saisisFin}
                   onChange={e => setSaisisFin(e.target.value)}
                   className="w-full px-2 py-1.5 rounded border text-sm"
                   style={{ borderColor: COL_BORDER }} />
          </Row>
          <Row label="Poste visé">
            <Select value={idPoste} onChange={setIdPoste} options={postes} />
          </Row>
          <Row label="Société">
            <Select value={idSte} onChange={setIdSte} options={societes} />
          </Row>
          <Row label="Annonceur">
            <Select value={idAnnonceur} onChange={setIdAnnonceur}
                    options={annonceurs} />
          </Row>
          <Row label="Boite Mail">
            <select value={mailSrc} onChange={e => setMailSrc(e.target.value)}
                    className="w-full px-2 py-1.5 rounded border text-sm"
                    style={{ borderColor: COL_BORDER }}>
              <option value="">—</option>
              {sources.map(s => (
                <option key={s.adr} value={s.adr}>{s.adr}</option>
              ))}
            </select>
          </Row>
          <Row label="Afficher">
            <select value={mode}
                    onChange={e => setMode(e.target.value as 'a_traiter' | 'convertis' | 'supprimes')}
                    className="w-full px-2 py-1.5 rounded border text-sm"
                    style={{ borderColor: COL_BORDER }}>
              <option value="a_traiter">À traiter</option>
              <option value="convertis">Convertis en CV</option>
              <option value="supprimes">Supprimés sans conversion</option>
            </select>
          </Row>
          <button type="button" onClick={search}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded text-white text-sm mt-2"
                  style={{ backgroundColor: COL_PRIMARY }}>
            <Filter className="w-4 h-4" />
            Filtrer
          </button>
          <div className="mt-4 space-y-1 text-xs"
               style={{ color: COL_BRUN }}>
            <div className="flex justify-between"><span>nb CV saisis</span>
              <strong>{data.nb_convertis.toLocaleString('fr-FR')}</strong></div>
            <div className="flex justify-between"><span>nb Mail à traiter</span>
              <strong>{data.nb_a_traiter.toLocaleString('fr-FR')}</strong></div>
          </div>
        </div>

        {/* Tableau */}
        <div className="flex-1 flex flex-col min-w-0 border rounded"
             style={{ borderColor: COL_BORDER }}>
          <div className="px-3 py-2 flex items-center gap-2 border-b"
               style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
            <button type="button" onClick={bulkDelete}
                    className="flex items-center gap-1 px-3 py-1.5 rounded border text-xs"
                    style={{
                      borderColor: COL_BORDER,
                      backgroundColor: '#B91C1C', color: 'white',
                    }}>
              <Trash2 className="w-3.5 h-3.5" />
              Supprimer la sélection
              {selected.size > 0 && (
                <span className="ml-1">({selected.size})</span>
              )}
            </button>
            <div className="flex-1" />
            <span className="text-xs italic" style={{ color: '#A68D8A' }}>
              nb CV : {data.rows.length.toLocaleString('fr-FR')}
              {data.rows.length === 2000 && ' (max)'}
            </span>
          </div>

          <div className="flex-1 overflow-auto">
            {loading ? (
              <div className="p-8 flex justify-center">
                <Loader2 className="w-6 h-6 animate-spin"
                         style={{ color: COL_PRIMARY }} />
              </div>
            ) : data.rows.length === 0 ? (
              <p className="p-8 text-center italic"
                 style={{ color: '#A68D8A' }}>
                Aucun mail correspondant aux filtres.
              </p>
            ) : (
              <table className="w-full text-xs">
                <thead className="sticky top-0"
                       style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                  <tr>
                    <th className="px-2 py-2 w-8">
                      <input type="checkbox"
                             checked={selected.size === data.rows.length && data.rows.length > 0}
                             onChange={toggleAll} />
                    </th>
                    <th className="px-2 py-2 text-left w-24">Action</th>
                    <th className="px-2 py-2 text-left">MailSource</th>
                    <th className="px-2 py-2 text-left">Date</th>
                    <th className="px-2 py-2 text-left">NOM Prénom</th>
                    <th className="px-2 py-2 text-left">Ville Cand.</th>
                    <th className="px-2 py-2 text-left">CP</th>
                    <th className="px-2 py-2 text-left">Mail Cand.</th>
                    <th className="px-2 py-2 text-left">GSM</th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map(r => {
                    const isSel = selected.has(r.id_mail)
                    return (
                      <tr key={r.id_mail} className="border-b"
                          style={{
                            borderColor: COL_BORDER,
                            backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                            color: isSel ? 'white' : COL_BRUN,
                          }}>
                        <td className="px-2 py-1.5 text-center">
                          <input type="checkbox" checked={isSel}
                                 onChange={() => toggleSel(r.id_mail)} />
                        </td>
                        <td className="px-2 py-1.5">
                          <div className="flex gap-1">
                            {r.is_converti && (
                              <button type="button"
                                      onClick={() => onOpenFiche(r.id_cv)}
                                      title="Ouvrir la fiche CV"
                                      className="p-1 rounded hover:bg-green-100">
                                <FileText className="w-3.5 h-3.5"
                                          style={{ color: isSel ? 'white' : '#16a34a' }} />
                              </button>
                            )}
                            <button type="button"
                                    onClick={() => setContentMail(r.id_mail)}
                                    title="Voir le contenu du mail"
                                    className="p-1 rounded hover:bg-blue-100">
                              <FileSearch className="w-3.5 h-3.5"
                                          style={{ color: isSel ? 'white' : COL_PRIMARY }} />
                            </button>
                            <button type="button"
                                    onClick={() => deleteMail(r.id_mail)}
                                    title="Supprimer ce mail"
                                    className="p-1 rounded hover:bg-red-100">
                              <Trash2 className="w-3.5 h-3.5"
                                      style={{ color: isSel ? 'white' : '#B91C1C' }} />
                            </button>
                          </div>
                        </td>
                        <td className="px-2 py-1.5 truncate max-w-[180px]"
                            title={r.mail_source}>
                          <Mail className="w-3 h-3 inline mr-1" />
                          {r.mail_source}
                        </td>
                        <td className="px-2 py-1.5">{fmtDateTime(r.date_mail)}</td>
                        <td className="px-2 py-1.5 font-semibold">{r.nom_prenom}</td>
                        <td className="px-2 py-1.5">{r.ville_cand}</td>
                        <td className="px-2 py-1.5">{r.cp_cand}</td>
                        <td className="px-2 py-1.5 truncate max-w-[180px]"
                            title={r.mail_cand}>{r.mail_cand}</td>
                        <td className="px-2 py-1.5">{r.gsm}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {contentMail && (
        <CvPresaisiContenuModal apiBase={apiBase} idMail={contentMail}
                                onClose={(newCvId, openFiche) => {
                                  setContentMail('')
                                  if (newCvId && openFiche) onOpenFiche(newCvId)
                                }}
                                onDeleted={search} />
      )}
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-[10px]" style={{ color: COL_BRUN }}>{label}</label>
      {children}
    </div>
  )
}

function Select({ value, onChange, options }: {
  value: string; onChange: (v: string) => void; options: ComboItem[]
}) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)}
            className="w-full px-2 py-1.5 rounded border text-sm"
            style={{ borderColor: COL_BORDER }}>
      <option value="">—</option>
      {options.map(o => <option key={o.id} value={o.id}>{o.label}</option>)}
    </select>
  )
}

