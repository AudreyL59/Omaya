/**
 * Fen_LieuRDV (WinDev) - Gestion des lieux de RDV (shared ADM + Vendeur).
 *
 * Liste avec actions :
 *  - Nouveau Lieu / Éditer / Dupliquer
 *  - Afficher sur Maps
 *  - Créer une fiche annuaire (V_later, juste flag affichable)
 *  - Supprimer
 *
 * Sous-modal Fen_LieuRDV_AjoutModif pour ajout/edit.
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Building2, Copy, Edit, MapPin, Plus, RotateCcw, Trash2,
} from 'lucide-react'
import { getToken } from '@/api'
import { showConfirm, showToast } from '../ui/dialog'
import LieuRDVEditModal from './LieuRDVEditModal'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'

interface LieuRDV {
  id_cv_lieu_rdv: string
  lib_lieu: string
  adresse1: string
  adresse2: string
  id_communes_france: string
  code_postal: string
  nom_ville: string
  latitude_deg: number | null
  longitude_deg: number | null
  is_actif: boolean
  is_in_annuaire: boolean
}

interface LieuxRDVPageProps {
  apiBase: string
}

export default function LieuxRDVPage({ apiBase }: LieuxRDVPageProps) {
  const [lieux, setLieux] = useState<LieuRDV[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState('')
  const [filtreActif, setFiltreActif] = useState<'tous' | 'actifs' | 'inactifs'>('actifs')
  const [editId, setEditId] = useState<string | null>(null)  // null = fermé, '0' = nouveau, 'X' = edit

  const reload = useCallback(() => {
    setLoading(true)
    const q = filtreActif === 'tous' ? '' : `?is_actif=${filtreActif === 'actifs'}`
    fetch(`${apiBase}/recrutement/cv/lieux-rdv${q}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then(setLieux)
      .finally(() => setLoading(false))
  }, [apiBase, filtreActif])

  useEffect(() => { reload() }, [reload])

  const selected = lieux.find(l => l.id_cv_lieu_rdv === selectedId)

  const onAjouter = () => setEditId('0')
  const onEditer = () => { if (selectedId) setEditId(selectedId) }

  const onDupliquer = async () => {
    if (!selectedId) return
    try {
      const r = await fetch(
        `${apiBase}/recrutement/cv/lieux-rdv/${selectedId}/duplicate`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      showToast('Lieu dupliqué.', 'success')
      reload()
      if (d.id_cv_lieu_rdv) setSelectedId(d.id_cv_lieu_rdv)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  const onMaps = () => {
    if (!selected?.latitude_deg || !selected?.longitude_deg) return
    window.open(
      `https://www.google.com/maps/?q=${selected.latitude_deg},${selected.longitude_deg}`,
      '_blank', 'noopener',
    )
  }

  const onSupprimer = async () => {
    if (!selectedId) return
    const ok = await showConfirm({
      title: 'Supprimer le lieu ?',
      message: 'Vous êtes sur le point de supprimer ce lieu de RDV. Confirmer ?',
      confirmLabel: 'Supprimer',
    })
    if (!ok) return
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/lieux-rdv/${selectedId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast('Lieu supprimé.', 'success')
      setSelectedId('')
      reload()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  return (
    <div className="p-4 space-y-3 max-w-7xl mx-auto">
      <div className="flex items-center gap-2">
        <Building2 className="w-5 h-5" style={{ color: COL_PRIMARY }} />
        <h1 className="text-xl font-bold" style={{ color: COL_BRUN }}>
          Lieux de RDV
          <span className="ml-2 text-sm font-normal" style={{ color: COL_PRIMARY }}>
            ({lieux.length})
          </span>
        </h1>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <Btn onClick={onAjouter} icon={Plus} primary>Nouveau Lieu</Btn>
        <Btn onClick={onEditer} icon={Edit} disabled={!selectedId}>Éditer</Btn>
        <Btn onClick={onDupliquer} icon={Copy} disabled={!selectedId}>Dupliquer</Btn>
        <Btn onClick={onMaps} icon={MapPin}
             disabled={!selected?.latitude_deg || !selected?.longitude_deg}>
          Afficher sur Maps
        </Btn>
        <div className="flex-1" />
        <select value={filtreActif}
                onChange={e => setFiltreActif(e.target.value as 'tous' | 'actifs' | 'inactifs')}
                className="px-2 py-1.5 rounded border text-sm"
                style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
          <option value="actifs">Actifs uniquement</option>
          <option value="inactifs">Inactifs uniquement</option>
          <option value="tous">Tous</option>
        </select>
        <Btn onClick={reload} icon={RotateCcw} />
        <Btn onClick={onSupprimer} icon={Trash2} variant="danger" disabled={!selectedId}>
          Supprimer
        </Btn>
      </div>

      {/* Tableau */}
      <div className="border rounded-lg overflow-auto bg-white"
           style={{ borderColor: COL_BORDER, maxHeight: 'calc(100vh - 220px)' }}>
        <table className="w-full text-xs">
          <thead className="sticky top-0 z-10"
                 style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
            <tr>
              <th className="px-2 py-2 text-left whitespace-nowrap">Intitulé</th>
              <th className="px-2 py-2 text-left">Adresse</th>
              <th className="px-2 py-2 text-left whitespace-nowrap">CP</th>
              <th className="px-2 py-2 text-left whitespace-nowrap">Ville</th>
              <th className="px-2 py-2 text-left">Compl. Adresse</th>
              <th className="px-2 py-2 text-center w-16">Visible</th>
              <th className="px-2 py-2 text-center w-20">Annuaire</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="p-6 text-center" style={{ color: '#A68D8A' }}>
                Chargement...
              </td></tr>
            ) : lieux.length === 0 ? (
              <tr><td colSpan={7} className="p-6 text-center italic"
                      style={{ color: '#A68D8A' }}>
                Aucun lieu.
              </td></tr>
            ) : (
              lieux.map(l => {
                const isSel = selectedId === l.id_cv_lieu_rdv
                return (
                  <tr key={l.id_cv_lieu_rdv}
                      onClick={() => setSelectedId(l.id_cv_lieu_rdv)}
                      onDoubleClick={() => setEditId(l.id_cv_lieu_rdv)}
                      className="cursor-pointer border-b"
                      style={{
                        backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                        color: isSel ? 'white' : COL_BRUN,
                        borderColor: COL_BORDER,
                      }}>
                    <td className="px-2 py-1.5 font-semibold">{l.lib_lieu}</td>
                    <td className="px-2 py-1.5">{l.adresse1}</td>
                    <td className="px-2 py-1.5 whitespace-nowrap">{l.code_postal}</td>
                    <td className="px-2 py-1.5">{l.nom_ville}</td>
                    <td className="px-2 py-1.5">{l.adresse2}</td>
                    <td className="px-2 py-1.5 text-center">{l.is_actif ? '✓' : ''}</td>
                    <td className="px-2 py-1.5 text-center">{l.is_in_annuaire ? '✓' : ''}</td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Modal ajout/edit */}
      {editId !== null && (
        <LieuRDVEditModal apiBase={apiBase} idLieu={editId}
                          onClose={(savedId) => {
                            setEditId(null)
                            reload()
                            if (savedId) setSelectedId(savedId)
                          }} />
      )}
    </div>
  )
}

function Btn({ onClick, icon: Icon, children, primary, disabled, variant }: {
  onClick: () => void
  icon: React.ComponentType<{ className?: string }>
  children?: React.ReactNode
  primary?: boolean
  disabled?: boolean
  variant?: 'danger'
}) {
  const bg = variant === 'danger' ? '#B91C1C' : primary ? COL_PRIMARY : 'white'
  const fg = primary || variant === 'danger' ? 'white' : COL_BRUN
  return (
    <button type="button" onClick={onClick} disabled={disabled}
            className="flex items-center gap-1 px-3 py-1.5 rounded border text-sm disabled:opacity-40"
            style={{ borderColor: COL_BORDER, backgroundColor: bg, color: fg }}>
      <Icon className="w-3.5 h-3.5" />
      {children}
    </button>
  )
}
