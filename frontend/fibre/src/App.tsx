import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from '@/pages/LoginPage'
import DashboardPage from '@/pages/DashboardPage'
import TicketsCallPage from '@/pages/TicketsCallPage'
import { DialogHost } from '@shared/ui/dialog'
import Layout from '@/components/Layout'
import ProtectedRoute from '@/components/ProtectedRoute'

// Basename = base Vite sans slash final. En dev + prod : '/cf'
const BASENAME = import.meta.env.BASE_URL.replace(/\/$/, '')

function App() {
  return (
    <BrowserRouter basename={BASENAME}>
      <DialogHost />
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Routes protegees avec sidebar (servies sous BASENAME) */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="tickets-call" element={<TicketsCallPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
