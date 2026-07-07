/**
 * Fen_ImportENI — Import partenaire PLENITUDE (ENI).
 *
 * Squelette : 5 types d'import (combo) + dates periode 1/2 + mois
 * paiement + simulation + upload Excel + bouton Demarrer + 6 onglets
 * resultats.
 *
 * La logique metier de chaque type sera implementee cote backend
 * (run_import) au fur et a mesure des procedures WinDev recues.
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
  { id: 1, label: 'Base Journalière CALL' },
  { id: 2, label: 'RUN Valides' },
  { id: 3, label: 'RUN Résils' },
  { id: 4, label: 'Base journalière ENI' },
]

interface Resume {
  nb_valides: number; nb_deja_statues: number; nb_doublons: number
  nb_introuvables: number; nb_decommissions: number; nb_resilies: number
  nb_modifications: number; nb_erreurs_mails: number
  nb_erreurs_entretien: number; nb_contrats_hors_delai: number
  nb_erreurs_offres: number; nb_erreurs_type_comptage: number
  nb_erreurs_energie_verte: number; nb_erreurs_car: number
  nb_erreurs_puiss: number; nb_erreurs_reforest: number
  nb_erreurs_protection: number
  nb_erreurs_mandat: number
}

interface ImportResult {
  ok: boolean
  type_import: number
  type_label: string
  simulation: boolean
  resume: Resume
  contrats_modifies: Record<string, unknown>[]
  contrats_non_trouves: Record<string, unknown>[]
  contrats_run: Record<string, unknown>[]
  pb_vendeur: Record<string, unknown>[]
  contrat_import_journ_eni: Record<string, unknown>[]
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

export default function ImportEniPage() {
  useDocumentTitle('Import ENI / PLENITUDE')

  const [logoSrc, setLogoSrc] = useState('')
  useEffect(() => {
    fetch(`${API_BASE}/imports/partenaires`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then((rows: Array<{ prefixe_bdd: string; logo_b64: string }>) => {
        const eni = (rows || []).find(p => p.prefixe_bdd === 'ENI')
        if (eni?.logo_b64) setLogoSrc(eni.logo_b64)
      })
      .catch(() => {})
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
  const [majProduit, setMajProduit] = useState(false)
  const [majEtats, setMajEtats] = useState(false)

  const [file, setFile] = useState<File | null>(null)
  const fileRef = useRef<HTMLInputElement | null>(null)

  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [tab, setTab] = useState<'resume' | 'modifies' | 'introuvables' | 'run' | 'pb_vend' | 'journ_eni'>('resume')

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
      fd.append('maj_produit_contrat_stand', String(majProduit))
      fd.append('maj_etats_contrats_existants', String(majEtats))
      fd.append('file', file)
      const r = await fetch(`${API_BASE}/imports/eni/run`, {
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
        {logoSrc && <img src={logoSrc} alt="Plenitude" className="h-7" />}
        Import ENI / PLENITUDE
        {simulation && (
          <span className="ml-2 text-xs px-2 py-0.5 rounded"
                style={{ backgroundColor: '#fef3c7', color: '#92400e' }}>
            SIMULATION
          </span>
        )}
      </h1>

      {/* Bandeau parametres - 3 sections empilees */}
      <div className="border rounded mb-3 divide-y"
           style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>

        {/* Section 1 : Fichier / Type / Simulation / Demarrer */}
        <div className="p-3 flex flex-wrap items-end gap-3">
          <div className="flex flex-col">
            <label className="text-[10px] mb-1" style={{ color: COL_BRUN }}>
              Fichier Excel
            </label>
            <input ref={fileRef} type="file"
                   accept=".xlsx,.xls,.xlsm,.csv"
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
            <label className="text-[10px] mb-1" style={{ color: COL_BRUN }}>
              Type d'import
            </label>
            <select value={typeImport}
                    onChange={e => setTypeImport(Number(e.target.value))}
                    className="px-2 py-1.5 rounded border text-sm h-9"
                    style={{ borderColor: COL_BORDER, minWidth: '220px' }}>
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
          <button type="button" onClick={demarrer} disabled={busy || !file}
                  className="flex items-center gap-2 px-4 py-1.5 rounded text-white text-sm disabled:opacity-50 h-9"
                  style={{ backgroundColor: COL_PRIMARY }}>
            {busy ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <Play className="w-4 h-4" />}
            Démarrer
          </button>
        </div>

        {/* Section 2 : GRPeriodePaiement - visible si type RUN (2/3) */}
        {(typeImport === 2 || typeImport === 3) && (
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

        {/* Section 3 : Options de MAJ */}
        <div className="p-3">
          <h3 className="text-[10px] uppercase font-bold mb-2"
              style={{ color: COL_PRIMARY }}>
            Options de mise à jour
          </h3>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={majProduit}
                     onChange={e => setMajProduit(e.target.checked)} />
              Mise à jour Produit contrat STAND
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={majEtats}
                     onChange={e => setMajEtats(e.target.checked)} />
              Mise à jour États des contrats existants
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
          {result.xlsx_b64 && (
            <span style={{ color: '#A68D8A' }}>
              {(Math.round(result.xlsx_b64.length * 0.75 / 1024))} ko
            </span>
          )}
          <div className="flex-1" />
          {result.mail_envoye ? (
            <span className="flex items-center gap-1"
                  style={{ color: '#16a34a' }}>
              <CheckCircle2 className="w-3.5 h-3.5" />
              <Mail className="w-3.5 h-3.5" />
              Mail BO envoyé
            </span>
          ) : (
            <span className="flex items-center gap-1"
                  style={{ color: '#B91C1C' }}>
              <XCircle className="w-3.5 h-3.5" />
              <Mail className="w-3.5 h-3.5" />
              Échec envoi mail
            </span>
          )}
        </div>
      )}

      {/* Onglets resultats */}
      <div className="flex-1 flex flex-col min-h-0 border rounded"
           style={{ borderColor: COL_BORDER }}>
        <div className="flex border-b overflow-x-auto"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          <Tab v={tab === 'resume'} onClick={() => setTab('resume')}>
            Résumé importation
          </Tab>
          <Tab v={tab === 'modifies'}
               onClick={() => setTab('modifies')}>
            Contrats modifiés{result && ` (${result.contrats_modifies.length})`}
          </Tab>
          <Tab v={tab === 'introuvables'}
               onClick={() => setTab('introuvables')}>
            Contrats non trouvés{result && ` (${result.contrats_non_trouves.length})`}
          </Tab>
          <Tab v={tab === 'run'} onClick={() => setTab('run')}>
            Contrats RUN{result && ` (${result.contrats_run.length})`}
          </Tab>
          <Tab v={tab === 'pb_vend'} onClick={() => setTab('pb_vend')}>
            Problème Vendeur{result && ` (${result.pb_vendeur.length})`}
          </Tab>
          <Tab v={tab === 'journ_eni'} onClick={() => setTab('journ_eni')}>
            Contrat Import Journ ENI{result && ` (${result.contrat_import_journ_eni.length})`}
          </Tab>
        </div>

        <div className="flex-1 overflow-auto p-3">
          {!result ? (
            <p className="italic text-sm text-center mt-8"
               style={{ color: '#A68D8A' }}>
              Choisis un fichier et clique sur Démarrer pour lancer l'import.
            </p>
          ) : tab === 'resume' ? (
            <ResumePanel resume={result.resume} />
          ) : (
            <RowsTable rows={
              tab === 'modifies' ? result.contrats_modifies :
              tab === 'introuvables' ? result.contrats_non_trouves :
              tab === 'run' ? result.contrats_run :
              tab === 'pb_vend' ? result.pb_vendeur :
              result.contrat_import_journ_eni
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

function ResumePanel({ resume }: { resume: Resume }) {
  const items: Array<[string, number]> = [
    ['NB Validés', resume.nb_valides],
    ['NB Déjà Statués', resume.nb_deja_statues],
    ['NB Doublons', resume.nb_doublons],
    ['NB Introuvables', resume.nb_introuvables],
    ['NB Décommissions', resume.nb_decommissions],
    ['NB Résiliés', resume.nb_resilies],
    ['NB Modifications', resume.nb_modifications],
    ['NB Erreurs de Mails', resume.nb_erreurs_mails],
    ['NB Erreurs d\'Entretien', resume.nb_erreurs_entretien],
    ['NB Contrats Hors Délai', resume.nb_contrats_hors_delai],
    ['NB Erreurs Offres', resume.nb_erreurs_offres],
    ['NB Erreurs type comptage', resume.nb_erreurs_type_comptage],
    ['NB Erreurs Energie Verte', resume.nb_erreurs_energie_verte],
    ['NB Erreurs CAR', resume.nb_erreurs_car],
    ['NB Erreurs de PUISS', resume.nb_erreurs_puiss],
    ['NB Erreurs Reforestation', resume.nb_erreurs_reforest],
    ['NB Erreurs Protection', resume.nb_erreurs_protection],
    ['NB Erreurs Mandat', resume.nb_erreurs_mandat],
  ]
  return (
    <div className="grid grid-cols-3 gap-2 max-w-3xl">
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
