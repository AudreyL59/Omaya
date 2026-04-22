import { motion } from 'framer-motion'
import { useAuth } from '@/hooks/useAuth'

export default function DashboardPage() {
  const { user } = useAuth()

  return (
    <div className="p-8">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-2xl font-bold text-gray-900">
          Bonjour {user?.prenom}
        </h1>
        <p className="text-gray-500 mt-1">Bienvenue sur l'intranet ADM.</p>

        <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-3">
          <InfoCard label="Login" value={user?.login || '—'} />
          <InfoCard label="Societe" value={String(user?.id_ste || '—')} />
          <InfoCard label="Poste" value={user?.prof_poste || '—'} />
          <InfoCard label="Droits" value={`${user?.droits.length || 0} acces`} />
        </div>
      </motion.div>
    </div>
  )
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 px-4 py-3">
      <div className="text-[10px] text-gray-400 uppercase tracking-wide">
        {label}
      </div>
      <div className="text-sm font-semibold text-gray-900 mt-0.5 truncate">
        {value}
      </div>
    </div>
  )
}
