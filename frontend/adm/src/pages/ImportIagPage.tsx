/**
 * Fen_ImportIAG — Import partenaire IAG (assurance).
 *
 * 2 types : Base Journalière, RUN (auto-dispatch valide/résil selon
 * 'ANNUL' dans le nom de fichier). Multi-fichier (l'op peut uploader
 * plusieurs Excel d'un coup). Onglets résultats variables selon type
 * (cf WinDev).
 */

import { useEffect, useRef, useState } from 'react'
import {
  Calendar, CheckCircle2, Download, FileUp, Loader2, Mail, Play, Trash2, XCircle,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PageHeader from '@/components/PageHeader'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

const API_BASE = '/api/adm'

const TYPES = [
  { id: 1, label: 'Base Journalière' },
  { id: 2, label: 'RUN' },
]

interface Resume {
  nb_fichiers: number; nb_ajoutes: number; nb_valides: number
  nb_resilies: number; nb_deja_saisis: number; nb_deja_statues: number
  nb_introuvables: number; nb_doublons: number
  nb_pb_vendeur: number; nb_erreurs: number
}

interface ImportResult {
  ok: boolean
  type_import: number
  type_label: string
  simulation: boolean
  resume: Resume
  fichiers_traites: string[]
  contrats_ajoutes: Record<string, unknown>[]
  contrats_modifies: Record<string, unknown>[]
  contrats_non_trouves: Record<string, unknown>[]
  contrats_run: Record<string, unknown>[]
  pb_vendeur: Record<string, unknown>[]
  message: string
  xlsx_b64: string
  xlsx_name: string
  mail_envoye: boolean
}

const downloadB64 = (b64: string, name: string): void => {
  const bin = atob(b64)
  const buf = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i)
  const blob = new Blob([buf], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = name || 'rapport.xlsx'
  document.body.appendChild(a); a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

const today = () => new Date().toISOString().slice(0, 10)
const moisCourant = () => {
  const d = new Date()
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${d.getFullYear()}`
}

export default function ImportIagPage() {
  useDocumentTitle('Import IAG')

  const [logoSrc, setLogoSrc] = useState('')
  useEffect(() => {
    fetch(`${API_BASE}/imports/partenaires`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then((rows: Array<{ prefixe_bdd: string; logo_b64: string }>) => {
        const iag = (rows || []).find(p => p.prefixe_bdd === 'IAG')
        if (iag?.logo_b64) setLogoSrc(iag.logo_b64)
      })
      .catch(() => {})
  }, [])

  const [typeImport, setTypeImport] = useState(1)
  const [simulation, setSimulation] = useState(true)
  const [formatVendeur, setFormatVendeur] = useState<'prenom_nom' | 'nom_prenom'>('prenom_nom')
  const [p1Du, setP1Du] = useState(today())
  const [p1Au, setP1Au] = useState(today())
  const [p1Mois, setP1Mois] = useState(moisCourant())
  const [p2Du, setP2Du] = useState(today())
  const [p2Au, setP2Au] = useState(today())
  const [p2Mois, setP2Mois] = useState(moisCourant())
  const [moisDistrib, setMoisDistrib] = useState(moisCourant())

  const [files, setFiles] = useState<File[]>([])
  const fileRef = useRef<HTMLInputElement | null>(null)

  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [tab, setTab] = useState<string>('resume')

  // Onglets dynamiques selon type (cf WinDev)
  const tabs = typeImport === 1
    ? [
        { key: 'resume',       label: 'Résumé importation' },
        { key: 'ajoutes',      label: 'Contrats ajoutés' },
        { key: 'modifies',     label: 'Contrats déjà saisis' },
        { key: 'introuvables', label: 'Contrats non trouvés' },
        { key: 'pb_vend',      label: 'Problème Vendeur' },
      ]
    : [
        { key: 'resume',       label: 'Résumé importation' },
        { key: 'modifies',     label: 'Contrats déjà statué' },
        { key: 'introuvables', label: 'Contrats non trouvés' },
        { key: 'run',          label: 'Contrats RUN' },
        { key: 'pb_vend',      label: 'Erreurs' },
      ]

  const removeFile = (idx: number) => {
    setFiles(prev => prev.filter((_, i) => i !== idx))
  }

  const demarrer = async () => {
    if (files.length === 0) { showToast('Choisis au moins un fichier.', 'info'); return }
    setBusy(true); setResult(null)
    try {
      const fd = new FormData()
      fd.append('type_import', String(typeImport))
      fd.append('simulation', String(simulation))
      fd.append('format_vendeur', formatVendeur)
      fd.append('periode1_du', p1Du); fd.append('periode1_au', p1Au)
      fd.append('periode1_mois_paiement', p1Mois)
      fd.append('periode2_du', p2Du); fd.append('periode2_au', p2Au)
      fd.append('periode2_mois_paiement', p2Mois)
      fd.append('mois_paiement_distrib', moisDistrib)
      files.forEach(f => fd.append('files', f))
      const r = await fetch(`${API_BASE}/imports/iag/run`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      })
      if (!r.ok) throw new Error(String(r.status))
      const d: ImportResult = await r.json()
      setResult(d)
      showToast(d.message || (d.ok ? 'Import terminé' : 'Échec'),
                d.ok ? 'success' : 'error')
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setBusy(false) }
  }

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-120px)]"
         style={{ color: COL_BRUN }}>
      <PageHeader
        iconNode={
          logoSrc ? <img src={logoSrc} alt="IAG" className="h-7" /> : undefined
        }
        title="Import IAG"
        backTo="/imports/contrats"
        right={
          simulation ? (
            <span className="text-xs px-2 py-0.5 rounded"
                  style={{ backgroundColor: '#fef3c7', color: '#92400e' }}>
              SIMULATION
            </span>
          ) : undefined
        }
      />

      {/* Bandeau parametres */}
      <div className="border rounded mb-3 divide-y"
           style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>

        {/* Section 1 : Fichiers + Type + Simulation + Demarrer */}
        <div className="p-3 flex flex-wrap items-end gap-3">
          <div className="flex flex-col">
            <label className="text-[10px] mb-1" style={{ color: COL_BRUN }}>
              Fichiers Excel (multi)
            </label>
            <input ref={fileRef} type="file" multiple
                   accept=".xlsx,.xls,.xlsm,.csv"
                   onChange={e => setFiles(Array.from(e.target.files || []))}
                   className="hidden" />
            <button type="button" onClick={() => fileRef.current?.click()}
                    className="flex items-center gap-1 px-3 py-1.5 rounded border text-xs h-9"
                    style={{ borderColor: COL_BORDER, color: COL_PRIMARY,
                             minWidth: '200px' }}>
              <FileUp className="w-3.5 h-3.5 shrink-0" />
              <span>
                {files.length === 0 ? 'Choisir mes fichiers'
                 : files.length === 1 ? files[0].name
                 : `${files.length} fichiers`}
              </span>
            </button>
          </div>
          <div className="flex flex-col">
            <label className="text-[10px] mb-1" style={{ color: COL_BRUN }}>
              Type d'import
            </label>
            <select value={typeImport}
                    onChange={e => setTypeImport(Number(e.target.value))}
                    className="px-2 py-1.5 rounded border text-sm h-9"
                    style={{ borderColor: COL_BORDER, minWidth: '200px' }}>
              {TYPES.map(t => (
                <option key={t.id} value={t.id}>{t.label}</option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm h-9"
                 style={{ color: COL_BRUN }}>
            <input type="checkbox" checked={simulation}
                   onChange={e => setSimulation(e.target.checked)} />
            Simulation
          </label>
          <div className="flex-1" />
          <button type="button" onClick={demarrer} disabled={busy || files.length === 0}
                  className="flex items-center gap-2 px-4 py-1.5 rounded text-white text-sm disabled:opacity-50 h-9"
                  style={{ backgroundColor: COL_PRIMARY }}>
            {busy ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <Play className="w-4 h-4" />}
            Démarrer
          </button>
        </div>

        {/* Liste des fichiers selectionnes */}
        {files.length > 0 && (
          <div className="px-3 py-2 text-xs space-y-1">
            {files.map((f, i) => (
              <div key={i} className="flex items-center gap-2">
                <FileUp className="w-3 h-3" style={{ color: COL_PRIMARY }} />
                <span className="flex-1 truncate">{f.name}</span>
                <span style={{ color: '#A68D8A' }}>
                  {Math.round(f.size / 1024)} ko
                </span>
                {typeImport === 2 && f.name.toUpperCase().includes('ANNUL') && (
                  <span className="px-1.5 py-0.5 rounded text-[10px]"
                        style={{ backgroundColor: '#fee2e2', color: '#991b1b' }}>
                    RÉSIL
                  </span>
                )}
                <button type="button" onClick={() => removeFile(i)}
                        className="p-0.5 text-red-600 hover:text-red-800">
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Section 2 : Periodes de paiement - visible si type RUN */}
        {typeImport === 2 && (
          <div className="p-3">
            <h3 className="text-[10px] uppercase font-bold mb-2"
                style={{ color: COL_PRIMARY }}>
              Périodes de paiement
            </h3>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
              <Periode label="Période 1" du={p1Du} setDu={setP1Du}
                       au={p1Au} setAu={setP1Au}
                       mois={p1Mois} setMois={setP1Mois} />
              <Periode label="Période 2" du={p2Du} setDu={setP2Du}
                       au={p2Au} setAu={setP2Au}
                       mois={p2Mois} setMois={setP2Mois} />
              <div className="flex flex-col">
                <label className="text-[10px] mb-1" style={{ color: COL_BRUN }}>
                  Mois paiement DISTRIB
                </label>
                <input type="text" value={moisDistrib}
                       onChange={e => setMoisDistrib(e.target.value)}
                       placeholder="MM-YYYY"
                       className="px-2 py-1.5 rounded border text-sm w-28 text-center"
                       style={{ borderColor: COL_BORDER }} />
              </div>
            </div>
          </div>
        )}

        {/* Section 3 : Format Nom Vendeur */}
        <div className="p-3">
          <h3 className="text-[10px] uppercase font-bold mb-2"
              style={{ color: COL_PRIMARY }}>
            Format Nom Vendeur dans le fichier
          </h3>
          <div className="flex gap-4 text-sm">
            <label className="flex items-center gap-2">
              <input type="radio" checked={formatVendeur === 'prenom_nom'}
                     onChange={() => setFormatVendeur('prenom_nom')} />
              Prénom Nom
            </label>
            <label className="flex items-center gap-2">
              <input type="radio" checked={formatVendeur === 'nom_prenom'}
                     onChange={() => setFormatVendeur('nom_prenom')} />
              Nom Prénom
            </label>
          </div>
        </div>
      </div>

      {/* Bandeau rapport + mail */}
      {result && (
        <div className="border rounded px-3 py-2 mb-3 flex items-center gap-3 text-xs"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          {result.xlsx_b64 && (
            <button type="button"
                    onClick={() => downloadB64(result.xlsx_b64, result.xlsx_name)}
                    className="flex items-center gap-1 px-3 py-1 rounded text-white"
                    style={{ backgroundColor: COL_PRIMARY }}>
              <Download className="w-3.5 h-3.5" />
              Télécharger rapport ({result.xlsx_name})
            </button>
          )}
          <div className="flex-1" />
          {result.mail_envoye ? (
            <span className="flex items-center gap-1" style={{ color: '#16a34a' }}>
              <CheckCircle2 className="w-3.5 h-3.5" />
              <Mail className="w-3.5 h-3.5" />
              Mail BO envoyé
            </span>
          ) : (
            <span className="flex items-center gap-1" style={{ color: '#B91C1C' }}>
              <XCircle className="w-3.5 h-3.5" />
              <Mail className="w-3.5 h-3.5" />
              Pas d'envoi mail
            </span>
          )}
        </div>
      )}

      {/* Onglets resultats */}
      <div className="flex-1 flex flex-col min-h-0 border rounded"
           style={{ borderColor: COL_BORDER }}>
        <div className="flex border-b overflow-x-auto"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          {tabs.map(t => {
            let n = 0
            if (result) {
              if (t.key === 'ajoutes') n = result.contrats_ajoutes.length
              else if (t.key === 'modifies') n = result.contrats_modifies.length
              else if (t.key === 'introuvables') n = result.contrats_non_trouves.length
              else if (t.key === 'run') n = result.contrats_run.length
              else if (t.key === 'pb_vend') n = result.pb_vendeur.length
            }
            return (
              <Tab key={t.key} v={tab === t.key} onClick={() => setTab(t.key)}>
                {t.label}{n > 0 && ` (${n})`}
              </Tab>
            )
          })}
        </div>

        <div className="flex-1 overflow-auto p-3">
          {!result ? (
            <p className="italic text-sm text-center mt-8"
               style={{ color: '#A68D8A' }}>
              Choisis un ou plusieurs fichiers Excel et clique sur Démarrer.
            </p>
          ) : tab === 'resume' ? (
            <ResumePanel resume={result.resume}
                         fichiers={result.fichiers_traites}
                         msg={result.message} />
          ) : (
            <RowsTable rows={
              tab === 'ajoutes' ? result.contrats_ajoutes :
              tab === 'modifies' ? result.contrats_modifies :
              tab === 'introuvables' ? result.contrats_non_trouves :
              tab === 'run' ? result.contrats_run :
              result.pb_vendeur
            } />
          )}
        </div>
      </div>
    </div>
  )
}

function Periode({ label, du, setDu, au, setAu, mois, setMois }: {
  label: string
  du: string; setDu: (v: string) => void
  au: string; setAu: (v: string) => void
  mois: string; setMois: (v: string) => void
}) {
  return (
    <div className="flex flex-col">
      <label className="text-[10px] mb-1 font-bold"
             style={{ color: COL_BRUN }}>{label}</label>
      <div className="flex items-center gap-1 flex-wrap">
        <span className="text-xs" style={{ color: COL_BRUN }}>Du</span>
        <div className="relative">
          <input type="date" value={du} onChange={e => setDu(e.target.value)}
                 className="px-2 py-1.5 rounded border text-sm pr-7 w-36"
                 style={{ borderColor: COL_BORDER }} />
          <Calendar className="w-3 h-3 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none"
                    style={{ color: COL_PRIMARY }} />
        </div>
        <span className="text-xs" style={{ color: COL_BRUN }}>au</span>
        <div className="relative">
          <input type="date" value={au} onChange={e => setAu(e.target.value)}
                 className="px-2 py-1.5 rounded border text-sm pr-7 w-36"
                 style={{ borderColor: COL_BORDER }} />
          <Calendar className="w-3 h-3 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none"
                    style={{ color: COL_PRIMARY }} />
        </div>
        <span className="text-xs whitespace-nowrap pl-2"
              style={{ color: COL_BRUN }}>Mois paiement</span>
        <input type="text" value={mois} onChange={e => setMois(e.target.value)}
               placeholder="MM-YYYY"
               className="px-2 py-1.5 rounded border text-sm w-24 text-center"
               style={{ borderColor: COL_BORDER }} />
      </div>
    </div>
  )
}

function Tab({ v, onClick, children }: {
  v: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button type="button" onClick={onClick}
            className="px-3 py-2 text-xs border-b-2 whitespace-nowrap"
            style={{
              borderColor: v ? COL_PRIMARY : 'transparent',
              color: v ? COL_PRIMARY : '#A68D8A',
              fontWeight: v ? 'bold' : 'normal',
            }}>
      {children}
    </button>
  )
}

function ResumePanel({ resume, fichiers, msg }: {
  resume: Resume; fichiers: string[]; msg: string
}) {
  const items: Array<[string, number]> = [
    ['NB Fichiers', resume.nb_fichiers],
    ['NB Ajoutés', resume.nb_ajoutes],
    ['NB Validés', resume.nb_valides],
    ['NB Résiliés', resume.nb_resilies],
    ['NB Déjà saisis', resume.nb_deja_saisis],
    ['NB Déjà statués', resume.nb_deja_statues],
    ['NB Introuvables', resume.nb_introuvables],
    ['NB Doublons', resume.nb_doublons],
    ['NB Pb Vendeur', resume.nb_pb_vendeur],
    ['NB Erreurs', resume.nb_erreurs],
  ]
  return (
    <div>
      <p className="text-sm italic mb-3" style={{ color: COL_BRUN }}>
        {msg}
      </p>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2 max-w-3xl">
        {items.map(([lbl, n]) => (
          <div key={lbl} className="flex justify-between border rounded px-3 py-2 text-sm"
               style={{ borderColor: COL_BORDER,
                        backgroundColor: n > 0 ? '#fef3c7' : 'white' }}>
            <span style={{ color: COL_BRUN }}>{lbl} :</span>
            <strong style={{ color: n > 0 ? '#92400e' : COL_BRUN }}>
              {n.toLocaleString('fr-FR')}
            </strong>
          </div>
        ))}
      </div>
      {fichiers.length > 0 && (
        <details className="mt-4 text-xs">
          <summary className="cursor-pointer" style={{ color: COL_BRUN }}>
            Fichiers traités ({fichiers.length})
          </summary>
          <ul className="pl-4 mt-2 space-y-1">
            {fichiers.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        </details>
      )}
    </div>
  )
}

function RowsTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (rows.length === 0) {
    return (
      <p className="italic text-sm text-center mt-8" style={{ color: '#A68D8A' }}>
        Aucune ligne dans cet onglet.
      </p>
    )
  }
  const keys = Object.keys(rows[0])
  return (
    <table className="w-full text-xs">
      <thead className="sticky top-0"
             style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
        <tr>
          {keys.map(k => (
            <th key={k} className="px-2 py-1.5 text-left whitespace-nowrap">{k}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} className="border-b" style={{ borderColor: COL_BORDER }}>
            {keys.map(k => (
              <td key={k} className="px-2 py-1.5 whitespace-nowrap">
                {String(r[k] ?? '')}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
