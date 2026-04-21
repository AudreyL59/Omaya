import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Calendar as CalendarIcon,
  MapPin,
  Phone,
  Mail,
  User,
  FileText,
  Pencil,
  Search,
  Filter,
  X,
  Loader2,
} from 'lucide-react'
import { getToken, getStoredUser } from '@/api'

interface AgendaRDV {
  id_evenement: string
  date_debut: string
  date_fin: string
  titre: string
  contenu: string
  id_categorie: number
  lib_categorie: string
  couleur_hex: string
  id_cv_statut: number
  id_cvtheque: string
  nom: string
  prenom: string
  gsm: string
  mail: string
  adresse: string
  cp: string
  ville: string
  profil: string
  observ: string
  id_cv_source: number
  id_elem_source: number
  cv_url: string
  statut_modif: boolean
}

interface RecruteurItem {
  id_salarie: string
  nom: string
  prenom: string
}

interface StatutItem {
  id_categorie: number
  lib_categorie: string
  id_cv_statut: number
}

// Catégories pour lesquelles on affiche la zone "Refus" (raisons)
const REFUS_CATEGORIES = new Set([4, 7])
// Catégories qui permettent de convoquer en JO (Retenu)
const CONVOC_CATEGORIES = new Set([2, 3])

// --- Helpers --------------------------------------------------------------

function parseDbDate(raw: string): Date | null {
  if (!raw) return null
  // ISO
  const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/)
  if (iso) {
    return new Date(+iso[1], +iso[2] - 1, +iso[3], +iso[4], +iso[5])
  }
  // WinDev YYYYMMDDHHMMSS...
  if (raw.length >= 12 && /^\d+$/.test(raw.slice(0, 12))) {
    return new Date(
      +raw.slice(0, 4),
      +raw.slice(4, 6) - 1,
      +raw.slice(6, 8),
      +raw.slice(8, 10),
      +raw.slice(10, 12),
    )
  }
  return null
}

function dayKey(raw: string): string {
  const d = parseDbDate(raw)
  if (!d) return raw.slice(0, 8)
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
}

