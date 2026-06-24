/**
 * Vue agenda JOUR d'un recruteur — sous-composant de EntretienAjoutModal.
 *
 * Affiche une grille heures (07h-19h, slots 30min) du jour selectionne
 * avec les RDV positionnes en blocs colores par categorie.
 * Click sur un slot libre -> callback(date, heure) pour pre-remplir le form.
 * Navigation < / > / 'Auj.' pour changer de jour.
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
const SLOT_PX = 30    // hauteur d'un slot de 30min (un peu plus grand en vue jour)

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
  jour: string                     // YYYY-MM-DD du jour affiche
  highlightHeure?: string          // HH:MM (le heure selectionne dans le form)
  onSelectSlot: (date: string, heure: string) => void
  onChangeJour: (date: string) => void
}

export default function RecruteurAgenda({
  apiBase, idRecruteur, jour, highlightHeure,
  onSelectSlot, onChangeJour,
}: RecruteurAgendaProps) {
  const [events, setEvents] = useState<AgendaEvent[]>([])
  const [loading, setLoading] = useState(false)

  const jourLabel = useMemo(() => {
    const d = new Date(`${jour}T00:00:00`)
    return d.toLocaleDateString('fr-FR', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    })
  }, [jour])

  useEffect(() => {
    if (!idRecruteur) { setEvents([]); return }
    setLoading(true)
    fetch(
      `${apiBase}/recrutement/cv/entretien/agenda/${idRecruteur}?semaine_du=${jour}`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
      .then(r => r.ok ? r.json() : [])
      .then((d: AgendaEvent[]) => {
        // Filtre uniquement les events du jour selectionne
        const filtered = (Array.isArray(d) ? d : []).filter(e =>
          e.date_debut.slice(0, 10) === jour,
        )
        setEvents(filtered)
      })
      .finally(() => setLoading(false))
  }, [apiBase, idRecruteur, jour])

  const eventsPositioned = useMemo(() => {
    return events.map(e => {
      const deb = new Date(e.date_debut.replace(' ', 'T'))
      const fin = new Date(e.date_fin.replace(' ', 'T'))
      const minDeb = deb.getHours() * 60 + deb.getMinutes()
      const minFin = fin.getHours() * 60 + fin.getMinutes()
      const startMin = HOUR_START * 60
      const top = Math.max(0, (minDeb - startMin) / 30 * SLOT_PX)
      const height = Math.max(SLOT_PX / 2, (minFin - minDeb) / 30 * SLOT_PX)
      return { ...e, top, height }
    })
  }, [events])

  const goToDay = (offsetDays: number) => {
    const d = new Date(`${jour}T00:00:00`)
    d.setDate(d.getDate() + offsetDays)
    onChangeJour(d.toISOString().slice(0, 10))
  }

  const handleSlotClick = (hour: number, minute: number) => {
    const hh = String(hour).padStart(2, '0')
    const mm = String(minute).padStart(2, '0')
    onSelectSlot(jour, `${hh}:${mm}`)
  }

  const totalSlots = (HOUR_END - HOUR_START) * 2

  return (
    <div className="flex flex-col h-full">
      {/* HEADER */}
      <div className="px-3 py-2 border-b flex items-center gap-2"
           style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
        <button type="button" onClick={() => goToDay(-1)}
                className="p-1 rounded hover:bg-white">
          <ChevronLeft className="w-4 h-4" style={{ color: COL_BRUN }} />
        </button>
        <div className="flex-1 text-center text-sm font-semibold capitalize"
             style={{ color: COL_BRUN }}>
          {jourLabel}
        </div>
        <button type="button" onClick={() => goToDay(1)}
                className="p-1 rounded hover:bg-white">
          <ChevronRight className="w-4 h-4" style={{ color: COL_BRUN }} />
        </button>
        <button type="button"
                onClick={() => onChangeJour(new Date().toISOString().slice(0, 10))}
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
             style={{ gridTemplateColumns: '60px 1fr' }}>
          {Array.from({ length: totalSlots }).map((_, slotIdx) => {
            const isFullHour = slotIdx % 2 === 0
            const hour = HOUR_START + Math.floor(slotIdx / 2)
            const minute = slotIdx % 2 === 0 ? 0 : 30
            const hh = String(hour).padStart(2, '0')
            const mm = String(minute).padStart(2, '0')
            const heureCle = `${hh}:${mm}`
            const isHighlight = highlightHeure === heureCle
            return (
              <div key={slotIdx} className="contents">
                <div className="text-xs text-right pr-2 border-b"
                     style={{
                       height: SLOT_PX,
                       borderColor: COL_BORDER,
                       color: isFullHour ? COL_BRUN : '#A68D8A',
                       lineHeight: `${SLOT_PX}px`,
                     }}>
                  {isFullHour ? `${hh}:00` : ''}
                </div>
                <button type="button"
                        onClick={() => handleSlotClick(hour, minute)}
                        className="border-b border-l hover:bg-blue-50"
                        style={{
                          height: SLOT_PX,
                          borderColor: COL_BORDER,
                          backgroundColor: isHighlight ? '#BFDBFE' : 'transparent',
                        }} />
              </div>
            )
          })}
        </div>

        {/* Events absolus (par-dessus la grille) */}
        <div className="absolute pointer-events-none"
             style={{ top: 0, left: 60, right: 0, bottom: 0 }}>
          <div className="relative h-full border-l"
               style={{ borderColor: COL_BORDER }}>
            {eventsPositioned.map(e => (
              <div key={e.id_agenda_evenement}
                   className="absolute left-1 right-1 rounded text-xs p-1.5 overflow-hidden"
                   style={{
                     top: e.top, height: e.height,
                     backgroundColor: `rgb(${e.couleur_r},${e.couleur_v},${e.couleur_b})`,
                     color: ((e.couleur_r + e.couleur_v + e.couleur_b) / 3) < 128 ? 'white' : COL_BRUN,
                     pointerEvents: 'auto',
                   }}
                   title={`${e.titre}\n${e.lib_lieu || ''} ${e.adresse_complete || ''}\nOpé : ${e.op_crea_nom}`}>
                <div className="font-semibold truncate">
                  {e.date_debut.slice(11, 16)} — {e.titre}
                </div>
                {e.lib_lieu && (
                  <div className="truncate text-[10px] opacity-90">{e.lib_lieu}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
