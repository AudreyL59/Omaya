/**
 * Wrapper ADM pour la page de recherche CV partagee.
 * ADM voit tout, pas de filtre force.
 */
import RechercheCVPage from '@shared/recrutement/RechercheCVPage'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { getStoredUser } from '@/api'

export default function RechercheCVPageAdm() {
  useDocumentTitle('Recherche CV')
  const user = getStoredUser()
  const myUserId = user ? String(user.id_salarie) : ''

  const openFiche = (idCv: string) => {
    // TODO commit ulterieur : ouvrir Fen_CVFiche en modal
    console.log('Ouvrir fiche CV', idCv)
  }

  return (
    <RechercheCVPage
      apiBase="/api/adm"
      myUserId={myUserId}
      onOpenFiche={openFiche}
    />
  )
}
