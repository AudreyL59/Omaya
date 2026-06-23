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
  Gauge,
  Loader2,
  Plus,
  Search,
  Settings,
  Sigma,
} from 'lucide-react'

import { getToken } from '@/api'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { showToast } from '@shared/ui/dialog'
import FicheVehiculeModal from '@/components/FicheVehiculeModal'
import GestionCarteCarbModal from '@/components/GestionCarteCarbModal'
import ImportFournisseurModal from '@/components/ImportFournisseurModal'
import CalculCartModal from '@/components/CalculCartModal'
import RechercheRelevModal from '@/components/RechercheRelevModal'
import AnalyseCarbModal from '@/components/AnalyseCarbModal'
import { AnimatePresence } from 'framer-motion'

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
  useDocumentTitle('Parc Auto')
  const [rows, setRows] = useState<Vehicule[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [ficheOpen, setFicheOpen] = useState<string | null>(null)
  const [carteCarbOpen, setCarteCarbOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [calculOpen, setCalculOpen] = useState(false)
  const [rechRelevOpen, setRechRelevOpen] = useState(false)
  const [alerteOpen, setAlerteOpen] = useState(false)

  const reload = () => {
    setLoading(true)
    fetch('/api/adm/parc-auto/vehicules', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d: Vehicule[]) => setRows(Array.isArray(d) ? d : []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    reload()
  }, [])

  const filtered = useMemo(() => {
    const q = search.trim().toUpperCase().replace(/[\s-]/g, '')
    if (!q) return rows
    return rows.filter((v) => v.immat.toUpperCase().replace(/[\s-]/g, '').includes(q))
  }, [rows, search])

  // Tri par immatriculation (cf. WinDev qui melange visuellement sans
  // ruptures par societe sur l'ecran TDB).
  const sortedByImmat = useMemo(
    () => [...filtered].sort((a, b) => a.immat.localeCompare(b.immat)),
    [filtered],
  )

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
          onClick={() => setCarteCarbOpen(true)}
        />
        <ToolbarBtn
          icon={<Database className="w-4 h-4" />}
          label="Importation Base Fournisseur"
          onClick={() => setImportOpen(true)}
        />
        <ToolbarBtn
          icon={<Sigma className="w-4 h-4" />}
          label="Calcul montant carte carburant"
          onClick={() => setCalculOpen(true)}
        />
        <ToolbarBtn
          icon={<Search className="w-4 h-4" />}
          label="Recherche relève"
          onClick={() => setRechRelevOpen(true)}
        />
        <ToolbarBtn
          icon={<AlertCircle className="w-4 h-4" />}
          label="Détecter Alerte Carb"
          onClick={() => setAlerteOpen(true)}
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
      ) : sortedByImmat.length === 0 && search ? (
        <div className="p-10 text-center text-sm italic text-[#A68D8A]">
          Aucun véhicule pour « {search} ».
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {!search && <AddCard />}
          {sortedByImmat.map((v) => (
            <VehiculeCard
              key={v.id_vehicule}
              v={v}
              onOpen={() => setFicheOpen(v.id_vehicule)}
            />
          ))}
        </div>
      )}

      <AnimatePresence>
        {ficheOpen && (
          <FicheVehiculeModal
            idVehicule={ficheOpen}
            onClose={() => setFicheOpen(null)}
            onChanged={reload}
          />
        )}
      </AnimatePresence>

      <GestionCarteCarbModal
        open={carteCarbOpen}
        onClose={() => setCarteCarbOpen(false)}
      />
      <ImportFournisseurModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
      />
      <CalculCartModal
        open={calculOpen}
        onClose={() => setCalculOpen(false)}
      />
      <RechercheRelevModal
        open={rechRelevOpen}
        onClose={() => setRechRelevOpen(false)}
      />
      <AnalyseCarbModal
        open={alerteOpen}
        onClose={() => setAlerteOpen(false)}
      />
    </div>
  )
}

function AddCard() {
  return (
    <button
      type="button"
      onClick={() => showToast('Ajout véhicule : à venir.', 'info')}
      className="flex items-center justify-center gap-3 rounded-lg bg-white hover:bg-[#FAF6F2] transition-colors"
      style={{
        border: `1px solid ${COL_BORDER}`,
        color: COL_BRUN,
        minHeight: '110px',
      }}
    >
      <div className="relative">
        <Car className="w-7 h-7" style={{ color: COL_BRUN }} />
        <Plus
          className="absolute -top-1 -right-2 w-3.5 h-3.5"
          style={{ color: COL_BRUN }}
        />
      </div>
      <span className="text-base font-medium">Ajouter un véhicule</span>
    </button>
  )
}

