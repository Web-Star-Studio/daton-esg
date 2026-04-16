import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, beforeEach, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ProjectWorkspaceLayout } from '../components/project-workspace-layout'
import { DashboardPage } from '../pages/dashboard-page'
import { ProjectDetailPage } from '../pages/project-detail-page'
import { ProjectDocumentsPage } from '../pages/project-documents-page'
import { ProjectFormPage } from '../pages/project-form-page'
import { ProjectIndicatorsPage } from '../pages/project-indicators-page'
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
  deleteProject: vi.fn(),
  confirmProjectDocumentUpload: vi.fn(),
  createProject: vi.fn(),
  createProjectDocumentUpload: vi.fn(),
  deleteProjectDocument: vi.fn(),
  fetchIndicatorTemplates: vi.fn().mockResolvedValue([]),
  fetchOdsGoals: vi.fn().mockResolvedValue([]),
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
  indicator_values: null,
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
      expect(
        screen.getByRole('heading', { name: /visão geral/i })
      ).toBeInTheDocument()
    })
  })

  it('preserves the current subroute when changing project from the selector', async () => {
    mockFetchProject.mockImplementation(async (projectId: string) =>
      projectId === 'project-2' ? secondProject : baseProject
    )
    mockFetchProjects.mockResolvedValue([baseProject, secondProject])
    mockFetchProjectDocuments.mockResolvedValue([])

    render(
      <MemoryRouter
        initialEntries={['/projects/project-1/documents/gestao-ambiental']}
      >
        <Routes>
          <Route
            path="/projects/:projectId"
            element={<ProjectWorkspaceLayout />}
          >
            <Route path="documents" element={<ProjectDocumentsPage />} />
            <Route
              path="documents/:directoryKey"
              element={<ProjectDocumentsPage />}
            />
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
      screen.getByRole('heading', { name: /4\. gestão ambiental/i })
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', {
        name: /arraste arquivos aqui ou clique para selecionar/i,
      })
    ).toBeInTheDocument()
    expect(mockFetchProject.mock.calls.map(([projectId]) => projectId)).toEqual(
      ['project-1', 'project-2']
    )
    expect(mockFetchProjectDocuments).toHaveBeenNthCalledWith(1, 'project-1', {
      directory_key: 'gestao-ambiental',
    })
    expect(mockFetchProjectDocuments).toHaveBeenNthCalledWith(2, 'project-2', {
      directory_key: 'gestao-ambiental',
    })
  })

  it('renders an error state instead of the form when loading an edit page fails', async () => {
    mockFetchProject.mockRejectedValue(new Error('Projeto indisponível'))

    render(
      <MemoryRouter initialEntries={['/projects/project-1/edit']}>
        <Routes>
          <Route
            path="/projects/:projectId/edit"
            element={<ProjectFormPage mode="edit" />}
          />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getAllByText('Projeto indisponível')).toHaveLength(2)
    })

    expect(
      screen.queryByLabelText(/nome da organização/i)
    ).not.toBeInTheDocument()
  })

  it('renders the indicators page with the heading', async () => {
    mockFetchProject.mockResolvedValue(baseProject)
    mockFetchProjects.mockResolvedValue([baseProject])

    render(
      <MemoryRouter initialEntries={['/projects/project-1/indicators']}>
        <Routes>
          <Route
            path="/projects/:projectId"
            element={<ProjectWorkspaceLayout />}
          >
            <Route path="indicators" element={<ProjectIndicatorsPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /indicadores esg/i })
      ).toBeInTheDocument()
    })
  })
})
