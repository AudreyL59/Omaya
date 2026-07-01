/**
 * Fen_SuiviSFR (Hub menu Suivi SFR).
 *
 * Page menu avec 9 cartes pointant vers les sous-fonctionnalites :
 *   - Ctts à raccorder    -> Fen_SFRCttaRacc
 *   - Rémunérations       -> Fen_RemInterneSFR
 *   - Ticket CALL SFR     -> Fen_TicketCallSFR
 *   - Extraction SFR      -> Fen_ExtractionSFR
 *   - Parcours Chaînés    -> Fen_ParcoursChaine
 *   - Cluster             -> Fen_SFRCluster + Fen_ClusterAjout
 *   - Offres EZY          -> Fen_OffresEZY
 *   - RDV Tech            -> Fen_SuiviRDVTECH
 *   - Extraction ETP      -> Fen_ETP
 *
 * Chaque carte ouvre une sous-route /suivi-sfr/<slug>. Les pages
 * detaillees sont implementees au fur et a mesure.
 */
import { Link } from 'react-router-dom'
import {
  CheckSquare, Euro, PhoneCall, Download, GitBranch, Boxes,
  ShoppingBag, CalendarClock, Users, Antenna,
} from 'lucide-react'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

interface MenuItem {
  key: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  to: string
  implemented?: boolean       // true = page complete, false = placeholder
}

const ITEMS: MenuItem[] = [
  { key: 'ctts-a-raccorder', label: 'Ctts à raccorder',
    icon: CheckSquare,    to: 'ctts-a-raccorder',  implemented: true },
  { key: 'remunerations',    label: 'Rémunérations',
    icon: Euro,           to: 'remunerations',     implemented: true },
  { key: 'ticket-call',      label: 'Ticket CALL SFR',
    icon: PhoneCall,      to: 'ticket-call',       implemented: true },
  { key: 'extraction',       label: 'Extraction SFR',
    icon: Download,       to: 'extraction',        implemented: true },
  { key: 'parcours-chaines', label: 'Parcours Chaînés',
    icon: GitBranch,      to: 'parcours-chaines',  implemented: true },
  { key: 'cluster',          label: 'Cluster',
    icon: Boxes,          to: 'cluster',           implemented: true },
  { key: 'offres-ezy',       label: 'Offres EZY',
    icon: ShoppingBag,    to: 'offres-ezy',        implemented: true },
  { key: 'rdv-tech',         label: 'RDV Tech',
    icon: CalendarClock,  to: 'rdv-tech',          implemented: false },
  { key: 'extraction-etp',   label: 'Extraction ETP',
    icon: Users,          to: 'extraction-etp',    implemented: false },
]

export default function SuiviSfrPage() {
  useDocumentTitle('Suivi SFR')

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-xl font-bold text-c-ink mb-1 flex items-center gap-2">
        <Antenna className="w-5 h-5 text-c-brand" />
        Suivi SFR
      </h1>
      <p className="text-sm text-c-ink-faint mb-6">
        Choisis une fonctionnalité ci-dessous.
      </p>

      <div className="grid grid-cols-3 gap-4">
        {ITEMS.map((it) => {
          const Icon = it.icon
          const dim = !it.implemented
          return (
            <Link key={it.key} to={it.to}
              className={`group relative flex flex-col items-center justify-center gap-3 p-6 rounded-xl border bg-white transition-all hover:shadow-md hover:-translate-y-0.5 ${
                dim ? 'border-c-line-soft opacity-60' : 'border-c-line hover:border-c-brand'
              }`}
              title={dim ? `${it.label} (à venir)` : it.label}
            >
              <div className={`p-3 rounded-full ${
                dim ? 'bg-c-surface-soft text-c-ink-faint-2'
                    : 'bg-c-brand/10 text-c-brand group-hover:bg-c-brand group-hover:text-white'
              }`}>
                <Icon className="w-6 h-6" />
              </div>
              <span className={`text-sm font-medium text-center ${
                dim ? 'text-c-ink-faint italic' : 'text-c-ink'
              }`}>
                {it.label}
              </span>
              {dim && (
                <span className="absolute top-2 right-2 text-[9px] uppercase tracking-wide text-c-ink-faint-2">
                  à venir
                </span>
              )}
            </Link>
          )
        })}
      </div>
    </div>
  )
}
