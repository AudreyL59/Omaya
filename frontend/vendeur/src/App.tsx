import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from '@/pages/LoginPage'
import DashboardPage from '@/pages/DashboardPage'
import MonComptePage from '@/pages/MonComptePage'
import CooptationPage from '@/pages/CooptationPage'
import AgendaRecrutementPage from '@/pages/AgendaRecrutementPage'
import AgendaCialPage from '@/pages/AgendaCialPage'
import CvthequePage from '@/pages/CvthequePage'
import ConfRdvPage from '@/pages/PageExterne/ConfRdvPage'
import CooptPage from '@/pages/PageExterne/CooptPage'
import OrganigrammePage from '@/pages/OrganigrammePage'
import ClustersPage from '@/pages/ClustersPage'
import TicketsCallSuiviPage from '@/pages/TicketsCallSuiviPage'
import TicketCallEnergiePage from '@/pages/TicketCallEnergiePage'
import TicketCallFibrePage from '@/pages/TicketCallFibrePage'
import ProductionPage from '@shared/production/ProductionPage'
import ProductionDetailPage from '@shared/production/ProductionDetailPage'
import TicketsPage from '@shared/tickets/TicketsPage'
import DialoguesPage from '@shared/dialogues/DialoguesPage'
import ProcessPage from '@shared/process/ProcessPage'
import ScoolSuiviPage from '@/pages/ScoolSuiviPage'
import GestionCodeOhmPage from '@/pages/GestionCodeOhmPage'
import { DialogHost } from '@shared/ui/dialog'
import { getToken, getStoredUser } from '@/api'

const VENDEUR_API = '/api/vendeur'
import Layout from '@/components/Layout'
import ProtectedRoute from '@/components/ProtectedRoute'

// Basename = base Vite sans slash final. En dev + prod : '/vendeur'
const BASENAME = import.meta.env.BASE_URL.replace(/\/$/, '')

function App() {
  return (
    <BrowserRouter basename={BASENAME}>
      <DialogHost />
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Pages externes publiques (sans login) */}
        <Route path="/PageExterne/conf-rdv/:idRdv" element={<ConfRdvPage />} />
        <Route path="/PageExterne/coopt" element={<CooptPage />} />

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
          <Route path="gestion-ohm" element={<GestionCodeOhmPage />} />
          <Route path="scool" element={<ScoolSuiviPage />} />
          <Route path="production" element={<ProductionPage apiBase={VENDEUR_API} />} />
          <Route path="production/jobs/:id" element={<ProductionDetailPage apiBase={VENDEUR_API} />} />
          <Route path="clusters" element={<ClustersPage />} />
          <Route path="tickets" element={<TicketsPage apiBase={VENDEUR_API} getToken={getToken} />} />
          <Route path="process" element={
            <ProcessPage apiBase={VENDEUR_API} getToken={getToken} canEdit={false} />
          } />
          <Route path="tickets-call" element={<TicketsCallSuiviPage />} />
          <Route path="tickets-call/energie" element={<TicketCallEnergiePage />} />
          <Route path="tickets-call/fibre" element={<TicketCallFibrePage />} />
          <Route path="dialogues" element={
            <DialoguesPage
              apiBase={VENDEUR_API}
              getToken={getToken}
              userCial={String(getStoredUser()?.id_salarie ?? '')} />
          } />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
