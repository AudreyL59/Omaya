import { motion } from 'framer-motion'
import { useAuth } from '@/hooks/useAuth'

export default function DashboardPage() {
  const { user } = useAuth()

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Bonjour' : hour < 18 ? 'Bon après-midi' : 'Bonsoir'

  return (
    <div className="p-8">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <h1 className="text-2xl font-bold text-gray-900">
          {greeting}, {user?.prenom} !
        </h1>
        <p className="text-gray-500 mt-1">
          Bienvenue sur l'Intranet Vendeur Omaya
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.4 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8"
      >
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <p className="text-sm font-medium text-gray-500">Profil</p>
          <p className="text-lg font-semibold text-gray-900 mt-1">
            {user?.prenom} {user?.nom}
          </p>
          <p className="text-sm text-gray-400 mt-0.5">{user?.prof_poste}</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <p className="text-sm font-medium text-gray-500">Statut</p>
          <div className="flex items-center gap-2 mt-1">
            <span className={`w-2 h-2 rounded-full ${user?.is_actif ? 'bg-green-500' : 'bg-red-500'}`} />
            <p className="text-lg font-semibold text-gray-900">
              {user?.is_actif ? 'Actif' : 'Inactif'}
            </p>
          </div>
          {user?.is_pause && (
            <p className="text-sm text-amber-500 mt-0.5">En pause</p>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <p className="text-sm font-medium text-gray-500">Droits</p>
          <p className="text-lg font-semibold text-gray-900 mt-1">
            {user?.droits.length} accès
          </p>
          <p className="text-sm text-gray-400 mt-0.5">
            {user?.droits.filter(d => d.startsWith('Intra')).length} intranets
          </p>
        </div>
      </motion.div>
    </div>
  )
}
