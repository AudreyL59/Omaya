import { useState, useEffect } from 'react'
import { getToken } from '@/api'

export interface MenuItem {
  key: string
  label: string
  route: string
  icon: string
  visible: boolean
  coded?: boolean   // page cible implémentée côté frontend (Route explicite)
}

export interface MenuSection {
  key: string
  label: string
  items: MenuItem[]
}

export interface HeaderAction {
  key: string
  label: string
  route: string
  icon: string
  visible: boolean
  coded?: boolean
  badge?: number
}

interface MenuResponse {
  menu_visible: boolean
  header_actions: HeaderAction[]
  sections: MenuSection[]
}

export function useMenu() {
  const [headerActions, setHeaderActions] = useState<HeaderAction[]>([])
  const [sections, setSections] = useState<MenuSection[]>([])
  const [menuVisible, setMenuVisible] = useState(true)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setLoading(false)
      return
    }

    fetch('/api/adm/menu', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data: MenuResponse) => {
        setMenuVisible(data.menu_visible)
        setHeaderActions((data.header_actions || []).filter((a) => a.visible))
        setSections(
          (data.sections || [])
            .map((s) => ({ ...s, items: s.items.filter((i) => i.visible) }))
            .filter((s) => s.items.length > 0),
        )
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return { headerActions, sections, menuVisible, loading }
}
