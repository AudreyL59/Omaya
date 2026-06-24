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

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowDown, ArrowUp, ArrowUpDown,
  Building2, Calendar, ChevronDown, ChevronLeft, ChevronRight, Folder,
  Loader2, MapPin, Phone, Search,
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

interface PresenceEntry {
  op_traite: string         // qui a la fiche ouverte
  op_nom: string
  statut_actuel: string
  last_op_crea: string      // qui a fait le dernier changement de statut
}

interface RechercheCVPageProps {
  apiBase: string                  // ex: '/api/adm'
  filtresForces?: Partial<Filtres> // ex: Vendeur force id_cvsource+id_elem_source
  myUserId?: string                // id_salarie du user connecte (pour couleurs)
  onOpenFiche?: (id_cvtheque: string) => void   // double-click ouvre Fen_CVFiche
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
  id_organigrammes?: string[]
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
  { key: 2, label: 'Agence', icon: Building2 },
  { key: 3, label: 'Tél', icon: Phone },
  { key: 4, label: 'Nom', icon: UserIcon },
]

const PROFILS = [
  { key: 1, label: 'ENI' },
  { key: 2, label: 'FIBRE' },
  { key: 3, label: 'Les 2' },
  { key: 4, label: 'Autre' },
]

interface ColDef {
  key: string
  label: string
  align?: 'left' | 'right' | 'center'
  nowrap?: boolean
}

const COLS: ColDef[] = [
  { key: 'identite',      label: 'Identité',           nowrap: true },
  { key: 'op_traitement', label: 'Op. Traitement',     nowrap: true },
  { key: 'statut',        label: 'Statut Actuel',      nowrap: true },
  { key: 'source',        label: 'Source',             nowrap: true },
  { key: 'detail_source', label: 'Détail Source',      nowrap: true },
  { key: 'age',           label: 'Age',                align: 'center' },
  { key: 'tel',           label: 'Tél',                nowrap: true },
  { key: 'localisation',  label: 'Localisation',       nowrap: true },
  { key: 'date_saisie',   label: 'Date Saisie',        nowrap: true },
  { key: 'date_rappel',   label: 'Rappel',             nowrap: true },
  { key: 'agence',        label: 'Agence',             nowrap: true },
  { key: 'equipe',        label: 'Équipe',             nowrap: true },
  { key: 'commentaire',   label: 'Dernier commentaire' },
]

function ThSortable({ col, sortKey, sortDir, onClick }: {
  col: ColDef
  sortKey: string
  sortDir: 'asc' | 'desc'
  onClick: () => void
}) {
  const active = sortKey === col.key
  return (
    <th onClick={onClick}
        className={`px-2 pt-2 pb-1 cursor-pointer select-none hover:bg-black/10 ${
          col.align === 'center' ? 'text-center' : 'text-left'
        } ${col.nowrap ? 'whitespace-nowrap' : ''}`}>
      <span className="inline-flex items-center gap-1">
        {col.label}
        {active
          ? (sortDir === 'asc' ? <ArrowUp className="w-3 h-3" />
                               : <ArrowDown className="w-3 h-3" />)
          : <ArrowUpDown className="w-3 h-3 opacity-40" />}
      </span>
    </th>
  )
}

