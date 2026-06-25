/**
 * Wrapper ADM pour Fen_VillesFavorites.
 */
import VillesFavoritesPage from '@shared/recrutement/VillesFavoritesPage'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

export default function VillesFavoritesPageAdm() {
  useDocumentTitle('Villes en favori')
  return <VillesFavoritesPage apiBase="/api/adm" />
}
