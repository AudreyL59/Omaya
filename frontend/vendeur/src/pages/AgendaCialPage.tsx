import { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Calendar as CalendarIcon,
  Clock,
  MapPin,
  Phone,
  Mail,
  User,
  Navigation,
  Plus,
  Route,
  TrendingUp,
  Home,
  Building2,
  FileSignature,
  Pencil,
  Search,
  X,
  Loader2,
} from 'lucide-react'
import { getToken, getStoredUser } from '@/api'
import { useGeocode, type GeoPoint } from '@/hooks/useGeocode'
import { useRoute } from '@/hooks/useRoute'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import L from 'leaflet'

// --- Types ---------------------------------------------------------------

interface AgendaCialRDV {
  id_rdv: string
  date_debut: string
  date_fin: string
  titre: string
  contenu: string
  info_compl: string
  id_categorie: number
  lib_categorie: string
  couleur_hex: string
  id_cv_statut: number
  id_tk_liste: string
  op_crea: number
  client_civilite: number
  client_nom: string
  client_prenom: string
  client_nom_marital: string
  client_naissance: string
  client_dep_naiss: number
  client_adresse1: string
  client_adresse2: string
  client_cp: string
  client_ville: string
  client_mobile: string
  client_email: string
  client_type_logement: number
  client_pro: boolean
  client_rs: string
  client_siret: string
  type_demande: number
}

interface CommercialItem {
  id_salarie: string
  nom: string
  prenom: string
}

// --- Helpers --------------------------------------------------------------

function parseDbDate(raw: string): Date | null {
  if (!raw) return null
  const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/)
  if (iso) return new Date(+iso[1], +iso[2] - 1, +iso[3], +iso[4], +iso[5])
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

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : s
}

function civiliteLabel(c: number): string {
  return { 1: 'M.', 2: 'Mme', 3: 'Mlle' }[c] || ''
}

function logementLabel(t: number): 'Maison' | 'Appartement' | '' {
  if (t === 1) return 'Maison'
  if (t === 2) return 'Appartement'
  return ''
}

function getWeekDates(today: Date): Date[] {
  const d = new Date(today)
  const dow = (d.getDay() + 6) % 7 // Monday = 0
  d.setDate(d.getDate() - dow)
  const out: Date[] = []
  for (let i = 0; i < 5; i++) {
    const x = new Date(d)
    x.setDate(d.getDate() + i)
    out.push(x)
  }
  return out
}

function typeDemandeLabel(t: number): string {
  if (t === 20) return 'Fibre'
  if (t === 22) return 'Énergie'
  return '—'
}

function formatDuree(min: number): string {
  if (min < 60) return `${min} min`
  const h = Math.floor(min / 60)
  const m = min % 60
  return m === 0 ? `${h}h` : `${h}h ${String(m).padStart(2, '0')}`
}

// --- Page entry -----------------------------------------------------------

