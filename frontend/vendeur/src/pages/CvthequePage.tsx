import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  X,
  Loader2,
  FileText,
  Filter,
  Home,
  User,
  Phone,
  Calendar as CalendarIcon,
  MapPin,
  Save,
  ExternalLink,
  Check,
  Copy,
} from 'lucide-react'
import { getToken, getStoredUser } from '@/api'

// --- Types ---------------------------------------------------------------

interface CvStatut {
  id_cv_statut: number
  lib_statut: string
}

interface CvSource {
  id_cv_source: number
  lib_source: string
}

interface CvAnnonceur {
  id_cv_annonceur: number
  lib_annonceur: string
}

interface Commune {
  cp: string
  ville: string
  id_communes_france: string
  latitude: number
  longitude: number
}

interface VendeurItem {
  id_salarie: string
  nom: string
  prenom: string
  poste: string
}

interface CvSuiviItem {
  id_cv_suivi: string
  datecrea: string
  op_crea: number
  op_crea_nom: string
  id_cv_statut: number
  statut_lib: string
  type_elem: string
  id_elem: string
  observation: string
}

interface CvFiche {
  id_cvtheque: string
  origine: number
  nom: string
  prenom: string
  pays: string
  adresse: string
  cp: string
  ville: string
  id_communes_france: number
  date_naissance: string
  age: number
  permis_b: boolean
  vehicule: boolean
  mail: string
  gsm: string
  fic_cv: string
  cv_url: string
  id_cv_poste: number
  id_cv_source: number
  id_elem_source: number
  nom_coopteur: string
  id_ste: number
  observation: string
  id_cv_statut: number
  traite_en_cours: boolean
  op_traite: number
}

interface CvFicheResponse {
  fiche: CvFiche
  suivi: CvSuiviItem[]
}

type HighlightKind = 'self' | 'other' | null

interface CvResult {
  id_cvtheque: string
  identite: string
  op_traitement: string
  date_saisie: string
  statut_actuel: number
  statut_actuel_lib: string
  statut_periode: number
  statut_periode_lib: string
  source: number
  source_lib: string
  age: number
  tel: string
  localisation: string
  detail_source: string
  agence: string
  equipe: string
  commentaire: string
  _highlight?: HighlightKind
  _highlight_until?: number
}

type SearchMode = 'cp' | 'tel' | 'nom'

// --- Helpers -------------------------------------------------------------

function formatDate(raw: string): string {
  if (!raw) return ''
  const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/)
  if (iso) return `${iso[3]}/${iso[2]}/${iso[1]} ${iso[4]}:${iso[5]}`
  if (raw.length >= 12 && /^\d+$/.test(raw.slice(0, 12))) {
    return `${raw.slice(6, 8)}/${raw.slice(4, 6)}/${raw.slice(0, 4)} ${raw.slice(8, 10)}:${raw.slice(10, 12)}`
  }
  return raw
}

function toISODate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function toYMD(d: Date): string {
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
}

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : s
}

// --- Page ----------------------------------------------------------------

