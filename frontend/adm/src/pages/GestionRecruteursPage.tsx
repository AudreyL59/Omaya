/**
 * Wrapper ADM pour Fen_Agenda_GestionRecruteur.
 */
import GestionRecruteursPage from '@shared/recrutement/GestionRecruteursPage'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

export default function GestionRecruteursPageAdm() {
  useDocumentTitle('Gestion Recruteurs')
  return <GestionRecruteursPage apiBase="/api/adm" />
}
