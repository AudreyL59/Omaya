/**
 * Vue agenda semaine d'un recruteur — sous-composant de EntretienAjoutModal.
 *
 * Affiche une grille jours (lun-dim) x heures (07h-19h, slots 30min) avec
 * les RDV positionnes en blocs colores par categorie.
 * Click sur un slot libre -> callback(date, heure) pour pre-remplir le form.
 */

import { useEffect, useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react'
import { getToken } from '@/api'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

const HOUR_START = 7
const HOUR_END = 19
const SLOT_PX = 24    // hauteur d'un slot de 30min
const DAYS = ['lun', 'mar', 'mer', 'jeu', 'ven', 'sam', 'dim']

interface AgendaEvent {
  id_agenda_evenement: string
  titre: string
  contenu: string
  date_debut: string
  date_fin: string
  lib_categorie: string
  couleur_r: number
  couleur_v: number
  couleur_b: number
  lib_lieu: string
  adresse_complete: string
  op_crea_nom: string
}

interface RecruteurAgendaProps {
  apiBase: string
  idRecruteur: string
  semaineDu: string                // YYYY-MM-DD a l'interieur de la semaine
  highlightDate?: string           // YYYY-MM-DD (le date selectionne dans le form)
  highlightHeure?: string          // HH:MM
  onSelectSlot: (date: string, heure: string) => void
  onChangeSemaine: (lundi: string) => void
}

export default function RecruteurAgenda({
  apiBase, idRecruteur, semaineDu, highlightDate, highlightHeure,
  onSelectSlot, onChangeSemaine,
}: RecruteurAgendaProps) {
  const [events, setEvents] = useState<AgendaEvent[]>([])
  const [loading, setLoading] = useState(false)

  // Calcule le lundi de la semaine
  const lundi = useMemo(() => mondayOf(semaineDu), [semaineDu])
  const semaineNum = useMemo(() => weekNumber(lundi), [lundi])
  const lundiLabel = useMemo(() => {
    const d = new Date(`${lundi}T00:00:00`)
    return d.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })
  }, [lundi])

  const days = useMemo(() => {
    const arr: { date: string; jour: string; numero: number }[] = []
    const base = new Date(`${lundi}T00:00:00`)
    for (let i = 0; i < 7; i++) {
      const d = new Date(base)
      d.setDate(base.getDate() + i)
      arr.push({
        date: d.toISOString().slice(0, 10),
        jour: DAYS[i],
        numero: d.getDate(),
      })
    }
    return arr
  }, [lundi])

  useEffect(() => {
    if (!idRecruteur) { setEvents([]); return }
    setLoading(true)
    fetch(
      `${apiBase}/recrutement/cv/entretien/agenda/${idRecruteur}?semaine_du=${lundi}`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
      .then(r => r.ok ? r.json() : [])
      .then((d: AgendaEvent[]) => setEvents(Array.isArray(d) ? d : []))
      .finally(() => setLoading(false))
  }, [apiBase, idRecruteur, lundi])

  const slotsByDay = useMemo(() => {
    // Regroupe les events par jour + calcule top + height en pixels
    const out: Record<string, Array<AgendaEvent & { top: number; height: number }>> = {}
    days.forEach(d => { out[d.date] = [] })
    events.forEach(e => {
      const deb = new Date(e.date_debut.replace(' ', 'T'))
      const fin = new Date(e.date_fin.replace(' ', 'T'))
      const dateKey = deb.toISOString().slice(0, 10)
      if (!out[dateKey]) return
      const minDeb = deb.getHours() * 60 + deb.getMinutes()
      const minFin = fin.getHours() * 60 + fin.getMinutes()
      const startMin = HOUR_START * 60
      const top = Math.max(0, (minDeb - startMin) / 30 * SLOT_PX)
      const height = Math.max(SLOT_PX / 2, (minFin - minDeb) / 30 * SLOT_PX)
      out[dateKey].push({ ...e, top, height })
    })
    return out
  }, [events, days])

  const goToWeek = (offsetDays: number) => {
    const d = new Date(`${lundi}T00:00:00`)
    d.setDate(d.getDate() + offsetDays)
    onChangeSemaine(d.toISOString().slice(0, 10))
  }

  const handleSlotClick = (date: string, hour: number, minute: number) => {
    const hh = String(hour).padStart(2, '0')
    const mm = String(minute).padStart(2, '0')
    onSelectSlot(date, `${hh}:${mm}`)
  }

  const totalHours = HOUR_END - HOUR_START
  const totalSlots = totalHours * 2

  return (
    <div className="flex flex-col h-full">
      {/* HEADER */}
      <div className="px-3 py-2 border-b flex items-center gap-2"
           style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
        <button type="button" onClick={() => goToWeek(-7)}
                className="p-1 rounded hover:bg-white">
          <ChevronLeft className="w-4 h-4" style={{ color: COL_BRUN }} />
        </button>
        <div className="flex-1 text-center">
          <div className="text-sm font-semibold capitalize" style={{ color: COL_BRUN }}>
            {lundiLabel}
          </div>
          <div className="text-xs" style={{ color: COL_PRIMARY }}>
            Semaine {semaineNum}
          </div>
        </div>
        <button type="button" onClick={() => goToWeek(7)}
                className="p-1 rounded hover:bg-white">
          <ChevronRight className="w-4 h-4" style={{ color: COL_BRUN }} />
        </button>
        <button type="button"
                onClick={() => onChangeSemaine(new Date().toISOString().slice(0, 10))}
                className="text-xs px-2 py-1 rounded border hover:bg-white"
                style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
          Auj.
        </button>
      </div>

      {/* GRID */}
      <div className="flex-1 overflow-auto relative" style={{ backgroundColor: 'white' }}>
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/70 z-10">
            <Loader2 className="w-5 h-5 animate-spin" style={{ color: COL_PRIMARY }} />
          </div>
        )}
        <div className="grid"
             style={{ gridTemplateColumns: `40px repeat(7, 1fr)` }}>
          {/* En-tete jours */}
          <div className="sticky top-0 z-[1]" style={{ backgroundColor: COL_BG_SOFT }} />
          {days.map(d => (
            <div key={d.date}
                 className="sticky top-0 z-[1] text-xs text-center py-1 border-b border-l"
                 style={{
                   backgroundColor: highlightDate === d.date ? '#E0EBED' : COL_BG_SOFT,
                   borderColor: COL_BORDER,
                   color: COL_BRUN,
                 }}>
              <div className="capitalize">{d.jour}</div>
              <div className="font-semibold">{d.numero}</div>
            </div>
          ))}

          {/* Colonne heures + cellules jours */}
          {Array.from({ length: totalSlots }).map((_, slotIdx) => {
            const isHalf = slotIdx % 2 === 0
            const hour = HOUR_START + Math.floor(slotIdx / 2)
            const minute = slotIdx % 2 === 0 ? 0 : 30
            return (
              <ContextualSlotRow key={slotIdx}
                                 hour={hour} minute={minute}
                                 isFullHour={isHalf}
                                 days={days}
                                 highlightDate={highlightDate}
                                 highlightHeure={highlightHeure}
                                 onSlotClick={handleSlotClick} />
            )
          })}
        </div>

        {/* Events absolus par jour : on les place par-dessus la grille via flex */}
        <div className="absolute pointer-events-none"
             style={{ top: 30, left: 40, right: 0, bottom: 0 }}>
          <div className="grid h-full"
               style={{ gridTemplateColumns: 'repeat(7, 1fr)' }}>
            {days.map(d => (
              <div key={d.date} className="relative border-l"
                   style={{ borderColor: COL_BORDER }}>
                {slotsByDay[d.date]?.map(e => (
                  <div key={e.id_agenda_evenement}
                       className="absolute left-0.5 right-0.5 rounded text-[10px] p-1 overflow-hidden cursor-default"
                       style={{
                         top: e.top, height: e.height,
                         backgroundColor: `rgb(${e.couleur_r},${e.couleur_v},${e.couleur_b})`,
                         color: ((e.couleur_r + e.couleur_v + e.couleur_b) / 3) < 128 ? 'white' : COL_BRUN,
                         pointerEvents: 'auto',
                       }}
                       title={`${e.titre}\n${e.lib_lieu || ''} ${e.adresse_complete || ''}\nOpé : ${e.op_crea_nom}`}>
                    <div className="font-semibold truncate">
                      {e.date_debut.slice(11, 16)} {e.titre}
                    </div>
                    {e.lib_lieu && (
                      <div className="truncate">{e.lib_lieu}</div>
                    )}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// Sous-composant ligne de slot (1 ligne d'heures = 7 cellules cliquables)
function ContextualSlotRow({ hour, minute, isFullHour, days, highlightDate, highlightHeure, onSlotClick }: {
  hour: number
  minute: number
  isFullHour: boolean
  days: { date: string; jour: string; numero: number }[]
  highlightDate?: string
  highlightHeure?: string
  onSlotClick: (date: string, hour: number, minute: number) => void
}) {
  const hh = String(hour).padStart(2, '0')
  const mm = String(minute).padStart(2, '0')
  const heureCle = `${hh}:${mm}`
  return (
    <>
      <div className="text-[10px] text-right pr-1 border-b"
           style={{
             height: SLOT_PX,
             borderColor: COL_BORDER,
             color: isFullHour ? COL_BRUN : '#A68D8A',
           }}>
        {isFullHour ? `${hh}:00` : ''}
      </div>
      {days.map(d => {
        const isHighlight = highlightDate === d.date && highlightHeure === heureCle
        return (
          <button key={d.date} type="button"
                  onClick={() => onSlotClick(d.date, hour, minute)}
                  className="border-b border-l hover:bg-blue-50"
                  style={{
                    height: SLOT_PX,
                    borderColor: COL_BORDER,
                    backgroundColor: isHighlight ? '#BFDBFE' : 'transparent',
                  }} />
        )
      })}
    </>
  )
}

// ============================================================================
// Helpers date
// ============================================================================

function mondayOf(yyyymmdd: string): string {
  const d = new Date(`${yyyymmdd}T00:00:00`)
  const dow = (d.getDay() + 6) % 7  // 0 = lundi
  d.setDate(d.getDate() - dow)
  return d.toISOString().slice(0, 10)
}

function weekNumber(yyyymmdd: string): number {
  const d = new Date(`${yyyymmdd}T00:00:00`)
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() + 4 - ((d.getDay() + 6) % 7 + 1))
  const yearStart = new Date(d.getFullYear(), 0, 1)
  return Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7)
}
