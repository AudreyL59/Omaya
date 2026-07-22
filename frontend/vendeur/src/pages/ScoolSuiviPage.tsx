// Page Suivi Scool (Vendeur) : formations dont je suis formateur ou
// destPromo, avec detail des stagiaires + calcul prod SFR sur la periode
// de formation.

import { useCallback, useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { getToken } from '@/api'

interface Formation {
  IDformation: string
  Intitule: string
  DateDebut: string
  DateFin: string
  NbHeureSalle: number
  NbHeureTerrain: number
  VilleFormation: string
  TypeProduit: string
  Categorie: string
  HeureJourSalle: number
  HeureJourTerrain: number
  FormationActive: boolean
}

interface Stagiaire {
  IDStagiaire: string
  Nom: string
  Prenom: string
  NomPrenom: string
  DateDebut: string
  DateFin: string
  EnActivite: boolean
  IDTypeSortie: number
  LibSortie: string
  Livrable: boolean
  NbFibreBrut: number
  NbFibreHR: number
  NbCQTBrut: number
  NbCQTHR: number
  NbMigBrut: number
  NbMigHR: number
  NbMobBrut: number
  NbMobHR: number
}

const API = '/api/vendeur/scool'

const fmtDateFR = (raw: string): string => {
  if (!raw) return ''
  const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})/)
  return m ? `${m[3]}/${m[2]}/${m[1]}` : raw
}

const todayISO = () => new Date().toISOString().slice(0, 10)

