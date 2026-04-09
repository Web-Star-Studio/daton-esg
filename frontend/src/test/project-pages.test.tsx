import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, beforeEach, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ProjectWorkspaceLayout } from '../components/project-workspace-layout'
import { DashboardPage } from '../pages/dashboard-page'
import { ProjectDetailPage } from '../pages/project-detail-page'
import { ProjectDocumentsPage } from '../pages/project-documents-page'
import { ProjectFormPage } from '../pages/project-form-page'
import { useAuth } from '../hooks/use-auth'
import {
  createProject,
  fetchProject,
  fetchProjectDocuments,
  fetchProjects,
  updateProject,
} from '../services/api-client'

vi.mock('../hooks/use-auth', () => ({
  useAuth: vi.fn(),
}))

vi.mock('../services/api-client', () => ({
  archiveProject: vi.fn(),
  confirmProjectDocumentUpload: vi.fn(),
  createProject: vi.fn(),
  createProjectDocumentUpload: vi.fn(),
  deleteProjectDocument: vi.fn(),
  fetchProject: vi.fn(),
  fetchProjectDocuments: vi.fn(),
  fetchProjects: vi.fn(),
  updateProject: vi.fn(),
  uploadFileToPresignedUrl: vi.fn(),
}))

const mockUseAuth = vi.mocked(useAuth)
const mockFetchProjects = vi.mocked(fetchProjects)
const mockFetchProject = vi.mocked(fetchProject)
const mockFetchProjectDocuments = vi.mocked(fetchProjectDocuments)
const mockCreateProject = vi.mocked(createProject)
const mockUpdateProject = vi.mocked(updateProject)

const baseProject = {
  id: 'project-1',
  org_name: 'Acme Inc.',
  org_sector: 'Energia',
  org_size: 'média',
  org_location: 'Recife',
  base_year: 2025,
  scope: 'Escopo base',
  status: 'collecting',
  material_topics: null,
  sdg_goals: null,
  created_at: '2026-04-06T00:00:00Z',
  updated_at: '2026-04-06T00:00:00Z',
}

const secondProject = {
  ...baseProject,
  id: 'project-2',
  org_name: 'Gabarado',
}

