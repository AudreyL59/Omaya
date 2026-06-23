/**
 * Fen_RechercheCV (WinDev) - Recherche CV partagee.
 *
 * Utilisee par 3 intranets : ADM, Vendeur, Call RH (cf. router factory
 * get_recherche_cv_router cote backend).
 *
 * Commit 2 (current) :
 *  - 3 modes actifs : CP simple, Tel, Nom
 *  - Filtres communs : source, profil ENI/FIBRE/Les2/Autre, age,
 *    periode, societe, statut courant
 *  - Tableau resultats avec coopteur/annonceur resolus
 *
 * Commit 3 (a venir) : presence en temps reel (op_traite + couleurs
 *   jaune/orange + long polling).
 * Commit 4 (a venir) : mode Agence (arbre orga).
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Calendar, ChevronLeft, ChevronRight, Loader2, MapPin, Phone, Search,
  User as UserIcon, X,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '../ui/dialog'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface ComboItem { id: string; label: string }
interface CommuneItem {
  id_communes_france: string
  code_postal: string
  nom_ville: string
  latitude_deg?: number | null
  longitude_deg?: number | null
}
interface CVRow {
  id_cvtheque: string
  identite: string
  nom: string
  prenom: string
  op_traitement: string
  op_traitement_id: string
  statut_actuel: string
  statut_periode: string
  source: string
  detail_source: string
  age: number
  tel: string
  localisation: string
  date_saisie: string
  date_rappel: string
  agence: string
  equipe: string
  commentaire: string
}

interface RechercheCVPageProps {
  apiBase: string                  // ex: '/api/adm'
  filtresForces?: Partial<Filtres> // ex: Vendeur force id_cvsource+id_elem_source
  ficheCvBase?: string             // ex: '/recrutement/cv' pour le double-click
}

interface Filtres {
  mode: number
  sous_mode_cp: number
  select_type_date: number
  select_profil: number
  date_debut?: string
  date_fin?: string
  id_communes_france?: string[]
  rayon_km?: number
  centre_lat?: number
  centre_lon?: number
  tel?: string
  nom?: string
  prenom?: string
  id_cvsource?: string
  id_elem_source?: string
  id_cvposte?: string
  id_ste?: string
  cv_statut_appel?: string
  age_min: number
  age_max: number
  limit: number
}

const MODES = [
  { key: 1, label: 'CP', icon: MapPin },
  { key: 2, label: 'Agence', icon: UserIcon, disabled: true },
  { key: 3, label: 'Tél', icon: Phone },
  { key: 4, label: 'Nom', icon: UserIcon },
]

const PROFILS = [
  { key: 1, label: 'ENI' },
  { key: 2, label: 'FIBRE' },
  { key: 3, label: 'Les 2' },
  { key: 4, label: 'Autre' },
]

export default function RechercheCVPage({
  apiBase, filtresForces = {},
}: RechercheCVPageProps) {
  const today = new Date().toISOString().slice(0, 10)
  const oneYearAgo = new Date(Date.now() - 365 * 86400000).toISOString().slice(0, 10)

  const [filtres, setFiltres] = useState<Filtres>({
    mode: 1, sous_mode_cp: 1, select_type_date: 1, select_profil: 3,
    date_debut: oneYearAgo, date_fin: today,
    age_min: 0, age_max: 100, limit: 1000,
    ...filtresForces,
  })

  const [sources, setSources] = useState<ComboItem[]>([])
  const [statuts, setStatuts] = useState<ComboItem[]>([])
  const [postes, setPostes] = useState<ComboItem[]>([])
  const [annonceurs, setAnnonceurs] = useState<ComboItem[]>([])
  const [societes, setSocietes] = useState<ComboItem[]>([])

  const [communesSel, setCommunesSel] = useState<CommuneItem[]>([])
  const [resultats, setResultats] = useState<CVRow[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedId, setSelectedId] = useState('')
  const [statuerVal, setStatuerVal] = useState('')

  const [sidebarOpen, setSidebarOpen] = useState(true)

  // Charger combos une fois
  useEffect(() => {
    const h = { Authorization: `Bearer ${getToken()}` }
    fetch(`${apiBase}/recrutement/cv/sources`, { headers: h })
      .then(r => r.json()).then(setSources)
    fetch(`${apiBase}/recrutement/cv/statuts`, { headers: h })
      .then(r => r.json()).then(setStatuts)
    fetch(`${apiBase}/recrutement/cv/postes`, { headers: h })
      .then(r => r.json()).then(setPostes)
    fetch(`${apiBase}/recrutement/cv/annonceurs`, { headers: h })
      .then(r => r.json()).then(setAnnonceurs)
    fetch(`${apiBase}/recrutement/cv/societes`, { headers: h })
      .then(r => r.json()).then(setSocietes)
  }, [apiBase])

  const statutsById = useMemo(() => {
    const m = new Map<string, string>()
    statuts.forEach(s => m.set(s.id, s.label))
    return m
  }, [statuts])

  const sourcesById = useMemo(() => {
    const m = new Map<string, string>()
    sources.forEach(s => m.set(s.id, s.label))
    return m
  }, [sources])

  const setMode = (mode: number) => {
    setFiltres(f => ({ ...f, mode }))
    setResultats([])
  }

  const lancer = async () => {
    if (filtres.mode === 1 && filtres.sous_mode_cp === 1 && communesSel.length === 0
        && !filtres.rayon_km) {
      showToast('Sélectionne au moins une commune ou un rayon.', 'info')
      return
    }
    if (filtres.mode === 3 && !filtres.tel) {
      showToast('Saisis un numéro de téléphone.', 'info')
      return
    }
    if (filtres.mode === 4 && !filtres.nom) {
      showToast('Saisis un nom.', 'info')
      return
    }
    setLoading(true)
    try {
      const payload: Filtres = {
        ...filtres,
        ...filtresForces,
        id_communes_france: communesSel.map(c => c.id_communes_france),
      }
      const r = await fetch(`${apiBase}/recrutement/cv/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(payload),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d: CVRow[] = await r.json()
      setResultats(d)
      if (d.length === 0) showToast('Aucun résultat.', 'info')
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  // Couleur ligne selon presence
  const rowStyle = (r: CVRow): React.CSSProperties => {
    if (selectedId === r.id_cvtheque) {
      return { backgroundColor: COL_PRIMARY_LIGHT, color: 'white' }
    }
    // Presence sera ajoutee au commit 3
    return { backgroundColor: 'white', color: COL_BRUN }
  }

  return (
    <div className="flex h-full">
      {/* SIDEBAR FILTRES */}
      {sidebarOpen && (
        <aside className="w-80 shrink-0 border-r bg-white p-3 overflow-y-auto"
               style={{ borderColor: COL_BORDER, maxHeight: 'calc(100vh - 80px)' }}>
          {/* Onglets modes */}
          <div className="flex gap-1 mb-3 border-b" style={{ borderColor: COL_BORDER }}>
            {MODES.map(m => {
              const Icon = m.icon
              const active = filtres.mode === m.key
              return (
                <button key={m.key} type="button" disabled={m.disabled}
                        onClick={() => setMode(m.key)}
                        className="flex-1 flex items-center justify-center gap-1 px-2 py-2 text-xs rounded-t transition-colors disabled:opacity-40"
                        style={{
                          backgroundColor: active ? COL_PRIMARY : 'transparent',
                          color: active ? 'white' : COL_BRUN,
                          borderBottom: active ? `2px solid ${COL_PRIMARY}` : 'none',
                        }}
                        title={m.disabled ? 'Disponible bientôt' : m.label}>
                  <Icon className="w-3.5 h-3.5" />
                  {m.label}
                </button>
              )
            })}
          </div>

          {/* MODE CP */}
          {filtres.mode === 1 && (
            <FiltresCP filtres={filtres} setFiltres={setFiltres}
                       communesSel={communesSel} setCommunesSel={setCommunesSel}
                       apiBase={apiBase} />
          )}
          {/* MODE TEL */}
          {filtres.mode === 3 && (
            <div className="space-y-2">
              <label className="text-xs font-semibold" style={{ color: COL_BRUN }}>
                Téléphone
              </label>
              <input type="text" value={filtres.tel || ''}
                     onChange={e => setFiltres({ ...filtres, tel: e.target.value })}
                     placeholder="06xxxxxxxx"
                     className="w-full px-2 py-1.5 rounded border bg-white text-sm"
                     style={{ borderColor: COL_BORDER }} />
            </div>
          )}
          {/* MODE NOM */}
          {filtres.mode === 4 && (
            <div className="space-y-2">
              <label className="text-xs font-semibold" style={{ color: COL_BRUN }}>Nom</label>
              <input type="text" value={filtres.nom || ''}
                     onChange={e => setFiltres({ ...filtres, nom: e.target.value })}
                     className="w-full px-2 py-1.5 rounded border bg-white text-sm uppercase"
                     style={{ borderColor: COL_BORDER }} />
              <label className="text-xs font-semibold" style={{ color: COL_BRUN }}>Prénom</label>
              <input type="text" value={filtres.prenom || ''}
                     onChange={e => setFiltres({ ...filtres, prenom: e.target.value })}
                     className="w-full px-2 py-1.5 rounded border bg-white text-sm uppercase"
                     style={{ borderColor: COL_BORDER }} />
            </div>
          )}

          {/* Filtres communs mode 1+2 */}
          {(filtres.mode === 1 || filtres.mode === 2) && (
            <FiltresCommuns filtres={filtres} setFiltres={setFiltres}
                            sources={sources} postes={postes} annonceurs={annonceurs}
                            societes={societes} statuts={statuts}
                            filtresForces={filtresForces} />
          )}

          <button type="button" onClick={lancer} disabled={loading}
                  className="w-full mt-4 flex items-center justify-center gap-2 px-3 py-2.5 rounded text-white text-sm font-semibold disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Lancer la recherche
          </button>
        </aside>
      )}

      {/* MAIN : tableau resultats */}
      <main className="flex-1 flex flex-col min-w-0 p-3 space-y-3">
        {/* Bandeau */}
        <div className="flex items-center gap-2 shrink-0">
          <button type="button" onClick={() => setSidebarOpen(o => !o)}
                  className="p-1.5 rounded border hover:bg-gray-50"
                  style={{ borderColor: COL_BORDER, color: COL_BRUN }}
                  title={sidebarOpen ? 'Cacher les filtres' : 'Afficher les filtres'}>
            {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
          <h1 className="text-lg font-bold flex-1" style={{ color: COL_BRUN }}>
            Recherche CV
            <span className="ml-2 text-sm font-normal" style={{ color: COL_PRIMARY }}>
              {resultats.length > 0 && `(${resultats.length} résultats)`}
            </span>
          </h1>

          {/* Bloc statuer la selection (V2) */}
          <div className="flex items-center gap-2">
            <select value={statuerVal}
                    onChange={e => setStatuerVal(e.target.value)}
                    className="px-2 py-1.5 rounded border bg-white text-sm"
                    style={{ borderColor: COL_BORDER }}>
              <option value="">Statut du CV...</option>
              {statuts.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
            </select>
            <button type="button" disabled
                    className="px-3 py-1.5 rounded text-white text-sm opacity-50 cursor-not-allowed"
                    style={{ backgroundColor: COL_PRIMARY }}
                    title="Disponible bientôt">
              Statuer la sélection
            </button>
          </div>
        </div>

        {/* Tableau */}
        <div className="flex-1 border rounded-lg overflow-auto bg-white"
             style={{ borderColor: COL_BORDER }}>
          <table className="w-full text-xs">
            <thead className="sticky top-0 z-10"
                   style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
              <tr>
                <th className="px-2 py-2 text-left whitespace-nowrap">Identité</th>
                <th className="px-2 py-2 text-left whitespace-nowrap">Op. Traitement</th>
                <th className="px-2 py-2 text-left whitespace-nowrap">Statut Actuel</th>
                <th className="px-2 py-2 text-left whitespace-nowrap">Source</th>
                <th className="px-2 py-2 text-left whitespace-nowrap">Détail Source</th>
                <th className="px-2 py-2 text-center whitespace-nowrap">Age</th>
                <th className="px-2 py-2 text-left whitespace-nowrap">Tél</th>
                <th className="px-2 py-2 text-left whitespace-nowrap">Localisation</th>
                <th className="px-2 py-2 text-left whitespace-nowrap">Date Saisie</th>
                <th className="px-2 py-2 text-left whitespace-nowrap">Rappel</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={10} className="p-6 text-center">
                  <Loader2 className="w-5 h-5 animate-spin inline" /></td></tr>
              ) : resultats.length === 0 ? (
                <tr><td colSpan={10} className="p-6 text-center italic"
                        style={{ color: '#A68D8A' }}>
                  Lance une recherche depuis le panneau de gauche.
                </td></tr>
              ) : (
                resultats.map(r => (
                  <tr key={r.id_cvtheque} onClick={() => setSelectedId(r.id_cvtheque)}
                      className="cursor-pointer border-b"
                      style={{ ...rowStyle(r), borderColor: COL_BORDER }}>
                    <td className="px-2 py-1.5 font-semibold whitespace-nowrap">
                      {r.identite}
                    </td>
                    <td className="px-2 py-1.5">{r.op_traitement}</td>
                    <td className="px-2 py-1.5">
                      {statutsById.get(r.statut_actuel) || ''}
                    </td>
                    <td className="px-2 py-1.5">{sourcesById.get(r.source) || ''}</td>
                    <td className="px-2 py-1.5">{r.detail_source}</td>
                    <td className="px-2 py-1.5 text-center">
                      {r.age > 0 ? r.age : ''}
                    </td>
                    <td className="px-2 py-1.5 whitespace-nowrap">{r.tel}</td>
                    <td className="px-2 py-1.5">{r.localisation}</td>
                    <td className="px-2 py-1.5 whitespace-nowrap">{r.date_saisie}</td>
                    <td className="px-2 py-1.5 whitespace-nowrap">{r.date_rappel}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  )
}

// ============================================================================
// Filtres CP : selection multi-communes via autocomplete
// ============================================================================

function FiltresCP({ filtres, setFiltres, communesSel, setCommunesSel, apiBase }: {
  filtres: Filtres
  setFiltres: (f: Filtres) => void
  communesSel: CommuneItem[]
  setCommunesSel: (c: CommuneItem[]) => void
  apiBase: string
}) {
  const [query, setQuery] = useState('')
  const [propositions, setPropositions] = useState<CommuneItem[]>([])
  const [searching, setSearching] = useState(false)

  const searchCommunes = useCallback(async () => {
    if (query.length < 2) {
      setPropositions([])
      return
    }
    setSearching(true)
    try {
      const r = await fetch(
        `${apiBase}/recrutement/cv/communes?q=${encodeURIComponent(query)}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (r.ok) setPropositions(await r.json())
    } finally { setSearching(false) }
  }, [query, apiBase])

  const ajouter = (c: CommuneItem) => {
    if (!communesSel.some(x => x.id_communes_france === c.id_communes_france)) {
      setCommunesSel([...communesSel, c])
      // si 1ere commune : centre = sa coord (pour rayon)
      if (communesSel.length === 0 && c.latitude_deg && c.longitude_deg) {
        setFiltres({ ...filtres, centre_lat: c.latitude_deg, centre_lon: c.longitude_deg })
      }
    }
    setQuery('')
    setPropositions([])
  }

  const retirer = (id: string) => {
    setCommunesSel(communesSel.filter(c => c.id_communes_france !== id))
  }

  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs font-semibold" style={{ color: COL_BRUN }}>
          Ville / CP
        </label>
        <div className="flex gap-1">
          <input type="text" value={query}
                 onChange={e => setQuery(e.target.value.toUpperCase())}
                 onKeyDown={e => { if (e.key === 'Enter') searchCommunes() }}
                 placeholder="Code postal ou ville"
                 className="flex-1 px-2 py-1.5 rounded border bg-white text-sm"
                 style={{ borderColor: COL_BORDER }} />
          <button type="button" onClick={searchCommunes} disabled={searching}
                  className="px-2 rounded border"
                  style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
            {searching ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                       : <Search className="w-3.5 h-3.5" />}
          </button>
        </div>
        {propositions.length > 0 && (
          <div className="mt-1 border rounded max-h-40 overflow-y-auto"
               style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
            {propositions.map(p => (
              <button key={p.id_communes_france} type="button"
                      onClick={() => ajouter(p)}
                      className="block w-full text-left px-2 py-1 text-xs hover:bg-white"
                      style={{ color: COL_BRUN }}>
                {p.code_postal} {p.nom_ville}
              </button>
            ))}
          </div>
        )}
        {communesSel.length > 0 && (
          <div className="mt-1 space-y-0.5 max-h-32 overflow-y-auto">
            {communesSel.map(c => (
              <div key={c.id_communes_france}
                   className="flex items-center justify-between text-xs px-2 py-1 rounded"
                   style={{ backgroundColor: COL_BG_SOFT, color: COL_BRUN }}>
                <span>{c.code_postal} {c.nom_ville}</span>
                <button type="button" onClick={() => retirer(c.id_communes_france)}
                        className="text-red-500 hover:text-red-700">
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <label className="text-xs font-semibold" style={{ color: COL_BRUN }}>
          Rayon (km)
        </label>
        <input type="number" value={filtres.rayon_km || ''}
               onChange={e => setFiltres({ ...filtres, rayon_km: Number(e.target.value) || undefined })}
               className="w-full px-2 py-1.5 rounded border bg-white text-sm"
               style={{ borderColor: COL_BORDER }}
               min={0} max={500} />
      </div>

      <div>
        <label className="text-xs font-semibold" style={{ color: COL_BRUN }}>
          Type recherche
        </label>
        <select value={filtres.sous_mode_cp}
                onChange={e => setFiltres({ ...filtres, sous_mode_cp: Number(e.target.value) })}
                className="w-full px-2 py-1.5 rounded border bg-white text-sm"
                style={{ borderColor: COL_BORDER }}>
          <option value={1}>Recherche classique par secteur</option>
          <option value={2}>CV sans commune</option>
          <option value={3}>Ne pas géolocaliser</option>
        </select>
      </div>
    </div>
  )
}

// ============================================================================
// Filtres communs : source, profil, age, periode, societe, statut
// ============================================================================

function FiltresCommuns({
  filtres, setFiltres, sources, postes, annonceurs, societes, statuts,
  filtresForces,
}: {
  filtres: Filtres
  setFiltres: (f: Filtres) => void
  sources: ComboItem[]
  postes: ComboItem[]
  annonceurs: ComboItem[]
  societes: ComboItem[]
  statuts: ComboItem[]
  filtresForces: Partial<Filtres>
}) {
  const sourceLocked = !!filtresForces.id_cvsource
  return (
    <div className="space-y-3 mt-3 pt-3 border-t" style={{ borderColor: COL_BORDER }}>
      {/* Periode */}
      <div>
        <label className="text-xs font-semibold flex items-center gap-1" style={{ color: COL_BRUN }}>
          <Calendar className="w-3 h-3" /> Période
        </label>
        <div className="flex gap-1 items-center text-xs">
          <input type="date" value={filtres.date_debut || ''}
                 onChange={e => setFiltres({ ...filtres, date_debut: e.target.value })}
                 className="flex-1 px-2 py-1.5 rounded border bg-white"
                 style={{ borderColor: COL_BORDER }} />
          <span style={{ color: COL_BRUN }}>au</span>
          <input type="date" value={filtres.date_fin || ''}
                 onChange={e => setFiltres({ ...filtres, date_fin: e.target.value })}
                 className="flex-1 px-2 py-1.5 rounded border bg-white"
                 style={{ borderColor: COL_BORDER }} />
        </div>
        <div className="flex gap-1 mt-1">
          <ToggleBtn active={filtres.select_type_date === 1}
                     onClick={() => setFiltres({ ...filtres, select_type_date: 1 })}>
            Date saisie/Rappel
          </ToggleBtn>
          <ToggleBtn active={filtres.select_type_date === 2}
                     onClick={() => setFiltres({ ...filtres, select_type_date: 2 })}>
            Date modif
          </ToggleBtn>
        </div>
      </div>

      {/* Profil */}
      <div>
        <label className="text-xs font-semibold" style={{ color: COL_BRUN }}>Profil</label>
        <div className="flex gap-1">
          {PROFILS.map(p => (
            <ToggleBtn key={p.key} active={filtres.select_profil === p.key}
                       onClick={() => setFiltres({ ...filtres, select_profil: p.key })}>
              {p.label}
            </ToggleBtn>
          ))}
        </div>
        {filtres.select_profil === 4 && (
          <select value={filtres.id_cvposte || ''}
                  onChange={e => setFiltres({ ...filtres, id_cvposte: e.target.value })}
                  className="w-full mt-1 px-2 py-1.5 rounded border bg-white text-sm"
                  style={{ borderColor: COL_BORDER }}>
            <option value="">— Tous les postes —</option>
            {postes.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
          </select>
        )}
      </div>

      {/* Source */}
      <div>
        <label className="text-xs font-semibold" style={{ color: COL_BRUN }}>Source</label>
        <select value={filtres.id_cvsource || ''} disabled={sourceLocked}
                onChange={e => setFiltres({ ...filtres, id_cvsource: e.target.value || undefined })}
                className="w-full px-2 py-1.5 rounded border bg-white text-sm disabled:bg-gray-100"
                style={{ borderColor: COL_BORDER }}>
          <option value="">— Toutes les sources —</option>
          {sources.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
        {filtres.id_cvsource === '2' && (
          <select value={filtres.id_elem_source || ''}
                  onChange={e => setFiltres({ ...filtres, id_elem_source: e.target.value || undefined })}
                  className="w-full mt-1 px-2 py-1.5 rounded border bg-white text-sm"
                  style={{ borderColor: COL_BORDER }}>
            <option value="">— Tous les annonceurs —</option>
            {annonceurs.map(a => <option key={a.id} value={a.id}>{a.label}</option>)}
          </select>
        )}
      </div>

      {/* Societe */}
      <div>
        <label className="text-xs font-semibold" style={{ color: COL_BRUN }}>Société</label>
        <select value={filtres.id_ste || ''}
                onChange={e => setFiltres({ ...filtres, id_ste: e.target.value || undefined })}
                className="w-full px-2 py-1.5 rounded border bg-white text-sm"
                style={{ borderColor: COL_BORDER }}>
          <option value="">— Toutes les sociétés —</option>
          {societes.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
      </div>

      {/* Statut courant */}
      <div>
        <label className="text-xs font-semibold" style={{ color: COL_BRUN }}>Statut actuel</label>
        <select value={filtres.cv_statut_appel || ''}
                onChange={e => setFiltres({ ...filtres, cv_statut_appel: e.target.value || undefined })}
                className="w-full px-2 py-1.5 rounded border bg-white text-sm"
                style={{ borderColor: COL_BORDER }}>
          <option value="">— Tous statuts —</option>
          {statuts.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
      </div>

      {/* Age */}
      <div>
        <label className="text-xs font-semibold" style={{ color: COL_BRUN }}>
          Âge entre {filtres.age_min} et {filtres.age_max} ans
        </label>
        <div className="flex gap-1">
          <input type="number" value={filtres.age_min}
                 onChange={e => setFiltres({ ...filtres, age_min: Number(e.target.value) || 0 })}
                 min={0} max={99}
                 className="w-16 px-2 py-1.5 rounded border bg-white text-sm"
                 style={{ borderColor: COL_BORDER }} />
          <input type="number" value={filtres.age_max}
                 onChange={e => setFiltres({ ...filtres, age_max: Number(e.target.value) || 100 })}
                 min={1} max={100}
                 className="w-16 px-2 py-1.5 rounded border bg-white text-sm"
                 style={{ borderColor: COL_BORDER }} />
        </div>
      </div>
    </div>
  )
}

function ToggleBtn({ active, onClick, children }: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button type="button" onClick={onClick}
            className="flex-1 px-2 py-1.5 rounded border text-xs"
            style={{
              backgroundColor: active ? COL_PRIMARY : 'white',
              color: active ? 'white' : COL_BRUN,
              borderColor: COL_BORDER,
            }}>
      {children}
    </button>
  )
}
