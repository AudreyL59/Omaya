/**
 * Fen_importFormIAG (WinDev) - Salariés -> Suivi des formations IAG.
 *
 * Layout 2 colonnes :
 *  - Gauche : selecteur de fichier .xls + mapping de colonnes + btn
 *    'Importer le fichier' + checkbox Simulation + zone Resume + tableau
 *    'Erreurs : vendeurs non trouves'.
 *  - Droite : tableau des salaries 'a former' (FormationIAG=0 ou
 *    score<13, filtres poste + societe).
 */

import { useCallback, useEffect, useState } from 'react'
import {
  AlertTriangle,
  GraduationCap,
  Loader2,
  Upload,
} from 'lucide-react'

import { getToken } from '@/api'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PageHeader from '@/components/PageHeader'
import { showToast } from '@shared/ui/dialog'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface AFormer {
  id_salarie: string
  nom: string
  prenom: string
  formation_iag: boolean
  formation_iag_score: number
  formation_iag_date: string
  id_ste: number
  en_pause: boolean
  lib_poste: string
  date_debut: string
}

interface VendeurErreur {
  nom: string
  prenom: string
  date_formation: string
  score: number
  nb_fiche: number
  code_iag: string
}

interface IagCols {
  code_iag: string
  date: string
  nom: string
  prenom: string
  score: string
}

const DEFAULT_COLS: IagCols = {
  code_iag: 'B',
  date: 'C',
  nom: 'D',
  prenom: 'E',
  score: 'G',
}

const COL_LABELS: Record<keyof IagCols, string> = {
  code_iag: 'Code IAG',
  date: 'Date Formation',
  nom: 'Nom',
  prenom: 'Prénom',
  score: 'Score',
}

const inputCls =
  'px-2 py-1.5 rounded border bg-white text-sm focus:outline-none focus:ring-1'