describe('project pages', () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      accessToken: 'access-token',
      completeNewPassword: vi.fn(async () => undefined),
      idToken: 'id-token',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(async () => undefined),
      logout: vi.fn(async () => undefined),
      pendingChallenge: null,
      resetPendingChallenge: vi.fn(),
      user: {
        id: 'user-1',
        cognito_sub: 'cognito-sub-1',
        email: 'consultor@example.com',
        name: 'Consultor ESG',
        role: 'consultant',
        created_at: '2026-04-06T00:00:00Z',
      },
    })
    mockFetchProjects.mockReset()
    mockFetchProject.mockReset()
    mockFetchProjectDocuments.mockReset()
    mockCreateProject.mockReset()
    mockUpdateProject.mockReset()
  })

  it('renders the projects dashboard with fetched projects', async () => {
    mockFetchProjects.mockResolvedValue([baseProject])

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <DashboardPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Acme Inc.')).toBeInTheDocument()
    })

    expect(mockFetchProjects).toHaveBeenCalledWith({
      search: undefined,
      status: undefined,
    })
    expect(
      screen.getByRole('button', { name: /novo projeto/i })
    ).toBeInTheDocument()
  })

  it('creates a project and redirects to the detail page', async () => {
    mockCreateProject.mockResolvedValue(baseProject)

    render(
      <MemoryRouter initialEntries={['/projects/new']}>
        <Routes>
          <Route
            path="/projects/new"
            element={<ProjectFormPage mode="create" />}
          />
          <Route
            path="/projects/:projectId"
            element={<div>Detalhe carregado</div>}
          />
        </Routes>
      </MemoryRouter>
    )

    fireEvent.change(screen.getByLabelText(/nome da organização/i), {
      target: { value: 'Acme Inc.' },
    })
    fireEvent.change(screen.getByLabelText(/ano-base/i), {
      target: { value: '2025' },
    })
    fireEvent.click(screen.getByRole('button', { name: /criar projeto/i }))

    await waitFor(() => {
      expect(mockCreateProject).toHaveBeenCalledWith({
        base_year: 2025,
        org_location: null,
        org_name: 'Acme Inc.',
        org_sector: null,
        org_size: null,
        scope: null,
      })
    })

    await waitFor(() => {
      expect(screen.getByText('Detalhe carregado')).toBeInTheDocument()
    })
  })

  it('opens the create project modal from the dashboard and creates a project', async () => {
    mockFetchProjects.mockResolvedValue([])
    mockCreateProject.mockResolvedValue(baseProject)

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route
            path="/projects/:projectId"
            element={<div>Detalhe carregado</div>}
          />
        </Routes>
      </MemoryRouter>
    )

    fireEvent.click(screen.getByRole('button', { name: /novo projeto/i }))

    expect(
      screen.getByRole('heading', { name: /criar novo projeto/i })
    ).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/nome da organização/i), {
      target: { value: 'Acme Inc.' },
    })
    fireEvent.change(screen.getByLabelText(/ano-base/i), {
      target: { value: '2025' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^criar$/i }))

    await waitFor(() => {
      expect(mockCreateProject).toHaveBeenCalledWith({
        base_year: 2025,
        org_location: null,
        org_name: 'Acme Inc.',
        org_sector: null,
        org_size: null,
        scope: null,
      })
    })

    await waitFor(() => {
      expect(screen.getByText('Detalhe carregado')).toBeInTheDocument()
    })
  })

  it('renders the project detail page and keeps generate disabled without documents', async () => {
    mockFetchProject.mockResolvedValue(baseProject)
    mockFetchProjects.mockResolvedValue([baseProject])
    mockFetchProjectDocuments.mockResolvedValue([])

    render(
      <MemoryRouter initialEntries={['/projects/project-1']}>
        <Routes>
          <Route
            path="/projects/:projectId"
            element={<ProjectWorkspaceLayout />}
          >
            <Route index element={<ProjectDetailPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/informações gerais/i)).toBeInTheDocument()
    })

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /editar/i })
      ).toBeInTheDocument()
      expect(
        screen.getByRole('button', { name: /upload de documentos/i })
      ).toBeInTheDocument()
      expect(
        screen.getByRole('button', { name: /gerar relatório/i })
      ).toBeDisabled()
    })
    expect(
      screen.getByText(/nenhum documento enviado ainda/i)
    ).toBeInTheDocument()
  })

  it('preserves the current subroute when changing project from the selector', async () => {
    mockFetchProject.mockImplementation(async (projectId: string) =>
      projectId === 'project-2' ? secondProject : baseProject
    )
    mockFetchProjects.mockResolvedValue([baseProject, secondProject])
    mockFetchProjectDocuments.mockResolvedValue([])

    render(
      <MemoryRouter initialEntries={['/projects/project-1/documents']}>
        <Routes>
          <Route
            path="/projects/:projectId"
            element={<ProjectWorkspaceLayout />}
          >
            <Route path="documents" element={<ProjectDocumentsPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /selecionar projeto/i })
      ).toHaveTextContent('Acme Inc.')
    })

    fireEvent.click(screen.getByRole('button', { name: /selecionar projeto/i }))
    fireEvent.click(screen.getByRole('link', { name: /gabarado/i }))

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /selecionar projeto/i })
      ).toHaveTextContent('Gabarado')
    })

    expect(
      screen.getByRole('heading', { name: /documentos/i })
    ).toBeInTheDocument()
    expect(
      screen.getByText(/nenhum documento enviado ainda/i)
    ).toBeInTheDocument()
  })
})
