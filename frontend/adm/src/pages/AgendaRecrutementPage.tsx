import { useState, useEffect, useCallback, useRef } from 'react'
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
import { showConfirm, showToast } from '@shared/ui/dialog'

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

/** Signature stable d'une liste de RDV : detecte ajouts/suppressions/
 *  modifications de statut/categorie/horaire en une comparaison string. */
function _rdvSignature(rdvs: { id_evenement: string; id_categorie: number; id_cv_statut: number; date_debut: string; date_fin: string }[]): string {
  return rdvs
    .map(
      (r) =>
        `${r.id_evenement}|${r.id_categorie}|${r.id_cv_statut}|${r.date_debut}|${r.date_fin}`,
    )
    .sort()
    .join(';')
}

/** Decrit le diff entre 2 listes de RDV : "2 nouveaux, 1 statut modifie". */
function _describeRdvDiff(
  oldRdvs: { id_evenement: string; id_categorie: number; id_cv_statut: number }[],
  newRdvs: { id_evenement: string; id_categorie: number; id_cv_statut: number }[],
): string {
  const oldIds = new Set(oldRdvs.map((r) => r.id_evenement))
  const newIds = new Set(newRdvs.map((r) => r.id_evenement))
  const added = newRdvs.filter((r) => !oldIds.has(r.id_evenement)).length
  const removed = oldRdvs.filter((r) => !newIds.has(r.id_evenement)).length
  const oldByIdSig = new Map(
    oldRdvs.map((r) => [r.id_evenement, `${r.id_categorie}|${r.id_cv_statut}`]),
  )
  const modified = newRdvs.filter(
    (r) =>
      oldByIdSig.has(r.id_evenement) &&
      oldByIdSig.get(r.id_evenement) !== `${r.id_categorie}|${r.id_cv_statut}`,
  ).length
  const parts: string[] = []
  if (added) parts.push(`${added} nouveau${added > 1 ? 'x RDV' : ' RDV'}`)
  if (removed) parts.push(`${removed} RDV supprimé${removed > 1 ? 's' : ''}`)
  if (modified)
    parts.push(`${modified} statut${modified > 1 ? 's' : ''} modifié${modified > 1 ? 's' : ''}`)
  return parts.join(', ') || 'changements détectés'
}

