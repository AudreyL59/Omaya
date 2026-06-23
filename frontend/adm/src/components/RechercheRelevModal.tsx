/**
 * Fen_RechercheRelev : Recherche relevé carte carburant.
 *
 * Filtres : Du / Au / Carte carburant (combo) / Type catégorie (combo).
 * Btn Loupe -> fetch + tableau (DATE, Heure, Fournisseur, NumCarte,
 * Catégorie, Lib_Type, MontantTTC, Attribuée à).
 * Ligne "Somme" en bas.
 */

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2, Search, X } from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface CarteCombo { id_carte_carburant: string; nom_carte: string }
interface Releve {
  id_carte_carb_releve_fournisseur: string
  date: string
  heure: string
  nom_fournisseur: string
  num_carte: string
  categorie: string
  lib_type: string
  montant_ttc: number
  attribue_a: string
}

const inputCls =
  'px-2 py-1.5 rounded border bg-white text-sm focus:outline-none focus:ring-1'

interface Props {
  open: boolean
  onClose: () => void
}

export default function RechercheRelevModal({ open, onClose }: Props) {
  const today = new Date()
  const firstOfMonth = new Date(today.getFullYear(), today.getMonth(), 1)
  const isoTd = (d: Date) => d.toISOString().slice(0, 10)
  const [du, setDu] = useState(isoTd(firstOfMonth))
  const [au, setAu] = useState(isoTd(today))
  const [idCarte, setIdCarte] = useState('')
  const [categorie, setCategorie] = useState('')
  const [cartes, setCartes] = useState<CarteCombo[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [lignes, setLignes] = useState<Releve[]>([])
  const [total, setTotal] = useState(0)
  const [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState('')

  useEffect(() => {
    if (!open) return
    fetch('/api/adm/carte-carb/cartes-combo', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.ok ? r.json() : [])
      .then((d) => setCartes(Array.isArray(d) ? d : []))
    fetch('/api/adm/carte-carb/categories', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.ok ? r.json() : [])
      .then((d) => setCategories(Array.isArray(d) ? d : []))
  }, [open])

  const handleSearch = async () => {
    setBusy(true)
    try {
      const url = new URL('/api/adm/carte-carb/releves/search', window.location.origin)
      url.searchParams.set('du', du)
      url.searchParams.set('au', au)
      if (idCarte) url.searchParams.set('id_carte_carburant', idCarte)
      if (categorie) url.searchParams.set('categorie', categorie)
      const r = await fetch(url.toString(), {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      setLignes(d.lignes || [])
      setTotal(d.total_ttc || 0)
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const fmtDate = (s: string) => s.length >= 10
    ? `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}` : ''
  const fmt = (n: number) => n.toFixed(2) + ' €'

  return (
    <AnimatePresence>
      {open && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="bg-white rounded-2xl shadow-xl w-full max-w-[90vw] max-h-[90vh] flex flex-col overflow-hidden"
            onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-3 border-b"
              style={{ borderColor: COL_BORDER, backgroundColor: COL_PRIMARY, color: 'white' }}>
              <h2 className="text-base font-semibold flex items-center gap-2">
                <Search className="w-5 h-5" />
                Recherche relevé
              </h2>
              <button onClick={onClose} className="text-white/80 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-auto p-4 space-y-3" style={{ backgroundColor: COL_BG_SOFT }}>
              <div className="flex items-center gap-2 flex-wrap">
                <label className="text-sm" style={{ color: COL_BRUN }}>Du</label>
                <input type="date" value={du} onChange={(e) => setDu(e.target.value)}
                  className={inputCls} style={{ borderColor: COL_BORDER }} />
                <label className="text-sm" style={{ color: COL_BRUN }}>Au</label>
                <input type="date" value={au} onChange={(e) => setAu(e.target.value)}
                  className={inputCls} style={{ borderColor: COL_BORDER }} />
                <label className="text-sm" style={{ color: COL_BRUN }}>Carte carburant</label>
                <select value={idCarte} onChange={(e) => setIdCarte(e.target.value)}
                  className={inputCls + ' min-w-[200px]'} style={{ borderColor: COL_BORDER }}>
                  <option value="">— Toutes —</option>
                  {cartes.map((c) => (
                    <option key={c.id_carte_carburant} value={c.id_carte_carburant}>
                      {c.nom_carte}
                    </option>
                  ))}
                </select>
                <label className="text-sm" style={{ color: COL_BRUN }}>Type</label>
                <select value={categorie} onChange={(e) => setCategorie(e.target.value)}
                  className={inputCls} style={{ borderColor: COL_BORDER }}>
                  <option value="">— Tous —</option>
                  {categories.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <button type="button" onClick={handleSearch} disabled={busy}
                  className="flex items-center gap-2 px-4 py-1.5 rounded text-white text-sm disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}>
                  {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                </button>
              </div>

              <div className="border rounded-lg overflow-auto bg-white"
                style={{ borderColor: COL_BORDER, maxHeight: 'calc(80vh - 160px)' }}>
                <table className="w-full text-xs">
                  <thead className="sticky top-0" style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                    <tr>
                      <th className="px-2 py-2 text-left w-28">DATE</th>
                      <th className="px-2 py-2 text-left w-20">Heure</th>
                      <th className="px-2 py-2 text-left">Fournisseur</th>
                      <th className="px-2 py-2 text-left">NumCarte</th>
                      <th className="px-2 py-2 text-left">Catégorie</th>
                      <th className="px-2 py-2 text-left">Lib_Type</th>
                      <th className="px-2 py-2 text-right w-28">MontantTTC</th>
                      <th className="px-2 py-2 text-left">Attribuée à</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lignes.length === 0 ? (
                      <tr><td colSpan={8} className="p-6 text-center italic" style={{ color: '#A68D8A' }}>
                        Aucun relevé. Lance une recherche.
                      </td></tr>
                    ) : (
                      lignes.map((l) => {
                        const isSel = selected === l.id_carte_carb_releve_fournisseur
                        return (
                          <tr key={l.id_carte_carb_releve_fournisseur}
                            onClick={() => setSelected(l.id_carte_carb_releve_fournisseur)}
                            className="cursor-pointer border-b"
                            style={{
                              backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                              color: isSel ? 'white' : COL_BRUN,
                              borderColor: COL_BORDER,
                            }}>
                            <td className="px-2 py-1">{fmtDate(l.date)}</td>
                            <td className="px-2 py-1">{l.heure}</td>
                            <td className="px-2 py-1">{l.nom_fournisseur}</td>
                            <td className="px-2 py-1">{l.num_carte}</td>
                            <td className="px-2 py-1">{l.categorie}</td>
                            <td className="px-2 py-1">{l.lib_type}</td>
                            <td className="px-2 py-1 text-right">{fmt(l.montant_ttc)}</td>
                            <td className="px-2 py-1">{l.attribue_a}</td>
                          </tr>
                        )
                      })
                    )}
                  </tbody>
                  {lignes.length > 0 && (
                    <tfoot className="sticky bottom-0" style={{ backgroundColor: COL_BG_SOFT }}>
                      <tr style={{ borderTop: `2px solid ${COL_PRIMARY}` }}>
                        <td colSpan={6} className="px-2 py-2 text-right font-semibold" style={{ color: COL_BRUN }}>
                          Somme
                        </td>
                        <td className="px-2 py-2 text-right font-semibold" style={{ color: COL_BRUN }}>
                          {fmt(total)}
                        </td>
                        <td />
                      </tr>
                    </tfoot>
                  )}
                </table>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
