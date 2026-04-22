import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  FileText,
  Calendar,
  ArrowLeftRight,
  Megaphone,
  ChevronRight,
} from 'lucide-react'

interface HubItem {
  key: string
  label: string
  description: string
  route: string
  icon: React.ReactNode
  accent: string
}

const ITEMS: HubItem[] = [
  {
    key: 'saisie-cv',
    label: 'Stats Saisie et Traitement CV',
    description: 'Volumetrie des CV saisis et traites',
    route: 'saisie-cv',
    icon: <FileText className="w-6 h-6" />,
    accent: 'from-blue-500 to-indigo-500',
  },
  {
    key: 'rdv',
    label: 'Stats Prise de RDV',
    description: 'Rendez-vous planifies par periode',
    route: 'rdv',
    icon: <Calendar className="w-6 h-6" />,
    accent: 'from-emerald-500 to-teal-500',
  },
  {
    key: 'dpae-sortie',
    label: 'Stats DPAE / Sortie',
    description: 'Entrees et sorties sur periode',
    route: 'dpae-sortie',
    icon: <ArrowLeftRight className="w-6 h-6" />,
    accent: 'from-amber-500 to-orange-500',
  },
  {
    key: 'annonceurs',
    label: 'Stats Annonceurs',
    description: 'Performance par source / annonceur',
    route: 'annonceurs',
    icon: <Megaphone className="w-6 h-6" />,
    accent: 'from-rose-500 to-pink-500',
  },
]

export default function StatRHPage() {
  const navigate = useNavigate()

  return (
    <div className="p-8 max-w-5xl">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-2xl font-bold text-gray-900">Stats RH</h1>
        <p className="text-gray-500 mt-1">
          Selectionne un rapport pour consulter les indicateurs.
        </p>
      </motion.div>

      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
        {ITEMS.map((item, i) => (
          <motion.button
            key={item.key}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            whileHover={{ y: -2 }}
            onClick={() => navigate(item.route)}
            className="group bg-white rounded-2xl border border-gray-200 p-5 text-left hover:shadow-lg hover:border-gray-300 transition-all"
          >
            <div className="flex items-start gap-4">
              <div
                className={`shrink-0 w-12 h-12 rounded-xl bg-gradient-to-br ${item.accent} text-white flex items-center justify-center shadow-sm`}
              >
                {item.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-gray-900">{item.label}</h3>
                  <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-gray-700 group-hover:translate-x-1 transition-all" />
                </div>
                <p className="text-sm text-gray-500 mt-1">{item.description}</p>
              </div>
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  )
}