export default function ScoolSuiviPage() {
  const [formations, setFormations] = useState<Formation[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [stagiaires, setStagiaires] = useState<Stagiaire[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingStag, setLoadingStag] = useState(false)

  // Filtres
  const [dateMin, setDateMin] = useState(todayISO())
  const [activesOnly, setActivesOnly] = useState(true)
  const [search, setSearch] = useState('')

  const chargerFormations = useCallback(async () => {
    setLoading(true)
    const qs = new URLSearchParams({
      date_min: dateMin, actives: String(activesOnly), search,
    })
    try {
      const r = await fetch(`${API}/formations?${qs}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      const data = r.ok ? await r.json() : []
      setFormations(Array.isArray(data) ? data : [])
    } catch {
      setFormations([])
    }
    setLoading(false)
  }, [dateMin, activesOnly, search])

  useEffect(() => {
    const iv = setTimeout(() => { void chargerFormations() }, 250)
    return () => clearTimeout(iv)
  }, [chargerFormations])

  const ouvrir = async (f: Formation) => {
    setSelectedId(f.IDformation)
    setLoadingStag(true)
    try {
      const r = await fetch(`${API}/formations/${f.IDformation}/stagiaires`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      const data = r.ok ? await r.json() : []
      setStagiaires(Array.isArray(data) ? data : [])
    } catch {
      setStagiaires([])
    }
    setLoadingStag(false)
  }

  return (
    <div className="flex flex-col h-full min-h-0 p-3 gap-3">
      {/* Filtres */}
      <div className="bg-white border border-c-line-soft rounded p-3 flex flex-wrap items-center gap-3 shrink-0">
        <label className="flex items-center gap-2 text-sm">
          <span className="text-c-ink-soft">Afficher depuis le</span>
          <input type="date" value={dateMin}
            onChange={e => setDateMin(e.target.value)}
            className="border border-c-line rounded px-2 py-1.5 text-sm bg-white" />
        </label>
        <label className="flex items-center gap-1.5 text-sm cursor-pointer">
          <input type="checkbox" checked={activesOnly}
            onChange={e => setActivesOnly(e.target.checked)}
            className="accent-c-brand" />
          Uniquement formations actives
        </label>
        <div className="relative flex-1 min-w-[220px] max-w-[400px]">
          <Search className="w-4 h-4 absolute left-2 top-2.5 text-c-ink-soft" />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Rechercher intitulé ou ville…"
            className="w-full pl-8 pr-2 py-1.5 text-sm border border-c-line rounded bg-white" />
        </div>
      </div>

      {/* Liste formations */}
      <section className="bg-white border border-c-line-soft rounded flex flex-col min-h-0 flex-1">
        <header className="px-3 py-2 border-b border-c-line-soft text-sm font-semibold">
          Formations ({formations.length})
        </header>
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-c-surface-soft sticky top-0 text-xs text-c-ink-soft uppercase">
              <tr>
                <th className="text-left px-3 py-2">Intitulé</th>
                <th className="text-left px-3 py-2">Ville</th>
                <th className="text-left px-3 py-2">Type</th>
                <th className="text-left px-3 py-2">Du</th>
                <th className="text-left px-3 py-2">Au</th>
                <th className="text-right px-3 py-2">H. Salle</th>
                <th className="text-right px-3 py-2">H. Terrain</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={7} className="text-center py-4 text-c-ink-soft">Chargement…</td></tr>
              )}
              {!loading && formations.length === 0 && (
                <tr><td colSpan={7} className="text-center py-4 italic text-c-ink-faint">
                  Aucune formation
                </td></tr>
              )}
              {formations.map(f => (
                <tr key={f.IDformation}
                  onClick={() => ouvrir(f)}
                  className={`cursor-pointer border-t border-c-line-soft hover:bg-c-brand-soft ${
                    selectedId === f.IDformation ? 'bg-c-brand-soft' : ''}`}>
                  <td className="px-3 py-1.5">{f.Intitule}</td>
                  <td className="px-3 py-1.5">{f.VilleFormation}</td>
                  <td className="px-3 py-1.5">
                    {f.TypeProduit}{f.Categorie && ` · ${f.Categorie}`}
                  </td>
                  <td className="px-3 py-1.5">{fmtDateFR(f.DateDebut)}</td>
                  <td className="px-3 py-1.5">{fmtDateFR(f.DateFin)}</td>
                  <td className="px-3 py-1.5 text-right tabular-nums">
                    {f.NbHeureSalle ? f.NbHeureSalle.toFixed(1) : ''}
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums">
                    {f.NbHeureTerrain ? f.NbHeureTerrain.toFixed(1) : ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Detail stagiaires */}
      {selectedId && (
        <section className="bg-white border border-c-line-soft rounded flex flex-col min-h-0 flex-1">
          <header className="px-3 py-2 border-b border-c-line-soft text-sm font-semibold">
            Détails stagiaires ({stagiaires.length})
          </header>
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-c-surface-soft sticky top-0 text-xs text-c-ink-soft uppercase">
                <tr>
                  <th className="text-left px-3 py-2">Nom</th>
                  <th className="text-left px-3 py-2">Prénom</th>
                  <th className="text-left px-3 py-2">Du</th>
                  <th className="text-left px-3 py-2">Au</th>
                  <th className="text-center px-3 py-2">Actif</th>
                  <th className="text-left px-3 py-2">Type sortie</th>
                  <th className="text-center px-3 py-2">Livrable</th>
                  <th className="text-right px-3 py-2">Fibre brut</th>
                  <th className="text-right px-3 py-2">Fibre HR</th>
                  <th className="text-right px-3 py-2">CQT brut</th>
                  <th className="text-right px-3 py-2">CQT HR</th>
                  <th className="text-right px-3 py-2">Mig brut</th>
                  <th className="text-right px-3 py-2">Mig HR</th>
                  <th className="text-right px-3 py-2">Mob brut</th>
                  <th className="text-right px-3 py-2">Mob HR</th>
                </tr>
              </thead>
              <tbody>
                {loadingStag && (
                  <tr><td colSpan={15} className="text-center py-4 text-c-ink-soft">Chargement…</td></tr>
                )}
                {!loadingStag && stagiaires.length === 0 && (
                  <tr><td colSpan={15} className="text-center py-4 italic text-c-ink-faint">
                    Aucun stagiaire
                  </td></tr>
                )}
                {stagiaires.map(s => (
                  <tr key={s.IDStagiaire}
                    className="border-t border-c-line-soft hover:bg-c-surface-soft">
                    <td className="px-3 py-1.5 font-semibold">{s.Nom}</td>
                    <td className="px-3 py-1.5">{s.Prenom}</td>
                    <td className="px-3 py-1.5">{fmtDateFR(s.DateDebut)}</td>
                    <td className="px-3 py-1.5">{fmtDateFR(s.DateFin)}</td>
                    <td className="px-3 py-1.5 text-center">
                      {s.EnActivite ? '✓' : '—'}
                    </td>
                    <td className="px-3 py-1.5">{s.LibSortie}</td>
                    <td className="px-3 py-1.5 text-center">
                      {s.Livrable ? '✓' : '—'}
                    </td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{s.NbFibreBrut || ''}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{s.NbFibreHR || ''}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{s.NbCQTBrut || ''}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{s.NbCQTHR || ''}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{s.NbMigBrut || ''}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{s.NbMigHR || ''}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{s.NbMobBrut || ''}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{s.NbMobHR || ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}
