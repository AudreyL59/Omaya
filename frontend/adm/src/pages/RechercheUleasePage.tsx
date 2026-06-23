/**
 * Fen_RechUlease (WinDev) - Ulease -> Recherche Véhicule / Conducteur.
 *
 * 2 sections cote-a-cote :
 *  - Recherche Vehicule : filtres + tableau + double-clic = ouvre la
 *    FicheVehiculeModal.
 *  - Recherche Conducteur : filtres + tableau (V1 sans double-clic).
 */

import { useCallback, useEffect, useState } from 'react'
import {
  AnimatePresence,
} from 'framer-motion'
import {
  Car as CarIcon,
  Loader2,
  Search,
  Users,
} from 'lucide-react'

import { getToken } from '@/api'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { showToast } from '@shared/ui/dialog'
import FicheVehiculeModal from '@/components/FicheVehiculeModal'

interface EtatVehicule { id_vehicule_etat: number; lib: string }
interface MarqueVehicule { id_vehicule_marque: string; nom: string }
interface Societe { id_ste: string; raison_sociale: string; rs_interne: string }

interface Lookups {
  etats: EtatVehicule[]
  marques: MarqueVehicule[]
  societes: Societe[]
}

interface Vehicule {
  id_vehicule: string
  modele: string
  immat: string
  chevaux_fiscaux: number
  forfait_km: number
  k_mdepart: number
  km_actuel: number
  marque_nom: string
  marque_logo: string
  lib_etat: string
}

interface Conducteur {
  id_conducteur: string
  id_salarie: string
  nom: string
  nom_marital: string
  prenom: string
  num_permis: string
  tel: string
  mobile: string
  id_ste: string
}

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

const inputCls =
  'w-full px-2.5 py-1.5 rounded border bg-white text-sm focus:outline-none focus:ring-1'

