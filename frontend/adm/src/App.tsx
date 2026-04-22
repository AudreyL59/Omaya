import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from '@/pages/LoginPage'
import DashboardPage from '@/pages/DashboardPage'
import PlaceholderPage from '@/pages/PlaceholderPage'
import StatRHPage from '@/pages/StatRHPage'
import StatRHRdvPage from '@/pages/StatRHRdvPage'
import Layout from '@/components/Layout'
import ProtectedRoute from '@/components/ProtectedRoute'

const BASENAME = import.meta.env.BASE_URL.replace(/\/$/, '')

function App() {
  return (
    <BrowserRouter basename={BASENAME}>
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
          <Route path="envois-sms" element={<PlaceholderPage />} />
          <Route path="factures" element={<PlaceholderPage />} />
          <Route path="recherche-rh" element={<PlaceholderPage />} />
          <Route path="stat-rh" element={<StatRHPage />} />
          <Route path="stat-rh/saisie-cv" element={<PlaceholderPage />} />
          <Route path="stat-rh/rdv" element={<StatRHRdvPage />} />
          <Route path="stat-rh/dpae-sortie" element={<PlaceholderPage />} />
          <Route path="stat-rh/annonceurs" element={<PlaceholderPage />} />
          <Route path="stat-adv" element={<PlaceholderPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
