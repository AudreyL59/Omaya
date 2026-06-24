import LieuxRDVPage from '@shared/recrutement/LieuxRDVPage'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

export default function LieuxRDVPageAdm() {
  useDocumentTitle('Lieux de RDV')
  return <LieuxRDVPage apiBase="/api/adm" />
}
