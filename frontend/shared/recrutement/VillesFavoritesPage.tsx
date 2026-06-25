/**
 * Fen_VillesFavorites (shared) — CRUD des villes en favori
 * (pgt_communes_france.favorite = TRUE).
 *
 * Toolbar : Ajouter une ville en favori (ouvre VilleAutocomplete dans
 * un sub-modal) + Retirer des favoris (sur ligne selectionnee).
 */

import { useCallback, useEffect, useState } from 'react'
import { Loader2, MapPin, Plus, Trash2, X } from 'lucide-react'
import { getToken } from '@/api'
import { showConfirm, showToast } from '../ui/dialog'
import VilleAutocomplete from './VilleAutocomplete'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface VilleFav {
  id_communes_france: string
  nom_ville: string
  code_postal: string
  departement: string
  latitude_deg: number
  longitude_deg: number
}

interface VillesFavoritesPageProps {
  apiBase: string
}

export default function VillesFavoritesPage({ apiBase }: VillesFavoritesPageProps) {
  const [rows, setRows] = useState<VilleFav[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState('')
  const [showAdd, setShowAdd] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    fetch(`${apiBase}/recrutement/cv/villes-favorites`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then(d => setRows(Array.isArray(d) ? d : []))
      .finally(() => setLoading(false))
  }, [apiBase])

  useEffect(() => { load() }, [load])

  const ajouter = async (id: string, cp: string, ville: string) => {
    if (!id) return
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/villes-favorites/${id}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast(`${cp} ${ville} ajouté aux favoris.`, 'success')
      setShowAdd(false)
      load()
    } catch (e) { showToast(`Erreur : ${(e as Error).message}`, 'error') }
  }

  const retirer = async () => {
    if (!selectedId) {
      showToast('Sélectionne une ville à retirer.', 'info'); return
    }
    const v = rows.find(r => r.id_communes_france === selectedId)
    const ok = await showConfirm({
      title: 'Retirer des favoris ?',
      message: `Vous êtes sur le point de retirer ${v?.code_postal || ''} ${v?.nom_ville || ''} des favoris. Voulez-vous continuer ?`,
      confirmLabel: 'Retirer',
    })
    if (!ok) return
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/villes-favorites/${selectedId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast('Ville retirée des favoris.', 'success')
      setSelectedId(''); load()
    } catch (e) { showToast(`Erreur : ${(e as Error).message}`, 'error') }
  }

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-120px)]"
         style={{ color: COL_BRUN }}>
      <h1 className="text-xl font-bold mb-3">Villes Favorites pour les imports CV</h1>

      <div className="flex-1 flex flex-col min-h-0 border rounded"
           style={{ borderColor: COL_BORDER }}>
        <div className="px-3 py-2 flex items-center gap-2 border-b"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          <button type="button" onClick={() => setShowAdd(true)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded text-white text-xs"
                  style={{ backgroundColor: COL_PRIMARY }}>
            <Plus className="w-3.5 h-3.5" />
            Ajouter une ville en favori
          </button>
          <button type="button" onClick={retirer} disabled={!selectedId}
                  className="flex items-center gap-1 px-3 py-1.5 rounded border text-xs disabled:opacity-40"
                  style={{
                    borderColor: COL_BORDER,
                    backgroundColor: '#B91C1C', color: 'white',
                  }}>
            <Trash2 className="w-3.5 h-3.5" />
            Retirer des favoris
          </button>
          <div className="flex-1" />
          <span className="text-xs italic" style={{ color: '#A68D8A' }}>
            {rows.length} ville(s) favorite(s)
          </span>
        </div>

        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="p-8 flex justify-center">
              <Loader2 className="w-6 h-6 animate-spin"
                       style={{ color: COL_PRIMARY }} />
            </div>
          ) : rows.length === 0 ? (
            <p className="p-8 text-center italic"
               style={{ color: '#A68D8A' }}>
              Aucune ville en favori.
            </p>
          ) : (
            <table className="w-full text-xs">
              <thead className="sticky top-0"
                     style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                <tr>
                  <th className="px-2 py-2 text-left">NomVille</th>
                  <th className="px-2 py-2 text-left">CodePostal</th>
                  <th className="px-2 py-2 text-left">Département</th>
                  <th className="px-2 py-2 text-right">Latitude</th>
                  <th className="px-2 py-2 text-right">Longitude</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(r => {
                  const isSel = selectedId === r.id_communes_france
                  return (
                    <tr key={r.id_communes_france}
                        onClick={() => setSelectedId(r.id_communes_france)}
                        className="border-b cursor-pointer"
                        style={{
                          borderColor: COL_BORDER,
                          backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                          color: isSel ? 'white' : COL_BRUN,
                        }}>
                      <td className="px-2 py-1.5 font-semibold">
                        <MapPin className="w-3 h-3 inline mr-1" />
                        {r.nom_ville}
                      </td>
                      <td className="px-2 py-1.5">{r.code_postal}</td>
                      <td className="px-2 py-1.5">{r.departement}</td>
                      <td className="px-2 py-1.5 text-right font-mono">
                        {r.latitude_deg ? r.latitude_deg.toFixed(4) : ''}
                      </td>
                      <td className="px-2 py-1.5 text-right font-mono">
                        {r.longitude_deg ? r.longitude_deg.toFixed(4) : ''}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Sub-modal : picker ville (Fen_RechercheVille) */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full"
               style={{ border: `1px solid ${COL_BORDER}` }}>
            <div className="px-4 py-3 border-b flex items-center gap-2"
                 style={{ borderColor: COL_BORDER }}>
              <Plus className="w-5 h-5" style={{ color: COL_PRIMARY }} />
              <h3 className="text-base font-bold flex-1" style={{ color: COL_BRUN }}>
                Choisir une ville à ajouter
              </h3>
              <button type="button" onClick={() => setShowAdd(false)}
                      className="p-1 rounded hover:bg-gray-100">
                <X className="w-4 h-4" style={{ color: COL_BRUN }} />
              </button>
            </div>
            <div className="p-4">
              <VilleAutocomplete apiBase={apiBase}
                                 value="" label=""
                                 onChange={ajouter}
                                 placeholder="Tape un CP ou une ville" />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
