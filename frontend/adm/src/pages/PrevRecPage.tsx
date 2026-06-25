/**
 * Wrapper ADM pour Fen_PrevRec (Prevision de recrutement).
 */
import PrevRecPage from '@shared/recrutement/PrevRecPage'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

export default function PrevRecPageAdm() {
  useDocumentTitle('Prévision de recrutement')
  return <PrevRecPage apiBase="/api/adm" />
}
