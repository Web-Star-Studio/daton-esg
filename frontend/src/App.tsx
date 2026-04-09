import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './components/protected-route'
import { useAuth } from './hooks/use-auth'
import { DashboardPage } from './pages/dashboard-page'
import { LoginPage } from './pages/login-page'
import { ProjectWorkspaceLayout } from './components/project-workspace-layout'
import { ProjectDetailPage } from './pages/project-detail-page'
import { ProjectDocumentsPage } from './pages/project-documents-page'
import { ProjectFormPage } from './pages/project-form-page'
import { ProjectIndicatorsPage } from './pages/project-indicators-page'

function FallbackRoute() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return null
  }

  return <Navigate to={isAuthenticated ? '/dashboard' : '/login'} replace />
}

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
      <Route
        path="/projects/new"
        element={
          <ProtectedRoute>
            <ProjectFormPage mode="create" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:projectId/edit"
        element={
          <ProtectedRoute>
            <ProjectFormPage mode="edit" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:projectId"
        element={
          <ProtectedRoute>
            <ProjectWorkspaceLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<ProjectDetailPage />} />
        <Route path="documents" element={<ProjectDocumentsPage />} />
        <Route path="indicators" element={<ProjectIndicatorsPage />} />
      </Route>
      <Route path="*" element={<FallbackRoute />} />
    </Routes>
  )
}

export default App