function isoWeekNumber(d: Date): number {
  // ISO 8601 : la semaine contient le jeudi de la semaine en cours.
  const target = new Date(d)
  target.setHours(0, 0, 0, 0)
  // Jeudi de la semaine = lundi + 3
  target.setDate(target.getDate() + 3 - ((target.getDay() + 6) % 7))
  const firstThursday = new Date(target.getFullYear(), 0, 4)
  const diff = (target.getTime() - firstThursday.getTime()) / 86400000
  return 1 + Math.round((diff - 3 + ((firstThursday.getDay() + 6) % 7)) / 7)
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
  const [mode, setMode] = useState<'day' | 'week' | 'range'>('week')
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

  // Calcule le lundi et le vendredi de la semaine contenant `day`.
  const weekRange = (() => {
    const d = new Date(day)
    const dow = d.getDay() // 0=dim, 1=lun, ...
    const offsetToMon = dow === 0 ? -6 : 1 - dow
    const mon = new Date(d)
    mon.setDate(d.getDate() + offsetToMon)
    const fri = new Date(mon)
    fri.setDate(mon.getDate() + 4)
    return { from: mon, to: fri }
  })()

  // Calcule from/to selon le mode (utilise par le fetch initial + polling)
  const computeRange = useCallback((): { from: string; to: string } => {
    if (mode === 'day') {
      return { from: toYMD(day), to: toYMD(day) }
    }
    if (mode === 'week') {
      return { from: toYMD(weekRange.from), to: toYMD(weekRange.to) }
    }
    return { from: dateFrom.replace(/-/g, ''), to: dateTo.replace(/-/g, '') }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, day, dateFrom, dateTo])

  useEffect(() => {
    if (!recruteurId) return
    const { from, to } = computeRange()

    setLoading(true)
    fetch(
      `/api/adm/agenda-recrutement?id_recruteur=${recruteurId}&date_from=${from}&date_to=${to}`,
      { headers: { Authorization: `Bearer ${getToken()}` } }
    )
      .then((r) => r.json())
      .then((data) => {
        const list = Array.isArray(data) ? (data as AgendaRDV[]) : []
        setRdvs(list)
        if (list.length > 0 && expanded === null) setExpanded(list[0].id_evenement)
      })
      .catch(() => setRdvs([]))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recruteurId, mode, day, dateFrom, dateTo, refreshKey])

  // Polling silencieux toutes les 30s : detecte les nouveaux RDV / RDV
  // supprimes / changements de statut (cf. memoire project_iis_no_sse -
  // long polling au lieu de SSE qui ne marche pas via IIS/ARR).
  const rdvsRef = useRef<AgendaRDV[]>([])
  rdvsRef.current = rdvs
  const statutOpenRef = useRef(false)
  statutOpenRef.current = !!statutRdv

  useEffect(() => {
    if (!recruteurId) return
    const tick = async () => {
      const { from, to } = computeRange()
      try {
        const r = await fetch(
          `/api/adm/agenda-recrutement?id_recruteur=${recruteurId}&date_from=${from}&date_to=${to}`,
          { headers: { Authorization: `Bearer ${getToken()}` } },
        )
        if (!r.ok) return
        const list = (await r.json()) as AgendaRDV[]
        if (!Array.isArray(list)) return
        const oldSig = _rdvSignature(rdvsRef.current)
        const newSig = _rdvSignature(list)
        if (oldSig === newSig) return  // pas de changement
        const diff = _describeRdvDiff(rdvsRef.current, list)
        setRdvs(list)
        // Toast discret (sauf si l'utilisateur est en train de statuer)
        if (!statutOpenRef.current) {
          showToast(`Agenda mis à jour : ${diff}`, 'info')
        }
      } catch {
        // erreur reseau -> on retentera au tick suivant
      }
    }
    // 5s : peu d'utilisateurs sur cet agenda (3-4 max), donc faible charge
    // serveur. Cf. memoire project_iis_no_sse : long polling.
    const interval = setInterval(tick, 5_000)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recruteurId, mode, day, dateFrom, dateTo])

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

  // Compteurs : seuls les vrais RDV (titre commence par "RDV : ") sont
  // comptabilisés. Les autres événements restent visibles dans le calendrier.
  const rdvOnly = rdvs.filter((r) => (r.titre || '').startsWith('RDV : '))
  const isRetenu = (lib: string) =>
    /retenu.*premier|retenu.*1er|retenu.*second|retenu.*2[èe]me|venu.*jo/i.test(lib)
  const stats = {
    total: rdvOnly.length,
    retenu: rdvOnly.filter((r) => isRetenu(r.lib_categorie)).length,
    non_retenu: rdvOnly.filter((r) => /Non.Retenu|Pas.Retenu/i.test(r.lib_categorie)).length,
    absent: rdvOnly.filter((r) => /Absent/i.test(r.lib_categorie)).length,
    attente: rdvOnly.filter((r) => /attente|traité/i.test(r.lib_categorie)).length,
  }

  const shiftDay = (delta: number) => {
    const nd = new Date(day)
    nd.setDate(nd.getDate() + delta)
    setDay(nd)
  }

  return (
    <div className="p-8">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-[#4E1D17]">Agenda de recrutement</h1>
        <p className="text-[#A68D8A] mt-1">RDV d'entretiens</p>
      </motion.div>

      <div className="mt-6">
        {/* Toolbar */}
        <div className="bg-white rounded-[10px] border border-[#E5DDDC] p-4 mb-4 flex items-center gap-3 flex-wrap">
          {/* Mode toggle */}
          <div className="flex gap-1 bg-[#EFE9E7] rounded-lg p-1">
            <button
              onClick={() => setMode('day')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                mode === 'day' ? 'bg-white text-[#17494E] shadow-sm' : 'text-[#A68D8A]'
              }`}
            >
              Jour
            </button>
            <button
              onClick={() => setMode('week')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                mode === 'week' ? 'bg-white text-[#17494E] shadow-sm' : 'text-[#A68D8A]'
              }`}
            >
              Semaine
            </button>
            <button
              onClick={() => setMode('range')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                mode === 'range' ? 'bg-white text-[#17494E] shadow-sm' : 'text-[#A68D8A]'
              }`}
            >
              Période
            </button>
          </div>

          {mode === 'week' ? (
            <div className="flex items-center gap-2">
              <button
                onClick={() => shiftDay(-7)}
                className="p-1.5 rounded-lg hover:bg-[#EFE9E7]"
                title="Semaine précédente"
              >
                <ChevronLeft className="w-4 h-4 text-[#4E1D17]/80" />
              </button>
              <div className="flex flex-col items-center px-3 py-1 border border-[#E5DDDC] rounded-lg text-sm">
                <span className="font-medium text-[#4E1D17]">
                  {capitalize(
                    weekRange.from.toLocaleDateString('fr-FR', {
                      month: 'long',
                      year: 'numeric',
                    }),
                  )}
                </span>
                <span className="text-[10px] text-[#A68D8A]">
                  Semaine {isoWeekNumber(weekRange.from)}
                </span>
              </div>
              <button
                onClick={() => shiftDay(7)}
                className="p-1.5 rounded-lg hover:bg-[#EFE9E7]"
                title="Semaine suivante"
              >
                <ChevronRight className="w-4 h-4 text-[#4E1D17]/80" />
              </button>
              <button
                onClick={() => setDay(new Date())}
                className="px-2 py-1 text-xs rounded-lg border border-[#E5DDDC] hover:bg-[#EFE9E7] text-[#4E1D17]"
              >
                Aujourd'hui
              </button>
            </div>
          ) : mode === 'day' ? (
            <div className="flex items-center gap-2">
              <button
                onClick={() => shiftDay(-1)}
                className="p-1.5 rounded-lg hover:bg-[#EFE9E7]"
              >
                <ChevronLeft className="w-4 h-4 text-[#4E1D17]/80" />
              </button>
              <div className="flex items-center gap-2 px-3 py-1.5 border border-[#E5DDDC] rounded-lg text-sm">
                <CalendarIcon className="w-4 h-4 text-[#A68D8A]/80" />
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
                className="p-1.5 rounded-lg hover:bg-[#EFE9E7]"
              >
                <ChevronRight className="w-4 h-4 text-[#4E1D17]/80" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 px-2 py-1 border border-[#E5DDDC] rounded-lg text-sm">
                <CalendarIcon className="w-3.5 h-3.5 text-[#A68D8A]/80" />
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="border-0 text-sm focus:outline-none font-medium bg-transparent"
                />
              </div>
              <span className="text-[#A68D8A]/80 text-xs">→</span>
              <div className="flex items-center gap-1 px-2 py-1 border border-[#E5DDDC] rounded-lg text-sm">
                <CalendarIcon className="w-3.5 h-3.5 text-[#A68D8A]/80" />
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="border-0 text-sm focus:outline-none font-medium bg-transparent"
                />
              </div>
            </div>
          )}

          <div className="h-6 w-px bg-[#E5DDDC] mx-1" />

          <button
            onClick={() => setShowRecruteurPicker(true)}
            className="flex items-center gap-2 px-3 py-1.5 border border-[#E5DDDC] rounded-lg text-sm text-[#4E1D17] hover:bg-[#EFE9E7] transition-colors"
          >
            <User className="w-4 h-4 text-[#A68D8A]/80" />
            <span className="font-medium">{recruteurName}</span>
            <ChevronDown className="w-3.5 h-3.5 text-[#A68D8A]/80" />
          </button>

          <div className="flex-1" />

          <div className="relative">
            <Search className="w-4 h-4 text-[#A68D8A]/80 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Rechercher un candidat..."
              value={searchCandidat}
              onChange={(e) => setSearchCandidat(e.target.value)}
              className="pl-9 pr-3 py-1.5 border border-[#E5DDDC] rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-[#E5DDDC] w-56"
            />
          </div>
        </div>

        {/* Stats cards */}
        <div className="grid grid-cols-5 gap-3 mb-5">
          <StatCard label="RDV total" value={stats.total} accent="text-[#4E1D17]" />
          <StatCard label="Retenus" value={stats.retenu} accent="text-[#17494E]" />
          <StatCard label="Non retenus" value={stats.non_retenu} accent="text-[#993636]" />
          <StatCard label="Absents" value={stats.absent} accent="text-slate-600" />
          <StatCard label="En attente" value={stats.attente} accent="text-[#A68D8A]" />
        </div>

        {/* Filter pills */}
        {categories.length > 0 && (
          <div className="flex items-center gap-2 mb-5 flex-wrap">
            <Filter className="w-4 h-4 text-[#A68D8A]/80" />
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

        {/* Vue Semaine : grille hebdomadaire lundi -> vendredi */}
        {mode === 'week' && (
          loading ? (
            <div className="flex items-center justify-center py-20 bg-white rounded-[10px] border border-[#E5DDDC]">
              <Loader2 className="w-6 h-6 text-[#E5DDDC] animate-spin" />
            </div>
          ) : (
            <WeekCalendarView
              rdvs={filteredRdvs}
              monday={weekRange.from}
              onClickRdv={(r) => {
                setExpanded(r.id_evenement)
                setStatutRdv(r)
              }}
            />
          )
        )}

        {/* Timeline (modes Jour + Période) */}
        {mode !== 'week' && (loading ? (
          <div className="flex items-center justify-center py-20 bg-white rounded-[10px] border border-[#E5DDDC]">
            <Loader2 className="w-6 h-6 text-[#E5DDDC] animate-spin" />
          </div>
        ) : filteredRdvs.length === 0 ? (
          <div className="text-center py-12 text-[#A68D8A]/80 text-sm bg-white rounded-[10px] border border-[#E5DDDC]">
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
                      <div className="text-sm font-semibold text-[#4E1D17] capitalize">
                        {formatDayFr(dkey)}
                      </div>
                      <div className="flex-1 h-px bg-[#E5DDDC]" />
                      <div className="text-xs text-[#A68D8A]">
                        {dayRdvs.length} RDV{dayRdvs.length > 1 ? 's' : ''}
                      </div>
                    </div>
                  )}
                  <div className="relative">
                    <div className="absolute left-[52px] top-3 bottom-3 w-px bg-[#E5DDDC]" />
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
        ))}
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
    <div className="bg-white rounded-[10px] border border-[#E5DDDC] px-4 py-3">
      <div className={`text-2xl font-bold ${accent}`}>{value}</div>
      <div className="text-xs text-[#A68D8A] mt-0.5">{label}</div>
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
          ? 'bg-[#17494E] text-white'
          : 'bg-white border border-[#E5DDDC] text-[#4E1D17]/80 hover:bg-[#EFE9E7]'
      }`}
    >
      {dotColor && (
        <span
          className="w-1.5 h-1.5 rounded-full"
          style={{ backgroundColor: dotColor }}
        />
      )}
      {label}
      <span className={active ? 'text-[#E5DDDC]' : 'text-[#A68D8A]/80'}>{count}</span>
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
        <div className="text-sm font-medium text-[#4E1D17]">{time}</div>
        {duration > 0 && <div className="text-xs text-[#A68D8A]/80">{duration}min</div>}
      </div>

      <div className="relative pt-4 shrink-0">
        <div
          className="w-4 h-4 rounded-full ring-4 ring-white shadow-sm"
          style={{ backgroundColor: rdv.couleur_hex || '#6b7280' }}
        />
      </div>

      <div className="flex-1 bg-white rounded-[10px] border border-[#E5DDDC] overflow-hidden hover:border-[#E5DDDC] transition-colors">
        <button
          onClick={onToggle}
          className="w-full px-5 py-3.5 flex items-center gap-3 text-left hover:bg-[#EFE9E7]/50"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3">
              <h3 className="font-semibold text-[#4E1D17]">{candidateName}</h3>
              <span
                className="px-2 py-0.5 rounded-full text-xs font-medium border"
                style={badgeStyle}
              >
                {rdv.lib_categorie}
              </span>
            </div>
            <p className="text-xs text-[#A68D8A] mt-0.5 truncate">
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
              className="p-1.5 rounded-lg hover:bg-[#EFE9E7] text-[#A68D8A]/80 hover:text-[#4E1D17]"
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
            className="p-1.5 rounded-lg hover:bg-[#EFE9E7] text-[#A68D8A]/80 hover:text-[#4E1D17]"
            title="Statuer le RDV"
          >
            <Pencil className="w-4 h-4" />
          </button>
          <ChevronDown
            className={`w-4 h-4 text-[#A68D8A]/80 transition-transform ${
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
              <div className="px-5 pb-5 border-t border-[#E5DDDC]">
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
                  <div className="mt-5 pt-4 border-t border-[#E5DDDC]">
                    <div className="text-xs font-medium text-[#A68D8A] uppercase tracking-wide mb-3">
                      Historique
                    </div>
                    <div className="text-xs text-[#4E1D17]/80 whitespace-pre-line leading-relaxed">
                      {rdv.contenu}
                    </div>
                  </div>
                )}

                {rdv.observ && (
                  <div className="mt-4 pt-4 border-t border-[#E5DDDC]">
                    <div className="text-xs font-medium text-[#A68D8A] uppercase tracking-wide mb-2">
                      Observations
                    </div>
                    <div className="text-xs text-[#4E1D17]/80 whitespace-pre-line leading-relaxed">
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
      <div className="text-[#E5DDDC] mt-0.5">{icon}</div>
      <div className="min-w-0">
        <div className="text-xs text-[#A68D8A]/80 uppercase tracking-wide">{label}</div>
        <div className="text-[#4E1D17] mt-0.5 truncate">{value}</div>
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
      `/api/adm/agenda-recrutement/recruteurs?q=${encodeURIComponent(search.trim())}`,
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
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E5DDDC]">
          <h2 className="text-lg font-semibold text-[#4E1D17]">Choisir le recruteur</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-[#EFE9E7] text-[#A68D8A]/80 hover:text-[#4E1D17]"
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
              className="flex-1 px-3 py-2.5 border border-[#E5DDDC] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#17494E] focus:border-transparent"
            />
            <button
              type="button"
              onClick={doSearch}
              className="px-3 py-2.5 border border-[#E5DDDC] rounded-lg hover:bg-[#EFE9E7]"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4 text-[#4E1D17]" />
              )}
            </button>
          </div>

          <div className="max-h-64 overflow-y-auto border border-[#E5DDDC] rounded-lg">
            {results.length === 0 ? (
              <div className="text-center py-8 text-[#A68D8A]/80 text-sm">
                {loading ? '' : 'Saisis un nom pour rechercher'}
              </div>
            ) : (
              results.map((r) => (
                <button
                  key={r.id_salarie}
                  type="button"
                  onClick={() => setSelected(r)}
                  className={`w-full text-left px-4 py-2.5 text-sm border-b border-[#E5DDDC] last:border-0 hover:bg-[#EFE9E7] ${
                    selected?.id_salarie === r.id_salarie ? 'bg-[#EFE9E7]' : ''
                  }`}
                >
                  <span className="font-medium text-[#4E1D17]">{r.nom}</span>{' '}
                  <span className="text-[#4E1D17]/80">{capitalize(r.prenom)}</span>
                </button>
              ))
            )}
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={() => selected && onSelect(selected)}
              disabled={!selected}
              className="flex-1 px-3 py-2.5 bg-[#17494E] text-white rounded-lg text-sm font-medium hover:bg-[#17494E]/90 disabled:opacity-50"
            >
              Valider
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-3 py-2.5 border border-[#E5DDDC] rounded-lg text-sm font-medium hover:bg-[#EFE9E7]"
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
    fetch('/api/adm/agenda-recrutement/statuts', {
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
      !(await showConfirm({
        message: `Vous êtes sur le point de statuer ce RDV en ${selected?.lib_categorie}.\nVoulez-vous continuer ?`,
      }))
    )
      return

    setSubmitting(true)
    try {
      const res = await fetch(
        `/api/adm/agenda-recrutement/rdv/${rdv.id_evenement}/statut`,
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
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E5DDDC] sticky top-0 bg-white z-10">
          <h2 className="text-lg font-semibold text-[#4E1D17]">Statuer le RDV</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-[#EFE9E7] text-[#A68D8A]/80 hover:text-[#4E1D17]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <div className="text-xs font-medium text-[#A68D8A]/80 uppercase tracking-wide mb-1">
              Candidat
            </div>
            <div className="text-sm font-semibold text-[#4E1D17]">
              {rdv.nom || rdv.prenom
                ? `${rdv.nom} ${capitalize(rdv.prenom)}`.trim()
                : rdv.titre}
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-[#A68D8A]/80 uppercase tracking-wide mb-1 block">
              Statut RDV
            </label>
            <select
              value={idCategorie}
              onChange={(e) => setIdCategorie(parseInt(e.target.value))}
              disabled={!rdv.statut_modif}
              className="w-full px-3 py-2.5 border border-[#E5DDDC] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#17494E] disabled:bg-white disabled:text-[#A68D8A] disabled:cursor-not-allowed"
            >
              <option value={0}>Choisir le statut</option>
              {statuts.map((s) => (
                <option key={s.id_categorie} value={s.id_categorie}>
                  {s.lib_categorie}
                </option>
              ))}
            </select>
            {!rdv.statut_modif && (
              <p className="text-xs text-[#A68D8A] mt-1.5 italic">
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
              <div className="text-xs text-[#4E1D17]/80">
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
            <label className="text-xs font-medium text-[#A68D8A]/80 uppercase tracking-wide mb-1 block">
              Motif {showRefus && <span className="text-red-500">*</span>}
            </label>
            <textarea
              value={motif}
              onChange={(e) => setMotif(e.target.value)}
              rows={3}
              placeholder="Minimum 5 caractères"
              className="w-full px-3 py-2.5 border border-[#E5DDDC] rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-[#17494E]"
            />
          </div>

          {error && (
            <p className="text-sm text-[#993636] bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {rdv.statut_modif && (
            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitting}
                className="flex-1 px-3 py-2.5 bg-[#17494E] text-white rounded-lg text-sm font-medium hover:bg-[#17494E]/90 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                Valider
              </button>
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-3 py-2.5 border border-[#E5DDDC] rounded-lg text-sm font-medium hover:bg-[#EFE9E7]"
              >
                Annuler
              </button>
            </div>
          )}

          {CONVOC_CATEGORIES.has(rdv.id_categorie) && (
            <div className="pt-4 mt-2 border-t border-[#E5DDDC]">
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
      !(await showConfirm({
        message:
          'Convoquer ce candidat en JO ?\n\nCela créera un ticket DPAE (service RH) et enverra les instructions au candidat.',
      }))
    )
      return

    setError('')
    setLoading(true)
    try {
      const res = await fetch(`/api/adm/agenda-recrutement/rdv/${idRdv}/convoc-jo`, {
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
        <p className="text-xs text-[#993636] mt-2 bg-red-50 border border-red-200 rounded-lg px-2 py-1.5">
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
    <label className="flex items-center gap-2 text-sm text-[#4E1D17] px-3 py-2 border border-[#E5DDDC] rounded-lg cursor-pointer hover:bg-[#EFE9E7]">
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

/** Assigne chaque RDV a une lane (colonne parallele) pour eviter les
 *  chevauchements visuels. Algo simple : on parcourt les RDV tries par
 *  date_debut, pour chacun on lui donne la 1ere lane libre (= aucune
 *  lane n'a un RDV en cours qui chevauche). Tous les RDV d'un meme
 *  groupe de chevauchement partagent le meme `totalLanes` pour que
 *  leur largeur soit cohérente. */
function assignLanes(
  rdvs: AgendaRDV[],
): Map<string, { lane: number; totalLanes: number }> {
  const out = new Map<string, { lane: number; totalLanes: number }>()
  if (rdvs.length === 0) return out

  // 1) Trouver les groupes de chevauchement (clusters)
  type Item = { rdv: AgendaRDV; start: number; end: number }
  const items: Item[] = rdvs
    .map((r) => {
      const s = parseDbDate(r.date_debut)?.getTime() ?? 0
      const e = parseDbDate(r.date_fin)?.getTime() ?? s + 30 * 60_000
      return { rdv: r, start: s, end: Math.max(e, s + 5 * 60_000) }
    })
    .sort((a, b) => a.start - b.start)

  let cluster: Item[] = []
  let clusterEnd = 0
  const flush = () => {
    if (cluster.length === 0) return
    // 2) Pour ce cluster, assigner les lanes
    const lanes: number[] = [] // lanes[i] = end time du dernier RDV sur la lane i
    const localAssign: { item: Item; lane: number }[] = []
    for (const it of cluster) {
      let assigned = -1
      for (let i = 0; i < lanes.length; i++) {
        if (lanes[i] <= it.start) {
          assigned = i
          lanes[i] = it.end
          break
        }
      }
      if (assigned === -1) {
        assigned = lanes.length
        lanes.push(it.end)
      }
      localAssign.push({ item: it, lane: assigned })
    }
    const total = lanes.length
    for (const a of localAssign) {
      out.set(a.item.rdv.id_evenement, { lane: a.lane, totalLanes: total })
    }
    cluster = []
    clusterEnd = 0
  }

  for (const it of items) {
    if (cluster.length === 0 || it.start < clusterEnd) {
      cluster.push(it)
      if (it.end > clusterEnd) clusterEnd = it.end
    } else {
      flush()
      cluster.push(it)
      clusterEnd = it.end
    }
  }
  flush()
  return out
}

// --- Vue calendrier hebdomadaire (cf. WinDev agenda) --------------------

const WEEK_HOUR_START = 8
const WEEK_HOUR_END = 19
const WEEK_PIXELS_PER_HOUR = 56

function WeekCalendarView({
  rdvs,
  monday,
  onClickRdv,
}: {
  rdvs: AgendaRDV[]
  monday: Date
  onClickRdv: (r: AgendaRDV) => void
}) {
  // 5 jours (Lundi → Vendredi)
  const days = Array.from({ length: 5 }, (_, i) => {
    const d = new Date(monday)
    d.setDate(monday.getDate() + i)
    return d
  })

  // Plage horaire 8h → 19h (11 lignes)
  const hours = Array.from(
    { length: WEEK_HOUR_END - WEEK_HOUR_START },
    (_, i) => WEEK_HOUR_START + i,
  )

  const todayYMD = toYMD(new Date())

  // Position d'un RDV en pixels depuis le top de la grille
  const positionRdv = (rdv: AgendaRDV) => {
    const start = parseDbDate(rdv.date_debut)
    const end = parseDbDate(rdv.date_fin)
    if (!start || !end) return null
    const startMin = start.getHours() * 60 + start.getMinutes()
    const endMin = end.getHours() * 60 + end.getMinutes()
    const baseMin = WEEK_HOUR_START * 60
    const top = ((startMin - baseMin) / 60) * WEEK_PIXELS_PER_HOUR
    const height = Math.max(
      18,
      ((endMin - startMin) / 60) * WEEK_PIXELS_PER_HOUR - 2,
    )
    return { top, height }
  }

  return (
    <div className="bg-white rounded-[10px] border border-[#E5DDDC] overflow-hidden">
      {/* Header : jours */}
      <div
        className="grid border-b border-[#E5DDDC] bg-[#FBF6F4]"
        style={{ gridTemplateColumns: '60px repeat(5, 1fr)' }}
      >
        <div />
        {days.map((d) => {
          const isToday = toYMD(d) === todayYMD
          return (
            <div
              key={d.toISOString()}
              className="text-center py-2 border-l border-[#E5DDDC]"
              style={{
                color: isToday ? '#17494E' : '#4E1D17',
                fontWeight: isToday ? 700 : 500,
                backgroundColor: isToday ? '#EFE9E7' : 'transparent',
              }}
            >
              <div className="text-xs uppercase opacity-70">
                {d.toLocaleDateString('fr-FR', { weekday: 'long' }).slice(0, 3)}
              </div>
              <div className="text-base">{d.getDate()}</div>
            </div>
          )
        })}
      </div>

      {/* Corps : grille horaire avec RDV en overlay */}
      <div className="relative">
        {/* Grille en arrière-plan */}
        <div
          className="grid"
          style={{ gridTemplateColumns: '60px repeat(5, 1fr)' }}
        >
          {/* Colonne heures + 5 colonnes jours */}
          <div>
            {hours.map((h) => (
              <div
                key={h}
                className="text-xs text-[#A68D8A] text-right pr-2 border-b border-[#E5DDDC]"
                style={{ height: WEEK_PIXELS_PER_HOUR, lineHeight: '14px', paddingTop: 2 }}
              >
                {h.toString().padStart(2, '0')}:00
              </div>
            ))}
          </div>
          {days.map((d, di) => {
            // RDV de ce jour assignes a des 'lanes' (colonnes paralleles)
            // pour eviter le chevauchement visuel (cf. screen WinDev avec
            // 2 RDV cote a cote sur 11h-12h).
            const dayRdvs = rdvs
              .filter((r) => dayKey(r.date_debut) === toYMD(d))
              .sort((a, b) => a.date_debut.localeCompare(b.date_debut))
            const assignments = assignLanes(dayRdvs)
            return (
              <div key={di} className="relative border-l border-[#E5DDDC]">
                {hours.map((h) => (
                  <div
                    key={h}
                    className="border-b border-[#E5DDDC]"
                    style={{ height: WEEK_PIXELS_PER_HOUR }}
                  />
                ))}
                {/* RDV en overlay absolu, repartis sur N lanes */}
                {dayRdvs.map((rdv) => {
                  const pos = positionRdv(rdv)
                  if (!pos) return null
                  const a = assignments.get(rdv.id_evenement)
                  if (!a) return null
                  const hex = rdv.couleur_hex || '#A68D8A'
                  // Largeur = 100% / nbLanes, position left = lane * largeur
                  const widthPct = 100 / a.totalLanes
                  const leftPct = a.lane * widthPct
                  return (
                    <button
                      key={rdv.id_evenement}
                      type="button"
                      onClick={() => onClickRdv(rdv)}
                      className="absolute text-left rounded px-1.5 py-0.5 text-[11px] leading-tight overflow-hidden hover:brightness-95 transition-all"
                      style={{
                        top: pos.top,
                        height: pos.height,
                        left: `calc(${leftPct}% + 2px)`,
                        width: `calc(${widthPct}% - 4px)`,
                        backgroundColor: hex + '66', // 40% opacity
                        color: '#4E1D17',
                        borderLeft: `3px solid ${hex}`,
                      }}
                      title={`${rdv.titre} (${formatTime(rdv.date_debut)} - ${formatTime(rdv.date_fin)})`}
                    >
                      <div className="font-semibold truncate">{rdv.titre}</div>
                      {pos.height > 26 && (
                        <div className="opacity-80 truncate text-[10px]">
                          {formatTime(rdv.date_debut)} – {formatTime(rdv.date_fin)}
                        </div>
                      )}
                    </button>
                  )
                })}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
