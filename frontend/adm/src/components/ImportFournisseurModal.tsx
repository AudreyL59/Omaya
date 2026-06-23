/**
 * Fen_ImportFournisseurCarte : import des releves Excel d'un fournisseur.
 *
 * Pour l'instant : Total Energies. Quand un autre fournisseur est choisi,
 * on affiche un placeholder.
 *
 * Le user :
 *  1. Choisit le fournisseur dans le combo.
 *  2. Si Total Energies : ajuste les mappings de colonnes Excel (defaults
 *     A-J).
 *  3. Coche/decoche Simulation.
 *  4. Clique 'Importer' -> file picker -> upload + affichage du resume.
 */

import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Database, Loader2, Upload, X } from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface Fournisseur {
  id_carte_fournisseur: string
  nom_fournisseur: string
  logo: string
}

interface TotalCols {
  id_facture: string
  compte_client: string
  num_carte: string
  code_carte: string
  date: string
  heure: string
  lieu: string
  lib_type: string
  montant_ht: string
  montant_ttc: string
}

const TOTAL_DEFAULTS: TotalCols = {
  id_facture: 'A',
  compte_client: 'B',
  num_carte: 'C',
  code_carte: 'D',
  date: 'E',
  heure: 'F',
  lieu: 'G',
  lib_type: 'H',
  montant_ht: 'I',
  montant_ttc: 'J',
}

const TOTAL_LABELS: Record<keyof TotalCols, string> = {
  id_facture: 'ID Facturation',
  compte_client: 'Cpte Client',
  num_carte: 'Num Carte',
  code_carte: 'Code Carte',
  date: 'Date',
  heure: 'Heure',
  lieu: 'Lieu',
  lib_type: 'Type',
  montant_ht: 'Montant HT',
  montant_ttc: 'Montant TTC',
}

const inputCls =
  'w-full px-2.5 py-1.5 rounded border bg-white text-sm focus:outline-none focus:ring-1'

interface Props {
  open: boolean
  onClose: () => void
}

export default function ImportFournisseurModal({ open, onClose }: Props) {
  const [fournisseurs, setFournisseurs] = useState<Fournisseur[]>([])
  const [idFour, setIdFour] = useState('')
  const [simulation, setSimulation] = useState(true)
  const [ligneDepart, setLigneDepart] = useState(2)
  const [cols, setCols] = useState<TotalCols>(TOTAL_DEFAULTS)
  const [busy, setBusy] = useState(false)
  const [resume, setResume] = useState<string[]>([])

  const reload = useCallback(() => {
    fetch('/api/adm/carte-carb/fournisseurs', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((d) => setFournisseurs(Array.isArray(d) ? d : []))
  }, [])

  useEffect(() => {
    if (open) reload()
  }, [open, reload])

  const fourLib =
    fournisseurs.find((f) => f.id_carte_fournisseur === idFour)?.nom_fournisseur || ''
  const isTotal = /total/i.test(fourLib)

  const handleImport = () => {
    if (!idFour) {
      showToast('Choisis un fournisseur.', 'error')
      return
    }
    if (!isTotal) {
      showToast('Import non supporté pour ce fournisseur.', 'error')
      return
    }
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.xls,.xlsx'
    input.onchange = async () => {
      const f = input.files?.[0]
      if (!f) return
      setBusy(true)
      setResume([])
      try {
        const fd = new FormData()
        fd.append('file', f)
        fd.append('type_import', 'total_energies')
        fd.append('id_carte_fournisseur', idFour)
        fd.append('ligne_depart', String(ligneDepart))
        fd.append('simulation', simulation ? 'true' : 'false')
        fd.append('cols', JSON.stringify(cols))
        const r = await fetch('/api/adm/carte-carb/import-fournisseur', {
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
        showToast(
          `${simulation ? 'Simulation' : 'Import'} OK : ${d.nb_ajout || 0} ajout(s) sur ${d.nb_lus || 0} ligne(s) lue(s)`,
          'success',
        )
      } catch (e) {
        showToast(`Échec : ${(e as Error).message}`, 'error')
      } finally {
        setBusy(false)
      }
    }
    input.click()
  }

  const upd = <K extends keyof TotalCols>(k: K, v: string) =>
    setCols((c) => ({ ...c, [k]: v.toUpperCase() }))

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div
              className="flex items-center justify-between px-5 py-3 border-b"
              style={{ borderColor: COL_BORDER, backgroundColor: COL_PRIMARY, color: 'white' }}
            >
              <h2 className="text-base font-semibold flex items-center gap-2">
                <Database className="w-5 h-5" />
                Import Fournisseur Carte Carburant
              </h2>
              <button onClick={onClose} className="text-white/80 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-auto p-5 space-y-4"
                 style={{ backgroundColor: COL_BG_SOFT }}>
              <div className="flex items-center gap-3">
                <select value={idFour} onChange={(e) => setIdFour(e.target.value)}
                        className={`${inputCls} flex-1`}
                        style={{ borderColor: COL_BORDER }}>
                  <option value="">Fournisseur</option>
                  {fournisseurs.map((f) => (
                    <option key={f.id_carte_fournisseur} value={f.id_carte_fournisseur}>
                      {f.nom_fournisseur}
                    </option>
                  ))}
                </select>
                <label className="flex items-center gap-2 text-sm whitespace-nowrap"
                       style={{ color: COL_BRUN }}>
                  <input type="checkbox" checked={simulation}
                         onChange={(e) => setSimulation(e.target.checked)} />
                  Simulation
                </label>
                <button type="button" onClick={handleImport} disabled={busy || !idFour}
                        className="flex items-center gap-2 px-4 py-1.5 rounded text-white text-sm font-medium disabled:opacity-50"
                        style={{ backgroundColor: COL_PRIMARY }}>
                  {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                  Importer
                </button>
              </div>

              {idFour && !isTotal && (
                <div className="text-sm italic" style={{ color: COL_BRUN }}>
                  Aucun mapping configuré pour ce fournisseur. Seul Total Energies
                  est supporté pour l'instant.
                </div>
              )}

              {idFour && isTotal && (
                <div className="border rounded-lg p-4 bg-white space-y-3"
                     style={{ borderColor: COL_BORDER }}>
                  <h3 className="text-sm font-bold uppercase" style={{ color: COL_BRUN }}>
                    Total Energies
                  </h3>
                  <div className="flex items-center gap-2">
                    <label className="text-sm w-32" style={{ color: COL_BRUN }}>
                      Ligne Départ :
                    </label>
                    <input type="number" min={1} value={ligneDepart}
                           onChange={(e) => setLigneDepart(Number(e.target.value) || 1)}
                           className={`${inputCls} w-24`}
                           style={{ borderColor: COL_BORDER }} />
                  </div>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                    {(Object.keys(TOTAL_LABELS) as (keyof TotalCols)[]).map((k) => (
                      <div key={k} className="flex items-center gap-2">
                        <label className="w-28 text-right" style={{ color: COL_BRUN }}>
                          {TOTAL_LABELS[k]} :
                        </label>
                        <input type="text" value={cols[k]}
                               onChange={(e) => upd(k, e.target.value)}
                               placeholder="A"
                               maxLength={3}
                               className={`${inputCls} w-16 uppercase`}
                               style={{ borderColor: COL_BORDER }} />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {resume.length > 0 && (
                <div className="border rounded-lg p-3 bg-white text-xs font-mono"
                     style={{ borderColor: COL_BORDER, color: COL_BRUN, maxHeight: 240, overflow: 'auto' }}>
                  {resume.map((l, i) => (
                    <div key={i} className="whitespace-pre-wrap">{l}</div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
