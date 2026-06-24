/**
 * Fen_LieuRDV_AjoutModif (WinDev) - Edition d'un lieu RDV.
 * Inclut geocodage API gouv.fr + bouton tester Maps.
 */

import { useEffect, useState } from 'react'
import {
  FileSearch, Globe, Loader2, MapPin, Save, X,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '../ui/dialog'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface LieuRDVEditModalProps {
  apiBase: string
  idLieu: string                  // '0' = nouveau
  onClose: (savedId?: string) => void
}

interface LieuData {
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
}

export default function LieuRDVEditModal({ apiBase, idLieu, onClose }: LieuRDVEditModalProps) {
  const isNew = idLieu === '0'
  const [lib, setLib] = useState('')
  const [adresse1, setAdresse1] = useState('')
  const [adresse2, setAdresse2] = useState('')
  const [idCom, setIdCom] = useState('')
  const [villeLabel, setVilleLabel] = useState('')
  const [cp, setCp] = useState('')
  const [ville, setVille] = useState('')
  const [lat, setLat] = useState<number | null>(null)
  const [lon, setLon] = useState<number | null>(null)
  const [isActif, setIsActif] = useState(true)
  const [loading, setLoading] = useState(!isNew)
  const [saving, setSaving] = useState(false)
  const [geocoding, setGeocoding] = useState(false)

  useEffect(() => {
    if (isNew) return
    fetch(`${apiBase}/recrutement/cv/lieux-rdv/${idLieu}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then((d: LieuData | null) => {
        if (!d) return
        setLib(d.lib_lieu); setAdresse1(d.adresse1); setAdresse2(d.adresse2)
        setIdCom(d.id_communes_france); setCp(d.code_postal); setVille(d.nom_ville)
        setVilleLabel(d.id_communes_france ? `${d.code_postal} ${d.nom_ville}` : '')
        setLat(d.latitude_deg); setLon(d.longitude_deg); setIsActif(d.is_actif)
      })
      .finally(() => setLoading(false))
  }, [apiBase, idLieu, isNew])

  const geocoder = async () => {
    if (!adresse1.trim() || !cp.trim() || !ville.trim()) {
      showToast('Renseigne adresse + ville d\'abord.', 'info')
      return
    }
    setGeocoding(true)
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/lieux-rdv/geocode`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ adresse: adresse1, code_postal: cp, nom_ville: ville }),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      if (d.found) {
        setLat(d.latitude_deg); setLon(d.longitude_deg)
        showToast(`Coords trouvées : ${d.latitude_deg?.toFixed(5)}, ${d.longitude_deg?.toFixed(5)}`, 'success')
      } else {
        showToast('Aucune coord trouvée pour cette adresse.', 'info')
      }
    } catch (e) {
      showToast(`Erreur géocodage : ${(e as Error).message}`, 'error')
    } finally { setGeocoding(false) }
  }

  const testerMaps = () => {
    if (!lat || !lon) return
    window.open(`https://www.google.com/maps/?q=${lat},${lon}`, '_blank', 'noopener')
  }

  const enregistrer = async () => {
    if (!lib.trim()) { showToast('Intitulé obligatoire.', 'info'); return }
    setSaving(true)
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/lieux-rdv`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id_cv_lieu_rdv: idLieu,
          lib_lieu: lib, adresse1, adresse2,
          id_communes_france: idCom,
          latitude_deg: lat, longitude_deg: lon, is_actif: isActif,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      showToast(isNew ? 'Lieu créé.' : 'Lieu modifié.', 'success')
      onClose(d.id_cv_lieu_rdv)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
         onClick={() => onClose()}>
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[95vh] flex flex-col"
           onClick={e => e.stopPropagation()}
           style={{ border: `1px solid ${COL_BORDER}` }}>
        <div className="px-4 py-3 border-b flex items-center gap-2"
             style={{ borderColor: COL_BORDER }}>
          <MapPin className="w-5 h-5" style={{ color: COL_PRIMARY }} />
          <h2 className="text-lg font-bold flex-1" style={{ color: COL_BRUN }}>
            {isNew ? 'Nouveau lieu de RDV' : 'Édition d\'un lieu de RDV'}
          </h2>
          <button type="button" onClick={() => onClose()}
                  className="p-1.5 rounded hover:bg-gray-100">
            <X className="w-5 h-5" style={{ color: COL_BRUN }} />
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center p-8">
            <Loader2 className="w-6 h-6 animate-spin" style={{ color: COL_PRIMARY }} />
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            <Row label="Intitulé *">
              <input type="text" value={lib} onChange={e => setLib(e.target.value)}
                     className="w-full px-2 py-1.5 rounded border text-sm"
                     style={{ borderColor: COL_BORDER }} />
            </Row>
            <Row label="Rue">
              <input type="text" value={adresse1} onChange={e => setAdresse1(e.target.value)}
                     placeholder="ex : 9 rue de la paix"
                     className="w-full px-2 py-1.5 rounded border text-sm"
                     style={{ borderColor: COL_BORDER }} />
              <p className="text-[10px] italic mt-0.5" style={{ color: '#A68D8A' }}>
                Ne mettre que le n° et la rue (pas le code postal ni la ville)
              </p>
            </Row>
            <Row label="Complément">
              <input type="text" value={adresse2} onChange={e => setAdresse2(e.target.value)}
                     placeholder="Immeuble, ZA, ZI, centre commercial, digicode, ..."
                     className="w-full px-2 py-1.5 rounded border text-sm"
                     style={{ borderColor: COL_BORDER }} />
            </Row>
            <Row label="Ville">
              <VillePicker apiBase={apiBase}
                           value={idCom} label={villeLabel}
                           onChange={(id, cpx, vx) => {
                             setIdCom(id); setCp(cpx); setVille(vx)
                             setVilleLabel(id ? `${cpx} ${vx}` : '')
                           }} />
            </Row>
            <label className="ml-32 flex items-center gap-2 text-sm" style={{ color: COL_BRUN }}>
              <input type="checkbox" checked={isActif} onChange={e => setIsActif(e.target.checked)} />
              Visible (actif)
            </label>

            <div className="grid grid-cols-2 gap-3 pt-3 border-t" style={{ borderColor: COL_BORDER }}>
              <Row label="Latitude">
                <input type="number" step="0.0000001" value={lat ?? ''}
                       onChange={e => setLat(e.target.value === '' ? null : Number(e.target.value))}
                       className="w-full px-2 py-1.5 rounded border text-sm"
                       style={{ borderColor: COL_BORDER }} />
              </Row>
              <Row label="Longitude">
                <input type="number" step="0.0000001" value={lon ?? ''}
                       onChange={e => setLon(e.target.value === '' ? null : Number(e.target.value))}
                       className="w-full px-2 py-1.5 rounded border text-sm"
                       style={{ borderColor: COL_BORDER }} />
              </Row>
            </div>
            <div className="flex gap-2 ml-32">
              <button type="button" onClick={geocoder} disabled={geocoding}
                      className="flex items-center gap-2 px-3 py-1.5 rounded border text-xs disabled:opacity-50"
                      style={{ borderColor: COL_BORDER, color: COL_PRIMARY }}>
                {geocoding ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                           : <Globe className="w-3.5 h-3.5" />}
                Coord depuis adresse (API gouv.fr)
              </button>
              <button type="button" onClick={testerMaps} disabled={!lat || !lon}
                      className="flex items-center gap-2 px-3 py-1.5 rounded border text-xs disabled:opacity-50"
                      style={{ borderColor: COL_BORDER, color: COL_PRIMARY }}>
                <MapPin className="w-3.5 h-3.5" /> Tester sur Maps
              </button>
            </div>
          </div>
        )}

        <div className="px-4 py-3 border-t flex items-center justify-end gap-2"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          <button type="button" onClick={() => onClose()}
                  className="px-3 py-1.5 rounded border text-sm"
                  style={{ borderColor: COL_BORDER, color: COL_BRUN, backgroundColor: 'white' }}>
            Annuler
          </button>
          <button type="button" onClick={enregistrer} disabled={saving || loading}
                  className="flex items-center gap-2 px-4 py-2 rounded text-white text-sm disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[120px_1fr] items-center gap-3 min-h-9">
      <label className="text-xs text-right" style={{ color: COL_BRUN }}>{label}</label>
      <div className="min-w-0">{children}</div>
    </div>
  )
}

function VillePicker({ apiBase, value, label, onChange }: {
  apiBase: string; value: string; label: string
  onChange: (id: string, cp: string, ville: string) => void
}) {
  const [query, setQuery] = useState('')
  const [props, setProps] = useState<Array<{
    id_communes_france: string; code_postal: string; nom_ville: string
  }>>([])
  const [searching, setSearching] = useState(false)

  const search = async () => {
    if (query.length < 2) return
    setSearching(true)
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/communes?q=${encodeURIComponent(query)}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (r.ok) setProps(await r.json())
    } finally { setSearching(false) }
  }

  if (value && value !== '0') {
    return (
      <div className="flex items-center gap-1">
        <div className="flex-1 px-2 py-1.5 rounded border bg-gray-50 text-sm"
             style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
          {label}
        </div>
        <button type="button" onClick={() => onChange('', '', '')}
                className="p-1 text-red-600 hover:text-red-800">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <div className="flex gap-1">
        <input type="text" value={query}
               onChange={e => setQuery(e.target.value.toUpperCase())}
               onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); search() } }}
               placeholder="CP ou ville"
               className="flex-1 px-2 py-1.5 rounded border text-sm"
               style={{ borderColor: COL_BORDER }} />
        <button type="button" onClick={search}
                className="px-2 rounded border"
                style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
          {searching ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                     : <FileSearch className="w-3.5 h-3.5" />}
        </button>
      </div>
      {props.length > 0 && (
        <div className="border rounded max-h-40 overflow-y-auto"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          {props.map(p => (
            <button key={p.id_communes_france} type="button"
                    onClick={() => {
                      onChange(p.id_communes_france, p.code_postal, p.nom_ville)
                      setProps([]); setQuery('')
                    }}
                    className="block w-full text-left px-2 py-1 text-xs hover:bg-white"
                    style={{ color: COL_BRUN }}>
              {p.code_postal} {p.nom_ville}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
