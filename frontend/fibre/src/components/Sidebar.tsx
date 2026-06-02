import { useState, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  User, Users, CalendarDays, CalendarCheck, FileText,
  Network, Settings, GraduationCap, BarChart3, Layers,
  Ticket, Workflow, Phone, PhoneCall, MessageSquare,
  ChevronLeft, ChevronRight, LogOut,
} from 'lucide-react'
import { useMenu, type MenuItem } from '@/hooks/useMenu'
import { useAuth } from '@/hooks/useAuth'
import logoOmaya from '@/assets/logo-omaya.png'

const MENU_ICONS: Record<string, React.ReactNode> = {
  mon_compte: <User className="w-5 h-5" />,
  cooptation: <Users className="w-5 h-5" />,
  agenda_recrutement: <CalendarDays className="w-5 h-5" />,
  agenda_cial: <CalendarCheck className="w-5 h-5" />,
  cvtheque: <FileText className="w-5 h-5" />,
  organigramme: <Network className="w-5 h-5" />,
  gestion_ohm: <Settings className="w-5 h-5" />,
  scool: <GraduationCap className="w-5 h-5" />,
  production: <BarChart3 className="w-5 h-5" />,
  clusters: <Layers className="w-5 h-5" />,
  tickets: <Ticket className="w-5 h-5" />,
  process: <Workflow className="w-5 h-5" />,
  tickets_call_suivi: <Phone className="w-5 h-5" />,
  tickets_call_energie: <PhoneCall className="w-5 h-5" />,
  tickets_call_fibre: <PhoneCall className="w-5 h-5" />,
  dialogues: <MessageSquare className="w-5 h-5" />,
}

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const { items, menuVisible } = useMenu()
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  // Auto-collapse sur mobile
  useEffect(() => {
    const checkMobile = () => setCollapsed(window.innerWidth < 768)
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  if (!menuVisible) return null

  return (
    <motion.aside
      animate={{ width: collapsed ? 72 : 260 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className="h-screen bg-gray-950 text-white flex flex-col shrink-0 overflow-hidden"
    >
      {/* Logo */}
      <div
        onClick={() => navigate('/')}
        className="flex items-center gap-3 px-4 py-5 border-b border-white/10 cursor-pointer hover:bg-white/5 transition-colors duration-200"
      >
        <img src={logoOmaya} alt="Omaya" className="w-10 h-10 shrink-0" />
        <AnimatePresence>
          {!collapsed && (
            <motion.span
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              className="font-semibold text-lg whitespace-nowrap overflow-hidden"
            >
              Omaya
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* Menu items */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {items.map((item: MenuItem) => (
          <NavLink
            key={item.key}
            to={item.route}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group ${
                isActive
                  ? 'bg-white/15 text-white'
                  : 'text-gray-400 hover:bg-white/5 hover:text-white'
              }`
            }
          >
            <span className="shrink-0">
              {MENU_ICONS[item.key] || <FileText className="w-5 h-5" />}
            </span>
            <AnimatePresence>
              {!collapsed && (
                <motion.span
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: 'auto' }}
                  exit={{ opacity: 0, width: 0 }}
                  className="text-sm whitespace-nowrap overflow-hidden"
                >
                  {item.label}
                </motion.span>
              )}
            </AnimatePresence>
          </NavLink>
        ))}
      </nav>

      {/* User + collapse */}
      <div className="border-t border-white/10 p-3 space-y-2">
        {/* User info */}
        <div className="flex items-center gap-3 px-2">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm font-medium shrink-0">
            {user?.prenom?.[0]}{user?.nom?.[0]}
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="overflow-hidden"
              >
                <p className="text-sm font-medium text-white whitespace-nowrap">
                  {user?.prenom} {user?.nom}
                </p>
                <p className="text-xs text-gray-500 whitespace-nowrap truncate">
                  {user?.login}
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1">
          <button
            onClick={logout}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-gray-400 hover:bg-white/5 hover:text-red-400 transition-all duration-200 w-full"
          >
            <LogOut className="w-4 h-4 shrink-0" />
            <AnimatePresence>
              {!collapsed && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="text-sm"
                >
                  Déconnexion
                </motion.span>
              )}
            </AnimatePresence>
          </button>
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center py-2 rounded-lg text-gray-500 hover:bg-white/5 hover:text-white transition-all duration-200"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
    </motion.aside>
  )
}
