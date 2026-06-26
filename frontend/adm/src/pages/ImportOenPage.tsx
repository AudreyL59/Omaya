/**
 * Fen_ImportOEN — Import OHM Énergie.
 * 4 types : Base Journalière / RUN Valide / RUN Résil / Thermostat.
 * Périodes visibles si type ∈ {2, 3} (cf WinDev si MoiMême > 1 et <> 4).
 */
import { useEffect, useRef, useState } from 'react'
import {
  Calendar, CheckCircle2, Download, FileUp, Loader2, Mail, Play, XCircle,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

const API_BASE = '/api/adm'

const TYPES = [
  { id: 1, label: 'Base Journalière' },
  { id: 2, label: 'RUN Valide' },
  { id: 3, label: 'RUN Résil' },
  { id: 4, label: 'Import Thermostat' },
]

interface Resume {
  nb_ajoutes: number; nb_modifies: number; nb_valides: number
  nb_resilies: number; nb_decommissions: number; nb_deja_statues: number
  nb_introuvables: number; nb_doublons: number; nb_hors_delai: number
  nb_erreurs: number; nb_pb_vendeur: number; nb_pb_statut: number; nb_pb_offre: number
}

interface ImportResult {
  ok: boolean; type_import: number; type_label: string; simulation: boolean
  resume: Resume
  contrats_ajoutes: Record<string, unknown>[]
  contrats_modifies: Record<string, unknown>[]
  contrats_run: Record<string, unknown>[]
  contrats_non_trouves: Record<string, unknown>[]
  pb_vendeur: Record<string, unknown>[]
  message: string; xlsx_b64: string; xlsx_name: string; mail_envoye: boolean
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

export default function ImportOenPage() {
  useDocumentTitle('Import OHM Énergie')

  const [logoSrc, setLogoSrc] = useState('')
  useEffect(() => {
    fetch(`${API_BASE}/imports/partenaires`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then((rows: Array<{ prefixe_bdd: string; logo_b64: string }>) => {
        const oen = (rows || []).find(p => p.prefixe_bdd === 'OEN')
        if (oen?.logo_b64) setLogoSrc(oen.logo_b64)
      }).catch(() => {})
  }, [])

  const [typeImport, setTypeImport] = useState(1)
  const [simulation, setSimulation] = useState(true)
  const [p1Du, setP1Du] = useState(today())
  const [p1Au, setP1Au] = useState(today())
  const [p1Mois, setP1Mois] = useState(moisCourant())
  const [p2Du, setP2Du] = useState(today())
  const [p2Au, setP2Au] = useState(today())
  const [p2Mois, setP2Mois] = useState(moisCourant())
  const [moisDistrib, setMoisDistrib] = useState(moisCourant())
  const [file, setFile] = useState<File | null>(null)
  const fileRef = useRef<HTMLInputElement | null>(null)

  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [tab, setTab] = useState<'resume' | 'ajoutes' | 'modifies' | 'run' | 'non_trouves' | 'pb_vend'>('resume')

  const demarrer = async () => {
    if (!file) { showToast('Choisis un fichier Excel.', 'info'); return }
    setBusy(true); setResult(null)
    try {
      const fd = new FormData()
      fd.append('type_import', String(typeImport))
      fd.append('simulation', String(simulation))
      fd.append('periode1_du', p1Du); fd.append('periode1_au', p1Au)
      fd.append('periode1_mois_paiement', p1Mois)
      fd.append('periode2_du', p2Du); fd.append('periode2_au', p2Au)
      fd.append('periode2_mois_paiement', p2Mois)
      fd.append('mois_paiement_distrib', moisDistrib)
      fd.append('file', file)
      const r = await fetch(`${API_BASE}/imports/oen/run`, {
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
      <h1 className="text-xl font-bold mb-3 flex items-center gap-2">
        {logoSrc && <img src={logoSrc} alt="OHM Énergie" className="h-7" />}
        Import OHM Énergie
        {simulation && (
          <span className="ml-2 text-xs px-2 py-0.5 rounded"
                style={{ backgroundColor: '#fef3c7', color: '#92400e' }}>
            SIMULATION
          </span>
        )}
      </h1>

      <div className="border rounded mb-3 divide-y"
           style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
        <div className="p-3 flex flex-wrap items-end gap-3">
          <div className="flex flex-col">
            <label className="text-[10px] mb-1">Fichier Excel</label>
            <input ref={fileRef} type="file" accept=".xlsx,.xls,.xlsm,.csv"
                   onChange={e => setFile(e.target.files?.[0] || null)}
                   className="hidden" />
            <button type="button" onClick={() => fileRef.current?.click()}
                    className="flex items-center gap-1 px-3 py-1.5 rounded border text-xs h-9"
                    style={{ borderColor: COL_BORDER, color: COL_PRIMARY,
                             minWidth: '200px', maxWidth: '320px' }}>
              <FileUp className="w-3.5 h-3.5 shrink-0" />
              <span className="truncate">
                {file ? `${file.name} (${Math.round(file.size / 1024)} ko)`
                      : 'Choisir mon fichier'}
              </span>
            </button>
          </div>
          <div className="flex flex-col">
            <label className="text-[10px] mb-1">Type d'import</label>
            <select value={typeImport}
                    onChange={e => setTypeImport(Number(e.target.value))}
                    className="px-2 py-1.5 rounded border text-sm h-9"
                    style={{ borderColor: COL_BORDER, minWidth: '220px' }}>
              {TYPES.map(t => (
                <option key={t.id} value={t.id}>{t.label}</option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm h-9">
            <input type="checkbox" checked={simulation}
                   onChange={e => setSimulation(e.target.checked)} />
            Simulation
          </label>
          <div className="flex-1" />
          <button type="button" onClick={demarrer} disabled={busy || !file}
                  className="flex items-center gap-2 px-4 py-1.5 rounded text-white text-sm disabled:opacity-50 h-9"
                  style={{ backgroundColor: COL_PRIMARY }}>
            {busy ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <Play className="w-4 h-4" />}
            Démarrer
          </button>
        </div>

        {(typeImport === 2 || typeImport === 3) && (
          <div className="p-3">
            <h3 className="text-[10px] uppercase font-bold mb-2"
                style={{ color: COL_PRIMARY }}>Périodes de paiement</h3>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
              <Periode label="Période 1" du={p1Du} setDu={setP1Du}
                       au={p1Au} setAu={setP1Au}
                       mois={p1Mois} setMois={setP1Mois} />
              <Periode label="Période 2" du={p2Du} setDu={setP2Du}
                       au={p2Au} setAu={setP2Au}
                       mois={p2Mois} setMois={setP2Mois} />
              <div className="flex flex-col">
                <label className="text-[10px] mb-1">Mois paiement DISTRIB</label>
                <input type="text" value={moisDistrib}
                       onChange={e => setMoisDistrib(e.target.value)}
                       placeholder="MM-YYYY"
                       className="px-2 py-1.5 rounded border text-sm w-28 text-center"
                       style={{ borderColor: COL_BORDER }} />
              </div>
            </div>
          </div>
        )}
      </div>

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
              <Mail className="w-3.5 h-3.5" /> Mail BO envoyé
            </span>
          ) : (
            <span className="flex items-center gap-1" style={{ color: '#B91C1C' }}>
              <XCircle className="w-3.5 h-3.5" />
              <Mail className="w-3.5 h-3.5" /> Pas d'envoi mail
            </span>
          )}
        </div>
      )}

      <div className="flex-1 flex flex-col min-h-0 border rounded"
           style={{ borderColor: COL_BORDER }}>
        <div className="flex border-b overflow-x-auto"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          <Tab v={tab === 'resume'} onClick={() => setTab('resume')}>Résumé</Tab>
          <Tab v={tab === 'ajoutes'} onClick={() => setTab('ajoutes')}>
            Ajoutés{result && ` (${result.contrats_ajoutes.length})`}
          </Tab>
          <Tab v={tab === 'modifies'} onClick={() => setTab('modifies')}>
            Modifiés{result && ` (${result.contrats_modifies.length})`}
          </Tab>
          <Tab v={tab === 'run'} onClick={() => setTab('run')}>
            RUN{result && ` (${result.contrats_run.length})`}
          </Tab>
          <Tab v={tab === 'non_trouves'} onClick={() => setTab('non_trouves')}>
            Non trouvés{result && ` (${result.contrats_non_trouves.length})`}
          </Tab>
          <Tab v={tab === 'pb_vend'} onClick={() => setTab('pb_vend')}>
            Erreurs/Pb{result && ` (${result.pb_vendeur.length})`}
          </Tab>
        </div>
        <div className="flex-1 overflow-auto p-3">
          {!result ? (
            <p className="italic text-sm text-center mt-8"
               style={{ color: '#A68D8A' }}>
              Choisis un fichier Excel et clique sur Démarrer.
            </p>
          ) : tab === 'resume' ? (
            <ResumePanel r={result.resume} msg={result.message} />
          ) : (
            <RowsTable rows={
              tab === 'ajoutes' ? result.contrats_ajoutes :
              tab === 'modifies' ? result.contrats_modifies :
              tab === 'run' ? result.contrats_run :
              tab === 'non_trouves' ? result.contrats_non_trouves :
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
      <label className="text-[10px] mb-1 font-bold">{label}</label>
      <div className="flex items-center gap-1 flex-wrap">
        <span className="text-xs">Du</span>
        <div className="relative">
          <input type="date" value={du} onChange={e => setDu(e.target.value)}
                 className="px-2 py-1.5 rounded border text-sm pr-7 w-36"
                 style={{ borderColor: COL_BORDER }} />
          <Calendar className="w-3 h-3 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none"
                    style={{ color: COL_PRIMARY }} />
        </div>
        <span className="text-xs">au</span>
        <div className="relative">
          <input type="date" value={au} onChange={e => setAu(e.target.value)}
                 className="px-2 py-1.5 rounded border text-sm pr-7 w-36"
                 style={{ borderColor: COL_BORDER }} />
          <Calendar className="w-3 h-3 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none"
                    style={{ color: COL_PRIMARY }} />
        </div>
        <span className="text-xs whitespace-nowrap pl-2">Mois paiement</span>
        <input type="text" value={mois} onChange={e => setMois(e.target.value)}
               placeholder="MM-YYYY"
               className="px-2 py-1.5 rounded border text-sm w-24 text-center"
               style={{ borderColor: COL_BORDER }} />
      </div>
    </div>
  )
}

function Tab({ v, onClick, children }: {
  v: boolean; onClick: () => void; children: React.ReactNode
}) {
  return (
    <button type="button" onClick={onClick}
            className="px-3 py-2 text-xs border-b-2 whitespace-nowrap"
            style={{
              borderColor: v ? COL_PRIMARY : 'transparent',
              color: v ? COL_PRIMARY : '#A68D8A',
              fontWeight: v ? 'bold' : 'normal',
            }}>{children}</button>
  )
}

function ResumePanel({ r, msg }: { r: Resume; msg: string }) {
  const items: Array<[string, number]> = [
    ['Ajoutés', r.nb_ajoutes], ['Modifiés', r.nb_modifies],
    ['Validés', r.nb_valides], ['Résiliés', r.nb_resilies],
    ['Décommissions', r.nb_decommissions], ['Déjà statués', r.nb_deja_statues],
    ['Introuvables', r.nb_introuvables], ['Doublons', r.nb_doublons],
    ['Hors délai', r.nb_hors_delai], ['Pb Vendeur', r.nb_pb_vendeur],
    ['Pb Statut', r.nb_pb_statut], ['Pb Offre', r.nb_pb_offre],
    ['Erreurs', r.nb_erreurs],
  ]
  return (
    <div>
      <p className="text-sm italic mb-3">{msg}</p>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2 max-w-3xl">
        {items.map(([lbl, n]) => (
          <div key={lbl} className="flex justify-between border rounded px-3 py-2 text-sm"
               style={{ borderColor: COL_BORDER,
                        backgroundColor: n > 0 ? '#fef3c7' : 'white' }}>
            <span>{lbl} :</span>
            <strong style={{ color: n > 0 ? '#92400e' : COL_BRUN }}>
              {n.toLocaleString('fr-FR')}
            </strong>
          </div>
        ))}
      </div>
    </div>
  )
}

function RowsTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (rows.length === 0) {
    return <p className="italic text-sm text-center mt-8"
              style={{ color: '#A68D8A' }}>Aucune ligne.</p>
  }
  const keys = Object.keys(rows[0])
  return (
    <table className="w-full text-xs">
      <thead className="sticky top-0"
             style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
        <tr>{keys.map(k => (
          <th key={k} className="px-2 py-1.5 text-left whitespace-nowrap">{k}</th>
        ))}</tr>
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
