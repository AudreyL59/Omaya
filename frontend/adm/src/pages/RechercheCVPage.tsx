/**
 * Wrapper ADM pour la page de recherche CV partagee.
 * ADM voit tout, pas de filtre force.
 * Double-click sur une ligne : ouvre Fen_CVFiche en modal.
 */
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import RechercheCVPage from '@shared/recrutement/RechercheCVPage'
import CVFicheModal from '@shared/recrutement/CVFicheModal'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { getStoredUser } from '@/api'

export default function RechercheCVPageAdm() {
  useDocumentTitle('Recherche CV')
  const user = getStoredUser()
  const myUserId = user ? String(user.id_salarie) : ''
  const [openId, setOpenId] = useState<string>('')
  const [removedIds, setRemovedIds] = useState<string[]>([])
  const location = useLocation()
  const navigate = useNavigate()

  // Si on arrive ici via navigate(..., {state: {openCvId}}) (typiquement
  // depuis Fen_CVSaisie), on ouvre directement la fiche CV creee.
  useEffect(() => {
    const state = location.state as { openCvId?: string } | null
    if (state?.openCvId) {
      setOpenId(state.openCvId)
      // Nettoie le state pour eviter de re-ouvrir si retour navigation
      navigate(location.pathname, { replace: true, state: {} })
    }
  }, [location, navigate])

  return (
    <>
      <RechercheCVPage
        apiBase="/api/adm"
        myUserId={myUserId}
        onOpenFiche={setOpenId}
        removedIds={removedIds}
      />
      {openId && (
        <CVFicheModal
          apiBase="/api/adm"
          idCv={openId}
          userDroits={user?.droits || []}
          onDeleted={(id) => setRemovedIds((prev) => [...prev, id])}
          onClose={() => setOpenId('')}
        />
      )}
    </>
  )
}
