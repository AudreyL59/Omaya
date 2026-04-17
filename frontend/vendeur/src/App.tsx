import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from '@/pages/LoginPage'
import DashboardPage from '@/pages/DashboardPage'
import PlaceholderPage from '@/pages/PlaceholderPage'
import Layout from '@/components/Layout'
import ProtectedRoute from '@/components/ProtectedRoute'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Routes protégées avec sidebar */}
        <Route
          path="/vendeur"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="mon-compte" element={<PlaceholderPage />} />
          <Route path="cooptation" element={<PlaceholderPage />} />
          <Route path="agenda-recrutement" element={<PlaceholderPage />} />
          <Route path="agenda-cial" element={<PlaceholderPage />} />
          <Route path="cvtheque" element={<PlaceholderPage />} />
          <Route path="organigramme" element={<PlaceholderPage />} />
          <Route path="gestion-ohm" element={<PlaceholderPage />} />
          <Route path="scool" element={<PlaceholderPage />} />
          <Route path="production" element={<PlaceholderPage />} />
          <Route path="clusters" element={<PlaceholderPage />} />
          <Route path="tickets" element={<PlaceholderPage />} />
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
