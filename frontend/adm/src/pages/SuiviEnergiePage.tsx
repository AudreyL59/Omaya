/**
 * Fen_SuiviEnergie (Hub menu Suivi Énergie).
 *
 * Page menu avec 2 cartes :
 *   - Extraction Call  -> Fen_ExtractionEnergie
 *   - Ticket CALL      -> Fen_TicketCall (Energie)
 *
 * Chaque carte ouvre une sous-route /suivi-energie/<slug>.
 * Meme pattern que SuiviSfrPage (hub avec cartes).
 */
import { Link } from 'react-router-dom'
import { Download, PhoneCall, Zap } from 'lucide-react'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

interface MenuItem {
  key: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  to: string
  implemented?: boolean
}

const ITEMS: MenuItem[] = [
  { key: 'extraction',  label: 'Extraction Call',
    icon: Download,     to: 'extraction',   implemented: false },
  { key: 'ticket-call', label: 'Ticket CALL',
    icon: PhoneCall,    to: 'ticket-call',  implemented: false },
]

export default function SuiviEnergiePage() {
  useDocumentTitle('Suivi Énergie')

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-xl font-bold text-c-ink mb-1 flex items-center gap-2">
        <Zap className="w-5 h-5 text-c-brand" />
        Suivi Énergie
      </h1>
      <p className="text-sm text-c-ink-faint mb-6">
        Choisis une fonctionnalité ci-dessous.
      </p>

      <div className="grid grid-cols-2 gap-4">
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
