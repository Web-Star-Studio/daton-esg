import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './components/protected-route'
import { DashboardPage } from './pages/dashboard-page'
import { HomePage } from './pages/home-page'
import { LoginPage } from './pages/login-page'

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
