/**
 * Wrapper Vendeur pour la page CVtheque partagee (identique a l'ADM).
 *
 * Le backend Vendeur (get_recherche_cv_router("vendeur")) force
 * automatiquement id_cvsource=1 + id_elem_source=user au moment
 * du /search. On n'a donc pas besoin de filtresForces cote frontend.
 *
 * Double-clic sur une ligne : ouvre Fen_CVFiche (CVFicheModal).
 *
 * L'ancien composant standalone est archive dans
 * CvthequePage.legacy.tsx.bak au cas ou.
 */
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import RechercheCVPage from '@shared/recrutement/RechercheCVPage'
import CVFicheModal from '@shared/recrutement/CVFicheModal'
import { getStoredUser } from '@/api'

const API_BASE = '/api/vendeur'

export default function CvthequePage() {
  useEffect(() => {
    const prev = document.title
    document.title = 'CVthèque · Omaya'
    return () => { document.title = prev }
  }, [])
  const user = getStoredUser()
  const myUserId = user ? String(user.id_salarie) : ''
  // Cf. WinDev :
  //   COMBO_IDcvsource = 1
  //   COMBO_IDcvsource..Visible = VerifDroit("CV_VoirComplet")
  const hasVoirComplet = (user?.droits || []).includes('CV_VoirComplet')
  const filtresForces = hasVoirComplet
    ? {}
    : { id_cvsource: '1', id_elem_source: myUserId }
  const [openId, setOpenId] = useState<string>('')
  const [removedIds, setRemovedIds] = useState<string[]>([])
  const [reopenSaisie, setReopenSaisie] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()

  // Si on arrive ici via navigate(..., {state: {openCvId}})
  // (typiquement depuis Fen_CVSaisie), on ouvre directement la fiche.
  useEffect(() => {
    const state = location.state as {
      openCvId?: string; reopenSaisieAfter?: boolean
    } | null
    if (state?.openCvId) {
      setOpenId(state.openCvId)
      setReopenSaisie(!!state.reopenSaisieAfter)
      navigate(location.pathname, { replace: true, state: {} })
    }
  }, [location, navigate])

  const handleFicheClose = () => {
    setOpenId('')
    if (reopenSaisie) {
      setReopenSaisie(false)
      navigate('/recrutement/saisie-cv')
    }
  }

  return (
    <>
      <RechercheCVPage
        apiBase={API_BASE}
        myUserId={myUserId}
        onOpenFiche={setOpenId}
        removedIds={removedIds}
        filtresForces={filtresForces}
        hideSource={!hasVoirComplet}
      />
      {openId && (
        <CVFicheModal
          apiBase={API_BASE}
          idCv={openId}
          userDroits={user?.droits || []}
          onDeleted={(id) => setRemovedIds((prev) => [...prev, id])}
          onClose={handleFicheClose}
        />
      )}
    </>
  )
}
