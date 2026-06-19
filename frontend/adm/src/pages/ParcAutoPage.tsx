/**
 * Fen_TdbUlease (WinDev) - Ulease -> Suivi du Parc Auto.
 *
 * Grille de cartes (3 par ligne) + carte 'Ajouter un véhicule' en tête.
 * Chaque carte : logo société (fond) + logo marque + immat + modèle +
 * état (en circulation, accident, etc.) + alerte rouge si CT/Révision/
 * carte grise problème.
 *
 * Toolbar : Gestion cartes carburant / Importation Base Fournisseur /
 * Calcul montant carte carburant / Recherche relève / Détecter Alerte Carb.
 * (Boutons en placeholder pour V2.)
 */

import { useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  Car,
  CarFront,
  CreditCard,
  Database,
  Loader2,
  Plus,
  Search,
  Settings,
  Sigma,
} from 'lucide-react'

import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'

interface Vehicule {
  id_vehicule: string
  immat: string
  modele: string
  marque_logo: string
  marque_nom: string
  etat_logo: string
  lib_etat: string
  id_vehicule_etat: number
  raison_sociale: string
  ste_logo: string
  alertes: string[]
  has_alerte: boolean
}

const COL_BRUN = '#4E1D17'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#FAF6F2'

export default function ParcAutoPage() {
  const [rows, setRows] = useState<Vehicule[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    setLoading(true)
    fetch('/api/adm/parc-auto/vehicules', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d: Vehicule[]) => setRows(Array.isArray(d) ? d : []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    const q = search.trim().toUpperCase().replace(/[\s-]/g, '')
    if (!q) return rows
    return rows.filter((v) => v.immat.toUpperCase().replace(/[\s-]/g, '').includes(q))
  }, [rows, search])

  // Regroupement par raison sociale pour les ruptures (cf. ORDER BY WinDev)
  const grouped = useMemo(() => {
    const map = new Map<string, Vehicule[]>()
    for (const v of filtered) {
      const k = v.raison_sociale || 'Sans société'
      const list = map.get(k) || []
      list.push(v)
      map.set(k, list)
    }
    return Array.from(map.entries())
  }, [filtered])

  return (
    <div className="p-6 max-w-7xl mx-auto font-normal">
      <div className="flex items-center gap-3 mb-5">
        <CarFront className="w-6 h-6" style={{ color: COL_BRUN }} />
        <h1 className="text-xl font-bold flex-1" style={{ color: COL_BRUN }}>
          TDB Ulease — Suivi du Parc Auto
        </h1>
      </div>

      {/* Toolbar */}
      <div
        className="flex flex-wrap items-center gap-2 p-3 mb-4 bg-white rounded-lg border"
        style={{ borderColor: COL_BORDER }}
      >
        <ToolbarBtn
          icon={<Settings className="w-4 h-4" />}
          label=""
          onClick={() => showToast('Réglages : à venir.', 'info')}
        />
        <ToolbarBtn
          icon={<CreditCard className="w-4 h-4" />}
          label="Gestion des cartes carburant"
          onClick={() =>
            showToast('Gestion cartes carburant : à venir.', 'info')
          }
        />
        <ToolbarBtn
          icon={<Database className="w-4 h-4" />}
          label="Importation Base Fournisseur"
          onClick={() => showToast('Importation : à venir.', 'info')}
        />
        <ToolbarBtn
          icon={<Sigma className="w-4 h-4" />}
          label="Calcul montant carte carburant"
          onClick={() => showToast('Calcul carburant : à venir.', 'info')}
        />
        <ToolbarBtn
          icon={<Search className="w-4 h-4" />}
          label="Recherche relève"
          onClick={() => showToast('Recherche relève : à venir.', 'info')}
        />
        <ToolbarBtn
          icon={<AlertCircle className="w-4 h-4" />}
          label="Détecter Alerte Carb"
          onClick={() => showToast('Détection alerte : à venir.', 'info')}
        />
        <span className="flex-1" />
        <div className="relative">
          <input
            type="text"
            placeholder="Chercher une immatriculation"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-3 pr-9 py-2 border rounded-md text-sm w-64"
            style={{ borderColor: COL_BORDER, color: COL_BRUN }}
          />
          <Search
            className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none"
            style={{ color: COL_BRUN }}
          />
        </div>
      </div>

      {loading ? (
        <div className="p-10 flex justify-center">
          <Loader2 className="w-5 h-5 animate-spin text-[#A68D8A]" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Carte 'Ajouter un véhicule' en tête */}
          {!search && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <AddCard />
              {/* Pas de groupe initial = on remplit la ligne avec les
                  premières cartes du premier groupe */}
            </div>
          )}

          {grouped.map(([ste, vehs]) => (
            <div key={ste}>
              <h2
                className="text-xs font-bold uppercase tracking-wide mb-2"
                style={{ color: COL_BRUN }}
              >
                {ste} ({vehs.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {vehs.map((v) => (
                  <VehiculeCard key={v.id_vehicule} v={v} />
                ))}
              </div>
            </div>
          ))}

          {filtered.length === 0 && (
            <div className="p-10 text-center text-sm italic text-[#A68D8A]">
              Aucun véhicule {search ? 'pour cette recherche' : ''}.
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function AddCard() {
  return (
    <button
      type="button"
      onClick={() => showToast('Ajout véhicule : à venir.', 'info')}
      className="flex items-center justify-center gap-2 p-6 rounded-lg border-2 border-dashed hover:bg-white transition-colors"
      style={{ borderColor: COL_BORDER, color: COL_BRUN }}
    >
      <Plus className="w-5 h-5" />
      <Car className="w-5 h-5" />
      <span className="text-sm font-medium">Ajouter un véhicule</span>
    </button>
  )
}

function VehiculeCard({ v }: { v: Vehicule }) {
  return (
    <div
      onClick={() =>
        showToast(`Fiche véhicule ${v.immat} : à venir.`, 'info')
      }
      className="relative p-4 rounded-lg bg-white border cursor-pointer hover:shadow-md transition-shadow overflow-hidden"
      style={{ borderColor: COL_BORDER, minHeight: '128px' }}
    >
      {/* Logo société en fond (faible opacité) */}
      {v.ste_logo && (
        <img
          src={v.ste_logo}
          alt=""
          className="absolute inset-0 w-full h-full object-contain opacity-10 pointer-events-none"
        />
      )}

      <div className="relative flex items-start gap-3">
        {/* Logo marque */}
        {v.marque_logo ? (
          <img
            src={v.marque_logo}
            alt={v.marque_nom}
            className="w-12 h-12 object-contain shrink-0"
          />
        ) : (
          <div className="w-12 h-12 shrink-0 flex items-center justify-center">
            <Car className="w-8 h-8" style={{ color: COL_BORDER }} />
          </div>
        )}

        <div className="flex-1 min-w-0 text-center">
          <div className="text-base font-bold" style={{ color: COL_BRUN }}>
            {v.immat || '—'}
          </div>
          <div className="text-xs mt-0.5" style={{ color: COL_BRUN }}>
            {v.modele}
          </div>
          <div className="flex items-center justify-center gap-1.5 mt-2 text-xs">
            <span
              className="inline-flex items-center justify-center w-4 h-4 rounded-full"
              style={{ backgroundColor: '#16a34a', color: 'white' }}
            >
              ✓
            </span>
            <span style={{ color: COL_BRUN }}>{v.lib_etat || 'INCONNU'}</span>
          </div>
        </div>

        {/* Badge alerte */}
        {v.has_alerte && (
          <div
            className="absolute top-0 right-0 w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold cursor-help"
            style={{ backgroundColor: '#B91C1C' }}
            title={v.alertes.join('\n')}
          >
            !
          </div>
        )}
      </div>
    </div>
  )
}

function ToolbarBtn({
  icon,
  label,
  onClick,
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm hover:bg-[#EFE9E7]"
      style={{ color: COL_BRUN, backgroundColor: COL_BG_SOFT }}
    >
      {icon}
      {label && <span>{label}</span>}
    </button>
  )
}
