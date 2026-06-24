/**
 * Wrapper ADM pour la page Recherche CV par mots-cles.
 */
import RechercheCvMotsClesPage from '@shared/recrutement/RechercheCvMotsClesPage'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

export default function RechercheCvMotsClesPageAdm() {
  useDocumentTitle('Recherche CV par mots-clés')
  return <RechercheCvMotsClesPage apiBase="/api/adm" />
}
