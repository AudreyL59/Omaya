import { useState, useEffect } from 'react'
import { getToken } from '@/api'

export interface MenuItem {
  key: string
  label: string
  route: string
  visible: boolean
}

interface MenuResponse {
  menu_visible: boolean
  items: MenuItem[]
}

export function useMenu() {
  const [items, setItems] = useState<MenuItem[]>([])
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
        setItems(data.items.filter((item) => item.visible))
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [])

  return { items, menuVisible, loading }
}
