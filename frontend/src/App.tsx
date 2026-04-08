import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './components/protected-route'
import { DashboardPage } from './pages/dashboard-page'
import { LoginPage } from './pages/login-page'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

export default App