function VehiculeCard({ v, onOpen }: { v: Vehicule; onOpen: () => void }) {
  return (
    <div
      onClick={onOpen}
      className="relative rounded-lg bg-white cursor-pointer hover:shadow-md transition-shadow overflow-hidden"
      style={{
        border: `1px solid ${COL_BORDER}`,
        minHeight: '110px',
      }}
    >
      {/* Logo societe en filigrane (50% largeur, colore en fond de page
          via mask-image + backgroundColor #FAF6F2). */}
      {v.ste_logo && (
        <div
          aria-hidden
          className="absolute top-0 left-0 pointer-events-none"
          style={{
            width: '50%',
            height: '100%',
            backgroundColor: '#FAF6F2',
            WebkitMaskImage: `url("${v.ste_logo}")`,
            maskImage: `url("${v.ste_logo}")`,
            WebkitMaskRepeat: 'no-repeat',
            maskRepeat: 'no-repeat',
            WebkitMaskPosition: 'center',
            maskPosition: 'center',
            WebkitMaskSize: 'contain',
            maskSize: 'contain',
          }}
        />
      )}

      {/* Layout : 2 col - logo marque gauche (grand, en teal) + infos centrees */}
      <div className="relative grid grid-cols-[110px_1fr] h-full">
        <div className="flex items-center justify-center p-2">
          {v.marque_logo ? (
            // CSS mask-image : applique le logo PNG transparent comme masque
            // et le colore en teal (cf. WinDev dIncrusteCouleur RVB(24,76,82))
            <div
              aria-label={v.marque_nom}
              style={{
                width: '90px',
                height: '80px',
                backgroundColor: '#17494E',
                WebkitMaskImage: `url("${v.marque_logo}")`,
                maskImage: `url("${v.marque_logo}")`,
                WebkitMaskRepeat: 'no-repeat',
                maskRepeat: 'no-repeat',
                WebkitMaskPosition: 'center',
                maskPosition: 'center',
                WebkitMaskSize: 'contain',
                maskSize: 'contain',
              }}
            />
          ) : (
            <Car className="w-14 h-14" style={{ color: COL_BORDER }} />
          )}
        </div>

        <div className="flex flex-col justify-center items-center text-center py-3 pr-4">
          <div
            className="text-lg font-bold tracking-wide"
            style={{ color: COL_BRUN }}
          >
            {v.immat || '—'}
          </div>
          <div className="text-xs mt-1" style={{ color: COL_BRUN }}>
            {v.modele}
          </div>
          <div
            className="flex items-center justify-center gap-1.5 mt-2 text-xs font-semibold"
            style={{ color: COL_BRUN }}
          >
            {v.etat_logo ? (
              <img
                src={v.etat_logo}
                alt=""
                className="w-4 h-4 object-contain"
              />
            ) : (
              <span
                className="inline-flex items-center justify-center w-4 h-4 rounded-full text-white text-[9px]"
                style={{ backgroundColor: '#16a34a' }}
              >
                ✓
              </span>
            )}
            <span>{v.lib_etat || 'INCONNU'}</span>
          </div>
        </div>
      </div>

      {/* Badge alerte rouge - haut droite */}
      {v.has_alerte && (
        <div
          className="absolute top-2 right-2 w-6 h-6 rounded-full flex items-center justify-center text-white text-sm font-bold cursor-help shadow"
          style={{ backgroundColor: '#B91C1C' }}
          title={v.alertes.join('\n')}
        >
          !
        </div>
      )}

      {/* Bouton bas-droite : ajout d'une releve kilometrique */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation()
          showToast(
            `Ajout relevé kilométrique ${v.immat} : à venir.`,
            'info',
          )
        }}
        className="absolute bottom-2 right-2 w-7 h-7 rounded-full flex items-center justify-center hover:bg-[#17494E]/10 transition-colors"
        title="Ajouter une relève kilométrique"
        style={{ color: '#17494E' }}
      >
        <Gauge className="w-5 h-5" />
      </button>
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
