/**
 * Planning visuel des Tickets Call SFR (onglet 3 de Fen_TicketCallSFR).
 *
 * Grille jour x ressource :
 *  - Axe X : ressources (Crea Ticket en 1er, puis operateurs par ordre alpha)
 *  - Axe Y : heures (auto-détectées selon les RDV du jour, par défaut 8h-20h)
 *  - Chaque RDV = rectangle positionné selon (date_début, ressource),
 *    hauteur = durée, fond = couleur selon délai
 *  - Tooltip au hover (titre + contenu + délai)
 *  - Navigation jour précédent / suivant
 */
import { useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, CheckCircle2, XCircle } from 'lucide-react'

interface PlanningRdv {
  titre: string; contenu: string
  date_debut: string; date_fin: string
  ressource: string; couleur: string
  delai_label: string; delai_min: number
  nb_valide: number
}

interface Props {
  rdvs: PlanningRdv[]
  initialDate?: string         // YYYY-MM-DD
}

const HOUR_HEIGHT = 60     // px par heure
const RES_WIDTH = 160      // px par colonne ressource

const dayKey = (iso: string): string => iso.slice(0, 10)
const dateLabel = (iso: string): string => {
  if (!iso) return ''
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('fr-FR', {
    weekday: 'short', day: '2-digit', month: 'short', year: 'numeric',
  })
}
const minutesInDay = (iso: string): number => {
  // 'YYYY-MM-DD HH:MM:SS' -> minutes depuis minuit
  const t = iso.length >= 19 ? iso.slice(11, 19) : '00:00:00'
  const [h, m] = t.split(':').map(Number)
  return (h || 0) * 60 + (m || 0)
}