export default function AgendaCialPage() {
  const stored = getStoredUser()
  const [commercialId, setCommercialId] = useState<string>(
    stored?.id_salarie ? String(stored.id_salarie) : ''
  )
  const [commercialName, setCommercialName] = useState<string>(
    stored ? `${stored.nom} ${capitalize(stored.prenom)}` : ''
  )
  const [showPicker, setShowPicker] = useState(false)
  const [view, setView] = useState<'week' | 'day'>('week')
  const [weekRef, setWeekRef] = useState<Date>(new Date())
  const [selectedDay, setSelectedDay] = useState<Date | null>(null)
  const [rdvs, setRdvs] = useState<AgendaCialRDV[]>([])
  const [loading, setLoading] = useState(false)

  const weekDates = useMemo(() => getWeekDates(weekRef), [weekRef])
  const weekFrom = weekDates[0]
  const weekTo = weekDates[weekDates.length - 1]

  useEffect(() => {
    if (!commercialId) return
    const from = toYMD(weekFrom)
    const to = toYMD(weekTo)
    setLoading(true)
    fetch(
      `/api/vendeur/agenda-cial?id_commercial=${commercialId}&date_from=${from}&date_to=${to}`,
      { headers: { Authorization: `Bearer ${getToken()}` } }
    )
      .then((r) => r.json())
      .then((data: AgendaCialRDV[]) => setRdvs(data || []))
      .catch(() => setRdvs([]))
      .finally(() => setLoading(false))
  }, [commercialId, weekFrom, weekTo])

  const rdvsByDay = useMemo(() => {
    const map: Record<string, AgendaCialRDV[]> = {}
    for (const r of rdvs) {
      const k = dayKey(r.date_debut)
      if (!map[k]) map[k] = []
      map[k].push(r)
    }
    return map
  }, [rdvs])

  const goToDay = (d: Date) => {
    setSelectedDay(d)
    setView('day')
  }

  const goToWeek = () => {
    setView('week')
    setSelectedDay(null)
  }

  const shiftWeek = (n: number) => {
    const d = new Date(weekRef)
    d.setDate(d.getDate() + n * 7)
    setWeekRef(d)
  }

  return (
    <div className="p-8">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-gray-900">Agenda commercial</h1>
        <p className="text-gray-500 mt-1">
          {view === 'week'
            ? 'Planification de la semaine'
            : selectedDay
              ? `RDV du ${selectedDay.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })}`
              : ''}
        </p>
      </motion.div>

      <div className="mt-6">
        <AnimatePresence mode="wait">
          {view === 'week' ? (
            <motion.div
              key="week"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <WeekView
                weekDates={weekDates}
                rdvsByDay={rdvsByDay}
                loading={loading}
                commercialName={commercialName}
                onPickCommercial={() => setShowPicker(true)}
                onShiftWeek={shiftWeek}
                onSelectDay={goToDay}
              />
            </motion.div>
          ) : (
            <motion.div
              key="day"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <DayView
                day={selectedDay!}
                rdvs={rdvsByDay[toYMD(selectedDay!)] || []}
                commercialName={commercialName}
                onPickCommercial={() => setShowPicker(true)}
                onBack={goToWeek}
                onShiftDay={(n) => {
                  const nd = new Date(selectedDay!)
                  nd.setDate(nd.getDate() + n)
                  setSelectedDay(nd)
                  const weekOfNd = getWeekDates(nd)
                  if (weekOfNd[0].getTime() !== weekFrom.getTime()) {
                    setWeekRef(nd)
                  }
                }}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {showPicker && (
          <CommercialPicker
            onClose={() => setShowPicker(false)}
            onSelect={(c) => {
              setCommercialId(c.id_salarie)
              setCommercialName(`${c.nom} ${capitalize(c.prenom)}`)
              setShowPicker(false)
            }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

// --- Week view ------------------------------------------------------------

function WeekView({
  weekDates,
  rdvsByDay,
  loading,
  commercialName,
  onPickCommercial,
  onShiftWeek,
  onSelectDay,
}: {
  weekDates: Date[]
  rdvsByDay: Record<string, AgendaCialRDV[]>
  loading: boolean
  commercialName: string
  onPickCommercial: () => void
  onShiftWeek: (n: number) => void
  onSelectDay: (d: Date) => void
}) {
  const allRdvs = Object.values(rdvsByDay).flat()
  const weekNum = getISOWeek(weekDates[0])
  const from = weekDates[0]
  const to = weekDates[weekDates.length - 1]

  return (
    <div className="max-w-7xl">
      {/* Toolbar */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4 flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <button onClick={() => onShiftWeek(-1)} className="p-1.5 rounded-lg hover:bg-gray-100">
            <ChevronLeft className="w-4 h-4 text-gray-600" />
          </button>
          <div className="flex items-center gap-2 px-3 py-1.5 border border-gray-200 rounded-lg text-sm">
            <CalendarIcon className="w-4 h-4 text-gray-400" />
            <span className="font-medium">
              Semaine {weekNum} · {from.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })} → {to.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })}
            </span>
          </div>
          <button onClick={() => onShiftWeek(1)} className="p-1.5 rounded-lg hover:bg-gray-100">
            <ChevronRight className="w-4 h-4 text-gray-600" />
          </button>
        </div>

        <div className="h-6 w-px bg-gray-200 mx-1" />

        <button
          onClick={onPickCommercial}
          className="flex items-center gap-2 px-3 py-1.5 border border-gray-200 rounded-lg text-sm text-gray-700 hover:bg-gray-50"
        >
          <User className="w-4 h-4 text-gray-400" />
          <span className="font-medium">{commercialName || 'Choisir commercial'}</span>
          <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
        </button>

        <div className="flex-1" />

        <button className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 shadow-sm">
          <Plus className="w-4 h-4" />
          Nouveau RDV
        </button>
      </div>

      {/* Stats semaine */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        <StatCard label="RDV semaine" value={String(allRdvs.length)} icon={<CalendarIcon className="w-4 h-4" />} accent="text-gray-900" />
        <StatCard label="Jours chargés" value={String(weekDates.filter(d => (rdvsByDay[toYMD(d)] || []).length > 0).length)} icon={<TrendingUp className="w-4 h-4" />} accent="text-emerald-600" />
        <StatCard label="Moyenne/jour" value={`${(allRdvs.length / 5).toFixed(1)} RDV`} icon={<Clock className="w-4 h-4" />} accent="text-blue-600" />
      </div>

      {/* Jours */}
      {loading ? (
        <div className="flex items-center justify-center py-20 bg-white rounded-xl border border-gray-200">
          <Loader2 className="w-6 h-6 text-gray-300 animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-5 gap-3">
          {weekDates.map((d, i) => (
            <DayColumn
              key={i}
              date={d}
              rdvs={rdvsByDay[toYMD(d)] || []}
              onClick={() => onSelectDay(d)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function DayColumn({
  date,
  rdvs,
  onClick,
}: {
  date: Date
  rdvs: AgendaCialRDV[]
  onClick: () => void
}) {
  const label = date.toLocaleDateString('fr-FR', { weekday: 'long' })
  const dateStr = date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' })
  const isToday = toYMD(date) === toYMD(new Date())

  return (
    <motion.div
      onClick={onClick}
      whileHover={{ y: -2 }}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onClick()}
      className={`bg-white rounded-xl border overflow-hidden flex flex-col cursor-pointer hover:shadow-md transition-all ${
        isToday ? 'border-gray-900 ring-2 ring-gray-900/5' : 'border-gray-200 hover:border-gray-300'
      }`}
    >
      <div className={`px-3 py-2.5 border-b border-gray-200 ${isToday ? 'bg-gray-900 text-white' : 'bg-gray-50'}`}>
        <div className={`text-xs uppercase tracking-wide ${isToday ? 'text-gray-300' : 'text-gray-500'}`}>
          {label}
        </div>
        <div className={`text-sm font-semibold mt-0.5 ${isToday ? 'text-white' : 'text-gray-900'}`}>
          {dateStr}
        </div>
        <div className={`flex items-center gap-3 mt-2 text-[10px] ${isToday ? 'text-gray-300' : 'text-gray-500'}`}>
          <span className="flex items-center gap-1">
            <CalendarIcon className="w-3 h-3" />
            {rdvs.length} RDV
          </span>
        </div>
      </div>

      <div className="p-2 space-y-2 flex-1 min-h-[400px]">
        {rdvs.length === 0 ? (
          <div className="text-center py-8 text-gray-300 text-xs italic">Aucun RDV</div>
        ) : (
          rdvs.map((rdv) => {
            const name = `${rdv.client_nom} ${capitalize(rdv.client_prenom)}`.trim() || rdv.titre
            return (
              <div
                key={rdv.id_rdv}
                className="bg-white border border-gray-100 rounded-lg p-2 hover:shadow-sm hover:border-gray-300"
              >
                <div className="flex items-center gap-1.5 mb-1">
                  <span
                    className="w-1.5 h-1.5 rounded-full"
                    style={{ backgroundColor: rdv.couleur_hex }}
                  />
                  <span className="text-xs font-semibold text-gray-900">
                    {formatTime(rdv.date_debut)}
                  </span>
                </div>
                <div className="text-xs font-medium text-gray-900 truncate">{name}</div>
                {rdv.client_ville && (
                  <div className="flex items-center gap-1 text-[10px] text-gray-500 mt-0.5">
                    <MapPin className="w-2.5 h-2.5" />
                    {rdv.client_ville}
                  </div>
                )}
                <div className="mt-1.5">
                  <span
                    className="text-[9px] px-1.5 py-0.5 rounded-full border"
                    style={{
                      color: rdv.couleur_hex,
                      borderColor: rdv.couleur_hex + '40',
                      backgroundColor: rdv.couleur_hex + '10',
                    }}
                  >
                    {rdv.lib_categorie}
                  </span>
                </div>
              </div>
            )
          })
        )}
      </div>
    </motion.div>
  )
}

// --- Day view -------------------------------------------------------------

function DayView({
  day,
  rdvs,
  commercialName,
  onPickCommercial,
  onBack,
  onShiftDay,
}: {
  day: Date
  rdvs: AgendaCialRDV[]
  commercialName: string
  onPickCommercial: () => void
  onBack: () => void
  onShiftDay: (n: number) => void
}) {
  const [selectedRdv, setSelectedRdv] = useState<string | null>(rdvs[0]?.id_rdv || null)
  const dayLabel = day.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

  const addresses = rdvs.map(buildAddress)
  const { points } = useGeocode(addresses)

  const geocoded = rdvs
    .map((rdv, i) => {
      const pt = points.get(addresses[i])
      return pt ? { rdv, pt, idx: i + 1 } : null
    })
    .filter((x): x is { rdv: AgendaCialRDV; pt: GeoPoint; idx: number } => x !== null)

  const { legs } = useRoute(geocoded.map((g) => g.pt))

  // Map : id_rdv → leg vers le RDV suivant
  const legToNext = useMemo(() => {
    const m: Record<string, { distance_m: number; duration_s: number }> = {}
    for (let i = 0; i < geocoded.length - 1; i++) {
      const leg = legs[i]
      if (leg) m[geocoded[i].rdv.id_rdv] = leg
    }
    return m
  }, [geocoded, legs])

  return (
    <div className="max-w-7xl">
      {/* Toolbar */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4 flex items-center gap-3 flex-wrap">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
          Retour semaine
        </button>

        <div className="h-6 w-px bg-gray-200 mx-1" />

        <div className="flex items-center gap-2">
          <button onClick={() => onShiftDay(-1)} className="p-1.5 rounded-lg hover:bg-gray-100">
            <ChevronLeft className="w-4 h-4 text-gray-600" />
          </button>
          <div className="flex items-center gap-2 px-3 py-1.5 border border-gray-200 rounded-lg text-sm">
            <CalendarIcon className="w-4 h-4 text-gray-400" />
            <span className="font-medium capitalize">{dayLabel}</span>
          </div>
          <button onClick={() => onShiftDay(1)} className="p-1.5 rounded-lg hover:bg-gray-100">
            <ChevronRight className="w-4 h-4 text-gray-600" />
          </button>
        </div>

        <div className="h-6 w-px bg-gray-200 mx-1" />

        <button
          onClick={onPickCommercial}
          className="flex items-center gap-2 px-3 py-1.5 border border-gray-200 rounded-lg text-sm text-gray-700 hover:bg-gray-50"
        >
          <User className="w-4 h-4 text-gray-400" />
          <span className="font-medium">{commercialName}</span>
          <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
        </button>

        <div className="flex-1" />

        <button className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 shadow-sm">
          <Plus className="w-4 h-4" />
          Nouveau RDV
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3 mb-4">
        <StatCard label="RDV du jour" value={String(rdvs.length)} icon={<CalendarIcon className="w-4 h-4" />} accent="text-gray-900" />
        <StatCard
          label="Distance totale"
          value={`${(legs.reduce((a, l) => a + l.distance_m, 0) / 1000).toFixed(1)} km`}
          icon={<Route className="w-4 h-4" />}
          accent="text-blue-600"
        />
        <StatCard
          label="Trajet cumulé"
          value={formatDuree(Math.round(legs.reduce((a, l) => a + l.duration_s, 0) / 60))}
          icon={<Clock className="w-4 h-4" />}
          accent="text-amber-600"
        />
        <StatCard label="Pros" value={String(rdvs.filter(r => r.client_pro).length)} icon={<Building2 className="w-4 h-4" />} accent="text-emerald-600" />
      </div>

      {/* Main split */}
      <div className="grid grid-cols-[minmax(0,1fr),minmax(0,1.2fr)] gap-4">
        <div className="space-y-3">
          {rdvs.length === 0 ? (
            <div className="text-center py-12 text-gray-400 text-sm bg-white rounded-xl border border-gray-200">
              Aucun RDV sur cette journée
            </div>
          ) : (
            rdvs.map((rdv, i) => (
              <RdvCard
                key={rdv.id_rdv}
                rdv={rdv}
                index={i + 1}
                selected={selectedRdv === rdv.id_rdv}
                onClick={() => setSelectedRdv(rdv.id_rdv)}
                legToNext={legToNext[rdv.id_rdv]}
              />
            ))
          )}
        </div>

        {/* Carte */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden sticky top-4 h-[calc(100vh-14rem)]">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-900">
              <MapPin className="w-4 h-4 text-gray-400" />
              Itinéraire du jour
            </div>
          </div>
          <MapReal rdvs={rdvs} selectedId={selectedRdv} onSelect={setSelectedRdv} />
        </div>
      </div>
    </div>
  )
}

function RdvCard({
  rdv,
  index,
  selected,
  onClick,
  legToNext,
}: {
  rdv: AgendaCialRDV
  index: number
  selected: boolean
  onClick: () => void
  legToNext?: { distance_m: number; duration_s: number }
}) {
  const time = formatTime(rdv.date_debut)
  const duration = durationMin(rdv.date_debut, rdv.date_fin)
  const civ = civiliteLabel(rdv.client_civilite)
  const logement = logementLabel(rdv.client_type_logement)
  const name = `${civ} ${rdv.client_nom} ${capitalize(rdv.client_prenom)}`.trim() || rdv.titre
  const fullAddr = [rdv.client_adresse1, rdv.client_cp, rdv.client_ville].filter(Boolean).join(', ')

  return (
    <>
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.005 }}
      className={`w-full text-left bg-white rounded-xl border transition-all ${
        selected ? 'border-gray-900 shadow-md ring-2 ring-gray-900/5' : 'border-gray-200 hover:border-gray-300'
      }`}
    >
      <div className="px-4 py-3 flex items-start gap-3">
        <div className="shrink-0 flex flex-col items-center gap-1">
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white"
            style={{ backgroundColor: rdv.couleur_hex }}
          >
            {index}
          </div>
          {duration > 0 && <div className="text-[10px] text-gray-400">{duration}min</div>}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="font-semibold text-gray-900 text-sm">{time}</span>
            <span
              className="px-1.5 py-0.5 rounded-full text-[10px] font-medium border"
              style={{
                color: rdv.couleur_hex,
                borderColor: rdv.couleur_hex + '40',
                backgroundColor: rdv.couleur_hex + '10',
              }}
            >
              {rdv.lib_categorie}
            </span>
            <span className="text-[10px] text-gray-400">· {typeDemandeLabel(rdv.type_demande)}</span>
          </div>
          <div className="font-medium text-gray-900 text-sm">{name}</div>
          {rdv.client_pro && rdv.client_rs && (
            <div className="text-xs text-gray-600 mt-0.5">{rdv.client_rs}</div>
          )}
          {fullAddr && (
            <div className="flex items-center gap-1 text-xs text-gray-500 mt-1">
              {logement === 'Maison' ? <Home className="w-3 h-3" /> : logement === 'Appartement' ? <Building2 className="w-3 h-3" /> : <MapPin className="w-3 h-3" />}
              <span>{fullAddr}</span>
            </div>
          )}
        </div>
      </div>

      {selected && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="border-t border-gray-100 px-4 py-2.5 flex items-center gap-2 flex-wrap overflow-hidden"
        >
          {rdv.client_mobile && (
            <a
              href={`tel:${rdv.client_mobile}`}
              onClick={(e) => e.stopPropagation()}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-700 bg-gray-50 hover:bg-gray-100 rounded-lg"
            >
              <Phone className="w-3.5 h-3.5" />
              {rdv.client_mobile}
            </a>
          )}
          {rdv.client_email && (
            <a
              href={`mailto:${rdv.client_email}`}
              onClick={(e) => e.stopPropagation()}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-700 bg-gray-50 hover:bg-gray-100 rounded-lg"
            >
              <Mail className="w-3.5 h-3.5" />
              Mail
            </a>
          )}
          {fullAddr && (
            <a
              href={`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(fullAddr)}`}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg"
            >
              <Navigation className="w-3.5 h-3.5" />
              Y aller
            </a>
          )}
          <div className="flex-1" />
          <button
            onClick={(e) => e.stopPropagation()}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700"
            title="Modifier"
          >
            <Pencil className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-white bg-gray-900 hover:bg-gray-800 rounded-lg"
          >
            <FileSignature className="w-3.5 h-3.5" />
            Souscription
          </button>
        </motion.div>
      )}
    </motion.button>
    {legToNext && (
      <div className="flex items-center justify-center gap-2 py-1.5 text-xs text-gray-500">
        <div className="flex-1 border-t border-dashed border-gray-300 ml-10" />
        <div className="flex items-center gap-1.5 px-2 py-0.5 bg-blue-50 border border-blue-100 rounded-full text-blue-700 font-medium">
          <Route className="w-3 h-3" />
          {(legToNext.distance_m / 1000).toFixed(1)} km
          <span className="text-blue-300">·</span>
          <Clock className="w-3 h-3" />
          {formatDuree(Math.max(1, Math.round(legToNext.duration_s / 60)))}
        </div>
        <div className="flex-1 border-t border-dashed border-gray-300 mr-4" />
      </div>
    )}
    </>
  )
}

function buildAddress(rdv: AgendaCialRDV): string {
  return [rdv.client_adresse1, rdv.client_cp, rdv.client_ville]
    .filter(Boolean)
    .join(', ')
}

function numberedIcon(n: number, color: string, highlighted: boolean): L.DivIcon {
  const size = highlighted ? 38 : 32
  const ring = highlighted ? 4 : 2
  return L.divIcon({
    className: '',
    html: `
      <div style="
        width: ${size}px;
        height: ${size}px;
        background: ${color};
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 700;
        font-size: ${highlighted ? 14 : 12}px;
        border: ${ring}px solid white;
        box-shadow: 0 4px 10px rgba(0,0,0,0.25);
        transform: translate(-50%, -100%);
        position: relative;
      ">${n}</div>
    `,
    iconSize: [size, size],
    iconAnchor: [0, 0],
  })
}

function FitBounds({ points }: { points: GeoPoint[] }) {
  const map = useMap()
  useEffect(() => {
    if (points.length === 0) return
    if (points.length === 1) {
      map.setView([points[0].lat, points[0].lon], 13)
      return
    }
    const bounds = L.latLngBounds(points.map((p) => [p.lat, p.lon]))
    map.fitBounds(bounds, { padding: [40, 40] })
  }, [points, map])
  return null
}

function MapReal({
  rdvs,
  selectedId,
  onSelect,
}: {
  rdvs: AgendaCialRDV[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  const addresses = rdvs.map(buildAddress)
  const { points, loading } = useGeocode(addresses)

  const geocoded = rdvs
    .map((rdv, i) => {
      const addr = addresses[i]
      const pt = points.get(addr)
      return pt ? { rdv, pt, idx: i + 1 } : null
    })
    .filter((x): x is { rdv: AgendaCialRDV; pt: GeoPoint; idx: number } => x !== null)

  const { line: routeLine, loading: routeLoading } = useRoute(
    geocoded.map((g) => g.pt)
  )

  // Fallback : ligne droite si pas de route calculée
  const polyline: [number, number][] =
    routeLine.length > 0
      ? routeLine
      : geocoded.map((g) => [g.pt.lat, g.pt.lon] as [number, number])

  // Centre par défaut France
  const defaultCenter: [number, number] = [46.6, 2.5]

  return (
    <div className="relative w-full h-full">
      <MapContainer
        center={defaultCenter}
        zoom={6}
        scrollWheelZoom
        className="w-full h-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {polyline.length > 1 && (
          <Polyline
            positions={polyline}
            pathOptions={{
              color: '#3b82f6',
              weight: 4,
              opacity: routeLine.length > 0 ? 0.7 : 0.4,
              dashArray: routeLine.length > 0 ? undefined : '8 6',
            }}
          />
        )}

        {geocoded.map(({ rdv, pt, idx }) => {
          const isSel = selectedId === rdv.id_rdv
          return (
            <Marker
              key={rdv.id_rdv}
              position={[pt.lat, pt.lon]}
              icon={numberedIcon(idx, rdv.couleur_hex || '#6b7280', isSel)}
              eventHandlers={{ click: () => onSelect(rdv.id_rdv) }}
            >
              <Popup>
                <div className="text-xs font-semibold text-gray-900">
                  {formatTime(rdv.date_debut)} · {rdv.client_nom}{' '}
                  {capitalize(rdv.client_prenom).charAt(0)}.
                </div>
                <div className="text-[10px] text-gray-500 mt-0.5">
                  {rdv.client_adresse1}
                  <br />
                  {rdv.client_cp} {rdv.client_ville}
                </div>
              </Popup>
            </Marker>
          )
        })}

        <FitBounds points={geocoded.map((g) => g.pt)} />
      </MapContainer>

      {(loading || routeLoading) && (
        <div className="absolute top-3 right-3 bg-white/95 rounded-lg shadow-sm border border-gray-200 text-xs text-gray-600 px-3 py-1.5 flex items-center gap-2 z-[400]">
          <Loader2 className="w-3 h-3 animate-spin" />
          {loading ? 'Géocodage...' : 'Calcul itinéraire...'}
        </div>
      )}
      {!loading && !routeLoading && geocoded.length < rdvs.length && (
        <div className="absolute top-3 right-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700 px-3 py-1.5 z-[400]">
          {rdvs.length - geocoded.length} adresse(s) non localisée(s)
        </div>
      )}
    </div>
  )
}

// --- Commercial picker ---------------------------------------------------

function CommercialPicker({
  onClose,
  onSelect,
}: {
  onClose: () => void
  onSelect: (c: CommercialItem) => void
}) {
  const [search, setSearch] = useState('')
  const [results, setResults] = useState<CommercialItem[]>([])
  const [selected, setSelected] = useState<CommercialItem | null>(null)
  const [loading, setLoading] = useState(false)

  const doSearch = () => {
    if (!search.trim()) return
    setLoading(true)
    fetch(
      `/api/vendeur/agenda-cial/commerciaux?q=${encodeURIComponent(search.trim())}`,
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
          <h2 className="text-lg font-semibold text-gray-900">Choisir le commercial</h2>
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
              placeholder="Nom du commercial"
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
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4 text-gray-700" />}
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

// --- Shared utilities -----------------------------------------------------

function StatCard({
  label,
  value,
  icon,
  accent,
}: {
  label: string
  value: string
  icon: React.ReactNode
  accent: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 px-4 py-3 flex items-center gap-3">
      <div className={`p-2 rounded-lg bg-gray-50 ${accent}`}>{icon}</div>
      <div>
        <div className={`text-xl font-bold ${accent}`}>{value}</div>
        <div className="text-xs text-gray-500">{label}</div>
      </div>
    </div>
  )
}

function getISOWeek(d: Date): number {
  const date = new Date(d)
  date.setHours(0, 0, 0, 0)
  date.setDate(date.getDate() + 3 - ((date.getDay() + 6) % 7))
  const week1 = new Date(date.getFullYear(), 0, 4)
  return (
    1 +
    Math.round(
      ((date.getTime() - week1.getTime()) / 86400000 -
        3 +
        ((week1.getDay() + 6) % 7)) /
        7
    )
  )
}