export default function CvthequePage() {
  const [results, setResults] = useState<CvResult[]>([])
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressMsg, setProgressMsg] = useState('')
  const [showSearch, setShowSearch] = useState(true)
  const [hasSearched, setHasSearched] = useState(false)
  const [openedCv, setOpenedCv] = useState<string | null>(null)

  // Polling temps réel : qui traite quoi + changement de statut
  const currentUser = getStoredUser()
  const currentUserId = currentUser?.id_salarie ? String(currentUser.id_salarie) : ''

  useEffect(() => {
    if (results.length === 0) return
    const ids = results.map((r) => r.id_cvtheque)

    const poll = async () => {
      try {
        const res = await fetch('/api/vendeur/cvtheque/traitement/bulk', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify(ids),
        })
        if (!res.ok) return
        const data: {
          id_cvtheque: string
          op_traitement: string
          statut_actuel: number
          statut_actuel_lib: string
          last_change_op: number
        }[] = await res.json()
        const byId = new Map(data.map((d) => [d.id_cvtheque, d]))

        setResults((prev) =>
          prev.map((r) => {
            const d = byId.get(r.id_cvtheque)
            if (!d) return r
            const statutChanged =
              d.statut_actuel !== r.statut_actuel &&
              r.statut_actuel !== 0 // ignore la première hydratation
            const traitChanged = d.op_traitement !== r.op_traitement
            if (!statutChanged && !traitChanged) return r

            let highlight: HighlightKind = r._highlight ?? null
            if (statutChanged) {
              highlight = String(d.last_change_op) === currentUserId ? 'self' : 'other'
            }
            return {
              ...r,
              op_traitement: d.op_traitement,
              statut_actuel: d.statut_actuel,
              statut_actuel_lib: d.statut_actuel_lib,
              _highlight: highlight,
            }
          })
        )
      } catch {}
    }

    poll()
    const interval = setInterval(poll, 3000)
    return () => clearInterval(interval)
  }, [results.length, currentUserId])

  const runSearch = async (body: any) => {
    setLoading(true)
    setShowSearch(false)
    setProgress(0)
    setProgressMsg('Démarrage...')
    try {
      const res = await fetch('/api/vendeur/cvtheque/search/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(body),
      })
      if (!res.body) throw new Error('Stream non disponible')
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let finalResults: CvResult[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (!line.trim()) continue
          try {
            const msg = JSON.parse(line)
            if (typeof msg.progress === 'number') {
              setProgress(msg.progress)
              if (msg.msg) setProgressMsg(msg.msg)
            } else if (msg.done) {
              finalResults = msg.results || []
            } else if (msg.error) {
              console.error('Erreur serveur:', msg.error)
            }
          } catch {}
        }
      }

      setResults(finalResults)
      setHasSearched(true)
    } catch (e) {
      console.error(e)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-gray-900">CVthèque</h1>
          <p className="text-gray-500 mt-1">
            {hasSearched ? `${results.length} résultat${results.length > 1 ? 's' : ''}` : 'Recherche dans la base de candidats'}
          </p>
        </div>
        <button
          onClick={() => setShowSearch(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 shadow-sm"
        >
          <Search className="w-4 h-4" />
          Nouvelle recherche
        </button>
      </motion.div>

      <div className="mt-6">
        {loading ? (
          <div className="bg-white rounded-xl border border-gray-200 px-8 py-12">
            <div className="flex items-center gap-3 mb-4">
              <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-medium text-gray-700">
                    {progressMsg || 'Recherche en cours...'}
                  </span>
                  <span className="text-sm font-semibold text-gray-900 tabular-nums">
                    {progress}%
                  </span>
                </div>
                <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gray-900 rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </div>
            </div>
          </div>
        ) : !hasSearched ? (
          <div className="text-center py-20 text-gray-400 text-sm bg-white rounded-xl border border-gray-200">
            Lance une recherche pour afficher les CVs
          </div>
        ) : results.length === 0 ? (
          <div className="text-center py-12 text-gray-400 text-sm bg-white rounded-xl border border-gray-200">
            Aucun CV ne correspond aux critères
          </div>
        ) : (
          <ResultsTable results={results} onOpen={setOpenedCv} />
        )}
      </div>

      <AnimatePresence>
        {showSearch && (
          <SearchPopup
            onClose={() => setShowSearch(false)}
            onSearch={runSearch}
          />
        )}
        {openedCv && (
          <FicheModal
            idCvtheque={openedCv}
            onClose={() => setOpenedCv(null)}
            onUpdated={(id, patch) => {
              setResults((prev) =>
                prev.map((r) => (r.id_cvtheque === id ? { ...r, ...patch } : r))
              )
            }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

// --- Results table -------------------------------------------------------

function ResultsTable({
  results,
  onOpen,
}: {
  results: CvResult[]
  onOpen: (id: string) => void
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="max-h-[calc(100vh-16rem)] overflow-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 sticky top-0 z-10">
            <tr className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th className="text-left px-4 py-3">Identité</th>
              <th className="text-left px-4 py-3">Traitement</th>
              <th className="text-left px-4 py-3">Date saisie</th>
              <th className="text-left px-4 py-3">Statut actuel</th>
              <th className="text-left px-4 py-3">Source</th>
              <th className="text-left px-4 py-3">Âge</th>
              <th className="text-left px-4 py-3">Tél</th>
              <th className="text-left px-4 py-3">Localisation</th>
              <th className="text-left px-4 py-3">Détail source</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr
                key={r.id_cvtheque}
                onClick={() => onOpen(r.id_cvtheque)}
                className={`border-t border-gray-100 transition-colors cursor-pointer ${
                  r._highlight === 'self'
                    ? 'bg-yellow-50 hover:bg-yellow-100'
                    : r._highlight === 'other'
                      ? 'bg-orange-50 hover:bg-orange-100'
                      : 'hover:bg-gray-50'
                }`}
              >
                <td className="px-4 py-3 font-medium text-gray-900">{r.identite}</td>
                <td className="px-4 py-3 text-gray-600">
                  {r.op_traitement && (
                    <span className="px-2 py-0.5 rounded-full text-xs bg-amber-50 text-amber-700 border border-amber-200">
                      {r.op_traitement}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-500">{formatDate(r.date_saisie)}</td>
                <td className="px-4 py-3 text-gray-700">{r.statut_actuel_lib || '—'}</td>
                <td className="px-4 py-3 text-gray-700">{r.source_lib || '—'}</td>
                <td className="px-4 py-3 text-gray-700">{r.age || '—'}</td>
                <td className="px-4 py-3 text-gray-700 font-mono text-xs">{r.tel || '—'}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">{r.localisation || '—'}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">{r.detail_source || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// --- Search popup --------------------------------------------------------

function SearchPopup({
  onClose,
  onSearch,
}: {
  onClose: () => void
  onSearch: (body: any) => void
}) {
  const [mode, setMode] = useState<SearchMode>('cp')

  // Par CP
  const [ville, setVille] = useState('')
  const [communes, setCommunes] = useState<Commune[]>([])
  const [selectedCp, setSelectedCp] = useState<string>('')
  const [loadingCommunes, setLoadingCommunes] = useState(false)
  const [rayon, setRayon] = useState(30)
  const [ageMin, setAgeMin] = useState(0)
  const [ageMax, setAgeMax] = useState(100)
  const [anciennete, setAnciennete] = useState('')
  const [dateDebut, setDateDebut] = useState('')
  const [dateFin, setDateFin] = useState('')
  const [statut, setStatut] = useState(0)
  const [profil, setProfil] = useState<1 | 2 | 3>(1) // 1 ENI, 2 Fibre, 3 Les 2
  const [source, setSource] = useState(0)
  const [idCoopteur, setIdCoopteur] = useState('')
  const [nomCoopteur, setNomCoopteur] = useState('')
  const [idAnnonceur, setIdAnnonceur] = useState(0)

  // Par Tél
  const [tel, setTel] = useState('')

  // Par Nom
  const [nom, setNom] = useState('')
  const [prenom, setPrenom] = useState('')

  // Référentiels
  const [statuts, setStatuts] = useState<CvStatut[]>([])
  const [sources, setSources] = useState<CvSource[]>([])
  const [annonceurs, setAnnonceurs] = useState<CvAnnonceur[]>([])
  const [showCoopteurPicker, setShowCoopteurPicker] = useState(false)

  useEffect(() => {
    const headers = { Authorization: `Bearer ${getToken()}` }
    Promise.all([
      fetch('/api/vendeur/cvtheque/statuts', { headers }).then((r) => r.json()),
      fetch('/api/vendeur/cvtheque/sources', { headers }).then((r) => r.json()),
      fetch('/api/vendeur/cvtheque/annonceurs', { headers }).then((r) => r.json()),
    ]).then(([st, sr, an]) => {
      setStatuts(st)
      setSources(sr)
      setAnnonceurs(an)
    })
  }, [])

  // Recherche ville → CP
  const searchVille = () => {
    if (!ville.trim()) return
    setLoadingCommunes(true)
    fetch(`/api/vendeur/cvtheque/communes?ville=${encodeURIComponent(ville.trim())}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((data: Commune[]) => {
        setCommunes(data)
        if (data.length === 1) setSelectedCp(data[0].cp)
      })
      .catch(() => {})
      .finally(() => setLoadingCommunes(false))
  }

  // Anciennete → date range
  const applyAnciennete = (v: string) => {
    setAnciennete(v)
    const today = new Date()
    let deb = new Date(today)
    let fin = new Date(today)
    if (v === '7j') deb.setDate(deb.getDate() - 7)
    else if (v === '15j') deb.setDate(deb.getDate() - 15)
    else if (v === '-1m') deb.setMonth(deb.getMonth() - 1)
    else if (v === '+1m') {
      deb = new Date(1970, 0, 1)
      fin.setMonth(fin.getMonth() - 1)
    }
    setDateDebut(toISODate(deb))
    setDateFin(toISODate(fin))
  }

  const selectedCommune = communes.find((c) => c.cp === selectedCp)

  const handleSubmit = () => {
    const body: any = { mode }
    if (mode === 'cp') {
      if (!selectedCommune) return alert('Choisis une ville et un CP')
      body.latitude = selectedCommune.latitude
      body.longitude = selectedCommune.longitude
      body.rayon_km = rayon
      body.date_debut = dateDebut ? toYMD(new Date(dateDebut)) : ''
      body.date_fin = dateFin ? toYMD(new Date(dateFin)) : ''
      body.age_min = ageMin
      body.age_max = ageMax
      body.id_cv_source = source
      body.id_coopteur = idCoopteur
      body.id_annonceur = idAnnonceur
      body.profil = profil
      body.id_cv_statut = statut
    } else if (mode === 'tel') {
      body.tel = tel
    } else {
      body.nom = nom
      body.prenom = prenom
    }
    onSearch(body)
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 sticky top-0 bg-white z-10">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Filter className="w-5 h-5 text-gray-400" />
            Critères de recherche
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {/* Mode */}
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            {(['cp', 'tel', 'nom'] as SearchMode[]).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`flex-1 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                  mode === m ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
                }`}
              >
                Par {m === 'cp' ? 'CP' : m === 'tel' ? 'Téléphone' : 'Nom'}
              </button>
            ))}
          </div>

          {/* Mode CP */}
          {mode === 'cp' && (
            <>
              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                  Ville
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={ville}
                    onChange={(e) => setVille(e.target.value.toUpperCase())}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), searchVille())}
                    placeholder="NOM DE VILLE"
                    className="flex-1 px-3 py-2.5 border border-gray-300 rounded-lg text-sm uppercase placeholder:normal-case placeholder:text-gray-400"
                  />
                  <button
                    type="button"
                    onClick={searchVille}
                    className="px-3 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    {loadingCommunes ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4 text-gray-700" />}
                  </button>
                </div>
              </div>

              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                    CP
                  </label>
                  <select
                    value={selectedCp}
                    onChange={(e) => setSelectedCp(e.target.value)}
                    disabled={communes.length === 0}
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm disabled:bg-gray-50"
                  >
                    <option value="">--- Choisir un CP ---</option>
                    {communes.map((c) => (
                      <option key={c.cp} value={c.cp}>
                        {c.cp} {c.ville}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="w-24">
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                    Rayon (km)
                  </label>
                  <input
                    type="number"
                    value={rayon}
                    onChange={(e) => setRayon(parseInt(e.target.value) || 0)}
                    min={1}
                    max={200}
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                  Âge entre
                </label>
                <div className="flex gap-2 items-center">
                  <input
                    type="number"
                    value={ageMin}
                    onChange={(e) => setAgeMin(parseInt(e.target.value) || 0)}
                    className="w-20 px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                  />
                  <span className="text-sm text-gray-500">et</span>
                  <input
                    type="number"
                    value={ageMax}
                    onChange={(e) => setAgeMax(parseInt(e.target.value) || 100)}
                    className="w-20 px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                  Datant de
                </label>
                <select
                  value={anciennete}
                  onChange={(e) => applyAnciennete(e.target.value)}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                >
                  <option value="">--- Choisir la période ---</option>
                  <option value="7j">- de 7 jours</option>
                  <option value="15j">- de 15 jours</option>
                  <option value="-1m">- d'1 mois</option>
                  <option value="+1m">+ d'1 mois</option>
                </select>
              </div>

              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                    Entre le
                  </label>
                  <input
                    type="date"
                    value={dateDebut}
                    onChange={(e) => setDateDebut(e.target.value)}
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
                <div className="flex-1">
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                    Et le
                  </label>
                  <input
                    type="date"
                    value={dateFin}
                    onChange={(e) => setDateFin(e.target.value)}
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                  Statut
                </label>
                <select
                  value={statut}
                  onChange={(e) => setStatut(parseInt(e.target.value))}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                >
                  <option value={0}>--- Choisir un statut ---</option>
                  {statuts.map((s) => (
                    <option key={s.id_cv_statut} value={s.id_cv_statut}>
                      {s.lib_statut}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex gap-4">
                {([1, 2, 3] as const).map((p) => (
                  <label key={p} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input
                      type="radio"
                      name="profil"
                      checked={profil === p}
                      onChange={() => setProfil(p)}
                    />
                    {p === 1 ? 'ENI' : p === 2 ? 'FIBRE' : 'Les 2'}
                  </label>
                ))}
              </div>

              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                  Source
                </label>
                <select
                  value={source}
                  onChange={(e) => {
                    setSource(parseInt(e.target.value))
                    setIdCoopteur('')
                    setNomCoopteur('')
                    setIdAnnonceur(0)
                  }}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                >
                  <option value={0}>--- Choisir une source ---</option>
                  {sources.map((s) => (
                    <option key={s.id_cv_source} value={s.id_cv_source}>
                      {s.lib_source}
                    </option>
                  ))}
                </select>
              </div>

              {source === 1 && (
                <button
                  type="button"
                  onClick={() => setShowCoopteurPicker(true)}
                  className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 text-gray-900"
                >
                  {nomCoopteur || 'Choisir le coopteur'}
                </button>
              )}

              {source === 2 && (
                <select
                  value={idAnnonceur}
                  onChange={(e) => setIdAnnonceur(parseInt(e.target.value))}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                >
                  <option value={0}>-- Choisir un annonceur --</option>
                  {annonceurs.map((a) => (
                    <option key={a.id_cv_annonceur} value={a.id_cv_annonceur}>
                      {a.lib_annonceur}
                    </option>
                  ))}
                </select>
              )}
            </>
          )}

          {/* Mode Tél */}
          {mode === 'tel' && (
            <div>
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                Numéro de téléphone
              </label>
              <input
                type="tel"
                value={tel}
                onChange={(e) => setTel(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleSubmit())}
                placeholder="06 12 34 56 78"
                autoFocus
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
              />
            </div>
          )}

          {/* Mode Nom */}
          {mode === 'nom' && (
            <>
              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                  Nom
                </label>
                <input
                  type="text"
                  value={nom}
                  onChange={(e) => setNom(e.target.value)}
                  placeholder="TOUT EN MAJUSCULE (SANS ACCENT)"
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                  Prénom
                </label>
                <input
                  type="text"
                  value={prenom}
                  onChange={(e) => setPrenom(e.target.value)}
                  placeholder="TOUT EN MAJUSCULE (SANS ACCENT)"
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                />
              </div>
            </>
          )}

          <button
            type="button"
            onClick={handleSubmit}
            className="w-full px-3 py-2.5 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 flex items-center justify-center gap-2"
          >
            <Search className="w-4 h-4" />
            Démarrer la recherche
          </button>
        </div>
      </motion.div>

      <AnimatePresence>
        {showCoopteurPicker && (
          <CoopteurPicker
            onClose={() => setShowCoopteurPicker(false)}
            onSelect={(v) => {
              setIdCoopteur(v.id_salarie)
              setNomCoopteur(`${v.nom} ${capitalize(v.prenom)}`)
              setShowCoopteurPicker(false)
            }}
          />
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function CoopteurPicker({
  onClose,
  onSelect,
}: {
  onClose: () => void
  onSelect: (v: VendeurItem) => void
}) {
  const [search, setSearch] = useState('')
  const [results, setResults] = useState<VendeurItem[]>([])
  const [selected, setSelected] = useState<VendeurItem | null>(null)
  const [loading, setLoading] = useState(false)

  const doSearch = () => {
    if (!search.trim()) return
    setLoading(true)
    fetch(`/api/vendeur/cooptation/vendeurs?q=${encodeURIComponent(search.trim())}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then(setResults)
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Choisir le coopteur</h2>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 space-y-3">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Nom du coopteur"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), doSearch())}
              autoFocus
              className="flex-1 px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
            />
            <button type="button" onClick={doSearch} className="px-3 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4 text-gray-700" />}
            </button>
          </div>
          <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-lg">
            {results.length === 0 ? (
              <div className="text-center py-8 text-gray-400 text-sm">{loading ? '' : 'Saisis un nom pour rechercher'}</div>
            ) : (
              results.map((v) => (
                <button
                  key={v.id_salarie}
                  type="button"
                  onClick={() => setSelected(v)}
                  className={`w-full text-left px-4 py-2.5 text-sm border-b border-gray-100 last:border-0 hover:bg-gray-50 ${
                    selected?.id_salarie === v.id_salarie ? 'bg-gray-100' : ''
                  }`}
                >
                  <span className="font-medium text-gray-900">{v.nom}</span>{' '}
                  <span className="text-gray-600">{capitalize(v.prenom)}</span>
                </button>
              ))
            )}
          </div>
          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={() => selected && onSelect(selected)}
              disabled={!selected}
              className="flex-1 px-3 py-2.5 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50"
            >
              Valider
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-3 py-2.5 border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50"
            >
              Annuler
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

const QUICK_ACTIONS: {
  label: string
  statut: number
  auto_obser?: string
  color: string
}[] = [
  { label: 'À recontacter', statut: 2, color: 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100' },
  { label: 'Étudiant', statut: 9, color: 'bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100' },
  { label: 'Hors cible', statut: 7, color: 'bg-orange-50 text-orange-700 border-orange-200 hover:bg-orange-100' },
  { label: 'Msg rép.', statut: 3, auto_obser: 'MESSAGE REP', color: 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100' },
  { label: 'Refus RH', statut: 5, color: 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100' },
  { label: 'Refus candidat', statut: 4, color: 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100' },
]

// --- Fiche modal ----------------------------------------------------------

function FicheModal({
  idCvtheque,
  onClose,
  onUpdated,
}: {
  idCvtheque: string
  onClose: () => void
  onUpdated?: (id: string, patch: Partial<CvResult>) => void
}) {
  const [data, setData] = useState<CvFicheResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`/api/vendeur/cvtheque/${idCvtheque}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then(setData)
      .finally(() => setLoading(false))

    // Verrouille le CV
    fetch(`/api/vendeur/cvtheque/${idCvtheque}/traitement`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify({ is_traite: true }),
    })

    // Libère à la fermeture
    return () => {
      fetch(`/api/vendeur/cvtheque/${idCvtheque}/traitement`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ is_traite: false }),
      })
    }
  }, [idCvtheque])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.97, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.97, y: 10 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-gradient-to-b from-gray-50 to-white rounded-2xl shadow-2xl w-full max-w-5xl max-h-[92vh] overflow-hidden flex flex-col"
      >
        {loading || !data ? (
          <div className="flex items-center justify-center py-32">
            <Loader2 className="w-8 h-8 text-gray-300 animate-spin" />
          </div>
        ) : (
          <FicheContent data={data} onClose={onClose} onUpdated={onUpdated} />
        )}
      </motion.div>
    </motion.div>
  )
}

function FicheContent({
  data,
  onClose,
  onUpdated,
}: {
  data: CvFicheResponse
  onClose: () => void
  onUpdated?: (id: string, patch: Partial<CvResult>) => void
}) {
  const { fiche: fiche0, suivi: suivi0 } = data
  const [fiche, setFiche] = useState<CvFiche>(fiche0)
  const [suivi, setSuivi] = useState<CvSuiviItem[]>(suivi0)
  const [saisirObser, setSaisirObser] = useState('')
  const [nouveauStatut, setNouveauStatut] = useState<number>(fiche0.id_cv_statut || 0)
  const [statuts, setStatuts] = useState<CvStatut[]>([])
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState('')
  const [showRdv, setShowRdv] = useState(false)

  useEffect(() => {
    fetch('/api/vendeur/cvtheque/statuts', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then(setStatuts)
      .catch(() => {})
  }, [])

  const fullName =
    `${fiche.nom} ${capitalize(fiche.prenom)}`.trim() || 'Candidat'
  const initials = (fiche.nom[0] || '') + (fiche.prenom[0] || '')

  const update = (patch: Partial<CvFiche>) => setFiche((f) => ({ ...f, ...patch }))

  const handleAddObservation = async () => {
    const text = saisirObser.trim()
    if (!text) return
    setSaving(true)
    try {
      const res = await fetch(
        `/api/vendeur/cvtheque/${fiche.id_cvtheque}/observation`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({ observation: text }),
        }
      )
      const body = await res.json()
      if (body.ok) {
        update({ observation: body.observation })
        setSaisirObser('')
        setToast('Observation ajoutée')
        setTimeout(() => setToast(''), 1500)
      }
    } catch (e) {
      console.error(e)
      alert("Erreur lors de l'ajout")
    } finally {
      setSaving(false)
    }
  }

  const handleQuickSave = async (newStatut: number, autoObser: string) => {
    if (!fiche.id_communes_france) {
      alert('Merci de choisir une ville valide')
      return
    }
    setSaving(true)
    try {
      const ancien = fiche0.id_cv_statut
      const res = await fetch(
        `/api/vendeur/cvtheque/${fiche.id_cvtheque}/save?ancien_statut=${ancien}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({
            nom: fiche.nom,
            prenom: fiche.prenom,
            pays: fiche.pays,
            adresse: fiche.adresse,
            id_communes_france: fiche.id_communes_france,
            date_naissance: fiche.date_naissance,
            permis_b: fiche.permis_b,
            vehicule: fiche.vehicule,
            mail: fiche.mail,
            gsm: fiche.gsm,
            id_cv_poste: fiche.id_cv_poste,
            id_cv_source: fiche.id_cv_source,
            id_elem_source: fiche.id_elem_source,
            id_ste: fiche.id_ste,
            observation: fiche.observation,
            saisir_obser: autoObser,
            id_cv_statut: newStatut,
            confirm_statut_6: false,
          }),
        }
      )
      await res.json()
      setToast('Statut mis à jour')
      setTimeout(() => setToast(''), 1500)
      const refreshed = await fetch(
        `/api/vendeur/cvtheque/${fiche.id_cvtheque}`,
        { headers: { Authorization: `Bearer ${getToken()}` } }
      ).then((r) => r.json())
      setFiche(refreshed.fiche)
      setSuivi(refreshed.suivi)
      setSaisirObser('')
      setNouveauStatut(refreshed.fiche.id_cv_statut)
      onUpdated?.(refreshed.fiche.id_cvtheque, {
        statut_actuel: refreshed.fiche.id_cv_statut,
        statut_actuel_lib: refreshed.suivi[0]?.statut_lib || '',
      })
    } catch (e) {
      console.error(e)
      alert('Erreur lors du changement de statut')
    } finally {
      setSaving(false)
    }
  }

  const handleSave = async (confirmStatut6 = false) => {
    if (!fiche.id_communes_france) {
      alert('Merci de choisir une ville valide')
      return
    }
    setSaving(true)
    try {
      const ancien = fiche0.id_cv_statut
      const res = await fetch(
        `/api/vendeur/cvtheque/${fiche.id_cvtheque}/save?ancien_statut=${ancien}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({
            nom: fiche.nom,
            prenom: fiche.prenom,
            pays: fiche.pays,
            adresse: fiche.adresse,
            id_communes_france: fiche.id_communes_france,
            date_naissance: fiche.date_naissance,
            permis_b: fiche.permis_b,
            vehicule: fiche.vehicule,
            mail: fiche.mail,
            gsm: fiche.gsm,
            id_cv_poste: fiche.id_cv_poste,
            id_cv_source: fiche.id_cv_source,
            id_elem_source: fiche.id_elem_source,
            id_ste: fiche.id_ste,
            observation: fiche.observation,
            saisir_obser: saisirObser,
            id_cv_statut: nouveauStatut,
            confirm_statut_6: confirmStatut6,
          }),
        }
      )
      const body = await res.json()
      if (body.need_confirm_statut6) {
        if (
          window.confirm(
            "Vous êtes sur le point de statuer ce RDV en 'Entretien planifié' sans passer par la prise de RDV. Voulez-vous continuer ?"
          )
        ) {
          return handleSave(true)
        }
        return
      }
      setToast('Modifications enregistrées')
      setTimeout(() => setToast(''), 2000)

      // Recharge la fiche
      const refreshed = await fetch(
        `/api/vendeur/cvtheque/${fiche.id_cvtheque}`,
        { headers: { Authorization: `Bearer ${getToken()}` } }
      ).then((r) => r.json())
      setFiche(refreshed.fiche)
      setSuivi(refreshed.suivi)
      setSaisirObser('')
      setNouveauStatut(refreshed.fiche.id_cv_statut)
      onUpdated?.(refreshed.fiche.id_cvtheque, {
        identite: `${refreshed.fiche.nom} ${capitalize(refreshed.fiche.prenom)}`.trim(),
        tel: refreshed.fiche.gsm,
        age: refreshed.fiche.age,
        statut_actuel: refreshed.fiche.id_cv_statut,
        statut_actuel_lib: refreshed.suivi[0]?.statut_lib || '',
      })
    } catch (e) {
      console.error(e)
      alert("Erreur lors de l'enregistrement")
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      {/* Header */}
      <div className="flex items-start gap-5 px-8 py-6 border-b border-gray-200 bg-white">
        <div className="w-14 h-14 rounded-full bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center text-white text-lg font-bold shrink-0">
          {initials.toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="text-xl font-bold text-gray-900 truncate">{fullName}</h2>
          <div className="flex items-center gap-4 mt-1 text-xs text-gray-500 flex-wrap">
            {fiche.age > 0 && (
              <span className="flex items-center gap-1">
                <CalendarIcon className="w-3 h-3" />
                {fiche.age} ans
              </span>
            )}
            {fiche.ville && (
              <span className="flex items-center gap-1">
                <MapPin className="w-3 h-3" />
                {fiche.cp} {fiche.ville}
              </span>
            )}
            {fiche.id_cv_source === 1 && fiche.nom_coopteur && (
              <span className="flex items-center gap-1">
                <User className="w-3 h-3" />
                Coopté par {fiche.nom_coopteur}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {fiche.cv_url && (
            <a
              href={fiche.cv_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50"
            >
              <FileText className="w-4 h-4" />
              CV
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-8 py-6 space-y-6">

        {/* Grid 2 colonnes */}
        <div className="grid grid-cols-2 gap-6">
          {/* Identité */}
          <Section title="Identité" icon={<User className="w-4 h-4" />}>
            <div className="grid grid-cols-2 gap-x-4 gap-y-3">
              <EditField label="Nom" value={fiche.nom} onChange={(v) => update({ nom: v })} />
              <EditField label="Prénom" value={fiche.prenom} onChange={(v) => update({ prenom: v })} />
              <EditField
                label="Date naissance"
                type="date"
                value={fiche.date_naissance ? fiche.date_naissance.slice(0, 10) : ''}
                onChange={(v) => update({ date_naissance: v })}
              />
              <div>
                <div className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">
                  Âge
                </div>
                <div className="text-sm text-gray-700 pt-2">{fiche.age || '—'}</div>
              </div>
              <div className="col-span-2 flex gap-4">
                <Toggle
                  label="Permis B"
                  on={fiche.permis_b}
                  onChange={(v) => update({ permis_b: v })}
                />
                <Toggle
                  label="Véhicule"
                  on={fiche.vehicule}
                  onChange={(v) => update({ vehicule: v })}
                />
              </div>
            </div>
          </Section>

          <Section title="Contact" icon={<Phone className="w-4 h-4" />}>
            <div className="space-y-3">
              <EditFieldCopy
                label="Mobile"
                value={fiche.gsm}
                onChange={(v) => update({ gsm: v })}
                onCopied={() => {
                  setToast('Mobile copié')
                  setTimeout(() => setToast(''), 1500)
                }}
                type="tel"
              />
              <EditFieldCopy
                label="Email"
                value={fiche.mail}
                onChange={(v) => update({ mail: v })}
                onCopied={() => {
                  setToast('Email copié')
                  setTimeout(() => setToast(''), 1500)
                }}
                type="email"
              />
              <EditField
                label="Adresse"
                value={fiche.adresse}
                onChange={(v) => update({ adresse: v })}
              />
              <div className="grid grid-cols-[auto,1fr] gap-3 items-end">
                <div>
                  <div className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">
                    CP
                  </div>
                  <div className="text-sm text-gray-900 px-3 py-2 bg-gray-50 rounded-lg w-20 text-center font-mono">
                    {fiche.cp || '—'}
                  </div>
                </div>
                <div>
                  <div className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">
                    Ville
                  </div>
                  <div className="text-sm text-gray-900 px-3 py-2 bg-gray-50 rounded-lg">
                    {fiche.ville || '—'}
                  </div>
                </div>
              </div>
            </div>
          </Section>

          <Section title="Recrutement" icon={<FileText className="w-4 h-4" />}>
            <div className="space-y-3">
              <Field label="Poste visé" value={posteLabel(fiche.id_cv_poste)} />
              <Field label="Source" value={sourceLabel(fiche.id_cv_source)} />
              {fiche.id_cv_source === 1 && (
                <Field label="Coopteur" value={fiche.nom_coopteur || '—'} />
              )}
            </div>
          </Section>

          <Section title="Statut" icon={<Home className="w-4 h-4" />}>
            <div className="space-y-3">
              <div>
                <div className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">
                  Statut actuel
                </div>
                <select
                  value={nouveauStatut}
                  onChange={(e) => setNouveauStatut(parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
                >
                  <option value={0}>—</option>
                  {statuts.map((s) => (
                    <option key={s.id_cv_statut} value={s.id_cv_statut}>
                      {s.lib_statut}
                    </option>
                  ))}
                </select>
                {nouveauStatut !== fiche0.id_cv_statut && nouveauStatut !== 0 && (
                  <div className="text-xs text-amber-600 mt-1.5">
                    ⚠ Le statut sera modifié à l'enregistrement
                  </div>
                )}
              </div>
              {suivi[0] && (
                <Field
                  label="Mis à jour"
                  value={`${formatDate(suivi[0].datecrea)} par ${suivi[0].op_crea_nom}`}
                />
              )}
            </div>
          </Section>
        </div>

        {/* Observation + saisir obser */}
        <Section title="Observations" icon={<FileText className="w-4 h-4" />}>
          <div className="space-y-3">
            {fiche.observation && (
              <div className="text-sm text-gray-700 whitespace-pre-line leading-relaxed bg-gray-50 rounded-lg p-3 max-h-40 overflow-y-auto">
                {fiche.observation}
              </div>
            )}
            <div>
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                Ajouter une observation
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={saisirObser}
                  onChange={(e) => setSaisirObser(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddObservation())}
                  placeholder="Nouvelle observation..."
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
                <button
                  type="button"
                  onClick={handleAddObservation}
                  disabled={!saisirObser.trim() || saving}
                  className="px-3 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Ajouter l'observation"
                >
                  <Check className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </Section>

        {/* Quick actions (statuage rapide) */}
        <div>
          <div className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">
            Statuer rapidement
          </div>
          <div className="flex flex-wrap gap-2">
            {QUICK_ACTIONS.map((b) => (
              <button
                key={b.label}
                disabled={saving}
                onClick={() => {
                  if (!window.confirm('Voulez-vous statuer ce CV ?')) return
                  setNouveauStatut(b.statut)
                  if (b.auto_obser) setSaisirObser(b.auto_obser)
                  setTimeout(() => handleQuickSave(b.statut, b.auto_obser || ''), 0)
                }}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${b.color} disabled:opacity-50`}
              >
                {b.label}
              </button>
            ))}
          </div>
        </div>

        {/* Historique */}
        <Section title={`Historique (${suivi.length})`} icon={<CalendarIcon className="w-4 h-4" />}>
          {suivi.length === 0 ? (
            <div className="text-center py-6 text-gray-400 text-sm italic">Aucun suivi</div>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto pr-2">
              {suivi.map((s) => (
                <div
                  key={s.id_cv_suivi}
                  className="bg-white border border-gray-200 rounded-lg p-3 hover:border-gray-300 transition-colors"
                >
                  <div className="flex items-center justify-between gap-3 mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded-full bg-gray-100 text-xs font-medium text-gray-700">
                        {s.statut_lib || 'Statut inconnu'}
                      </span>
                      {s.type_elem && (
                        <span className="text-xs text-gray-400">· {s.type_elem}</span>
                      )}
                    </div>
                    <div className="text-xs text-gray-400">{formatDate(s.datecrea)}</div>
                  </div>
                  <div className="text-xs text-gray-600 mb-1">par {s.op_crea_nom}</div>
                  {s.observation && (
                    <div className="text-xs text-gray-700 mt-1 whitespace-pre-line">
                      {s.observation}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Section>
      </div>

      {/* Modal Planifier RDV */}
      <AnimatePresence>
        {showRdv && (
          <PriseRdvModal
            fiche={fiche}
            onClose={() => setShowRdv(false)}
            onDone={() => {
              setShowRdv(false)
              setToast('RDV planifié')
              setTimeout(() => setToast(''), 2000)
              // Refresh
              fetch(`/api/vendeur/cvtheque/${fiche.id_cvtheque}`, {
                headers: { Authorization: `Bearer ${getToken()}` },
              })
                .then((r) => r.json())
                .then((d) => {
                  setFiche(d.fiche)
                  setSuivi(d.suivi)
                  onUpdated?.(d.fiche.id_cvtheque, {
                    statut_actuel: d.fiche.id_cv_statut,
                    statut_actuel_lib: d.suivi[0]?.statut_lib || '',
                  })
                })
            }}
          />
        )}
      </AnimatePresence>

      {/* Toast */}
      {toast && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          className="absolute bottom-24 left-1/2 -translate-x-1/2 bg-emerald-600 text-white px-4 py-2 rounded-lg shadow-lg text-sm font-medium z-10"
        >
          {toast}
        </motion.div>
      )}

      {/* Footer actions */}
      <div className="px-8 py-4 border-t border-gray-200 bg-white flex items-center justify-between gap-3">
        <div className="text-xs text-gray-400">ID : {fiche.id_cvtheque}</div>
        <div className="flex gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50"
          >
            Fermer
          </button>
          <button
            onClick={() => setShowRdv(true)}
            className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <CalendarIcon className="w-4 h-4" />
            Planifier un RDV
          </button>
          <button
            onClick={() => handleSave(false)}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Enregistrer
          </button>
        </div>
      </div>
    </>
  )
}

function EditField({
  label,
  value,
  onChange,
  type = 'text',
}: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
}) {
  return (
    <div>
      <div className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">
        {label}
      </div>
      <input
        type={type}
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
      />
    </div>
  )
}

function EditFieldCopy({
  label,
  value,
  onChange,
  onCopied,
  type = 'text',
}: {
  label: string
  value: string
  onChange: (v: string) => void
  onCopied: () => void
  type?: string
}) {
  const handleCopy = async () => {
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
      onCopied()
    } catch {
      // Fallback
      const ta = document.createElement('textarea')
      ta.value = value
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      onCopied()
    }
  }

  return (
    <div>
      <div className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">
        {label}
      </div>
      <div className="flex gap-2">
        <input
          type={type}
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
        />
        <button
          type="button"
          onClick={handleCopy}
          disabled={!value}
          title="Copier"
          className="px-2.5 py-2 border border-gray-300 rounded-lg text-gray-500 hover:bg-gray-50 hover:text-gray-900 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Copy className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

function Toggle({
  label,
  on,
  onChange,
}: {
  label: string
  on: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={on}
        onChange={(e) => onChange(e.target.checked)}
        className="sr-only"
      />
      <span
        className={`w-9 h-5 rounded-full transition-colors relative ${on ? 'bg-emerald-500' : 'bg-gray-300'}`}
      >
        <span
          className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${on ? 'translate-x-4' : 'translate-x-0.5'}`}
        />
      </span>
      <span className="text-sm text-gray-700">{label}</span>
    </label>
  )
}

// --- Sub-components for fiche --------------------------------------------

function Section({
  title,
  icon,
  children,
}: {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="flex items-center gap-2 text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">
        <span className="text-gray-400">{icon}</span>
        {title}
      </h3>
      {children}
    </div>
  )
}

function Field({
  label,
  value,
}: {
  label: string
  value: React.ReactNode
}) {
  return (
    <div>
      <div className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-0.5">
        {label}
      </div>
      <div className="text-sm text-gray-900">{value || '—'}</div>
    </div>
  )
}

// --- Prise de RDV modal --------------------------------------------------

interface SessionItem {
  id_prevision_recrut: string
  date_session: string
  nom_ville: string
  label: string
  id_recruteur: string
  recruteur_nom: string
  id_lieu_rdv: number
}

interface LieuRdvItem {
  id_cv_lieu_rdv: number
  lib_lieu: string
}

interface LieuRdvInfo extends LieuRdvItem {
  adresse1: string
  adresse2: string
  cp: string
  nom_ville: string
  latitude: number
  longitude: number
}

interface SalonVisioItem {
  id_salon_visio: string
  lib_salon: string
}

interface SalonVisioInfo extends SalonVisioItem {
  lien: string
  id_reunion: string
  mdp: string
}

interface AgendaRdv {
  id_evenement: string
  date_debut: string
  date_fin: string
  titre: string
  lib_categorie: string
  couleur_hex: string
}

function PriseRdvModal({
  fiche,
  onClose,
  onDone,
}: {
  fiche: CvFiche
  onClose: () => void
  onDone: () => void
}) {
  const stored = getStoredUser()
  const [sessions, setSessions] = useState<SessionItem[]>([])
  const [lieux, setLieux] = useState<LieuRdvItem[]>([])
  const [idSession, setIdSession] = useState<string>('')
  const [recruteurId, setRecruteurId] = useState<string>(
    stored?.id_salarie ? String(stored.id_salarie) : ''
  )
  const [recruteurName, setRecruteurName] = useState<string>(
    stored ? `${stored.nom} ${capitalize(stored.prenom)}` : ''
  )
  const [showRecruteurPicker, setShowRecruteurPicker] = useState(false)
  const [dateRdv, setDateRdv] = useState<string>('')
  const [heureRdv, setHeureRdv] = useState<string>('15:00')
  const [typeEntretien, setTypeEntretien] = useState<'Physique' | 'Visio'>('Physique')
  const [idLieu, setIdLieu] = useState<number>(0)
  const [lieuInfo, setLieuInfo] = useState<LieuRdvInfo | null>(null)
  const [salons, setSalons] = useState<SalonVisioItem[]>([])
  const [idSalon, setIdSalon] = useState<string>('')
  const [salonInfo, setSalonInfo] = useState<SalonVisioInfo | null>(null)
  const [envoyerSms, setEnvoyerSms] = useState(true)
  const [gsm, setGsm] = useState(fiche.gsm)
  const [mail, setMail] = useState(fiche.mail)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [dayRdvs, setDayRdvs] = useState<AgendaRdv[]>([])
  const [loadingAgenda, setLoadingAgenda] = useState(false)

  // Charge sessions + lieux
  useEffect(() => {
    const h = { Authorization: `Bearer ${getToken()}` }
    fetch('/api/vendeur/cvtheque/rdv/sessions', { headers: h })
      .then((r) => r.json())
      .then(setSessions)
      .catch(() => {})
    fetch('/api/vendeur/cvtheque/rdv/lieux', { headers: h })
      .then((r) => r.json())
      .then(setLieux)
      .catch(() => {})
  }, [])

  // Salons visio par recruteur
  useEffect(() => {
    if (typeEntretien !== 'Visio' || !recruteurId) return
    fetch(
      `/api/vendeur/cvtheque/rdv/salons-visio?id_salarie=${recruteurId}`,
      { headers: { Authorization: `Bearer ${getToken()}` } }
    )
      .then((r) => r.json())
      .then(setSalons)
      .catch(() => {})
  }, [typeEntretien, recruteurId])

  // Info lieu
  useEffect(() => {
    if (!idLieu) {
      setLieuInfo(null)
      return
    }
    fetch(`/api/vendeur/cvtheque/rdv/lieux/${idLieu}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then(setLieuInfo)
      .catch(() => setLieuInfo(null))
  }, [idLieu])

  // Info salon
  useEffect(() => {
    if (!idSalon) {
      setSalonInfo(null)
      return
    }
    fetch(`/api/vendeur/cvtheque/rdv/salons-visio/${idSalon}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then(setSalonInfo)
      .catch(() => setSalonInfo(null))
  }, [idSalon])

  // Agenda du recruteur pour la date choisie
  useEffect(() => {
    if (!recruteurId || !dateRdv) {
      setDayRdvs([])
      return
    }
    const ymd = dateRdv.replace(/-/g, '')
    setLoadingAgenda(true)
    fetch(
      `/api/vendeur/agenda-recrutement?id_recruteur=${recruteurId}&date_from=${ymd}&date_to=${ymd}`,
      { headers: { Authorization: `Bearer ${getToken()}` } }
    )
      .then((r) => r.json())
      .then((d) => setDayRdvs(Array.isArray(d) ? d : []))
      .catch(() => setDayRdvs([]))
      .finally(() => setLoadingAgenda(false))
  }, [recruteurId, dateRdv])

  const handleSubmit = async () => {
    setError('')
    if (!recruteurId) return setError('Recruteur requis')
    if (!dateRdv || !heureRdv) return setError('Date et heure requises')
    if (typeEntretien === 'Physique' && !idLieu) return setError('Lieu requis')
    if (typeEntretien === 'Visio' && !idSalon) return setError('Salon visio requis')

    const when = `${dateRdv} à ${heureRdv} avec ${recruteurName}`
    if (!window.confirm(`Voulez-vous planifier ce RDV ?\n\n${when}`)) return

    setSubmitting(true)
    try {
      const res = await fetch('/api/vendeur/cvtheque/rdv', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id_cvtheque: fiche.id_cvtheque,
          id_recruteur: recruteurId,
          id_session: idSession || '0',
          date_rdv: dateRdv,
          heure_rdv: heureRdv,
          type_entretien: typeEntretien,
          id_lieu_rdv: idLieu,
          id_salon_visio: idSalon || '0',
          envoyer_sms: envoyerSms,
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Erreur')
      }
      onDone()
    } catch (e: any) {
      setError(e.message || 'Erreur')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl max-h-[92vh] overflow-hidden flex flex-col"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <CalendarIcon className="w-5 h-5 text-gray-400" />
            Planifier un RDV
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div
          className="flex-1 overflow-hidden grid"
          style={{ gridTemplateColumns: 'minmax(0, 420px) minmax(0, 1fr)' }}
        >
          <div className="p-6 space-y-4 overflow-y-auto border-r border-gray-200">
          <div className="bg-gray-50 rounded-lg px-3 py-2 text-sm">
            <span className="text-gray-500">Candidat :</span>{' '}
            <span className="font-semibold text-gray-900">
              {fiche.nom} {capitalize(fiche.prenom)}
            </span>
          </div>

          {/* Session */}
          <div>
            <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
              Session (optionnel)
            </label>
            <select
              value={idSession}
              onChange={(e) => {
                const v = e.target.value
                setIdSession(v)
                if (!v) return
                const s = sessions.find((x) => x.id_prevision_recrut === v)
                if (!s) return
                // Pré-remplir depuis la session
                if (s.id_recruteur && s.id_recruteur !== '0') {
                  setRecruteurId(s.id_recruteur)
                  setRecruteurName(s.recruteur_nom)
                }
                // Date : format ISO ou WinDev → YYYY-MM-DD
                const ds = s.date_session
                if (ds) {
                  if (ds.includes('-')) {
                    setDateRdv(ds.slice(0, 10))
                  } else if (/^\d{8}/.test(ds)) {
                    setDateRdv(`${ds.slice(0, 4)}-${ds.slice(4, 6)}-${ds.slice(6, 8)}`)
                  }
                }
                if (s.id_lieu_rdv === 1) {
                  setTypeEntretien('Visio')
                  setIdLieu(0)
                } else if (s.id_lieu_rdv > 0) {
                  setTypeEntretien('Physique')
                  setIdLieu(s.id_lieu_rdv)
                }
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">--- Choisir une session ---</option>
              {sessions.map((s) => (
                <option key={s.id_prevision_recrut} value={s.id_prevision_recrut}>
                  {s.label}
                  {s.recruteur_nom ? ` · ${s.recruteur_nom}` : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Recruteur */}
          <div>
            <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
              Recruteur
            </label>
            <button
              type="button"
              onClick={() => setShowRecruteurPicker(true)}
              className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 text-left"
            >
              {recruteurName || 'Choisir le recruteur'}
            </button>
          </div>

          {/* Date + Heure */}
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                Date
              </label>
              <input
                type="date"
                value={dateRdv}
                onChange={(e) => setDateRdv(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>
            <div className="w-28">
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                Heure
              </label>
              <input
                type="time"
                value={heureRdv}
                onChange={(e) => setHeureRdv(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>
          </div>

          {/* Type entretien */}
          <div className="flex gap-4">
            {(['Physique', 'Visio'] as const).map((t) => (
              <label key={t} className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="radio"
                  name="typeEntretien"
                  checked={typeEntretien === t}
                  onChange={() => setTypeEntretien(t)}
                />
                RDV {t === 'Physique' ? 'physique' : t}
              </label>
            ))}
          </div>

          {/* Lieu ou Visio */}
          {typeEntretien === 'Physique' && (
            <div>
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                Lieu
              </label>
              <select
                value={idLieu}
                onChange={(e) => setIdLieu(parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              >
                <option value={0}>--- Choisir un lieu ---</option>
                {lieux.map((l) => (
                  <option key={l.id_cv_lieu_rdv} value={l.id_cv_lieu_rdv}>
                    {l.lib_lieu}
                  </option>
                ))}
              </select>
              {lieuInfo && (
                <div className="bg-gray-50 rounded-lg p-3 mt-2 text-xs text-gray-700 space-y-0.5">
                  <div className="font-semibold">{lieuInfo.lib_lieu}</div>
                  <div>{lieuInfo.adresse1}</div>
                  {lieuInfo.adresse2 && <div>{lieuInfo.adresse2}</div>}
                  <div>
                    {lieuInfo.cp} {lieuInfo.nom_ville}
                  </div>
                  {lieuInfo.latitude && lieuInfo.longitude && (
                    <a
                      href={`https://www.google.com/maps/?q=${lieuInfo.latitude},${lieuInfo.longitude}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-blue-600 hover:underline pt-1"
                    >
                      <MapPin className="w-3 h-3" />
                      Afficher sur Maps
                    </a>
                  )}
                </div>
              )}
            </div>
          )}

          {typeEntretien === 'Visio' && (
            <div>
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                Salon visio
              </label>
              <select
                value={idSalon}
                onChange={(e) => setIdSalon(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              >
                <option value="">--- Choisir un salon ---</option>
                {salons.map((s) => (
                  <option key={s.id_salon_visio} value={s.id_salon_visio}>
                    {s.lib_salon}
                  </option>
                ))}
              </select>
              {salonInfo && (
                <div className="bg-gray-50 rounded-lg p-3 mt-2 text-xs text-gray-700 space-y-1">
                  <div className="font-semibold">{salonInfo.lib_salon}</div>
                  {salonInfo.lien && (
                    <div className="truncate">
                      <span className="text-gray-500">Lien :</span>{' '}
                      <a href={salonInfo.lien} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                        {salonInfo.lien}
                      </a>
                    </div>
                  )}
                  {salonInfo.id_reunion && (
                    <div>
                      <span className="text-gray-500">ID :</span> {salonInfo.id_reunion}
                    </div>
                  )}
                  {salonInfo.mdp && (
                    <div>
                      <span className="text-gray-500">Code :</span> {salonInfo.mdp}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Envoi SMS */}
          <label className="flex items-center gap-2 text-sm cursor-pointer pt-1">
            <input
              type="checkbox"
              checked={envoyerSms}
              onChange={(e) => setEnvoyerSms(e.target.checked)}
            />
            Envoyer un SMS de confirmation
          </label>

          {/* Mobile + Mail récap */}
          <div className="space-y-2">
            <div>
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                Mobile
              </label>
              <input
                type="tel"
                value={gsm}
                onChange={(e) => setGsm(e.target.value)}
                disabled
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50 text-gray-500"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
                Email
              </label>
              <input
                type="email"
                value={mail}
                onChange={(e) => setMail(e.target.value)}
                disabled
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50 text-gray-500"
              />
            </div>
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-3 py-2.5 border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50"
            >
              Retour fiche CV
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={submitting}
              className="flex-1 px-3 py-2.5 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
              Valider le RDV
            </button>
          </div>
          </div>

          {/* Panneau agenda du recruteur */}
          <div className="bg-gray-50 overflow-y-auto">
            <AgendaPreview
              dayRdvs={dayRdvs}
              dateRdv={dateRdv}
              heureRdv={heureRdv}
              onPickHour={setHeureRdv}
              loading={loadingAgenda}
              recruteurName={recruteurName}
            />
          </div>
        </div>
      </motion.div>

      <AnimatePresence>
        {showRecruteurPicker && (
          <CoopteurPicker
            onClose={() => setShowRecruteurPicker(false)}
            onSelect={(v) => {
              setRecruteurId(v.id_salarie)
              setRecruteurName(`${v.nom} ${capitalize(v.prenom)}`)
              setShowRecruteurPicker(false)
              setIdSalon('')
              setSalonInfo(null)
            }}
          />
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function AgendaPreview({
  dayRdvs,
  dateRdv,
  heureRdv,
  onPickHour,
  loading,
  recruteurName,
}: {
  dayRdvs: AgendaRdv[]
  dateRdv: string
  heureRdv: string
  onPickHour: (h: string) => void
  loading: boolean
  recruteurName: string
}) {
  // Créneaux de 30 min de 08:00 à 20:00
  const HOURS = Array.from({ length: 25 }, (_, i) => {
    const h = 8 + Math.floor(i / 2)
    const m = i % 2 === 0 ? '00' : '30'
    return `${String(h).padStart(2, '0')}:${m}`
  })

  const parseTime = (raw: string): { start: number; end: number } | null => {
    const iso = raw.match(/^\d{4}-\d{2}-\d{2}[T ](\d{2}):(\d{2})/)
    if (!iso) return null
    const startMin = parseInt(iso[1]) * 60 + parseInt(iso[2])
    return { start: startMin, end: startMin }
  }

  // Pour chaque RDV, calculer start/end en minutes
  const blocks = dayRdvs
    .map((rdv) => {
      const s = parseTime(rdv.date_debut)
      const e = parseTime(rdv.date_fin)
      if (!s) return null
      return {
        rdv,
        start_min: s.start,
        end_min: e?.start || s.start + 30,
      }
    })
    .filter((b): b is { rdv: AgendaRdv; start_min: number; end_min: number } => b !== null)

  const SLOT_PX = 32 // 30min = 32px
  const BASE_MIN = 8 * 60 // 08:00
  const TOTAL_MIN = 12 * 60 // 08:00 → 20:00

  // Position du créneau sélectionné
  let selectedMin = 0
  const selMatch = heureRdv.match(/^(\d{2}):(\d{2})/)
  if (selMatch) selectedMin = parseInt(selMatch[1]) * 60 + parseInt(selMatch[2])

  const formatDayFr = (ymd: string) => {
    if (!ymd) return ''
    try {
      const d = new Date(ymd)
      return d.toLocaleDateString('fr-FR', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
      })
    } catch {
      return ymd
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">Agenda</div>
          <div className="text-sm font-semibold text-gray-900 mt-0.5 capitalize">
            {dateRdv ? formatDayFr(dateRdv) : '— choisis une date —'}
          </div>
          {recruteurName && (
            <div className="text-xs text-gray-500 mt-0.5">{recruteurName}</div>
          )}
        </div>
        {loading && <Loader2 className="w-4 h-4 text-gray-300 animate-spin" />}
      </div>

      {!dateRdv ? (
        <div className="text-center py-16 text-gray-400 text-sm italic">
          Choisis une date pour voir l'agenda
        </div>
      ) : (
        <div
          className="relative bg-white rounded-lg border border-gray-200 overflow-hidden"
          style={{ height: `${(TOTAL_MIN / 30) * SLOT_PX}px` }}
        >
          {/* Grille des créneaux */}
          {HOURS.map((time, i) => {
            const isFullHour = time.endsWith(':00')
            const isSelected = time === heureRdv
            const slotMin = parseInt(time.slice(0, 2)) * 60 + parseInt(time.slice(3, 5))
            const isOccupied = blocks.some(
              (b) => b.start_min <= slotMin && slotMin < b.end_min
            )
            return (
              <button
                key={time}
                type="button"
                onClick={() => onPickHour(time)}
                disabled={isOccupied}
                className={`absolute left-0 right-0 border-b ${
                  isFullHour ? 'border-gray-200' : 'border-gray-100'
                } flex items-center px-3 text-xs transition-colors ${
                  isSelected
                    ? 'bg-emerald-50 ring-2 ring-emerald-500 z-20'
                    : isOccupied
                      ? 'bg-transparent cursor-not-allowed'
                      : 'hover:bg-emerald-50/50 cursor-pointer'
                }`}
                style={{
                  top: `${i * SLOT_PX}px`,
                  height: `${SLOT_PX}px`,
                }}
              >
                <span
                  className={`w-12 shrink-0 font-mono ${
                    isFullHour ? 'text-gray-500 font-medium' : 'text-gray-300'
                  }`}
                >
                  {isFullHour ? time : ''}
                </span>
              </button>
            )
          })}

          {/* Blocs RDV existants */}
          {blocks.map(({ rdv, start_min, end_min }) => {
            const top = ((start_min - BASE_MIN) / 30) * SLOT_PX
            const height = Math.max(((end_min - start_min) / 30) * SLOT_PX, SLOT_PX)
            if (top < 0 || top > TOTAL_MIN / 30 * SLOT_PX) return null
            return (
              <div
                key={rdv.id_evenement}
                className="absolute left-14 right-2 rounded-md px-2 py-1 shadow-sm border text-xs overflow-hidden z-10"
                style={{
                  top: `${top}px`,
                  height: `${height}px`,
                  backgroundColor: (rdv.couleur_hex || '#6b7280') + '20',
                  borderColor: (rdv.couleur_hex || '#6b7280') + '60',
                }}
                title={rdv.titre}
              >
                <div className="font-semibold text-gray-900 truncate">{rdv.titre}</div>
                {rdv.lib_categorie && (
                  <div className="text-[10px] text-gray-500 truncate">
                    {rdv.lib_categorie}
                  </div>
                )}
              </div>
            )
          })}

          {/* Curseur du créneau choisi */}
          {heureRdv && (
            <div
              className="absolute left-14 right-2 border-t-2 border-emerald-500 pointer-events-none z-30"
              style={{
                top: `${((selectedMin - BASE_MIN) / 30) * SLOT_PX}px`,
              }}
            >
              <div className="absolute -left-14 -top-3 bg-emerald-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">
                {heureRdv}
              </div>
            </div>
          )}
        </div>
      )}

      <p className="text-[10px] text-gray-400 mt-3 text-center">
        Clique sur un créneau libre pour le sélectionner
      </p>
    </div>
  )
}


function posteLabel(id: number): string {
  // Mapping connu : 1 = VRP Energie, 10/13 = Fibre, etc.
  const map: Record<number, string> = {
    0: '--- sans profil ---',
    1: 'VRP Énergie',
    10: 'Technicien Fibre',
    13: 'Commercial Fibre',
  }
  return map[id] || `Poste #${id}`
}

function sourceLabel(id: number): string {
  const map: Record<number, string> = {
    0: '—',
    1: 'Cooptation',
    2: 'Annonceurs',
  }
  return map[id] || `Source #${id}`
}
