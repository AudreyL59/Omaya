/**
 * Page wrapper pour la saisie de CV (item menu).
 * Monte CVSaisieModal au mount, redirige vers la recherche CV au close.
 */
import { useNavigate } from 'react-router-dom'
import CVSaisieModal from '@shared/recrutement/CVSaisieModal'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

export default function SaisieCVPage() {
  useDocumentTitle('Saisie de CV')
  const navigate = useNavigate()
  return (
    <CVSaisieModal
      apiBase="/api/adm"
      onClose={(createdId, goToFiche) => {
        if (createdId && goToFiche) {
          // Apres creation + 'Aller sur la fiche' : redirige vers Recherche CV
          // qui ouvrira le modal fiche via le state (ou rien, simple navigation)
          navigate('/recrutement/recherche-cv')
        } else {
          navigate('/recrutement/recherche-cv')
        }
      }}
    />
  )
}
