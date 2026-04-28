import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { useMenu, type MenuSection } from '@/hooks/useMenu'
import MenuIcon from '@/components/MenuIcon'

export default function DashboardPage() {
  const { user } = useAuth()
  const { sections, loading } = useMenu()

  return (
    <div className="px-6 py-6 max-w-[1400px] mx-auto">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-xl font-bold text-[#17494E]">
          Bonjour {user?.prenom}
        </h1>
        <p className="text-xs text-[#4E1D17]/70 mt-0.5">
          Bienvenue sur l'intranet ADM.
        </p>
      </motion.div>

      {loading && (
        <div className="text-sm text-[#4E1D17]/60 mt-8">Chargement du menu…</div>
      )}

      <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {sections.map((s, i) => (
          <SectionCard key={s.key} section={s} delay={i * 0.03} />
        ))}
      </div>
    </div>
  )
}

function SectionCard({
  section,
  delay,
}: {
  section: MenuSection
  delay: number
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.25 }}
      className="bg-white border border-[#E5DDDC] rounded-[10px] p-4 shadow-sm"
    >
      <h2 className="text-[11px] font-bold uppercase tracking-wider text-[#4E1D17] mb-3 pb-2 border-b border-[#E5DDDC]">
        {section.label}
      </h2>
      <ul className="space-y-0.5">
        {section.items.map((item) => (
          <li key={item.key}>
            <Link
              to={item.route}
              title={item.coded === false ? 'Page non encore développée' : undefined}
              className={
                item.coded === false
                  ? 'flex items-center gap-2.5 px-2 py-1.5 rounded-md text-sm text-gray-400 font-normal italic hover:bg-gray-100 transition-colors group'
                  : 'flex items-center gap-2.5 px-2 py-1.5 rounded-md text-sm text-[#4E1D17] font-normal hover:bg-[#EFE9E7] hover:text-[#17494E] transition-colors group'
              }
            >
              <span className={item.coded === false ? 'text-gray-300 shrink-0' : 'text-[#17494E] shrink-0'}>
                <MenuIcon name={item.icon} className="w-4 h-4" />
              </span>
              <span className="truncate">{item.label}</span>
            </Link>
          </li>
        ))}
      </ul>
    </motion.div>
  )
}
