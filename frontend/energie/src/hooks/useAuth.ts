import { useState, useEffect, useCallback } from 'react'
import {
  getToken,
  removeToken,
  getStoredUser,
  removeStoredUser,
  setStoredUser,
  type UserToken,
} from '@/api'

export function useAuth() {
  const [user, setUser] = useState<UserToken | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)

  const doLogout = useCallback(() => {
    removeToken()
    removeStoredUser()
    setUser(null)
    setIsAuthenticated(false)
    const loginPath = `${import.meta.env.BASE_URL}login`
    if (!window.location.pathname.startsWith(loginPath)) {
      window.location.href = loginPath
    }
  }, [])

  useEffect(() => {
    const token = getToken()
    const storedUser = getStoredUser()
    if (!token || !storedUser) {
      setLoading(false)
      return
    }

    // Optimiste : on montre l'app pendant qu'on valide le token en arriere-plan
    setUser(storedUser)
    setIsAuthenticated(true)
    setLoading(false)

    // Validation serveur : si le token est expire/invalide, on logout
    fetch('/api/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) {
          doLogout()
          return null
        }
        return res.json()
      })
      .then((fresh: UserToken | null) => {
        if (fresh) {
          setUser(fresh)
          setStoredUser(fresh)
        }
      })
      .catch(() => {
        // Erreur reseau : on ne deconnecte pas brutalement
      })
  }, [doLogout])

  return { user, isAuthenticated, loading, logout: doLogout }
}
