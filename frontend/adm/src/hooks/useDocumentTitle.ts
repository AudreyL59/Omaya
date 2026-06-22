/**
 * Hook pour le titre de l'onglet navigateur.
 *
 * Usage : useDocumentTitle('Registre du personnel') -> "OMAYA Adm — Registre
 * du personnel". A la sortie, restaure le titre d'origine du document.
 */

import { useEffect } from 'react'

const PREFIX = 'OMAYA Adm'

export function useDocumentTitle(suffix: string | null | undefined) {
  useEffect(() => {
    const original = document.title
    const s = (suffix || '').trim()
    document.title = s ? `${PREFIX} — ${s}` : PREFIX
    return () => {
      document.title = original
    }
  }, [suffix])
}