export default function RechercheCVPage({
  apiBase, filtresForces = {}, myUserId = '', onOpenFiche,
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
  const [orgasSel, setOrgasSel] = useState<{ id: string; lib: string }[]>([])
  const [resultats, setResultats] = useState<CVRow[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedId, setSelectedId] = useState('')
  const [statuerVal, setStatuerVal] = useState('')
  const [presence, setPresence] = useState<Record<string, PresenceEntry>>({})
  // statut au moment de la recherche initiale (pour detecter les changements)
  const [statutSnapshot, setStatutSnapshot] = useState<Record<string, string>>({})
  // ids des CV dont le statut a change depuis la recherche
  const [changedIds, setChangedIds] = useState<Set<string>>(new Set())
  // Tri + filtres par colonne
  const [sortKey, setSortKey] = useState<string>('')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [exporting, setExporting] = useState(false)

  const [sidebarOpen, setSidebarOpen] = useState(true)

  // Charger combos une fois + cleanup orphans
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
    // Libere mes claims orphelins (sessions interrompues)
    fetch(`${apiBase}/recrutement/cv/orphans/release`, {
      method: 'POST', headers: h,
    }).catch(() => {})
  }, [apiBase])

  // Polling presence + statut tous les 1.5s tant qu'on a des resultats
  useEffect(() => {
    if (resultats.length === 0) return
    const ids = resultats.map(r => r.id_cvtheque)
    let stopped = false

    const poll = async () => {
      try {
        const r = await fetch(`${apiBase}/recrutement/cv/presence`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({ ids }),
        })
        if (r.ok && !stopped) {
          const d: Record<string, PresenceEntry> = await r.json()
          setPresence(d)
          // Detecte les changements de statut vs snapshot
          const newChanges = new Set<string>()
          Object.entries(d).forEach(([id, p]) => {
            const snap = statutSnapshot[id]
            if (snap && p.statut_actuel && snap !== p.statut_actuel) {
              newChanges.add(id)
            }
          })
          setChangedIds(newChanges)
        }
      } catch { /* silent */ }
    }
    poll()
    const interval = setInterval(poll, 1500)
    return () => { stopped = true; clearInterval(interval) }
  }, [apiBase, resultats, statutSnapshot])

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

  // Filtre + tri client-side appliques sur les resultats
  const displayedRows = useMemo(() => {
    const valueFor = (r: CVRow, key: string): string => {
      const pres = presence[r.id_cvtheque]
      switch (key) {
        case 'identite':       return r.identite
        case 'op_traitement':  return pres?.op_nom || r.op_traitement
        case 'statut':         return statutsById.get(pres?.statut_actuel || r.statut_actuel) || ''
        case 'source':         return sourcesById.get(r.source) || ''
        case 'detail_source':  return r.detail_source
        case 'age':            return String(r.age || '')
        case 'tel':            return r.tel
        case 'localisation':   return r.localisation
        case 'date_saisie':    return r.date_saisie
        case 'date_rappel':    return r.date_rappel
        case 'agence':         return r.agence
        case 'equipe':         return r.equipe
        case 'commentaire':    return r.commentaire
        default: return ''
      }
    }
    let arr = resultats
    // Filtre par colonne
    const activeFilters = Object.entries(filters).filter(([, v]) => v.trim())
    if (activeFilters.length > 0) {
      arr = arr.filter(r =>
        activeFilters.every(([k, v]) =>
          valueFor(r, k).toLowerCase().includes(v.toLowerCase())
        )
      )
    }
    // Tri
    if (sortKey) {
      const isNumeric = sortKey === 'age'
      const isDate = sortKey === 'date_saisie' || sortKey === 'date_rappel'
      arr = [...arr].sort((a, b) => {
        const va = valueFor(a, sortKey)
        const vb = valueFor(b, sortKey)
        let cmp = 0
        if (isNumeric) {
          cmp = (parseInt(va, 10) || 0) - (parseInt(vb, 10) || 0)
        } else if (isDate) {
          cmp = (va || '').localeCompare(vb || '')
        } else {
          cmp = va.localeCompare(vb, 'fr', { sensitivity: 'base' })
        }
        return sortDir === 'asc' ? cmp : -cmp
      })
    }
    return arr
  }, [resultats, filters, sortKey, sortDir, presence, statutsById, sourcesById])

  const toggleSort = (k: string) => {
    if (sortKey !== k) { setSortKey(k); setSortDir('asc'); return }
    if (sortDir === 'asc') { setSortDir('desc'); return }
    setSortKey(''); setSortDir('asc')
  }

  const exportXlsx = async () => {
    if (displayedRows.length === 0) {
      showToast('Aucune ligne à exporter.', 'info')
      return
    }
    setExporting(true)
    try {
      const enriched = displayedRows.map(r => {
        const pres = presence[r.id_cvtheque]
        return {
          ...r,
          op_traitement: pres?.op_nom || r.op_traitement,
          statut_actuel_lib: statutsById.get(pres?.statut_actuel || r.statut_actuel) || '',
          source_lib: sourcesById.get(r.source) || '',
        }
      })
      const r = await fetch(`${apiBase}/recrutement/cv/export.xlsx`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ rows: enriched }),
      })
      if (!r.ok) throw new Error(String(r.status))
      const blob = await r.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `RechercheCV_${new Date().toISOString().slice(0, 10)}.xlsx`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (e) {
      showToast(`Erreur export : ${(e as Error).message}`, 'error')
    } finally { setExporting(false) }
  }

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
    if (filtres.mode === 2 && orgasSel.length === 0) {
      showToast('Sélectionne au moins une agence / équipe.', 'info')
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
        id_organigrammes: orgasSel.map(o => o.id),
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
      // Snapshot des statuts pour detecter les changements ulterieurs
      const snap: Record<string, string> = {}
      d.forEach(row => { snap[row.id_cvtheque] = row.statut_actuel })
      setStatutSnapshot(snap)
      setChangedIds(new Set())
      if (d.length === 0) showToast('Aucun résultat.', 'info')
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  // Couleur ligne selon presence + selection + changement de statut.
  // Regle WinDev :
  //  - selection -> vert primary
  //  - statut change depuis la recherche :
  //      jaune si c'est MOI qui ai fait le dernier traitement (last_op_crea)
  //      orange si c'est un AUTRE
  //  - fiche actuellement ouverte (sans changement) : teinte tres claire
  //  - sinon blanc
  const rowStyle = (r: CVRow): React.CSSProperties => {
    const isSel = selectedId === r.id_cvtheque
    const pres = presence[r.id_cvtheque]
    const opTraite = pres?.op_traite || ''
    const lastOp = pres?.last_op_crea || ''
    const changed = changedIds.has(r.id_cvtheque)

    if (isSel) {
      return { backgroundColor: COL_PRIMARY_LIGHT, color: 'white' }
    }
    // Statut change -> couleur selon QUI a traite (last_op_crea), pas
    // selon qui a la fiche ouverte (op_traite).
    if (changed) {
      if (lastOp && lastOp === myUserId) {
        return { backgroundColor: '#FEF08A', color: COL_BRUN }  // jaune
      }
      return { backgroundColor: '#FED7AA', color: COL_BRUN }    // orange
    }
    // Fiche actuellement ouverte par qqun (sans changement de statut)
    if (opTraite) {
      if (opTraite === myUserId) {
        return { backgroundColor: '#FEF9C3', color: COL_BRUN }  // jaune clair
      }
      return { backgroundColor: '#FFEDD5', color: COL_BRUN }    // orange clair
    }
    return { backgroundColor: 'white', color: COL_BRUN }
  }

  // Ouvre Fen_CVFiche : appelle juste le callback. Le claim est fait
  // par le modal au mount (et l'alerte 'deja ouvert' aussi).
  const handleOpenFiche = (idCv: string) => {
    onOpenFiche?.(idCv)
  }

  // Detection manuelle du double-click (onDoubleClick natif ne se
  // declenche pas toujours quand onClick re-render le DOM entre les 2
  // clicks). On considere double-click : 2 clicks <400ms sur la meme ligne.
  const lastClickRef = useRef<{ id: string; t: number }>({ id: '', t: 0 })
  const handleRowClick = (idCv: string) => {
    const now = Date.now()
    const prev = lastClickRef.current
    if (prev.id === idCv && (now - prev.t) < 400) {
      lastClickRef.current = { id: '', t: 0 }
      handleOpenFiche(idCv)
      return
    }
    lastClickRef.current = { id: idCv, t: now }
    setSelectedId(idCv)
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
                <button key={m.key} type="button"
                        onClick={() => setMode(m.key)}
                        className="flex-1 flex items-center justify-center gap-1 px-2 py-2 text-xs rounded-t transition-colors"
                        style={{
                          backgroundColor: active ? COL_PRIMARY : 'transparent',
                          color: active ? 'white' : COL_BRUN,
                          borderBottom: active ? `2px solid ${COL_PRIMARY}` : 'none',
                        }}
                        title={m.label}>
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
          {/* MODE AGENCE */}
          {filtres.mode === 2 && (
            <FiltresAgence orgasSel={orgasSel} setOrgasSel={setOrgasSel}
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
            <button type="button" onClick={exportXlsx} disabled={exporting}
                    className="px-3 py-1.5 rounded text-white text-sm disabled:opacity-50"
                    style={{ backgroundColor: COL_PRIMARY }}
                    title="Exporter au format Excel (.xlsx)">
              {exporting ? <Loader2 className="w-4 h-4 animate-spin inline" />
                         : 'Exporter Excel'}
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
                {COLS.map(c => (
                  <ThSortable key={c.key} col={c}
                              sortKey={sortKey} sortDir={sortDir}
                              onClick={() => toggleSort(c.key)} />
                ))}
              </tr>
              <tr style={{ backgroundColor: '#0F3336' }}>
                {COLS.map(c => (
                  <th key={c.key} className="px-1 pb-1">
                    <input type="text" value={filters[c.key] || ''}
                           onChange={e => setFilters(f => ({ ...f, [c.key]: e.target.value }))}
                           placeholder="filtrer..."
                           className="w-full px-1 py-0.5 text-xs rounded text-gray-900"
                           style={{ backgroundColor: 'white' }} />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={COLS.length} className="p-6 text-center">
                  <Loader2 className="w-5 h-5 animate-spin inline" /></td></tr>
              ) : displayedRows.length === 0 ? (
                <tr><td colSpan={COLS.length} className="p-6 text-center italic"
                        style={{ color: '#A68D8A' }}>
                  {resultats.length === 0
                    ? 'Lance une recherche depuis le panneau de gauche.'
                    : 'Aucune ligne ne correspond aux filtres.'}
                </td></tr>
              ) : (
                displayedRows.map(r => {
                  const pres = presence[r.id_cvtheque]
                  // Priorite a la donnee live du polling (meme si vide).
                  // Fallback sur le snapshot initial uniquement si pas
                  // encore polle.
                  const statutLive = pres ? pres.statut_actuel : r.statut_actuel
                  const opNom = pres ? pres.op_nom : r.op_traitement
                  return (
                  <tr key={r.id_cvtheque}
                      onClick={() => handleRowClick(r.id_cvtheque)}
                      className="cursor-pointer border-b"
                      style={{ ...rowStyle(r), borderColor: COL_BORDER }}>
                    <td className="px-2 py-1.5 font-semibold whitespace-nowrap">
                      {r.identite}
                    </td>
                    <td className="px-2 py-1.5">{opNom}</td>
                    <td className="px-2 py-1.5">
                      {statutsById.get(statutLive) || ''}
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
                    <td className="px-2 py-1.5 whitespace-nowrap">{r.agence}</td>
                    <td className="px-2 py-1.5 whitespace-nowrap">{r.equipe}</td>
                    <td className="px-2 py-1.5 truncate max-w-xs" title={r.commentaire}>
                      {r.commentaire}
                    </td>
                  </tr>
                  )
                })
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
    // 1 seule commune : remplace la precedente
    setCommunesSel([c])
    if (c.latitude_deg && c.longitude_deg) {
      setFiltres({ ...filtres, centre_lat: c.latitude_deg, centre_lon: c.longitude_deg })
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
        <select value="" onChange={e => {
                  const v = e.target.value
                  if (!v) return
                  const [deb, fin] = computePeriode(v)
                  setFiltres({ ...filtres, date_debut: deb, date_fin: fin })
                  e.target.value = ''
                }}
                className="w-full px-2 py-1.5 rounded border bg-white text-xs"
                style={{ borderColor: COL_BORDER }}>
          <option value="">— Ancienneté —</option>
          <option value="7j">- de 7 jours</option>
          <option value="15j">- de 15 jours</option>
          <option value="-1mois">- d&apos;1 mois</option>
          <option value="+1mois">+ d&apos;1 mois</option>
        </select>
        <div className="flex gap-1 items-center text-xs mt-1">
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

// ============================================================================
// Filtres Agence : arbre orga lazy load (Reseau > Agences > Equipes)
// ============================================================================

interface OrgaNode {
  idorganigramme: string
  lib_orga: string
  has_children: boolean
}

function FiltresAgence({ orgasSel, setOrgasSel, apiBase }: {
  orgasSel: { id: string; lib: string }[]
  setOrgasSel: (v: { id: string; lib: string }[]) => void
  apiBase: string
}) {
  const [racine, setRacine] = useState<OrgaNode[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetch(`${apiBase}/recrutement/cv/organigramme/children?id_parent=0`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then(setRacine)
      .finally(() => setLoading(false))
  }, [apiBase])

  const toggleSel = (n: OrgaNode) => {
    const exist = orgasSel.some(s => s.id === n.idorganigramme)
    if (exist) {
      setOrgasSel(orgasSel.filter(s => s.id !== n.idorganigramme))
    } else {
      setOrgasSel([...orgasSel, { id: n.idorganigramme, lib: n.lib_orga }])
    }
  }

  const isSelected = (id: string) => orgasSel.some(s => s.id === id)

  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold" style={{ color: COL_BRUN }}>
        Agences / Équipes
        {orgasSel.length > 0 && (
          <span className="ml-1 font-normal" style={{ color: COL_PRIMARY }}>
            ({orgasSel.length})
          </span>
        )}
      </div>

      {/* Selection courante */}
      {orgasSel.length > 0 && (
        <div className="space-y-0.5 max-h-24 overflow-y-auto">
          {orgasSel.map(s => (
            <div key={s.id}
                 className="flex items-center justify-between text-xs px-2 py-1 rounded"
                 style={{ backgroundColor: COL_BG_SOFT, color: COL_BRUN }}>
              <span className="truncate">{s.lib}</span>
              <button type="button"
                      onClick={() => setOrgasSel(orgasSel.filter(o => o.id !== s.id))}
                      className="text-red-500 hover:text-red-700 shrink-0 ml-1">
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Arbre */}
      <div className="border rounded max-h-80 overflow-y-auto"
           style={{ borderColor: COL_BORDER, backgroundColor: 'white' }}>
        {loading ? (
          <div className="p-3 text-center">
            <Loader2 className="w-4 h-4 animate-spin inline" />
          </div>
        ) : (
          <div className="text-xs">
            {/* Racine "Reseau" virtuelle */}
            <div className="px-2 py-1 font-semibold flex items-center gap-1"
                 style={{ color: COL_BRUN, backgroundColor: COL_BG_SOFT }}>
              <Folder className="w-3 h-3" /> Réseau
            </div>
            {racine.map(n => (
              <TreeNode key={n.idorganigramme} node={n} level={1}
                        apiBase={apiBase}
                        isSelected={isSelected}
                        onToggle={toggleSel} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function TreeNode({ node, level, apiBase, isSelected, onToggle }: {
  node: OrgaNode
  level: number
  apiBase: string
  isSelected: (id: string) => boolean
  onToggle: (n: OrgaNode) => void
}) {
  const [open, setOpen] = useState(false)
  const [children, setChildren] = useState<OrgaNode[] | null>(null)
  const [loading, setLoading] = useState(false)

  const handleOpen = async () => {
    if (open) { setOpen(false); return }
    if (children === null && node.has_children) {
      setLoading(true)
      try {
        const r = await fetch(
          `${apiBase}/recrutement/cv/organigramme/children?id_parent=${node.idorganigramme}`,
          { headers: { Authorization: `Bearer ${getToken()}` } },
        )
        if (r.ok) setChildren(await r.json())
        else setChildren([])
      } finally { setLoading(false) }
    }
    setOpen(true)
  }

  const sel = isSelected(node.idorganigramme)
  return (
    <div>
      <div className="flex items-center gap-1 px-1 py-0.5 hover:bg-gray-50 cursor-pointer"
           style={{ paddingLeft: 8 + level * 12 }}>
        <button type="button" onClick={handleOpen}
                className="w-4 h-4 flex items-center justify-center"
                style={{ visibility: node.has_children ? 'visible' : 'hidden' }}>
          {loading ? <Loader2 className="w-3 h-3 animate-spin" />
                   : open ? <ChevronDown className="w-3 h-3" />
                          : <ChevronRight className="w-3 h-3" />}
        </button>
        <input type="checkbox" checked={sel}
               onChange={() => onToggle(node)}
               className="cursor-pointer" />
        <button type="button" onClick={() => onToggle(node)}
                className="flex-1 text-left truncate"
                style={{ color: COL_BRUN }}>
          {node.lib_orga}
        </button>
      </div>
      {open && children && children.length > 0 && (
        <div>
          {children.map(c => (
            <TreeNode key={c.idorganigramme} node={c} level={level + 1}
                      apiBase={apiBase}
                      isSelected={isSelected} onToggle={onToggle} />
          ))}
        </div>
      )}
    </div>
  )
}

/** Calcule [date_debut, date_fin] (YYYY-MM-DD) selon le preset. */
function computePeriode(preset: string): [string, string] {
  const today = new Date()
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  const d = new Date(today)
  if (preset === '7j') {
    d.setDate(d.getDate() - 7)
    return [fmt(d), fmt(today)]
  }
  if (preset === '15j') {
    d.setDate(d.getDate() - 15)
    return [fmt(d), fmt(today)]
  }
  if (preset === '-1mois') {
    d.setMonth(d.getMonth() - 1)
    return [fmt(d), fmt(today)]
  }
  if (preset === '+1mois') {
    d.setMonth(d.getMonth() - 1)
    return ['1970-01-01', fmt(d)]
  }
  return [fmt(d), fmt(today)]
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