function formatDayFr(ymd: string): string {
  const y = +ymd.slice(0, 4)
  const m = +ymd.slice(4, 6)
  const d = +ymd.slice(6, 8)
  const dt = new Date(y, m - 1, d)
  return dt.toLocaleDateString('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

function formatTime(raw: string): string {
  const d = parseDbDate(raw)
  if (!d) return ''
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function durationMin(start: string, end: string): number {
  const a = parseDbDate(start)
  const b = parseDbDate(end)
  if (!a || !b) return 0
  return Math.max(0, Math.round((b.getTime() - a.getTime()) / 60000))
}

function toYMD(d: Date): string {
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
}

function toISODate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : s
}

function hexToSoftStyle(hex: string): React.CSSProperties {
  // Utilise la couleur DB comme accent + fond léger
  return {
    color: hex,
    backgroundColor: hex + '15',
    borderColor: hex + '40',
  }
}

// --- Page -----------------------------------------------------------------

export default function AgendaRecrutementPage() {
  const stored = getStoredUser()
  const today = new Date()
  const [mode, setMode] = useState<'day' | 'range'>('day')
  const [day, setDay] = useState<Date>(today)
  const [dateFrom, setDateFrom] = useState(toISODate(today))
  const [dateTo, setDateTo] = useState(toISODate(today))
  const [recruteurId, setRecruteurId] = useState<string>(
    stored?.id_salarie ? String(stored.id_salarie) : ''
  )
  const [recruteurName, setRecruteurName] = useState<string>(
    stored ? `${stored.nom} ${capitalize(stored.prenom)}` : ''
  )
  const [rdvs, setRdvs] = useState<AgendaRDV[]>([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState<string>('all')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [showRecruteurPicker, setShowRecruteurPicker] = useState(false)
  const [searchCandidat, setSearchCandidat] = useState('')
  const [statutRdv, setStatutRdv] = useState<AgendaRDV | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    if (!recruteurId) return
    const from = mode === 'day' ? toYMD(day) : dateFrom.replace(/-/g, '')
    const to = mode === 'day' ? toYMD(day) : dateTo.replace(/-/g, '')

    setLoading(true)
    fetch(
      `/api/vendeur/agenda-recrutement?id_recruteur=${recruteurId}&date_from=${from}&date_to=${to}`,
      { headers: { Authorization: `Bearer ${getToken()}` } }
    )
      .then((r) => r.json())
      .then((data: AgendaRDV[]) => {
        setRdvs(data || [])
        if (data && data.length > 0 && expanded === null) setExpanded(data[0].id_evenement)
      })
      .catch(() => setRdvs([]))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recruteurId, mode, day, dateFrom, dateTo, refreshKey])

  const categories = Array.from(
    new Map(
      rdvs.map((r) => [
        r.id_categorie,
        { id: r.id_categorie, label: r.lib_categorie, color: r.couleur_hex },
      ])
    ).values()
  )

  const filteredRdvs = rdvs.filter((r) => {
    if (filter !== 'all' && String(r.id_categorie) !== filter) return false
    if (searchCandidat.trim()) {
      const s = searchCandidat.trim().toUpperCase()
      if (!`${r.nom} ${r.prenom}`.toUpperCase().includes(s)) return false
    }
    return true
  })

  const days = Array.from(new Set(filteredRdvs.map((r) => dayKey(r.date_debut)))).sort()

  const stats = {
    total: rdvs.length,
    retenu: rdvs.filter((r) => /retenu.*\(e\)$|Retenu/.test(r.lib_categorie)).length,
    non_retenu: rdvs.filter((r) => /Non.Retenu|Pas.Retenu/i.test(r.lib_categorie)).length,
    absent: rdvs.filter((r) => /Absent/i.test(r.lib_categorie)).length,
    attente: rdvs.filter((r) => /attente|traité/i.test(r.lib_categorie)).length,
  }

  const shiftDay = (delta: number) => {
    const nd = new Date(day)
    nd.setDate(nd.getDate() + delta)
    setDay(nd)
  }

  return (
    <div className="p-8">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-gray-900">Agenda de recrutement</h1>
        <p className="text-gray-500 mt-1">RDV d'entretiens</p>
      </motion.div>

      <div className="max-w-5xl mt-6">
        {/* Toolbar */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4 flex items-center gap-3 flex-wrap">
          {/* Mode toggle */}
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setMode('day')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                mode === 'day' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
              }`}
            >
              Jour
            </button>
            <button
              onClick={() => setMode('range')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                mode === 'range' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
              }`}
            >
              Période
            </button>
          </div>

          {mode === 'day' ? (
            <div className="flex items-center gap-2">
              <button
                onClick={() => shiftDay(-1)}
                className="p-1.5 rounded-lg hover:bg-gray-100"
              >
                <ChevronLeft className="w-4 h-4 text-gray-600" />
              </button>
              <div className="flex items-center gap-2 px-3 py-1.5 border border-gray-200 rounded-lg text-sm">
                <CalendarIcon className="w-4 h-4 text-gray-400" />
                <input
                  type="date"
                  value={toISODate(day)}
                  onChange={(e) => {
                    const [y, m, d] = e.target.value.split('-').map(Number)
                    setDay(new Date(y, m - 1, d))
                  }}
                  className="border-0 text-sm focus:outline-none font-medium bg-transparent"
                />
              </div>
              <button
                onClick={() => shiftDay(1)}
                className="p-1.5 rounded-lg hover:bg-gray-100"
              >
                <ChevronRight className="w-4 h-4 text-gray-600" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 px-2 py-1 border border-gray-200 rounded-lg text-sm">
                <CalendarIcon className="w-3.5 h-3.5 text-gray-400" />
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="border-0 text-sm focus:outline-none font-medium bg-transparent"
                />
              </div>
              <span className="text-gray-400 text-xs">→</span>
              <div className="flex items-center gap-1 px-2 py-1 border border-gray-200 rounded-lg text-sm">
                <CalendarIcon className="w-3.5 h-3.5 text-gray-400" />
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="border-0 text-sm focus:outline-none font-medium bg-transparent"
                />
              </div>
            </div>
          )}

          <div className="h-6 w-px bg-gray-200 mx-1" />

          <button
            onClick={() => setShowRecruteurPicker(true)}
            className="flex items-center gap-2 px-3 py-1.5 border border-gray-200 rounded-lg text-sm text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <User className="w-4 h-4 text-gray-400" />
            <span className="font-medium">{recruteurName}</span>
            <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
          </button>

          <div className="flex-1" />

          <div className="relative">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Rechercher un candidat..."
              value={searchCandidat}
              onChange={(e) => setSearchCandidat(e.target.value)}
              className="pl-9 pr-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-gray-300 w-56"
            />
          </div>
        </div>

        {/* Stats cards */}
        <div className="grid grid-cols-5 gap-3 mb-5">
          <StatCard label="RDV total" value={stats.total} accent="text-gray-900" />
          <StatCard label="Retenus" value={stats.retenu} accent="text-emerald-600" />
          <StatCard label="Non retenus" value={stats.non_retenu} accent="text-red-600" />
          <StatCard label="Absents" value={stats.absent} accent="text-slate-600" />
          <StatCard label="En attente" value={stats.attente} accent="text-gray-500" />
        </div>

        {/* Filter pills */}
        {categories.length > 0 && (
          <div className="flex items-center gap-2 mb-5 flex-wrap">
            <Filter className="w-4 h-4 text-gray-400" />
            <FilterPill
              active={filter === 'all'}
              onClick={() => setFilter('all')}
              label="Tous"
              count={rdvs.length}
            />
            {categories.map((cat) => {
              const count = rdvs.filter((r) => r.id_categorie === cat.id).length
              return (
                <FilterPill
                  key={cat.id}
                  active={filter === String(cat.id)}
                  onClick={() => setFilter(String(cat.id))}
                  label={cat.label}
                  count={count}
                  dotColor={cat.color}
                />
              )
            })}
          </div>
        )}

        {/* Timeline */}
        {loading ? (
          <div className="flex items-center justify-center py-20 bg-white rounded-xl border border-gray-200">
            <Loader2 className="w-6 h-6 text-gray-300 animate-spin" />
          </div>
        ) : filteredRdvs.length === 0 ? (
          <div className="text-center py-12 text-gray-400 text-sm bg-white rounded-xl border border-gray-200">
            Aucun RDV sur cette période
          </div>
        ) : (
          <div className="space-y-6">
            {days.map((dkey) => {
              const dayRdvs = filteredRdvs.filter((r) => dayKey(r.date_debut) === dkey)
              return (
                <div key={dkey}>
                  {mode === 'range' && (
                    <div className="flex items-center gap-3 mb-3">
                      <div className="text-sm font-semibold text-gray-900 capitalize">
                        {formatDayFr(dkey)}
                      </div>
                      <div className="flex-1 h-px bg-gray-200" />
                      <div className="text-xs text-gray-500">
                        {dayRdvs.length} RDV{dayRdvs.length > 1 ? 's' : ''}
                      </div>
                    </div>
                  )}
                  <div className="relative">
                    <div className="absolute left-[52px] top-3 bottom-3 w-px bg-gray-200" />
                    <div className="space-y-3">
                      {dayRdvs.map((rdv) => (
                        <TimelineCard
                          key={rdv.id_evenement}
                          rdv={rdv}
                          expanded={expanded === rdv.id_evenement}
                          onToggle={() =>
                            setExpanded(
                              expanded === rdv.id_evenement ? null : rdv.id_evenement
                            )
                          }
                          onStatuer={() => setStatutRdv(rdv)}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      <AnimatePresence>
        {showRecruteurPicker && (
          <RecruteurPicker
            onClose={() => setShowRecruteurPicker(false)}
            onSelect={(rec) => {
              setRecruteurId(rec.id_salarie)
              setRecruteurName(`${rec.nom} ${capitalize(rec.prenom)}`)
              setShowRecruteurPicker(false)
            }}
          />
        )}
        {statutRdv && (
          <StatuerModal
            rdv={statutRdv}
            onClose={() => setStatutRdv(null)}
            onSaved={() => {
              setStatutRdv(null)
              setRefreshKey((k) => k + 1)
            }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

// --- Sub-components -------------------------------------------------------

function StatCard({
  label,
  value,
  accent,
}: {
  label: string
  value: number
  accent: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 px-4 py-3">
      <div className={`text-2xl font-bold ${accent}`}>{value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  )
}

function FilterPill({
  active,
  onClick,
  label,
  count,
  dotColor,
}: {
  active: boolean
  onClick: () => void
  label: string
  count: number
  dotColor?: string
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
        active
          ? 'bg-gray-900 text-white'
          : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
      }`}
    >
      {dotColor && (
        <span
          className="w-1.5 h-1.5 rounded-full"
          style={{ backgroundColor: dotColor }}
        />
      )}
      {label}
      <span className={active ? 'text-gray-300' : 'text-gray-400'}>{count}</span>
    </button>
  )
}

function TimelineCard({
  rdv,
  expanded,
  onToggle,
  onStatuer,
}: {
  rdv: AgendaRDV
  expanded: boolean
  onToggle: () => void
  onStatuer: () => void
}) {
  const time = formatTime(rdv.date_debut)
  const duration = durationMin(rdv.date_debut, rdv.date_fin)
  const badgeStyle = hexToSoftStyle(rdv.couleur_hex || '#6b7280')
  const fullAddress = [rdv.adresse, rdv.cp, rdv.ville].filter(Boolean).join(', ')
  const candidateName =
    rdv.nom || rdv.prenom ? `${rdv.nom} ${capitalize(rdv.prenom)}`.trim() : rdv.titre

  return (
    <div className="flex gap-4 items-start">
      <div className="text-right pt-3 w-[44px] shrink-0">
        <div className="text-sm font-medium text-gray-900">{time}</div>
        {duration > 0 && <div className="text-xs text-gray-400">{duration}min</div>}
      </div>

      <div className="relative pt-4 shrink-0">
        <div
          className="w-4 h-4 rounded-full ring-4 ring-white shadow-sm"
          style={{ backgroundColor: rdv.couleur_hex || '#6b7280' }}
        />
      </div>

      <div className="flex-1 bg-white rounded-xl border border-gray-200 overflow-hidden hover:border-gray-300 transition-colors">
        <button
          onClick={onToggle}
          className="w-full px-5 py-3.5 flex items-center gap-3 text-left hover:bg-gray-50/50"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3">
              <h3 className="font-semibold text-gray-900">{candidateName}</h3>
              <span
                className="px-2 py-0.5 rounded-full text-xs font-medium border"
                style={badgeStyle}
              >
                {rdv.lib_categorie}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-0.5 truncate">
              {rdv.profil || '—'}
              {rdv.gsm && ` · ${rdv.gsm}`}
            </p>
          </div>
          {rdv.cv_url && (
            <a
              href={rdv.cv_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700"
              title="Ouvrir le CV"
            >
              <FileText className="w-4 h-4" />
            </a>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation()
              onStatuer()
            }}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700"
            title="Statuer le RDV"
          >
            <Pencil className="w-4 h-4" />
          </button>
          <ChevronDown
            className={`w-4 h-4 text-gray-400 transition-transform ${
              expanded ? 'rotate-180' : ''
            }`}
          />
        </button>

        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="px-5 pb-5 border-t border-gray-100">
                <div className="grid grid-cols-2 gap-x-6 gap-y-3 mt-4 text-sm">
                  <DetailRow
                    icon={<User className="w-3.5 h-3.5" />}
                    label="Profil"
                    value={rdv.profil || '—'}
                  />
                  <DetailRow
                    icon={<MapPin className="w-3.5 h-3.5" />}
                    label="Adresse"
                    value={fullAddress || '—'}
                  />
                  <DetailRow
                    icon={<Phone className="w-3.5 h-3.5" />}
                    label="Téléphone"
                    value={rdv.gsm || '—'}
                  />
                  <DetailRow
                    icon={<Mail className="w-3.5 h-3.5" />}
                    label="Email"
                    value={rdv.mail || '—'}
                  />
                </div>

                {rdv.contenu && (
                  <div className="mt-5 pt-4 border-t border-gray-100">
                    <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
                      Historique
                    </div>
                    <div className="text-xs text-gray-600 whitespace-pre-line leading-relaxed">
                      {rdv.contenu}
                    </div>
                  </div>
                )}

                {rdv.observ && (
                  <div className="mt-4 pt-4 border-t border-gray-100">
                    <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                      Observations
                    </div>
                    <div className="text-xs text-gray-600 whitespace-pre-line leading-relaxed">
                      {rdv.observ}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

function DetailRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: string
}) {
  return (
    <div className="flex gap-2">
      <div className="text-gray-300 mt-0.5">{icon}</div>
      <div className="min-w-0">
        <div className="text-xs text-gray-400 uppercase tracking-wide">{label}</div>
        <div className="text-gray-900 mt-0.5 truncate">{value}</div>
      </div>
    </div>
  )
}

// --- Recruteur picker -----------------------------------------------------

function RecruteurPicker({
  onClose,
  onSelect,
}: {
  onClose: () => void
  onSelect: (r: RecruteurItem) => void
}) {
  const [search, setSearch] = useState('')
  const [results, setResults] = useState<RecruteurItem[]>([])
  const [selected, setSelected] = useState<RecruteurItem | null>(null)
  const [loading, setLoading] = useState(false)

  const doSearch = () => {
    if (!search.trim()) return
    setLoading(true)
    fetch(
      `/api/vendeur/agenda-recrutement/recruteurs?q=${encodeURIComponent(search.trim())}`,
      { headers: { Authorization: `Bearer ${getToken()}` } }
    )
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
          <h2 className="text-lg font-semibold text-gray-900">Choisir le recruteur</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-3">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Nom du recruteur"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), doSearch())}
              autoFocus
              className="flex-1 px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
            />
            <button
              type="button"
              onClick={doSearch}
              className="px-3 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4 text-gray-700" />
              )}
            </button>
          </div>

          <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-lg">
            {results.length === 0 ? (
              <div className="text-center py-8 text-gray-400 text-sm">
                {loading ? '' : 'Saisis un nom pour rechercher'}
              </div>
            ) : (
              results.map((r) => (
                <button
                  key={r.id_salarie}
                  type="button"
                  onClick={() => setSelected(r)}
                  className={`w-full text-left px-4 py-2.5 text-sm border-b border-gray-100 last:border-0 hover:bg-gray-50 ${
                    selected?.id_salarie === r.id_salarie ? 'bg-gray-100' : ''
                  }`}
                >
                  <span className="font-medium text-gray-900">{r.nom}</span>{' '}
                  <span className="text-gray-600">{capitalize(r.prenom)}</span>
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

// --- Statuer modal --------------------------------------------------------

function StatuerModal({
  rdv,
  onClose,
  onSaved,
}: {
  rdv: AgendaRDV
  onClose: () => void
  onSaved: () => void
}) {
  const [statuts, setStatuts] = useState<StatutItem[]>([])
  const [idCategorie, setIdCategorie] = useState<number>(
    rdv.id_categorie < 10 ? rdv.id_categorie : 0
  )
  const [motif, setMotif] = useState('')
  const [pbPresentation, setPbPresentation] = useState(false)
  const [pbElocution, setPbElocution] = useState(false)
  const [pbMotivation, setPbMotivation] = useState(false)
  const [pbHoraires, setPbHoraires] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/api/vendeur/agenda-recrutement/statuts', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then(setStatuts)
      .catch(() => {})
  }, [])

  const showRefus = REFUS_CATEGORIES.has(idCategorie)

  const handleSubmit = async () => {
    setError('')
    if (idCategorie === 0) return setError('Veuillez choisir un statut')
    if (showRefus && motif.trim().length < 5)
      return setError('Motif requis (minimum 5 caractères)')

    const selected = statuts.find((s) => s.id_categorie === idCategorie)
    if (
      !window.confirm(
        `Vous êtes sur le point de statuer ce RDV en ${selected?.lib_categorie}.\nVoulez-vous continuer ?`
      )
    )
      return

    setSubmitting(true)
    try {
      const res = await fetch(
        `/api/vendeur/agenda-recrutement/rdv/${rdv.id_evenement}/statut`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({
            id_categorie: idCategorie,
            motif,
            pb_presentation: pbPresentation,
            pb_elocution: pbElocution,
            pb_motivation: pbMotivation,
            pb_horaires: pbHoraires,
          }),
        }
      )
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Erreur')
      }
      onSaved()
    } catch (e: any) {
      setError(e.message || 'Erreur lors de la mise à jour')
    } finally {
      setSubmitting(false)
    }
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
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 sticky top-0 bg-white z-10">
          <h2 className="text-lg font-semibold text-gray-900">Statuer le RDV</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <div className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">
              Candidat
            </div>
            <div className="text-sm font-semibold text-gray-900">
              {rdv.nom || rdv.prenom
                ? `${rdv.nom} ${capitalize(rdv.prenom)}`.trim()
                : rdv.titre}
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
              Statut RDV
            </label>
            <select
              value={idCategorie}
              onChange={(e) => setIdCategorie(parseInt(e.target.value))}
              disabled={!rdv.statut_modif}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed"
            >
              <option value={0}>Choisir le statut</option>
              {statuts.map((s) => (
                <option key={s.id_categorie} value={s.id_categorie}>
                  {s.lib_categorie}
                </option>
              ))}
            </select>
            {!rdv.statut_modif && (
              <p className="text-xs text-gray-500 mt-1.5 italic">
                Ce RDV a déjà été statué, le statut n'est plus modifiable.
              </p>
            )}
          </div>

          {showRefus && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="space-y-2"
            >
              <div className="text-xs text-gray-600">
                Vous n'avez pas retenu le candidat pour les raisons suivantes :
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Checkbox
                  label="Pb Présentation"
                  checked={pbPresentation}
                  onChange={setPbPresentation}
                />
                <Checkbox
                  label="Pb Motivation"
                  checked={pbMotivation}
                  onChange={setPbMotivation}
                />
                <Checkbox
                  label="Pb Elocution"
                  checked={pbElocution}
                  onChange={setPbElocution}
                />
                <Checkbox
                  label="Pb Horaires"
                  checked={pbHoraires}
                  onChange={setPbHoraires}
                />
              </div>
            </motion.div>
          )}

          <div>
            <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 block">
              Motif {showRefus && <span className="text-red-500">*</span>}
            </label>
            <textarea
              value={motif}
              onChange={(e) => setMotif(e.target.value)}
              rows={3}
              placeholder="Minimum 5 caractères"
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-gray-900"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {rdv.statut_modif && (
            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitting}
                className="flex-1 px-3 py-2.5 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
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
          )}

          {CONVOC_CATEGORIES.has(rdv.id_categorie) && (
            <div className="pt-4 mt-2 border-t border-gray-200">
              <ConvocJoButton
                idRdv={rdv.id_evenement}
                onDone={onSaved}
              />
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  )
}

function ConvocJoButton({
  idRdv,
  onDone,
}: {
  idRdv: string
  onDone: () => void
}) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleClick = async () => {
    if (
      !window.confirm(
        'Convoquer ce candidat en JO ?\n\nCela créera un ticket DPAE (service RH) et enverra les instructions au candidat.'
      )
    )
      return

    setError('')
    setLoading(true)
    try {
      const res = await fetch(`/api/vendeur/agenda-recrutement/rdv/${idRdv}/convoc-jo`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Erreur')
      }
      onDone()
    } catch (e: any) {
      setError(e.message || 'Erreur lors de la convocation')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={handleClick}
        disabled={loading}
        className="w-full px-3 py-2.5 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 flex items-center justify-center gap-2"
      >
        {loading && <Loader2 className="w-4 h-4 animate-spin" />}
        Convoquer en JO
      </button>
      {error && (
        <p className="text-xs text-red-600 mt-2 bg-red-50 border border-red-200 rounded-lg px-2 py-1.5">
          {error}
        </p>
      )}
    </div>
  )
}

function Checkbox({
  label,
  checked,
  onChange,
}: {
  label: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-gray-700 px-3 py-2 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="w-4 h-4"
      />
      {label}
    </label>
  )
}
