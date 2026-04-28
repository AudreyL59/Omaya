import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useLocation, NavLink, Link } from 'react-router-dom'
import { ChevronDown, LogOut } from 'lucide-react'
import { useMenu, type HeaderAction, type MenuSection } from '@/hooks/useMenu'
import { useAuth } from '@/hooks/useAuth'
import { getToken } from '@/api'
import logoOmaya from '@/assets/logo-omaya.png'
import MenuIcon from '@/components/MenuIcon'

// Détecte le MIME depuis le préfixe base64 (JPEG /9j/, PNG iVBORw, GIF R0lGOD)
function photoDataUrl(b64: string): string {
  if (!b64) return ''
  const mime = b64.startsWith('/9j/')
    ? 'jpeg'
    : b64.startsWith('R0lGOD')
      ? 'gif'
      : 'png'
  return `data:image/${mime};base64,${b64}`
}

export default function Header() {
  const { headerActions, sections, menuVisible } = useMenu()
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  // Trouve la section contenant la route courante (pour le dropdown contextuel).
  const currentSection: MenuSection | null = useMemo(() => {
    const path = location.pathname.replace(/\/$/, '')
    if (!path || path === '/') return null
    for (const s of sections) {
      if (s.items.some((it) => path === it.route || path.startsWith(it.route + '/'))) {
        return s
      }
    }
    return null
  }, [sections, location.pathname])

  const [photo, setPhoto] = useState<string>(() => {
    if (!user) return ''
    return sessionStorage.getItem(`adm_photo_${user.id_salarie}`) || ''
  })

  useEffect(() => {
    if (!user) return
    const cacheKey = `adm_photo_v2_${user.id_salarie}`
    const cached = sessionStorage.getItem(cacheKey)
    if (cached) {
      setPhoto(cached)
      return
    }
    fetch(`/api/adm/mon-compte/fiche/${user.id_salarie}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(async (r) => {
        if (!r.ok) {
          console.warn('[Header] photo fetch failed:', r.status, await r.text())
          return null
        }
        return r.json()
      })
      .then((data) => {
        const p = data?.identite?.photo || ''
        if (p) {
          sessionStorage.setItem(cacheKey, p)
          setPhoto(p)
        } else {
          console.warn('[Header] photo vide dans la fiche', data?.identite)
        }
      })
      .catch((e) => console.warn('[Header] photo fetch error:', e))
  }, [user])

  if (!menuVisible) return null

  return (
    <header className="bg-[#17494E] text-white shrink-0">
      <div className="px-4 py-3 flex items-center gap-4">
        {/* Logo + identité user (cliquable → home) */}
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-3 px-2 py-1 rounded-lg hover:bg-white/10 transition-colors min-w-0"
          title="Retour à l'accueil"
        >
          <div className="w-11 h-11 rounded-full bg-white/15 ring-2 ring-white/20 flex items-center justify-center overflow-hidden shrink-0">
            {photo ? (
              <img
                src={photoDataUrl(photo)}
                alt={`${user?.prenom ?? ''} ${user?.nom ?? ''}`}
                className="w-full h-full object-cover"
              />
            ) : (
              <img src={logoOmaya} alt="Omaya" className="w-7 h-7" />
            )}
          </div>
          <div className="text-left min-w-0">
            <div className="text-xs leading-tight text-white/70">{user?.prenom}</div>
            <div className="text-sm font-semibold leading-tight truncate max-w-[160px]">
              {(user?.nom || '').toUpperCase()}
            </div>
          </div>
        </button>

        {/* Barre d'icônes (centrée, plein largeur disponible) */}
        <nav className="flex-1 flex items-center justify-center gap-1 overflow-x-auto">
          {headerActions.map((a) => (
            <HeaderActionButton key={a.key} action={a} />
          ))}
        </nav>

        {/* Déconnexion */}
        <button
          onClick={logout}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-white/80 hover:bg-white/10 hover:text-white transition-colors"
          title="Déconnexion"
        >
          <LogOut className="w-4 h-4" />
          <span className="text-sm hidden md:inline">Déconnexion</span>
        </button>
      </div>

      {/* Breadcrumb / barre de sections */}
      {location.pathname !== '/' && (
        <div className="bg-[#0F353A] px-4 py-1.5 text-xs text-white/80 flex flex-wrap items-center gap-x-1 gap-y-1 relative">
          <button
            onClick={() => navigate('/')}
            className="hover:text-white hover:underline shrink-0 pr-2"
          >
            ← Accueil
          </button>
          {sections.map((s) => (
            <SectionDropdown
              key={s.key}
              section={s}
              currentPath={location.pathname}
              isCurrent={currentSection?.key === s.key}
            />
          ))}
        </div>
      )}
    </header>
  )
}

function SectionDropdown({
  section,
  currentPath,
  isCurrent: isSectionCurrent = false,
}: {
  section: MenuSection
  currentPath: string
  isCurrent?: boolean
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement | null>(null)

  // Ferme au clic extérieur
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Ferme à la navigation
  useEffect(() => {
    setOpen(false)
  }, [currentPath])

  const isCurrent = (route: string) =>
    currentPath === route || currentPath.startsWith(route + '/')

  return (
    <div ref={ref} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={
          isSectionCurrent
            ? 'inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-white/15 text-white transition-colors'
            : 'inline-flex items-center gap-1 px-2 py-0.5 rounded-md hover:bg-white/10 hover:text-white transition-colors'
        }
      >
        <span className={isSectionCurrent ? 'font-bold' : 'font-medium'}>{section.label}</span>
        <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-1 z-30 min-w-[260px] bg-white border border-[#E5DDDC] rounded-[10px] shadow-lg overflow-hidden">
          <ul className="py-1">
            {section.items.map((it) => {
              const active = isCurrent(it.route)
              const dim = it.coded === false
              return (
                <li key={it.key}>
                  <Link
                    to={it.route}
                    title={dim ? `${it.label} (non développée)` : undefined}
                    className={
                      dim
                        ? 'flex items-center gap-2.5 px-3 py-2 text-sm text-[#A68D8A] italic hover:bg-[#FAF6F2] transition-colors'
                        : active
                          ? 'flex items-center gap-2.5 px-3 py-2 text-sm bg-[#EFE9E7] text-[#17494E] font-bold transition-colors'
                          : 'flex items-center gap-2.5 px-3 py-2 text-sm text-[#4E1D17] hover:bg-[#EFE9E7] hover:text-[#17494E] transition-colors'
                    }
                  >
                    <span
                      className={
                        dim
                          ? 'text-[#E5DDDC] shrink-0'
                          : active
                            ? 'text-[#17494E] shrink-0'
                            : 'text-[#17494E] shrink-0'
                      }
                    >
                      <MenuIcon name={it.icon} className="w-4 h-4" />
                    </span>
                    <span className="truncate">{it.label}</span>
                  </Link>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}

function HeaderActionButton({ action }: { action: HeaderAction }) {
  const dim = action.coded === false
  return (
    <NavLink
      to={action.route}
      className={({ isActive }) =>
        `relative flex items-center justify-center w-11 h-11 rounded-lg transition-colors ${
          dim
            ? 'text-white/30 hover:bg-white/5 hover:text-white/50'
            : isActive
              ? 'bg-white/15 text-white'
              : 'text-white/80 hover:bg-white/10 hover:text-white'
        }`
      }
      title={dim ? `${action.label} (non développée)` : action.label}
    >
      <MenuIcon name={action.icon} className="w-5 h-5" />
      {action.badge !== undefined && action.badge > 0 && (
        <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-[#993636] text-[10px] font-semibold flex items-center justify-center">
          {action.badge > 99 ? '99+' : action.badge}
        </span>
      )}
    </NavLink>
  )
}
