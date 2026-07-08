/**
 * Fen_ScoolPlanning - Planning des formateurs.
 *
 * Vue timeline : une ligne par formateur (ressource) + blocs de
 * formation etales sur les colonnes jours de la periode.
 *
 * Navigation Jour / Semaine / Mois + Aujourd'hui + Precedent / Suivant.
 * Toggle 'Voir les formateurs sortis'.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Calendar as CalendarIcon, ChevronLeft, ChevronRight, Loader2,
} from 'lucide-react'
import { getToken } from '@/api'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PageHeader from '@/components/PageHeader'

const API_BASE = '/api/adm'

interface Ressource {
  id_formateur: string
  nom: string
  prenom: string
  niveau: string
  is_actif: boolean
}

interface EventRow {
  id: string
  id_formation: string
  id_formateur: string
  titre: string
  date_debut: string
  date_fin: string
  couleur: string
  kind: string
}

type Vue = 'jour' | 'semaine' | 'mois'

const MOIS_FR = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
]
const JOURS_FR = ['lun', 'mar', 'mer', 'jeu', 'ven', 'sam', 'dim']

// --- Helpers dates ---

const toIso = (d: Date): string => {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}
const fromIso = (iso: string): Date => {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}
const addDays = (d: Date, n: number): Date => {
  const c = new Date(d); c.setDate(c.getDate() + n); return c
}
const startOfWeek = (d: Date): Date => {
  const c = new Date(d)
  const dow = (c.getDay() + 6) % 7  // 0 = lundi
  c.setDate(c.getDate() - dow)
  return c
}
const startOfMonth = (d: Date): Date =>
  new Date(d.getFullYear(), d.getMonth(), 1)
const endOfMonth = (d: Date): Date =>
  new Date(d.getFullYear(), d.getMonth() + 1, 0)
const numeroSemaine = (d: Date): number => {
  const target = new Date(d.valueOf())
  const dayNr = (d.getDay() + 6) % 7
  target.setDate(target.getDate() - dayNr + 3)
  const firstThursday = target.valueOf()
  target.setMonth(0, 1)
  if (target.getDay() !== 4) {
    target.setMonth(0, 1 + ((4 - target.getDay()) + 7) % 7)
  }
  return 1 + Math.ceil((firstThursday - target.valueOf()) / 604800000)
}

// --- Page ---

export default function ScoolPlanningPage() {
  useDocumentTitle('Planning S\'Cool')

  const [vue, setVue] = useState<Vue>('semaine')
  const [refDate, setRefDate] = useState(new Date())
  const [ressources, setRessources] = useState<Ressource[]>([])
  const [events, setEvents] = useState<EventRow[]>([])
  const [avecSortis, setAvecSortis] = useState(false)
  const [loading, setLoading] = useState(false)

  // Calcule dateDeb/dateFin selon la vue
  const { dateDeb, dateFin, jours } = useMemo(() => {
    let d0: Date, d1: Date
    if (vue === 'jour') {
      d0 = refDate; d1 = refDate
    } else if (vue === 'semaine') {
      d0 = startOfWeek(refDate); d1 = addDays(d0, 6)
    } else {
      d0 = startOfMonth(refDate); d1 = endOfMonth(refDate)
    }
    const list: Date[] = []
    for (let d = new Date(d0); d <= d1; d = addDays(d, 1)) {
      list.push(new Date(d))
    }
    return {
      dateDeb: toIso(d0), dateFin: toIso(d1), jours: list,
    }
  }, [vue, refDate])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/scool/planning?date_deb=${dateDeb}&date_fin=${dateFin}&avec_sortis=${avecSortis}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      const d = await r.json()
      setRessources(d.ressources || [])
      setEvents(d.events || [])
    } finally { setLoading(false) }
  }, [dateDeb, dateFin, avecSortis])
  useEffect(() => { void load() }, [load])

  const precedent = () => {
    if (vue === 'jour') setRefDate((d) => addDays(d, -1))
    else if (vue === 'semaine') setRefDate((d) => addDays(d, -7))
    else setRefDate((d) => new Date(d.getFullYear(), d.getMonth() - 1, 1))
  }
  const suivant = () => {
    if (vue === 'jour') setRefDate((d) => addDays(d, 1))
    else if (vue === 'semaine') setRefDate((d) => addDays(d, 7))
    else setRefDate((d) => new Date(d.getFullYear(), d.getMonth() + 1, 1))
  }
  const aujourdhui = () => setRefDate(new Date())

  const titreNav = (() => {
    if (vue === 'jour') {
      return `${JOURS_FR[(refDate.getDay() + 6) % 7]} ${refDate.getDate()} ${MOIS_FR[refDate.getMonth()]} ${refDate.getFullYear()}`
    }
    if (vue === 'semaine') {
      const d0 = startOfWeek(refDate)
      const d1 = addDays(d0, 6)
      return (
        `Semaine ${numeroSemaine(refDate)} : ${d0.getDate()} ${MOIS_FR[d0.getMonth()].slice(0, 4)}. `
        + `- ${d1.getDate()} ${MOIS_FR[d1.getMonth()].slice(0, 4)}. ${d1.getFullYear()}`
      )
    }
    return `${MOIS_FR[refDate.getMonth()]} ${refDate.getFullYear()}`
  })()

  // Groupement events par formateur
  const eventsByFormateur = useMemo(() => {
    const m = new Map<string, EventRow[]>()
    events.forEach((e) => {
      const arr = m.get(e.id_formateur) || []
      arr.push(e); m.set(e.id_formateur, arr)
    })
    return m
  }, [events])

  const isWeekend = (d: Date) => d.getDay() === 0 || d.getDay() === 6

  return (
    <div className="min-h-screen bg-[#F5F5F0] p-6">
      <div className="max-w-full mx-auto">
        <PageHeader icon={CalendarIcon} title="Planning S'Cool" />

        {/* Barre de nav */}
        <div className="bg-white rounded-lg shadow p-3 mb-4">
          <div className="flex items-center gap-2 flex-wrap">
            <button onClick={precedent}
                    className="p-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2]">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <div className="min-w-[300px] text-center">
              <div className="text-base font-semibold text-[#17494E]">{titreNav}</div>
            </div>
            <button onClick={suivant}
                    className="p-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2]">
              <ChevronRight className="w-4 h-4" />
            </button>

            <div className="ml-4 flex rounded border border-[#E5E0D5]">
              {(['jour', 'semaine', 'mois'] as Vue[]).map((v) => (
                <button key={v}
                        onClick={() => setVue(v)}
                        className={`px-3 py-1.5 text-sm ${
                          vue === v ? 'bg-[#17494E] text-white' : 'text-[#17494E]'
                        }`}>
                  {v[0].toUpperCase() + v.slice(1)}
                </button>
              ))}
            </div>
            <button onClick={aujourdhui}
                    className="px-3 py-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] text-sm">
              Aujourd'hui
            </button>

            <label className="ml-auto flex items-center gap-2 text-xs">
              <input type="checkbox" checked={avecSortis}
                     onChange={(e) => setAvecSortis(e.target.checked)}
                     className="accent-[#17494E]" />
              <span className="text-[#8B7355]">Voir les formateurs sortis</span>
            </label>
            {loading && <Loader2 className="w-4 h-4 animate-spin text-[#8B7355]" />}
          </div>
        </div>

        {/* Grille planning */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <div style={{
              display: 'grid',
              gridTemplateColumns: `220px repeat(${jours.length}, minmax(60px, 1fr))`,
            }}>
              {/* Header : nom colonne ressource + jours */}
              <div className="bg-[#17494E] text-white p-2 text-xs font-semibold sticky left-0">
                Formateur
              </div>
              {jours.map((d, i) => (
                <div key={i}
                     className={`bg-[#17494E] text-white p-1.5 text-center text-[11px] border-l border-[#0F3438] ${
                       isWeekend(d) ? 'bg-[#0F3438]' : ''
                     }`}>
                  <div>{JOURS_FR[(d.getDay() + 6) % 7]}</div>
                  <div className="font-semibold">{d.getDate()}/{d.getMonth() + 1}</div>
                </div>
              ))}

              {/* Lignes ressources */}
              {ressources.map((r) => (
                <RessourceRow
                  key={r.id_formateur}
                  ressource={r}
                  jours={jours}
                  events={eventsByFormateur.get(r.id_formateur) || []}
                  isWeekend={isWeekend}
                />
              ))}
            </div>
          </div>

          {ressources.length === 0 && !loading && (
            <div className="p-8 text-center text-gray-400 text-sm">
              Aucun formateur sur cette période
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function RessourceRow({
  ressource, jours, events, isWeekend,
}: {
  ressource: Ressource
  jours: Date[]
  events: EventRow[]
  isWeekend: (d: Date) => boolean
}) {
  const nbJours = jours.length
  const jourDeb = jours[0]
  const jourFin = jours[nbJours - 1]

  // Filtre events qui chevauchent la periode + calcule slots
  const eventsWithLayout = useMemo(() => {
    return events.map((e) => {
      const d0 = fromIso(e.date_debut)
      const d1 = e.date_fin ? fromIso(e.date_fin) : d0
      const eff0 = d0 < jourDeb ? jourDeb : d0
      const eff1 = d1 > jourFin ? jourFin : d1
      const startIdx = Math.floor(
        (eff0.getTime() - jourDeb.getTime()) / (86400000),
      )
      const endIdx = Math.floor(
        (eff1.getTime() - jourDeb.getTime()) / (86400000),
      )
      return {
        e,
        startIdx: Math.max(0, startIdx),
        endIdx: Math.min(nbJours - 1, endIdx),
      }
    })
  }, [events, jourDeb, jourFin, nbJours])

  return (
    <>
      {/* Colonne ressource */}
      <div className="p-2 border-t border-[#F0EDE5] bg-[#F5F5F0] sticky left-0 z-10">
        <div className="text-xs font-semibold text-[#17494E]">
          {ressource.nom}
        </div>
        <div className="text-[11px] text-[#8B7355]">
          {ressource.prenom}
          {!ressource.is_actif && (
            <span className="ml-1 text-[9px] text-red-600">(sorti)</span>
          )}
        </div>
      </div>

      {/* Cellules jours (fond) */}
      {jours.map((d, i) => (
        <div key={i}
             className={`border-t border-l border-[#F0EDE5] h-12 relative ${
               isWeekend(d) ? 'bg-[#FAF9F5]' : ''
             }`}>
          {/* Events qui commencent sur ce jour */}
          {eventsWithLayout
            .filter((x) => x.startIdx === i)
            .map((x) => (
              <div
                key={x.e.id}
                title={x.e.titre}
                className="absolute top-1 bottom-1 rounded text-white text-[10px] px-1.5 py-0.5 overflow-hidden shadow-sm"
                style={{
                  left: '2px',
                  width: `calc(${(x.endIdx - x.startIdx + 1) * 100}% - 4px)`,
                  backgroundColor: x.e.couleur,
                }}
              >
                <div className="truncate font-medium leading-tight">
                  {x.e.titre}
                </div>
              </div>
            ))}
        </div>
      ))}
    </>
  )
}
