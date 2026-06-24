/**
 * Wrapper ADM pour la page de recherche CV partagee.
 * ADM voit tout, pas de filtre force.
 * Double-click sur une ligne : ouvre Fen_CVFiche en modal.
 */
import { useState } from 'react'
import RechercheCVPage from '@shared/recrutement/RechercheCVPage'
import CVFicheModal from '@shared/recrutement/CVFicheModal'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { getStoredUser } from '@/api'

export default function RechercheCVPageAdm() {
  useDocumentTitle('Recherche CV')
  const user = getStoredUser()
  const myUserId = user ? String(user.id_salarie) : ''
  const [openId, setOpenId] = useState<string>('')

  return (
    <>
      <RechercheCVPage
        apiBase="/api/adm"
        myUserId={myUserId}
        onOpenFiche={setOpenId}
      />
      {openId && (
        <CVFicheModal
          apiBase="/api/adm"
          idCv={openId}
          userDroits={user?.droits || []}
          onClose={() => setOpenId('')}
        />
      )}
    </>
  )
}