export default function TicketCallPlanning({ rdvs, initialDate }: Props) {
  const allDays = useMemo(
    () => Array.from(new Set(rdvs.map(r => dayKey(r.date_debut)))).sort(),
    [rdvs],
  )
  const [currentDay, setCurrentDay] = useState(
    () => initialDate || allDays[0] || new Date().toISOString().slice(0, 10),
  )

  const dayRdvs = useMemo(
    () => rdvs.filter(r => dayKey(r.date_debut) === currentDay),
    [rdvs, currentDay],
  )

  // Ressources : Crea Ticket en 1er, puis operateurs par ordre alpha
  const ressources = useMemo(() => {
    const set = new Set(dayRdvs.map(r => r.ressource))
    const all = Array.from(set)
    const crea = all.filter(r => r === 'Crea Ticket')
    const others = all.filter(r => r !== 'Crea Ticket').sort()
    return [...crea, ...others]
  }, [dayRdvs])

  // Plage horaire : min/max des RDV (arrondi à l'heure), defaut 8h-20h
  const [hStart, hEnd] = useMemo(() => {
    if (dayRdvs.length === 0) return [8, 20]
    let min = 24 * 60, max = 0
    for (const r of dayRdvs) {
      const s = minutesInDay(r.date_debut)
      const e = minutesInDay(r.date_fin)
      if (s < min) min = s
      if (e > max) max = e
    }
    const hs = Math.max(0, Math.floor(min / 60))
    const he = Math.min(24, Math.ceil(max / 60))
    return [hs, Math.max(he, hs + 1)]
  }, [dayRdvs])

  const hours = useMemo(
    () => Array.from({ length: hEnd - hStart }, (_, i) => hStart + i),
    [hStart, hEnd],
  )
  const gridHeight = hours.length * HOUR_HEIGHT

  const idxToday = allDays.indexOf(currentDay)
  const prevDay = idxToday > 0 ? allDays[idxToday - 1] : null
  const nextDay = idxToday >= 0 && idxToday < allDays.length - 1
    ? allDays[idxToday + 1] : null

  return (
    <div className="flex h-full overflow-hidden">
      {/* Colonne legende (gauche) */}
      <div className="w-44 shrink-0 p-3 border-r border-c-line text-xs">
        <div className="font-bold text-c-ink mb-1 capitalize">
          {dateLabel(currentDay)}
        </div>
        <div className="text-c-ink-faint mb-3">
          {dayRdvs.length} RDV
        </div>
        <div className="flex items-center gap-1 mb-2">
          <button type="button" onClick={() => prevDay && setCurrentDay(prevDay)}
            disabled={!prevDay}
            className="p-1 rounded hover:bg-c-surface-soft disabled:opacity-30">
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <input type="date" value={currentDay}
            onChange={(e) => setCurrentDay(e.target.value)}
            className="flex-1 px-1 py-0.5 border border-c-line rounded text-[10px]" />
          <button type="button" onClick={() => nextDay && setCurrentDay(nextDay)}
            disabled={!nextDay}
            className="p-1 rounded hover:bg-c-surface-soft disabled:opacity-30">
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="mt-3 space-y-1">
          {[
            ['#86efac', 'Entre 0 et 3 min'],
            ['#fde68a', 'Entre 3 et 5 min'],
            ['#fdba74', 'Entre 5 et 7 min'],
            ['#fca5a5', 'Entre 7 et plus'],
          ].map(([c, l]) => (
            <div key={l} className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded" style={{ background: c }} />
              <span>{l}</span>
            </div>
          ))}
        </div>
        <div className="mt-3 space-y-1">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-c-brand" />
            <span>Vente validée</span>
          </div>
          <div className="flex items-center gap-1.5">
            <XCircle className="w-3.5 h-3.5 text-red-600" />
            <span>Vente refusée</span>
          </div>
        </div>
      </div>

      {/* Zone planning */}
      <div className="flex-1 overflow-auto">
        {ressources.length === 0 ? (
          <p className="text-sm italic text-center text-c-ink-faint-2 mt-12">
            Aucun RDV pour ce jour.
          </p>
        ) : (
          <div className="relative" style={{
            width: 60 + ressources.length * RES_WIDTH,
            minHeight: 30 + gridHeight,
          }}>
            {/* Header ressources (sticky top) */}
            <div className="sticky top-0 z-20 bg-white border-b border-c-line flex"
              style={{ height: 30, paddingLeft: 60 }}>
              {ressources.map(r => (
                <div key={r}
                  className="flex items-center justify-center text-[11px] font-medium border-r border-c-line-soft px-2"
                  style={{ width: RES_WIDTH }}>
                  <span className="truncate" title={r}>{r}</span>
                </div>
              ))}
            </div>

            {/* Colonne heures (sticky left) */}
            <div className="absolute top-[30px] left-0 w-[60px] bg-c-surface-soft border-r border-c-line z-10"
              style={{ height: gridHeight }}>
              {hours.map(h => (
                <div key={h}
                  className="text-[10px] text-c-ink-faint pl-2 border-t border-c-line-soft"
                  style={{ height: HOUR_HEIGHT }}>
                  {String(h).padStart(2, '0')}:00
                </div>
              ))}
            </div>

            {/* Grille principale */}
            <div className="absolute left-[60px] top-[30px]">
              {ressources.map((res, colIdx) => (
                <div key={res}
                  className="absolute top-0 border-r border-c-line-soft"
                  style={{
                    left: colIdx * RES_WIDTH,
                    width: RES_WIDTH,
                    height: gridHeight,
                  }}>
                  {/* Lignes heures */}
                  {hours.map(h => (
                    <div key={h}
                      className="border-t border-c-line-soft"
                      style={{ height: HOUR_HEIGHT }} />
                  ))}
                  {/* RDV de cette ressource */}
                  {dayRdvs
                    .filter(r => r.ressource === res)
                    .map((r, i) => {
                      const startMin = minutesInDay(r.date_debut)
                      const endMin = Math.max(
                        minutesInDay(r.date_fin), startMin + 3,
                      )
                      const offsetTop = (startMin - hStart * 60) * (HOUR_HEIGHT / 60)
                      const height = Math.max(
                        (endMin - startMin) * (HOUR_HEIGHT / 60), 18,
                      )
                      return (
                        <div key={i}
                          className="absolute left-0.5 right-0.5 rounded shadow-sm overflow-hidden text-[10px] text-c-ink cursor-default"
                          style={{
                            top: offsetTop, height, background: r.couleur,
                            border: '1px solid rgba(0,0,0,0.15)',
                          }}
                          title={
                            `${r.titre}\nDélai : ${r.delai_min} min`
                            + (r.contenu ? '\n\n' + r.contenu : '')
                          }>
                          <div className="px-1 py-0.5 flex items-center gap-1 truncate">
                            {r.nb_valide > 0
                              ? <CheckCircle2 className="w-2.5 h-2.5 text-c-brand shrink-0" />
                              : <XCircle className="w-2.5 h-2.5 text-red-600 shrink-0" />}
                            <span className="truncate font-medium">{r.titre}</span>
                          </div>
                        </div>
                      )
                    })}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
