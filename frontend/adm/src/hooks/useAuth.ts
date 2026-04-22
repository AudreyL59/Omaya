import { useState, useEffect, useCallback } from 'react'
import { getToken, removeToken, getStoredUser, removeStoredUser, type UserToken } from '@/api'

export function useAuth() {
  const [user, setUser] = useState<UserToken | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = getToken()
    const storedUser = getStoredUser()
    if (token && storedUser) {
      setUser(storedUser)
      setIsAuthenticated(true)
    }
    setLoading(false)
  }, [])

  const logout = useCallback(() => {
    removeToken()
    removeStoredUser()
    setUser(null)
    setIsAuthenticated(false)
    window.location.href = `${import.meta.env.BASE_URL}login`
  }, [])

  return { user, isAuthenticated, loading, logout }
}
