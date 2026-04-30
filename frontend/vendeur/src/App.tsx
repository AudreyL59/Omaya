import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from '@/pages/LoginPage'
import DashboardPage from '@/pages/DashboardPage'
import MonComptePage from '@/pages/MonComptePage'
import CooptationPage from '@/pages/CooptationPage'
import AgendaRecrutementPage from '@/pages/AgendaRecrutementPage'
import AgendaCialPage from '@/pages/AgendaCialPage'
import CvthequePage from '@/pages/CvthequePage'
import OrganigrammePage from '@/pages/OrganigrammePage'
import ClustersPage from '@/pages/ClustersPage'
import ProductionPage from '@shared/production/ProductionPage'
import ProductionDetailPage from '@shared/production/ProductionDetailPage'
import TicketsPage from '@shared/tickets/TicketsPage'
import { getToken } from '@/api'

const VENDEUR_API = '/api/vendeur'
import PlaceholderPage from '@/pages/PlaceholderPage'
import Layout from '@/components/Layout'
import ProtectedRoute from '@/components/ProtectedRoute'

// Basename = base Vite sans slash final. En dev + prod : '/vendeur'
const BASENAME = import.meta.env.BASE_URL.replace(/\/$/, '')

function App() {
  return (
    <BrowserRouter basename={BASENAME}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Routes protégées avec sidebar (servies sous BASENAME) */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="mon-compte" element={<MonComptePage />} />
          <Route path="cooptation" element={<CooptationPage />} />
          <Route path="agenda-recrutement" element={<AgendaRecrutementPage />} />
          <Route path="agenda-cial" element={<AgendaCialPage />} />
          <Route path="cvtheque" element={<CvthequePage />} />
          <Route path="organigramme" element={<OrganigrammePage />} />
          <Route path="gestion-ohm" element={<PlaceholderPage />} />
          <Route path="scool" element={<PlaceholderPage />} />
          <Route path="production" element={<ProductionPage apiBase={VENDEUR_API} />} />
          <Route path="production/jobs/:id" element={<ProductionDetailPage apiBase={VENDEUR_API} />} />
          <Route path="clusters" element={<ClustersPage />} />
          <Route path="tickets" element={<TicketsPage apiBase={VENDEUR_API} getToken={getToken} />} />
          <Route path="process" element={<PlaceholderPage />} />
          <Route path="tickets-call" element={<PlaceholderPage />} />
          <Route path="tickets-call/energie" element={<PlaceholderPage />} />
          <Route path="tickets-call/fibre" element={<PlaceholderPage />} />
          <Route path="dialogues" element={<PlaceholderPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
