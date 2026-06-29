/**
 * Fen_ImportNotation — Import notations contrats (multi-partenaire).
 *
 * Le mapping colonnes + le barème (notes_sur) sont auto-remplis depuis
 * /imports/notation/mapping/{partenaire} à chaque changement de combo.
 * La note est normalisée sur 5 avant écriture en BDD.
 */
import { useEffect, useRef, useState } from 'react'
import { Download, FileUp, Loader2, Play, Star } from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'
const API_BASE = '/api/adm'

interface Partenaire {
  prefixe_bdd: string; lib_partenaire: string
}
interface Ligne {
  num_bs: string; vendeur: string; agence: string; equipe: string
  date_signature: string; note_normalisee: number
  info_notes: string; statut: string
}
interface Result {
  ok: boolean; message: string
  nb_lignes: number; nb_importees: number; nb_introuvables: number
  nb_erreurs: number
  lignes: Ligne[]
  erreurs: Array<{ num_bs: string; erreur: string }>
  xlsx_b64: string; xlsx_name: string
}

const downloadB64 = (b64: string, name: string): void => {
  const bin = atob(b64); const buf = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i)
  const blob = new Blob([buf], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = name || 'notations.xlsx'
  document.body.appendChild(a); a.click()
  document.body.removeChild(a); URL.revokeObjectURL(url)
}

