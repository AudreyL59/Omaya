/**
 * Fen_AjoutColonneImport — Ajoute des colonnes calculées à un fichier Excel.
 *
 * 7 actions disponibles (boutons). Mode partenaire : 'liste' (combo) ou
 * 'colonne' (lit le partenaire depuis une colonne du fichier).
 */
import { useEffect, useRef, useState } from 'react'
import {
  Download, FileUp, Loader2, Plus, Zap,
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

interface Partenaire {
  prefixe_bdd: string; lib_partenaire: string; is_actif: boolean
}
interface Result {
  ok: boolean; nb_lignes_traitees: number; nb_lignes_enrichies: number
  xlsx_b64: string; xlsx_name: string; message: string
}

const ACTIONS: Array<{ id: string; label: string; icon?: 'zap' | 'plus' }> = [
  { id: 'vendeur_agence_equipe', label: 'Ajouter Colonnes Vendeur / Agence / Equipe', icon: 'plus' },
  { id: 'date_signature',        label: 'Ajouter Colonne Date de Signature', icon: 'plus' },
  { id: 'lib_produit',           label: 'Ajouter Colonne Lib Produit', icon: 'plus' },
  { id: 'etat_omaya',            label: 'Ajouter Colonnes Etat Omaya', icon: 'plus' },
  { id: 'info_client',           label: 'Ajouter Colonnes Info Client', icon: 'plus' },
  { id: 'car_eni',               label: 'Ajouter Colonne CAR (uniquement pour ENI)', icon: 'zap' },
  { id: 'infos_run_rem_sfr',     label: 'Ajouter colonnes infos Run et REM SFR', icon: 'plus' },
]

const downloadB64 = (b64: string, name: string): void => {
  const bin = atob(b64); const buf = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i)
  const blob = new Blob([buf], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = name || 'fichier.xlsx'
  document.body.appendChild(a); a.click()
  document.body.removeChild(a); URL.revokeObjectURL(url)
}

export default function ImportAjoutColonnePage() {
  useDocumentTitle('Ajout colonne import')
  const [partenaires, setPartenaires] = useState<Partenaire[]>([])
  const [file, setFile] = useState<File | null>(null)
  const fileRef = useRef<HTMLInputElement | null>(null)
  const [colNumContrat, setColNumContrat] = useState('B')
  const [modePartenaire, setModePartenaire] = useState<'liste' | 'colonne'>('liste')
  const [partenaire, setPartenaire] = useState('')
  const [colPartenaire, setColPartenaire] = useState('A')
  const [busy, setBusy] = useState<string | null>(null)
  const [result, setResult] = useState<Result | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/imports/masse/partenaires`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then((d: Partenaire[]) => setPartenaires(Array.isArray(d) ? d : []))
  }, [])

  const run = async (action: string) => {
    if (!file) { showToast('Choisis un fichier.', 'info'); return }
    if (modePartenaire === 'liste' && !partenaire) {
      showToast('Choisis un partenaire.', 'info'); return
    }
    setBusy(action); setResult(null)
    try {
      const fd = new FormData()
      fd.append('file', file); fd.append('action', action)
      fd.append('col_num_contrat', colNumContrat)
      fd.append('mode_partenaire', modePartenaire)
      fd.append('partenaire', partenaire)
      fd.append('col_partenaire', colPartenaire)
      const r = await fetch(`${API_BASE}/imports/ajout-colonne/run`, {
        method: 'POST', headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      })
      if (!r.ok) throw new Error(String(r.status))
      const d: Result = await r.json()
      setResult(d)
      if (d.ok && d.xlsx_b64) {
        downloadB64(d.xlsx_b64, d.xlsx_name)
        showToast(d.message, 'success')
      } else {
        showToast(d.message || 'Échec', 'error')
      }
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setBusy(null) }
  }

  return (
    <div className="p-4 max-w-3xl" style={{ color: COL_BRUN }}>
      <PageHeader icon={Plus} title="Ajouter des colonnes" />

      <div className="border rounded p-3 mb-3 space-y-3"
           style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
        <div className="flex items-end gap-3 flex-wrap">
          <div className="flex flex-col">
            <label className="text-[10px] mb-1">Fichier Excel</label>
            <input ref={fileRef} type="file" accept=".xlsx,.xls,.xlsm"
                   onChange={e => setFile(e.target.files?.[0] || null)}
                   className="hidden" />
            <button type="button" onClick={() => fileRef.current?.click()}
                    className="flex items-center gap-1 px-3 py-1.5 rounded border text-xs h-9"
                    style={{ borderColor: COL_BORDER, color: COL_PRIMARY,
                             minWidth: '260px' }}>
              <FileUp className="w-3.5 h-3.5" />
              <span className="truncate">{file?.name || 'Choisir un fichier'}</span>
            </button>
          </div>
          <div className="flex flex-col">
            <label className="text-[10px] mb-1">Col N°Contrat</label>
            <input type="text" value={colNumContrat}
                   onChange={e => setColNumContrat(e.target.value.toUpperCase())}
                   className="px-2 py-1.5 rounded border text-sm w-14 text-center"
                   style={{ borderColor: COL_BORDER }} />
          </div>
        </div>
        <div className="flex items-end gap-3 flex-wrap">
          <label className="flex items-center gap-2 text-sm">
            <input type="radio" checked={modePartenaire === 'liste'}
                   onChange={() => setModePartenaire('liste')} />
            Part dans la liste
          </label>
          {modePartenaire === 'liste' && (
            <select value={partenaire}
                    onChange={e => setPartenaire(e.target.value)}
                    className="px-2 py-1.5 rounded border text-sm h-9"
                    style={{ borderColor: COL_BORDER, minWidth: '160px' }}>
              <option value="">—</option>
              {partenaires.map(p => (
                <option key={p.prefixe_bdd}
                        value={p.prefixe_bdd?.toLowerCase()}>
                  {p.lib_partenaire}
                </option>
              ))}
            </select>
          )}
          <label className="flex items-center gap-2 text-sm">
            <input type="radio" checked={modePartenaire === 'colonne'}
                   onChange={() => setModePartenaire('colonne')} />
            Colonne du fichier
          </label>
          {modePartenaire === 'colonne' && (
            <input type="text" value={colPartenaire}
                   onChange={e => setColPartenaire(e.target.value.toUpperCase())}
                   placeholder="Col Partenaire"
                   className="px-2 py-1.5 rounded border text-sm w-14 text-center"
                   style={{ borderColor: COL_BORDER }} />
          )}
        </div>
        {modePartenaire === 'liste' && (
          <p className="text-xs italic" style={{ color: '#A68D8A' }}>
            Attention, tous les contrats du fichier doivent être de cet opérateur.
          </p>
        )}
      </div>

      <div className="border rounded p-2 space-y-1"
           style={{ borderColor: COL_BORDER }}>
        {ACTIONS.map(a => (
          <button key={a.id} type="button" onClick={() => run(a.id)}
                  disabled={busy !== null || !file}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded text-sm hover:bg-gray-50 disabled:opacity-40"
                  style={{ color: COL_BRUN }}>
            {a.icon === 'zap' ? (
              <Zap className="w-4 h-4" style={{ color: '#f59e0b' }} />
            ) : (
              <Plus className="w-4 h-4" style={{ color: COL_PRIMARY }} />
            )}
            <span className="flex-1 text-left">{a.label}</span>
            {busy === a.id && (
              <Loader2 className="w-4 h-4 animate-spin"
                       style={{ color: COL_PRIMARY }} />
            )}
          </button>
        ))}
      </div>

      {result && (
        <div className="mt-3 border rounded px-3 py-2 text-xs flex items-center gap-3"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          <span className="flex-1">{result.message}</span>
          {result.xlsx_b64 && (
            <button type="button"
                    onClick={() => downloadB64(result.xlsx_b64, result.xlsx_name)}
                    className="flex items-center gap-1 px-3 py-1 rounded text-white"
                    style={{ backgroundColor: COL_PRIMARY }}>
              <Download className="w-3.5 h-3.5" />
              Télécharger
            </button>
          )}
        </div>
      )}
    </div>
  )
}
