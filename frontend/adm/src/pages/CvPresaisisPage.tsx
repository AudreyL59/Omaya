/**
 * Wrapper ADM pour Fen_CVPresaisis (liste mails CV recus a traiter).
 */
import { useState } from 'react'
import CvPresaisisPage from '@shared/recrutement/CvPresaisisPage'
import CVFicheModal from '@shared/recrutement/CVFicheModal'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { getStoredUser } from '@/api'

export default function CvPresaisisPageAdm() {
  useDocumentTitle('CV Pré-saisis')
  const user = getStoredUser()
  const [openId, setOpenId] = useState('')

  return (
    <>
      <CvPresaisisPage apiBase="/api/adm" onOpenFiche={setOpenId} />
      {openId && (
        <CVFicheModal apiBase="/api/adm" idCv={openId}
                      userDroits={user?.droits || []}
                      onClose={() => setOpenId('')} />
      )}
    </>
  )
}