export default function FormationsIAGPage() {
  useDocumentTitle('Formations IAG')
  const [aFormer, setAFormer] = useState<AFormer[]>([])
  const [loadingList, setLoadingList] = useState(true)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [cols, setCols] = useState<IagCols>(DEFAULT_COLS)
  const [limitJours, setLimitJours] = useState(30)
  const [simulation, setSimulation] = useState(true)
  const [busy, setBusy] = useState(false)
  const [resume, setResume] = useState<string[]>([])
  const [erreurs, setErreurs] = useState<VendeurErreur[]>([])
  const [nbMaj, setNbMaj] = useState(0)
  const [selectedAFormer, setSelectedAFormer] = useState('')

  const reload = useCallback(() => {
    setLoadingList(true)
    fetch('/api/adm/formations-iag/a-former', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((d) => setAFormer(Array.isArray(d) ? d : []))
      .finally(() => setLoadingList(false))
  }, [])

  useEffect(() => { reload() }, [reload])

  const onPickFile = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.xls,.xlsx'
    input.onchange = () => {
      const f = input.files?.[0]
      if (f) setSelectedFile(f)
    }
    input.click()
  }

  const handleImport = async () => {
    if (!selectedFile) {
      showToast('Sélectionne d\'abord un fichier Excel.', 'error')
      return
    }
    setBusy(true)
    setResume([])
    setErreurs([])
    setNbMaj(0)
    try {
      const fd = new FormData()
      fd.append('file', selectedFile)
      fd.append('cols', JSON.stringify(cols))
      fd.append('limit_jours', String(limitJours))
      fd.append('simulation', simulation ? 'true' : 'false')
      const r = await fetch('/api/adm/formations-iag/import', {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const d = await r.json()
      setResume(d.resume || [])
      setErreurs(d.vendeurs_erreur || [])
      setNbMaj(d.nb_maj || 0)
      showToast(
        `${simulation ? 'Simulation' : 'Import'} OK : ${d.nb_maj || 0} vendeur(s) mis à jour sur ${d.nb_lus || 0} lignes`,
        'success',
      )
      if (!simulation) reload()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const updCol = <K extends keyof IagCols>(k: K, v: string) =>
    setCols((c) => ({ ...c, [k]: v.toUpperCase() }))

  return (
    <div className="p-6 max-w-7xl mx-auto font-normal space-y-4">
      <PageHeader icon={GraduationCap} title="Suivi des formations IAG" />

      <div className="grid grid-cols-2 gap-4">
        {/* Gauche : Import */}
        <div className="space-y-3">
          <div className="bg-white border rounded-lg p-4 space-y-3"
               style={{ borderColor: COL_BORDER }}>
            <div className="flex items-center gap-2">
              <label className="text-sm w-40" style={{ color: COL_BRUN }}>
                Fichier Import XLS :
              </label>
              <input type="text" readOnly
                     value={selectedFile?.name || 'c:\\répertoire\\fichier.ext'}
                     className={`${inputCls} flex-1`} style={{ borderColor: COL_BORDER }} />
              <button type="button" onClick={onPickFile}
                      className="px-3 py-1.5 rounded text-white text-sm"
                      style={{ backgroundColor: '#16a34a' }}>
                <Upload className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-[140px_1fr] gap-y-1 gap-x-2 items-center text-sm"
                 style={{ color: COL_BRUN }}>
              <span className="font-semibold col-span-2">Colonnes Import XLS :</span>
              {(Object.keys(COL_LABELS) as (keyof IagCols)[]).map((k) => (
                <div key={k} className="contents">
                  <label className="text-right">{COL_LABELS[k]} :</label>
                  <input type="text" value={cols[k]}
                         onChange={(e) => updCol(k, e.target.value)}
                         maxLength={2}
                         className={`${inputCls} w-12 uppercase`}
                         style={{ borderColor: COL_BORDER }} />
                </div>
              ))}
            </div>

            <div className="flex items-center gap-2 text-sm" style={{ color: COL_BRUN }}>
              <label className="w-40">Limiter aux</label>
              <input type="number" min={0} value={limitJours}
                     onChange={(e) => setLimitJours(Number(e.target.value) || 0)}
                     className={`${inputCls} w-20`}
                     style={{ borderColor: COL_BORDER }} />
              <span>derniers jours</span>
            </div>

            <div className="flex items-center gap-3 pt-1">
              <button type="button" onClick={handleImport}
                      disabled={busy || !selectedFile}
                      className="flex items-center gap-2 px-4 py-1.5 rounded text-white text-sm font-medium disabled:opacity-50"
                      style={{ backgroundColor: COL_PRIMARY }}>
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                Importer le fichier
              </button>
              <label className="flex items-center gap-2 text-sm" style={{ color: COL_BRUN }}>
                <input type="checkbox" checked={simulation}
                       onChange={(e) => setSimulation(e.target.checked)} />
                Faire une simulation
              </label>
            </div>

            {nbMaj > 0 && (
              <div className="text-sm font-semibold" style={{ color: COL_BRUN }}>
                NB Vendeurs mis à jour : {nbMaj}
              </div>
            )}

            {resume.length > 0 && (
              <div className="border rounded p-2 bg-gray-50 text-xs font-mono whitespace-pre-wrap"
                   style={{ borderColor: COL_BORDER, color: COL_BRUN, maxHeight: 180, overflow: 'auto' }}>
                {resume.join('\n')}
              </div>
            )}
          </div>

          {/* Tableau erreurs */}
          <div className="bg-white border rounded-lg p-3"
               style={{ borderColor: COL_BORDER }}>
            <h3 className="text-xs font-bold uppercase flex items-center gap-2 mb-2"
                style={{ color: COL_BRUN }}>
              <AlertTriangle className="w-3.5 h-3.5" />
              Vendeurs non trouvés ({erreurs.length})
            </h3>
            <div className="border rounded overflow-auto"
                 style={{ borderColor: COL_BORDER, maxHeight: 200 }}>
              <table className="w-full text-xs">
                <thead className="sticky top-0" style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                  <tr>
                    <th className="px-2 py-1.5 text-left w-10">nb</th>
                    <th className="px-2 py-1.5 text-left">Nom</th>
                    <th className="px-2 py-1.5 text-left">Prénom</th>
                    <th className="px-2 py-1.5 text-left w-24">Date</th>
                    <th className="px-2 py-1.5 text-right w-14">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {erreurs.length === 0 ? (
                    <tr><td colSpan={5} className="p-2 text-center italic" style={{ color: '#A68D8A' }}>
                      Aucune erreur.
                    </td></tr>
                  ) : (
                    erreurs.map((e, i) => (
                      <tr key={i} className="border-b" style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
                        <td className="px-2 py-1">{e.nb_fiche}</td>
                        <td className="px-2 py-1">{e.nom}</td>
                        <td className="px-2 py-1">{e.prenom}</td>
                        <td className="px-2 py-1">{e.date_formation}</td>
                        <td className="px-2 py-1 text-right">{e.score}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Droite : Liste à former */}
        <div className="bg-white border rounded-lg p-3 space-y-2"
             style={{ borderColor: COL_BORDER }}>
          <h3 className="text-sm font-bold uppercase flex items-center gap-2"
              style={{ color: COL_BRUN }}>
            <GraduationCap className="w-4 h-4" />
            À former ({aFormer.length})
          </h3>
          <p className="text-xs italic" style={{ color: COL_BRUN }}>
            Salariés actifs concernés (FormationIAG = 0 ou score &lt; 13)
            sur les postes VRP / MANAGER / AGENCE / REGION / DA.
          </p>
          <div className="border rounded overflow-auto"
               style={{ borderColor: COL_BORDER, maxHeight: 'calc(70vh - 80px)', backgroundColor: COL_BG_SOFT }}>
            <table className="w-full text-xs">
              <thead className="sticky top-0" style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                <tr>
                  <th className="px-2 py-2 text-left">nbFiche</th>
                  <th className="px-2 py-2 text-left">Nom</th>
                  <th className="px-2 py-2 text-left">Prénom</th>
                  <th className="px-2 py-2 text-left">Date Formation</th>
                  <th className="px-2 py-2 text-right w-14">Score</th>
                </tr>
              </thead>
              <tbody>
                {loadingList ? (
                  <tr><td colSpan={5} className="p-4 text-center">
                    <Loader2 className="w-4 h-4 animate-spin inline" /></td></tr>
                ) : aFormer.length === 0 ? (
                  <tr><td colSpan={5} className="p-4 text-center italic" style={{ color: '#A68D8A' }}>
                    Aucun salarié à former.</td></tr>
                ) : (
                  aFormer.map((s) => {
                    const isSel = selectedAFormer === s.id_salarie
                    return (
                      <tr key={s.id_salarie}
                          onClick={() => setSelectedAFormer(s.id_salarie)}
                          className="cursor-pointer border-b"
                          style={{
                            backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                            color: isSel ? 'white' : COL_BRUN,
                            borderColor: COL_BORDER,
                          }}>
                        <td className="px-2 py-1">{s.id_ste}</td>
                        <td className="px-2 py-1 font-semibold">{s.nom}</td>
                        <td className="px-2 py-1">{s.prenom}</td>
                        <td className="px-2 py-1">{s.formation_iag_date
                          ? `${s.formation_iag_date.slice(8,10)}/${s.formation_iag_date.slice(5,7)}/${s.formation_iag_date.slice(0,4)}`
                          : ''}</td>
                        <td className="px-2 py-1 text-right">{s.formation_iag_score || ''}</td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