export default function ImportNotationPage() {
  useDocumentTitle('Import notations')
  const [partenaires, setPartenaires] = useState<Partenaire[]>([])
  const [partenaire, setPartenaire] = useState('')
  const [colNum, setColNum] = useState('')
  const [colNote, setColNote] = useState('')
  const [colInfo, setColInfo] = useState('')
  const [notesSur, setNotesSur] = useState(5)
  const [simulation, setSimulation] = useState(true)
  const [file, setFile] = useState<File | null>(null)
  const fileRef = useRef<HTMLInputElement | null>(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<Result | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/imports/masse/partenaires`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then((d: Partenaire[]) => setPartenaires(Array.isArray(d) ? d : []))
  }, [])

  // Auto-remplit mapping selon partenaire
  useEffect(() => {
    if (!partenaire) {
      setColNum(''); setColNote(''); setColInfo(''); setNotesSur(5)
      return
    }
    fetch(`${API_BASE}/imports/notation/mapping/${partenaire}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : {})
      .then((d: { col_num?: string; col_note?: string;
                  col_info?: string; notes_sur?: number }) => {
        setColNum(d.col_num || '')
        setColNote(d.col_note || '')
        setColInfo(d.col_info || '')
        setNotesSur(d.notes_sur || 5)
      })
  }, [partenaire])

  const demarrer = async () => {
    if (!file) { showToast('Choisis un fichier.', 'info'); return }
    if (!partenaire) { showToast('Choisis un partenaire.', 'info'); return }
    if (!colNum || !colNote) {
      showToast('Mapping colonnes incomplet (Num + Note requis).', 'info')
      return
    }
    setBusy(true); setResult(null)
    try {
      const fd = new FormData()
      fd.append('file', file); fd.append('partenaire', partenaire)
      fd.append('col_num_contrat', colNum); fd.append('col_note', colNote)
      fd.append('col_info', colInfo); fd.append('notes_sur', String(notesSur))
      fd.append('simulation', String(simulation))
      const r = await fetch(`${API_BASE}/imports/notation/run`, {
        method: 'POST', headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      })
      if (!r.ok) throw new Error(String(r.status))
      const d: Result = await r.json()
      setResult(d)
      showToast(d.message, d.ok ? 'success' : 'error')
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setBusy(false) }
  }

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-120px)]"
         style={{ color: COL_BRUN }}>
      <h1 className="text-xl font-bold mb-3 flex items-center gap-2">
        <Star className="w-5 h-5" style={{ color: '#f59e0b' }} />
        Import notations
        {simulation && (
          <span className="ml-2 text-xs px-2 py-0.5 rounded"
                style={{ backgroundColor: '#fef3c7', color: '#92400e' }}>
            SIMULATION
          </span>
        )}
      </h1>

      <div className="border rounded p-3 mb-3 flex items-end gap-3 flex-wrap"
           style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
        <div className="flex flex-col">
          <label className="text-[10px] mb-1">Partenaire</label>
          <select value={partenaire}
                  onChange={e => setPartenaire(e.target.value)}
                  className="px-2 py-1.5 rounded border text-sm h-9"
                  style={{ borderColor: COL_BORDER, minWidth: '160px' }}>
            <option value="">—</option>
            {partenaires.map(p => (
              <option key={p.prefixe_bdd} value={p.prefixe_bdd?.toLowerCase()}>
                {p.lib_partenaire}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col">
          <label className="text-[10px] mb-1">Fichier Excel</label>
          <input ref={fileRef} type="file" accept=".xlsx,.xls,.xlsm"
                 onChange={e => setFile(e.target.files?.[0] || null)}
                 className="hidden" />
          <button type="button" onClick={() => fileRef.current?.click()}
                  className="flex items-center gap-1 px-3 py-1.5 rounded border text-xs h-9"
                  style={{ borderColor: COL_BORDER, color: COL_PRIMARY,
                           minWidth: '220px' }}>
            <FileUp className="w-3.5 h-3.5" />
            <span className="truncate">{file?.name || 'Choisir un fichier'}</span>
          </button>
        </div>
        <div className="flex flex-col">
          <label className="text-[10px] mb-1">Col N° Contrat</label>
          <input type="text" value={colNum}
                 onChange={e => setColNum(e.target.value.toUpperCase())}
                 className="px-2 py-1.5 rounded border text-sm w-14 text-center"
                 style={{ borderColor: COL_BORDER }} />
        </div>
        <div className="flex flex-col">
          <label className="text-[10px] mb-1">Col Note</label>
          <input type="text" value={colNote}
                 onChange={e => setColNote(e.target.value.toUpperCase())}
                 className="px-2 py-1.5 rounded border text-sm w-14 text-center"
                 style={{ borderColor: COL_BORDER }} />
        </div>
        <div className="flex flex-col">
          <label className="text-[10px] mb-1">Col Info</label>
          <input type="text" value={colInfo}
                 onChange={e => setColInfo(e.target.value.toUpperCase())}
                 className="px-2 py-1.5 rounded border text-sm w-14 text-center"
                 style={{ borderColor: COL_BORDER }} />
        </div>
        <div className="flex flex-col">
          <label className="text-[10px] mb-1">Notes sur</label>
          <input type="number" value={notesSur} min={1}
                 onChange={e => setNotesSur(Number(e.target.value))}
                 className="px-2 py-1.5 rounded border text-sm w-16 text-center"
                 style={{ borderColor: COL_BORDER }} />
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
          Démarrer l'import
        </button>
      </div>

      {result && (
        <div className="border rounded px-3 py-2 mb-3 flex items-center gap-3 text-xs"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          <span className="flex-1">{result.message}</span>
          {result.xlsx_b64 && (
            <button type="button"
                    onClick={() => downloadB64(result.xlsx_b64, result.xlsx_name)}
                    className="flex items-center gap-1 px-3 py-1 rounded text-white"
                    style={{ backgroundColor: COL_PRIMARY }}>
              <Download className="w-3.5 h-3.5" />
              Télécharger ({result.xlsx_name})
            </button>
          )}
        </div>
      )}

      <div className="flex-1 overflow-auto border rounded"
           style={{ borderColor: COL_BORDER }}>
        {!result ? (
          <p className="italic text-sm text-center mt-8" style={{ color: '#A68D8A' }}>
            Choisis un partenaire + fichier, vérifie le mapping puis clique sur Démarrer.
          </p>
        ) : (
          <>
            {result.lignes.length > 0 && (
              <table className="w-full text-xs">
                <thead className="sticky top-0"
                       style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                  <tr>
                    <th className="px-2 py-1.5 text-left">Num BS</th>
                    <th className="px-2 py-1.5 text-left">Vendeur</th>
                    <th className="px-2 py-1.5 text-left">Agence</th>
                    <th className="px-2 py-1.5 text-left">Equipe</th>
                    <th className="px-2 py-1.5 text-left">Date Sign</th>
                    <th className="px-2 py-1.5 text-center">Note /5</th>
                    <th className="px-2 py-1.5 text-left">Info</th>
                    <th className="px-2 py-1.5 text-left">Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {result.lignes.map((l, i) => (
                    <tr key={i} className="border-b" style={{ borderColor: COL_BORDER }}>
                      <td className="px-2 py-1.5">{l.num_bs}</td>
                      <td className="px-2 py-1.5">{l.vendeur}</td>
                      <td className="px-2 py-1.5">{l.agence}</td>
                      <td className="px-2 py-1.5">{l.equipe}</td>
                      <td className="px-2 py-1.5">{l.date_signature}</td>
                      <td className="px-2 py-1.5 text-center font-bold"
                          style={{ color: COL_PRIMARY }}>
                        {l.note_normalisee}
                      </td>
                      <td className="px-2 py-1.5">{l.info_notes}</td>
                      <td className="px-2 py-1.5">{l.statut}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {result.erreurs.length > 0 && (
              <div className="p-3 border-t" style={{ borderColor: COL_BORDER }}>
                <h3 className="text-xs font-bold mb-2" style={{ color: '#B91C1C' }}>
                  Erreurs ({result.erreurs.length})
                </h3>
                <table className="w-full text-xs">
                  <tbody>
                    {result.erreurs.map((e, i) => (
                      <tr key={i} className="border-b" style={{ borderColor: COL_BORDER }}>
                        <td className="px-2 py-1.5">{e.num_bs}</td>
                        <td className="px-2 py-1.5" style={{ color: '#B91C1C' }}>
                          {e.erreur}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
