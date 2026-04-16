import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ProjectWorkspaceLayout } from '../components/project-workspace-layout'
import { useAuth } from '../hooks/use-auth'
import { ProjectMaterialityPage } from '../pages/project-materiality-page'
import {
  fetchOdsGoals,
  fetchProject,
  fetchProjects,
  updateProject,
} from '../services/api-client'

vi.mock('../hooks/use-auth', () => ({
  useAuth: vi.fn(),
}))

vi.mock('../services/api-client', () => ({
  createProjectGenerationThread: vi.fn(),
  deleteProjectGenerationThread: vi.fn(),
  fetchIndicatorTemplates: vi.fn(),
  fetchOdsGoals: vi.fn(),
  fetchProject: vi.fn(),
  fetchProjectGenerationThread: vi.fn(),
  fetchProjectGenerationThreads: vi.fn(),
  fetchProjects: vi.fn(),
  streamProjectGenerationMessage: vi.fn(),
  updateProject: vi.fn(),
}))

const mockUseAuth = vi.mocked(useAuth)
const mockFetchProject = vi.mocked(fetchProject)
const mockFetchProjects = vi.mocked(fetchProjects)
const mockFetchOdsGoals = vi.mocked(fetchOdsGoals)
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

describe('ProjectMaterialityPage', () => {
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
    mockFetchProject.mockReset()
    mockFetchProjects.mockReset()
    mockFetchOdsGoals.mockReset()
    mockUpdateProject.mockReset()
    mockFetchProject.mockResolvedValue(baseProject)
    mockFetchProjects.mockResolvedValue([baseProject])
    mockFetchOdsGoals.mockResolvedValue([
      {
        ods_number: 7,
        objetivo: 'Energia Limpa e Acessível',
        metas: [{ meta_code: '7.1', meta_text: 'Acesso universal à energia' }],
      },
      {
        ods_number: 13,
        objetivo: 'Ação contra a Mudança Global do Clima',
        metas: [],
      },
    ])
    mockUpdateProject.mockImplementation(async (_id, payload) => ({
      ...baseProject,
      material_topics: (payload.material_topics ?? null) as never,
      sdg_goals: (payload.sdg_goals ?? null) as never,
    }))
  })

  function renderPage() {
    return render(
      <MemoryRouter initialEntries={['/projects/project-1/materiality']}>
        <Routes>
          <Route
            path="/projects/:projectId"
            element={<ProjectWorkspaceLayout />}
          >
            <Route path="materiality" element={<ProjectMaterialityPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    )
  }

  it('renders pillars and topics from the static catalog', async () => {
    renderPage()

    expect(
      await screen.findByRole('heading', {
        level: 2,
        name: /materialidade & ods/i,
      })
    ).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('Descarbonização e GEE')).toBeInTheDocument()
      expect(
        screen.getByText('Diversidade, Equidade e Inclusão (DEI)')
      ).toBeInTheDocument()
      expect(
        screen.getByText('Ética, Anticorrupção e Compliance')
      ).toBeInTheDocument()
    })
  })

  it('renders ODS cards fetched from the reference API', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('ODS 7')).toBeInTheDocument()
      expect(screen.getByText('Energia Limpa e Acessível')).toBeInTheDocument()
      expect(screen.getByText('ODS 13')).toBeInTheDocument()
    })
  })

  it('saves selected material topics and SDG goals when Save is clicked', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Descarbonização e GEE')).toBeInTheDocument()
    })

    const topicCheckbox = screen.getByRole('checkbox', {
      name: /descarbonização e gee/i,
    })
    fireEvent.click(topicCheckbox)

    await waitFor(() => {
      expect(topicCheckbox).toBeChecked()
    })

    fireEvent.click(
      screen.getByRole('checkbox', { name: /ods 7.*energia limpa/i })
    )

    fireEvent.click(screen.getByRole('button', { name: /salvar/i }))

    await waitFor(() => {
      expect(mockUpdateProject).toHaveBeenCalled()
    })

    const call = mockUpdateProject.mock.calls[0]
    expect(call[0]).toBe('project-1')
    expect(call[1].material_topics).toEqual([
      { pillar: 'E', topic: 'Descarbonização e GEE', priority: 3 },
    ])
    expect(call[1].sdg_goals).toEqual([
      {
        ods_number: 7,
        objetivo: 'Energia Limpa e Acessível',
        acao: '',
        indicador: '',
        resultado: '',
      },
    ])
  })
})
