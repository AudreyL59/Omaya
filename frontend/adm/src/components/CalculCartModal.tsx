/**
 * Fen_CalculCart : Calcul montant carte carburant.
 *
 * Combo Mois + input Annee + btn 'Demarrer Calcul'.
 * Tableau resultats : Code, Num Carte, Nom Prenom, Vehicule, Calcul Prod,
 * Agence, Equipe, NB Place, nb Prod Tot, nb Jours, Moy Prod, Detecte,
 * Attribue, Carburant, Peage, Total, Diff, Validé.
 * Montant Attribue editable (clic) -> PUT /calcul/{id}/attribue.
 */

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2, Play, Sigma, X } from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface Ligne {
  id_carte_calcul_att: string
  id_carte_attribution: string
  code_carte: string
  num_carte: string
  nom_prenom: string
  vehicule: string
  calcul_prod: boolean
  agence: string
  equipe: string
  nb_place: number
  nb_prod_tot: number
  nb_jours_prod: number
  moy_prod: number
  montant_detecte: number
  montant_attribue: number
  montant_carb: number
  montant_peage: number
  montant_total: number
  difference: number
  montant_valide: number
}

const MOIS = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
]

interface Props {
  open: boolean
  onClose: () => void
}

export default function CalculCartModal({ open, onClose }: Props) {
  const today = new Date()
  const [mois, setMois] = useState(today.getMonth() + 1)
  const [annee, setAnnee] = useState(today.getFullYear())
  const [lignes, setLignes] = useState<Ligne[]>([])
  const [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState('')
  const [edit, setEdit] = useState<{ id: string; val: string } | null>(null)

  // Au load : essaie de lire un calcul existant pour mois/annee courant
  useEffect(() => {
    if (!open) return
    fetch(`/api/adm/carte-carb/calcul?mois=${mois}&annee=${annee}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((d) => setLignes(Array.isArray(d) ? d : []))
  }, [open, mois, annee])

  const handleCalcul = async () => {
    setBusy(true)
    setLignes([])
    try {
      const r = await fetch('/api/adm/carte-carb/calcul', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ mois, annee }),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const d = await r.json()
      setLignes(d.lignes || [])
      showToast(`Calcul terminé : ${(d.lignes || []).length} attribution(s)`, 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const saveAttribue = async (id: string, val: number) => {
    try {
      const r = await fetch(`/api/adm/carte-carb/calcul/${id}/attribue`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ montant_attribue: val }),
      })
      if (!r.ok) throw new Error(String(r.status))
      // Met a jour localement + recalcule Montant_valide
      setLignes((rows) => rows.map((l) => {
        if (l.id_carte_calcul_att !== id) return l
        const diff = l.montant_detecte - l.montant_total
        const valide = diff < 0 ? val + diff : val
        return { ...l, montant_attribue: val, difference: diff, montant_valide: valide }
      }))
      showToast('Modifié.', 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    }
  }

  const fmt = (n: number) => n.toFixed(0) + ' €'

  return (
    <AnimatePresence>
      {open && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="bg-white rounded-2xl shadow-xl w-full max-w-[95vw] max-h-[90vh] flex flex-col overflow-hidden"
            onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-3 border-b"
              style={{ borderColor: COL_BORDER, backgroundColor: COL_PRIMARY, color: 'white' }}>
              <h2 className="text-base font-semibold flex items-center gap-2">
                <Sigma className="w-5 h-5" />
                Calcul montant carte carburant
              </h2>
              <button onClick={onClose} className="text-white/80 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-auto p-4 space-y-3" style={{ backgroundColor: COL_BG_SOFT }}>
              <div className="flex items-center gap-3">
                <label className="text-sm" style={{ color: COL_BRUN }}>Mois :</label>
                <select value={mois} onChange={(e) => setMois(Number(e.target.value))}
                  className="px-2 py-1.5 rounded border text-sm"
                  style={{ borderColor: COL_BORDER }}>
                  {MOIS.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
                </select>
                <label className="text-sm" style={{ color: COL_BRUN }}>Année :</label>
                <input type="number" value={annee} onChange={(e) => setAnnee(Number(e.target.value))}
                  className="px-2 py-1.5 rounded border text-sm w-24"
                  style={{ borderColor: COL_BORDER }} />
                <button type="button" onClick={handleCalcul} disabled={busy}
                  className="flex items-center gap-2 px-4 py-1.5 rounded text-white text-sm font-medium disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}>
                  {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  Démarrer Calcul
                </button>
                <div className="flex-1" />
                {lignes.length > 0 && (
                  <span className="text-xs italic" style={{ color: COL_BRUN }}>
                    {lignes.length} attribution(s) — clic sur Attribué pour modifier
                  </span>
                )}
              </div>

              <div className="border rounded-lg overflow-auto bg-white"
                style={{ borderColor: COL_BORDER, maxHeight: 'calc(80vh - 130px)' }}>
                <table className="w-full text-xs">
                  <thead className="sticky top-0" style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                    <tr>
                      <th className="px-2 py-2 text-left">Code</th>
                      <th className="px-2 py-2 text-left">Num Carte</th>
                      <th className="px-2 py-2 text-left">Nom Prénom</th>
                      <th className="px-2 py-2 text-left">Véhicule</th>
                      <th className="px-2 py-2 text-center w-12">Prod</th>
                      <th className="px-2 py-2 text-left">Agence</th>
                      <th className="px-2 py-2 text-left">Équipe</th>
                      <th className="px-2 py-2 text-right w-14">Place</th>
                      <th className="px-2 py-2 text-right w-14">Prod</th>
                      <th className="px-2 py-2 text-right w-14">Jrs</th>
                      <th className="px-2 py-2 text-right w-16">Moy</th>
                      <th className="px-2 py-2 text-right w-20">Détecté</th>
                      <th className="px-2 py-2 text-right w-20">Attribué</th>
                      <th className="px-2 py-2 text-right w-20">Carb</th>
                      <th className="px-2 py-2 text-right w-20">Péage</th>
                      <th className="px-2 py-2 text-right w-20">Total</th>
                      <th className="px-2 py-2 text-right w-20">Diff</th>
                      <th className="px-2 py-2 text-right w-20">Validé</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lignes.length === 0 ? (
                      <tr><td colSpan={18} className="p-6 text-center italic" style={{ color: '#A68D8A' }}>
                        Aucun résultat. Choisis un mois/année et clique sur Démarrer Calcul.
                      </td></tr>
                    ) : (
                      lignes.map((l) => {
                        const isSel = selected === l.id_carte_calcul_att
                        const isEditing = edit?.id === l.id_carte_calcul_att
                        return (
                          <tr key={l.id_carte_calcul_att}
                            onClick={() => setSelected(l.id_carte_calcul_att)}
                            className="cursor-pointer border-b"
                            style={{
                              backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                              color: isSel ? 'white' : COL_BRUN,
                              borderColor: COL_BORDER,
                            }}>
                            <td className="px-2 py-1">{l.code_carte}</td>
                            <td className="px-2 py-1">{l.num_carte}</td>
                            <td className="px-2 py-1">{l.nom_prenom}</td>
                            <td className="px-2 py-1">{l.vehicule}</td>
                            <td className="px-2 py-1 text-center">{l.calcul_prod ? '✓' : ''}</td>
                            <td className="px-2 py-1">{l.agence}</td>
                            <td className="px-2 py-1">{l.equipe}</td>
                            <td className="px-2 py-1 text-right">{l.nb_place || ''}</td>
                            <td className="px-2 py-1 text-right">{l.nb_prod_tot || ''}</td>
                            <td className="px-2 py-1 text-right">{l.nb_jours_prod || ''}</td>
                            <td className="px-2 py-1 text-right">{l.moy_prod ? l.moy_prod.toFixed(1) : ''}</td>
                            <td className="px-2 py-1 text-right">{fmt(l.montant_detecte)}</td>
                            <td className="px-2 py-1 text-right">
                              {isEditing ? (
                                <input type="number" autoFocus value={edit.val}
                                  onClick={(e) => e.stopPropagation()}
                                  onChange={(e) => setEdit({ id: l.id_carte_calcul_att, val: e.target.value })}
                                  onBlur={() => {
                                    const v = Number(edit.val) || 0
                                    if (v !== l.montant_attribue) saveAttribue(l.id_carte_calcul_att, v)
                                    setEdit(null)
                                  }}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') (e.target as HTMLInputElement).blur()
                                    if (e.key === 'Escape') setEdit(null)
                                  }}
                                  className="w-16 px-1 py-0.5 border rounded text-right text-xs"
                                  style={{ color: COL_BRUN }} />
                              ) : (
                                <span onClick={(e) => {
                                  e.stopPropagation()
                                  setEdit({ id: l.id_carte_calcul_att, val: String(l.montant_attribue) })
                                }} className="cursor-text underline-offset-2 hover:underline">
                                  {fmt(l.montant_attribue)}
                                </span>
                              )}
                            </td>
                            <td className="px-2 py-1 text-right">{fmt(l.montant_carb)}</td>
                            <td className="px-2 py-1 text-right">{fmt(l.montant_peage)}</td>
                            <td className="px-2 py-1 text-right font-semibold">{fmt(l.montant_total)}</td>
                            <td className="px-2 py-1 text-right" style={{
                              color: isSel ? 'white' : (l.difference < 0 ? '#B91C1C' : COL_BRUN),
                            }}>{fmt(l.difference)}</td>
                            <td className="px-2 py-1 text-right font-semibold">{fmt(l.montant_valide)}</td>
                          </tr>
                        )
                      })
                    )}
                  </tbody>
                </table>
              </div>

              <div className="text-xs italic" style={{ color: COL_BRUN }}>
                Diff = Montant Détecté − Total carte. Si négatif, Validé = Attribué + Diff (= ajustement défavorable).
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
