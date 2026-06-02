import { useEffect, useRef, useState } from 'react'
import type { GeoPoint } from './useGeocode'

/**
 * Calcule l'itinéraire routier entre N points via OSRM (serveur public).
 *
 * Service public : https://router.project-osrm.org (free, pas de clé).
 * Rate-limit raisonnable, self-hosting possible pour prod.
 *
 * Retourne la liste des positions [lat, lon] formant le tracé.
 */

export interface RouteLeg {
  distance_m: number
  duration_s: number
}

export interface RouteResult {
  line: [number, number][]
  legs: RouteLeg[]
}

const CACHE: Map<string, RouteResult> = new Map()

function cacheKey(points: GeoPoint[]): string {
  return points.map((p) => `${p.lat.toFixed(5)},${p.lon.toFixed(5)}`).join('|')
}

async function fetchRoute(points: GeoPoint[]): Promise<RouteResult> {
  const key = cacheKey(points)
  const cached = CACHE.get(key)
  if (cached) return cached

  const empty: RouteResult = { line: [], legs: [] }
  if (points.length < 2) return empty

  const coords = points.map((p) => `${p.lon},${p.lat}`).join(';')
  const url = `https://router.project-osrm.org/route/v1/driving/${coords}?overview=full&geometries=geojson`

  try {
    const res = await fetch(url)
    if (!res.ok) {
      CACHE.set(key, empty)
      return empty
    }
    const data = await res.json()
    const route = data?.routes?.[0]
    const geom = route?.geometry?.coordinates as [number, number][] | undefined
    if (!geom) {
      CACHE.set(key, empty)
      return empty
    }
    const line = geom.map(([lon, lat]) => [lat, lon] as [number, number])
    const legs: RouteLeg[] = (route.legs || []).map((l: any) => ({
      distance_m: l.distance || 0,
      duration_s: l.duration || 0,
    }))
    const result: RouteResult = { line, legs }
    CACHE.set(key, result)
    return result
  } catch {
    CACHE.set(key, empty)
    return empty
  }
}

export function useRoute(points: GeoPoint[]) {
  const [result, setResult] = useState<RouteResult>({ line: [], legs: [] })
  const [loading, setLoading] = useState(false)
  const reqRef = useRef(0)

  useEffect(() => {
    if (points.length < 2) {
      setResult({ line: [], legs: [] })
      return
    }

    const reqId = ++reqRef.current
    setLoading(true)

    fetchRoute(points)
      .then((r) => {
        if (reqRef.current === reqId) setResult(r)
      })
      .finally(() => {
        if (reqRef.current === reqId) setLoading(false)
      })
  }, [cacheKey(points)])

  return { line: result.line, legs: result.legs, loading }
}
