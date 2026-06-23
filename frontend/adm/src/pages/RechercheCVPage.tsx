/**
 * Wrapper ADM pour la page de recherche CV partagee.
 * ADM voit tout, pas de filtre force.
 */
import RechercheCVPage from '@shared/recrutement/RechercheCVPage'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

export default function RechercheCVPageAdm() {
  useDocumentTitle('Recherche CV')
  return <RechercheCVPage apiBase="/api/adm" />
}
