/**
 * <AuthImage /> - affiche une image derriere un endpoint protege par
 * Bearer token.
 *
 * La balise <img src="..."> native ne peut pas envoyer un header
 * Authorization, donc les endpoints proteges renvoient 401 -> le
 * navigateur declenche un prompt Basic Auth.
 *
 * Ce composant :
 *  1. fetch(url, { Authorization: Bearer ... })
 *  2. cree un objectURL a partir du blob retourne
 *  3. revoke l'objectURL au demontage / changement d'url
 *
 * Usage :
 *   <AuthImage src="/api/adm/xxx/photo/1" alt="..." className="..."/>
 */
import { useEffect, useState } from 'react'

interface Props {
  src: string
  alt?: string
  className?: string
  fallback?: React.ReactNode
  getToken: () => string | null
}

export function AuthImage({
  src, alt = '', className = '', fallback = null, getToken,
}: Props) {
  const [objUrl, setObjUrl] = useState<string>('')
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    let currentObj = ''
    setError(false)
    setObjUrl('')
    void (async () => {
      try {
        const r = await fetch(src, {
          headers: { Authorization: `Bearer ${getToken()}` },
        })
        if (!r.ok) throw new Error(String(r.status))
        const b = await r.blob()
        if (cancelled) return
        currentObj = URL.createObjectURL(b)
        setObjUrl(currentObj)
      } catch {
        if (!cancelled) setError(true)
      }
    })()
    return () => {
      cancelled = true
      if (currentObj) URL.revokeObjectURL(currentObj)
    }
  }, [src, getToken])

  if (error) return <>{fallback}</>
  if (!objUrl) return <>{fallback}</>
  return <img src={objUrl} alt={alt} className={className} />
}
