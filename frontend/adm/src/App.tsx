import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from '@/pages/LoginPage'
import DashboardPage from '@/pages/DashboardPage'
import PlaceholderPage from '@/pages/PlaceholderPage'
import StatRHPage from '@/pages/StatRHPage'
import StatRHRdvPage from '@/pages/StatRHRdvPage'
import StatRHEntreeSortiePage from '@/pages/StatRHEntreeSortiePage'
import StatRHSaisieCvPage from '@/pages/StatRHSaisieCvPage'
import StatRHAnnonceursPage from '@/pages/StatRHAnnonceursPage'
import AgendaRecrutementPage from '@/pages/AgendaRecrutementPage'
import OrganigrammePage from '@/pages/OrganigrammePage'
import RecherchePage from '@/pages/RecherchePage'
import RegistreRHPage from '@/pages/RegistreRHPage'
import DpaeRecherchePage from '@/pages/DpaeRecherchePage'
import DpaeNouvellePage from '@/pages/DpaeNouvellePage'
import CttTravailPage from '@/pages/CttTravailPage'
import ProductionPage from '@shared/production/ProductionPage'
import ProductionDetailPage from '@shared/production/ProductionDetailPage'
import AdmTicketsPage from '@/pages/AdmTicketsPage'
import Layout from '@/components/Layout'
import ProtectedRoute from '@/components/ProtectedRoute'
import { DialogHost } from '@shared/ui/dialog'

const BASENAME = import.meta.env.BASE_URL.replace(/\/$/, '')
const ADM_API = '/api/adm'

function App() {
  return (
    <BrowserRouter basename={BASENAME}>
      <DialogHost />
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="agenda-recrutement" element={<AgendaRecrutementPage />} />
          <Route path="envois-sms" element={<PlaceholderPage />} />
          <Route path="factures" element={<PlaceholderPage />} />
          <Route path="recherche-rh" element={<PlaceholderPage />} />
          <Route path="stat-rh" element={<StatRHPage />} />
          <Route path="stat-rh/saisie-cv" element={<StatRHSaisieCvPage />} />
          <Route path="stat-rh/rdv" element={<StatRHRdvPage />} />
          <Route path="stat-rh/dpae-sortie" element={<StatRHEntreeSortiePage />} />
          <Route path="stat-rh/annonceurs" element={<StatRHAnnonceursPage />} />
          <Route path="stat-adv" element={<PlaceholderPage />} />
          <Route path="organigramme" element={<OrganigrammePage />} />
          <Route path="recherche" element={<RecherchePage />} />
          <Route path="salaries/registre" element={<RegistreRHPage />} />
          <Route path="salaries/dpae" element={<DpaeRecherchePage />} />
          <Route path="salaries/dpae/nouvelle" element={<DpaeNouvellePage />} />
          <Route path="salaries/contrats" element={<CttTravailPage />} />
          <Route path="production" element={<ProductionPage apiBase={ADM_API} />} />
          <Route path="production/jobs/:id" element={<ProductionDetailPage apiBase={ADM_API} />} />
          <Route path="tickets" element={<AdmTicketsPage />} />
          {/* Fallback : toute route inconnue dans le shell auth → Placeholder */}
          <Route path="*" element={<PlaceholderPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