export default function RechercheUleasePage() {
  useDocumentTitle('Recherche Ulease')
  const [lookups, setLookups] = useState<Lookups | null>(null)
  const [ficheOpen, setFicheOpen] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/adm/recherche-ulease/lookups', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setLookups(d))
  }, [])

  return (
    <div className="p-6 max-w-7xl mx-auto font-normal space-y-6">
      <div className="flex items-center gap-3">
        <Search className="w-6 h-6" style={{ color: COL_BRUN }} />
        <h1 className="text-xl font-bold" style={{ color: COL_BRUN }}>
          Recherche Véhicule / Conducteur
        </h1>
      </div>

      <RechercheVehiculeSection
        lookups={lookups}
        onOpenFiche={(id) => setFicheOpen(id)}
      />

      <RechercheConducteurSection lookups={lookups} />

      <AnimatePresence>
        {ficheOpen && (
          <FicheVehiculeModal
            idVehicule={ficheOpen}
            onClose={() => setFicheOpen(null)}
            onChanged={() => { /* recherche n'a pas besoin d'auto-refresh */ }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

// ============================================================================
// Section Recherche Véhicule
// ============================================================================

function RechercheVehiculeSection({
  lookups,
  onOpenFiche,
}: {
  lookups: Lookups | null
  onOpenFiche: (id: string) => void
}) {
  const [modele, setModele] = useState('')
  const [chevaux, setChevaux] = useState('')
  const [immat, setImmat] = useState('')
  const [idEtat, setIdEtat] = useState('')
  const [idMarque, setIdMarque] = useState('')
  const [rows, setRows] = useState<Vehicule[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState('')

  const handleSearch = useCallback(async () => {
    setLoading(true)
    try {
      const url = new URL(
        '/api/adm/recherche-ulease/vehicules',
        window.location.origin,
      )
      if (modele) url.searchParams.set('modele', modele)
      if (chevaux) url.searchParams.set('chevaux', chevaux)
      if (immat) url.searchParams.set('immat', immat)
      if (idEtat) url.searchParams.set('id_etat', idEtat)
      if (idMarque) url.searchParams.set('id_marque', idMarque)
      const r = await fetch(url.toString(), {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      setRows(Array.isArray(d) ? d : [])
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [modele, chevaux, immat, idEtat, idMarque])

  // Auto-search au chargement initial (= liste complete des vehicules)
  useEffect(() => {
    if (lookups) handleSearch()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lookups])

  return (
    <section
      className="bg-white rounded-lg shadow-sm border p-4"
      style={{ borderColor: COL_BORDER }}
    >
      <h2 className="text-base font-bold flex items-center gap-2 mb-3"
          style={{ color: COL_BRUN }}>
        <CarIcon className="w-4 h-4" />
        Rechercher un véhicule
      </h2>
      <div className="grid grid-cols-[260px_1fr] gap-4">
        {/* Filtres */}
        <div className="space-y-2">
          <input type="text" value={modele}
                 onChange={(e) => setModele(e.target.value)}
                 onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                 placeholder="Modèle de véhicule"
                 className={inputCls} style={{ borderColor: COL_BORDER }} />
          <input type="text" value={immat}
                 onChange={(e) => setImmat(e.target.value.toUpperCase())}
                 onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                 placeholder="Immatriculation"
                 className={inputCls} style={{ borderColor: COL_BORDER }} />
          <input type="number" value={chevaux}
                 onChange={(e) => setChevaux(e.target.value)}
                 onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                 placeholder="NB chevaux fiscaux"
                 className={inputCls} style={{ borderColor: COL_BORDER }} />
          <select value={idEtat}
                  onChange={(e) => setIdEtat(e.target.value)}
                  className={inputCls} style={{ borderColor: COL_BORDER }}>
            <option value="">Tous les états</option>
            {lookups?.etats.map((e) => (
              <option key={e.id_vehicule_etat} value={e.id_vehicule_etat}>
                {e.lib}
              </option>
            ))}
          </select>
          <select value={idMarque}
                  onChange={(e) => setIdMarque(e.target.value)}
                  className={inputCls} style={{ borderColor: COL_BORDER }}>
            <option value="">Toutes les marques</option>
            {lookups?.marques.map((m) => (
              <option key={m.id_vehicule_marque} value={m.id_vehicule_marque}>
                {m.nom}
              </option>
            ))}
          </select>
          <button type="button" onClick={handleSearch} disabled={loading}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded text-white text-sm disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Rechercher
          </button>
          <p className="text-xs italic" style={{ color: COL_BRUN }}>
            {rows.length} véhicule(s) — double-clic = ouvrir
          </p>
        </div>

        {/* Tableau */}
        <div className="border rounded-lg overflow-auto bg-white"
             style={{ borderColor: COL_BORDER, maxHeight: 420 }}>
          <table className="w-full text-xs">
            <thead className="sticky top-0" style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
              <tr>
                <th className="px-2 py-2 text-left">Modèle</th>
                <th className="px-2 py-2 text-right w-12">CV</th>
                <th className="px-2 py-2 text-left">Immat</th>
                <th className="px-2 py-2 text-right w-20">Forfait KM</th>
                <th className="px-2 py-2 text-right w-20">KM achat</th>
                <th className="px-2 py-2 text-right w-20">KM actuel</th>
                <th className="px-2 py-2 text-left">Marque</th>
                <th className="px-2 py-2 text-left">État</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr><td colSpan={8} className="p-6 text-center italic" style={{ color: '#A68D8A' }}>
                  Aucun résultat.
                </td></tr>
              ) : (
                rows.map((r) => {
                  const isSel = selected === r.id_vehicule
                  return (
                    <tr key={r.id_vehicule}
                        onClick={() => setSelected(r.id_vehicule)}
                        onDoubleClick={() => onOpenFiche(r.id_vehicule)}
                        className="cursor-pointer border-b"
                        style={{
                          backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                          color: isSel ? 'white' : COL_BRUN,
                          borderColor: COL_BORDER,
                        }}>
                      <td className="px-2 py-1">{r.modele}</td>
                      <td className="px-2 py-1 text-right">{r.chevaux_fiscaux || ''}</td>
                      <td className="px-2 py-1 font-semibold">{r.immat}</td>
                      <td className="px-2 py-1 text-right">{r.forfait_km || ''}</td>
                      <td className="px-2 py-1 text-right">{r.k_mdepart || ''}</td>
                      <td className="px-2 py-1 text-right">{r.km_actuel || ''}</td>
                      <td className="px-2 py-1 flex items-center gap-1">
                        {r.marque_logo && (
                          <img src={r.marque_logo} alt=""
                               className="w-5 h-5 object-contain" />
                        )}
                        {r.marque_nom}
                      </td>
                      <td className="px-2 py-1">{r.lib_etat}</td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}

// ============================================================================
// Section Recherche Conducteur
// ============================================================================

function RechercheConducteurSection({ lookups }: { lookups: Lookups | null }) {
  const [nom, setNom] = useState('')
  const [prenom, setPrenom] = useState('')
  const [numPermis, setNumPermis] = useState('')
  const [idSte, setIdSte] = useState('')
  const [tel, setTel] = useState('')
  const [mobile, setMobile] = useState('')
  const [rows, setRows] = useState<Conducteur[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState('')

  const handleSearch = async () => {
    setLoading(true)
    try {
      const url = new URL(
        '/api/adm/recherche-ulease/conducteurs',
        window.location.origin,
      )
      if (nom) url.searchParams.set('nom', nom)
      if (prenom) url.searchParams.set('prenom', prenom)
      if (numPermis) url.searchParams.set('num_permis', numPermis)
      if (idSte) url.searchParams.set('id_ste', idSte)
      if (tel) url.searchParams.set('tel', tel)
      if (mobile) url.searchParams.set('mobile', mobile)
      const r = await fetch(url.toString(), {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      setRows(Array.isArray(d) ? d : [])
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch()
  }

  return (
    <section
      className="bg-white rounded-lg shadow-sm border p-4"
      style={{ borderColor: COL_BORDER }}
    >
      <h2 className="text-base font-bold flex items-center gap-2 mb-3"
          style={{ color: COL_BRUN }}>
        <Users className="w-4 h-4" />
        Rechercher un conducteur
      </h2>
      <div className="grid grid-cols-[260px_1fr] gap-4">
        <div className="space-y-2">
          <input type="text" value={nom}
                 onChange={(e) => setNom(e.target.value.toUpperCase())}
                 onKeyDown={onKey}
                 placeholder="Nom (sans accent)"
                 className={inputCls} style={{ borderColor: COL_BORDER }} />
          <input type="text" value={prenom}
                 onChange={(e) => setPrenom(e.target.value)}
                 onKeyDown={onKey}
                 placeholder="Prénom"
                 className={inputCls} style={{ borderColor: COL_BORDER }} />
          <input type="text" value={tel}
                 onChange={(e) => setTel(e.target.value)}
                 onKeyDown={onKey}
                 placeholder="Tél fixe"
                 className={inputCls} style={{ borderColor: COL_BORDER }} />
          <input type="text" value={mobile}
                 onChange={(e) => setMobile(e.target.value)}
                 onKeyDown={onKey}
                 placeholder="Tél mobile"
                 className={inputCls} style={{ borderColor: COL_BORDER }} />
          <select value={idSte}
                  onChange={(e) => setIdSte(e.target.value)}
                  className={inputCls} style={{ borderColor: COL_BORDER }}>
            <option value="">Toutes les sociétés</option>
            {lookups?.societes.map((s) => (
              <option key={s.id_ste} value={s.id_ste}>
                {s.rs_interne || s.raison_sociale}
              </option>
            ))}
          </select>
          <input type="text" value={numPermis}
                 onChange={(e) => setNumPermis(e.target.value)}
                 onKeyDown={onKey}
                 placeholder="Numéro de permis"
                 className={inputCls} style={{ borderColor: COL_BORDER }} />
          <button type="button" onClick={handleSearch} disabled={loading}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded text-white text-sm disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Rechercher
          </button>
          <p className="text-xs italic" style={{ color: COL_BRUN }}>
            {rows.length} conducteur(s)
          </p>
        </div>

        <div className="border rounded-lg overflow-auto bg-white"
             style={{ borderColor: COL_BORDER, maxHeight: 420 }}>
          <table className="w-full text-xs">
            <thead className="sticky top-0" style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
              <tr>
                <th className="px-2 py-2 text-left">Nom</th>
                <th className="px-2 py-2 text-left">Nom marital</th>
                <th className="px-2 py-2 text-left">Prénom</th>
                <th className="px-2 py-2 text-left">N° Permis</th>
                <th className="px-2 py-2 text-left">Tél fixe</th>
                <th className="px-2 py-2 text-left">Mobile</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr><td colSpan={6} className="p-6 text-center italic" style={{ color: '#A68D8A' }}>
                  Aucun résultat.
                </td></tr>
              ) : (
                rows.map((c) => {
                  const isSel = selected === c.id_conducteur
                  return (
                    <tr key={c.id_conducteur}
                        onClick={() => setSelected(c.id_conducteur)}
                        className="cursor-pointer border-b"
                        style={{
                          backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                          color: isSel ? 'white' : COL_BRUN,
                          borderColor: COL_BORDER,
                        }}>
                      <td className="px-2 py-1 font-semibold">{c.nom}</td>
                      <td className="px-2 py-1">{c.nom_marital}</td>
                      <td className="px-2 py-1">{c.prenom}</td>
                      <td className="px-2 py-1">{c.num_permis}</td>
                      <td className="px-2 py-1">{c.tel}</td>
                      <td className="px-2 py-1">{c.mobile}</td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
