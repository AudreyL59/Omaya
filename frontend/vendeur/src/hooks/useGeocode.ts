import { useEffect, useRef, useState } from 'react'

/**
 * Géocode un lot d'adresses via l'API Adresse (gouv.fr).
 * Endpoint gratuit, sans clé, limité aux adresses françaises.
 *
 * Cache local par adresse pour éviter les appels redondants.
 */

export interface GeoPoint {
  lat: number
  lon: number
}

const CACHE: Map<string, GeoPoint | null> = new Map()

async function geocodeOne(address: string): Promise<GeoPoint | null> {
  const cached = CACHE.get(address)
  if (cached !== undefined) return cached

  try {
    const res = await fetch(
      `https://api-adresse.data.gouv.fr/search/?q=${encodeURIComponent(address)}&limit=1`
    )
    if (!res.ok) {
      CACHE.set(address, null)
      return null
    }
    const data = await res.json()
    const feat = data?.features?.[0]
    if (!feat?.geometry?.coordinates) {
      CACHE.set(address, null)
      return null
    }
    const [lon, lat] = feat.geometry.coordinates
    const point: GeoPoint = { lat, lon }
    CACHE.set(address, point)
    return point
  } catch {
    CACHE.set(address, null)
    return null
  }
}

/**
 * Géocode en parallèle (avec limite concurrence) et retourne une map adresse → point.
 */
export function useGeocode(addresses: string[]) {
  const [points, setPoints] = useState<Map<string, GeoPoint | null>>(new Map())
  const [loading, setLoading] = useState(false)
  const reqRef = useRef(0)

  useEffect(() => {
    const uniq = Array.from(new Set(addresses.filter(Boolean)))
    if (uniq.length === 0) {
      setPoints(new Map())
      return
    }

    const reqId = ++reqRef.current
    setLoading(true)

    const initial = new Map<string, GeoPoint | null>()
    for (const a of uniq) {
      if (CACHE.has(a)) initial.set(a, CACHE.get(a)!)
    }
    setPoints(new Map(initial))

    const toFetch = uniq.filter((a) => !CACHE.has(a))
    if (toFetch.length === 0) {
      setLoading(false)
      return
    }

    // Concurrence limitée à 5 requêtes parallèles
    const BATCH = 5
    let index = 0
    const results = new Map(initial)

    const runNext = async (): Promise<void> => {
      if (reqRef.current !== reqId) return
      const i = index++
      if (i >= toFetch.length) return
      const addr = toFetch[i]
      const pt = await geocodeOne(addr)
      results.set(addr, pt)
      if (reqRef.current === reqId) {
        setPoints(new Map(results))
      }
      return runNext()
    }

    Promise.all(Array.from({ length: Math.min(BATCH, toFetch.length) }, runNext))
      .finally(() => {
        if (reqRef.current === reqId) setLoading(false)
      })
  }, [addresses.join('|')])

  return { points, loading }
}
