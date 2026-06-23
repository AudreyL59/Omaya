/**
 * Fen_AnalyseCarb : Détecter Alerte Carb.
 *
 * Détecte les pleins de Carburant le Vendredi suivis d'un plein le
 * Lundi suivant sur la même carte (= soupçon d'usage perso le weekend).
 *
 * Filtres : Du / Au. Btn 'Détecter alerte' -> tableau (Num Carte, Nom
 * Conducteur, Date Vendredi, Détail alerte).
 */

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertCircle, Loader2, X } from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface Alerte {
  num_carte: string
  date_vendredi: string
  nom_conducteur: string
  detail_alerte: string
}

const inputCls =
  'px-2 py-1.5 rounded border bg-white text-sm focus:outline-none focus:ring-1'

interface Props {
  open: boolean
  onClose: () => void
}

export default function AnalyseCarbModal({ open, onClose }: Props) {
  const today = new Date()
  const firstOfMonth = new Date(today.getFullYear(), today.getMonth(), 1)
  const isoTd = (d: Date) => d.toISOString().slice(0, 10)
  const [du, setDu] = useState(isoTd(firstOfMonth))
  const [au, setAu] = useState(isoTd(today))
  const [list, setList] = useState<Alerte[]>([])
  const [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState('')

  const handleDetect = async () => {
    setBusy(true)
    try {
      const url = new URL('/api/adm/carte-carb/alertes/detect', window.location.origin)
      url.searchParams.set('du', du)
      url.searchParams.set('au', au)
      const r = await fetch(url.toString(), {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      setList(Array.isArray(d) ? d : [])
      showToast(`${(Array.isArray(d) ? d : []).length} alerte(s) détectée(s)`, 'info')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const fmtDate = (s: string) => s.length >= 10
    ? `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}` : ''

  return (
    <AnimatePresence>
      {open && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="bg-white rounded-2xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden"
            onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-3 border-b"
              style={{ borderColor: COL_BORDER, backgroundColor: COL_PRIMARY, color: 'white' }}>
              <h2 className="text-base font-semibold flex items-center gap-2">
                <AlertCircle className="w-5 h-5" />
                Analyse Utilisation Carte Carb
              </h2>
              <button onClick={onClose} className="text-white/80 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-auto p-4 space-y-3" style={{ backgroundColor: COL_BG_SOFT }}>
              <div className="flex items-center gap-3 flex-wrap">
                <label className="text-sm" style={{ color: COL_BRUN }}>Du</label>
                <input type="date" value={du} onChange={(e) => setDu(e.target.value)}
                  className={inputCls} style={{ borderColor: COL_BORDER }} />
                <label className="text-sm" style={{ color: COL_BRUN }}>Au</label>
                <input type="date" value={au} onChange={(e) => setAu(e.target.value)}
                  className={inputCls} style={{ borderColor: COL_BORDER }} />
                <button type="button" onClick={handleDetect} disabled={busy}
                  className="flex items-center gap-2 px-4 py-1.5 rounded text-white text-sm disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}>
                  {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <AlertCircle className="w-4 h-4" />}
                  Détecter alerte
                </button>
                {list.length > 0 && (
                  <span className="text-xs italic ml-auto" style={{ color: COL_BRUN }}>
                    {list.length} alerte(s)
                  </span>
                )}
              </div>

              <div className="text-xs italic" style={{ color: COL_BRUN }}>
                Détecte les pleins Carburant le Vendredi suivis d'un plein le Lundi suivant
                sur la même carte (soupçon d'utilisation personnelle le weekend).
              </div>

              <div className="border rounded-lg overflow-auto bg-white"
                style={{ borderColor: COL_BORDER, maxHeight: 'calc(80vh - 200px)' }}>
                <table className="w-full text-xs">
                  <thead className="sticky top-0" style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                    <tr>
                      <th className="px-2 py-2 text-left w-32">Num Carte</th>
                      <th className="px-2 py-2 text-left w-48">Nom Conducteur</th>
                      <th className="px-2 py-2 text-left w-28">Date Vendredi</th>
                      <th className="px-2 py-2 text-left">Détail alerte</th>
                    </tr>
                  </thead>
                  <tbody>
                    {list.length === 0 ? (
                      <tr><td colSpan={4} className="p-6 text-center italic" style={{ color: '#A68D8A' }}>
                        Aucune alerte détectée.
                      </td></tr>
                    ) : (
                      list.map((a, i) => {
                        const key = `${a.num_carte}-${a.date_vendredi}-${i}`
                        const isSel = selected === key
                        return (
                          <tr key={key}
                            onClick={() => setSelected(key)}
                            className="cursor-pointer border-b"
                            style={{
                              backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                              color: isSel ? 'white' : COL_BRUN,
                              borderColor: COL_BORDER,
                            }}>
                            <td className="px-2 py-1">{a.num_carte}</td>
                            <td className="px-2 py-1">{a.nom_conducteur}</td>
                            <td className="px-2 py-1">{fmtDate(a.date_vendredi)}</td>
                            <td className="px-2 py-1 whitespace-pre-wrap">{a.detail_alerte}</td>
                          </tr>
                        )
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
