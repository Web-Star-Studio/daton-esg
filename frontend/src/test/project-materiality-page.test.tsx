import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  ProjectWorkspaceContext,
  type ProjectWorkspaceContextValue,
} from '../hooks/use-project-workspace'
import { ProjectMaterialityPage } from '../pages/project-materiality-page'
import {
  fetchGriStandards,
  fetchOdsGoals,
  listExtractionSuggestions,
  updateProject,
} from '../services/api-client'
import type { ProjectRecord } from '../types/project'

// Mock the api-client module so the page never reaches the network and we
// don't pull the heavy module graph (markdown, amplify, etc.).
vi.mock('../services/api-client', () => ({
  fetchGriStandards: vi.fn(),
  fetchOdsGoals: vi.fn(),
  fetchProject: vi.fn(),
  updateProject: vi.fn(),
  // Hook below uses these — keep them as no-op vi.fn()s.
  listExtractionSuggestions: vi.fn(),
  startExtractionRun: vi.fn(),
  fetchExtractionRun: vi.fn(),
  streamExtractionRun: vi.fn(),
  updateExtractionSuggestion: vi.fn(),
  bulkUpdateExtractionSuggestions: vi.fn(),
}))

const mockFetchGriStandards = vi.mocked(fetchGriStandards)
const mockFetchOdsGoals = vi.mocked(fetchOdsGoals)
const mockUpdateProject = vi.mocked(updateProject)
const mockListExtractionSuggestions = vi.mocked(listExtractionSuggestions)

const baseProject: ProjectRecord = {
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

function makeContextValue(
  overrides: Partial<ProjectWorkspaceContextValue> = {}
): ProjectWorkspaceContextValue {
  return {
    closeAgentDrawer: vi.fn(),
    currentProjectId: 'project-1',
    isAgentDrawerOpen: false,
    isLoadingWorkspace: false,
    navigateToProject: vi.fn(),
    openAgentDrawer: vi.fn(),
    project: baseProject,
    projects: [baseProject],
    setActiveSidebarKey: vi.fn(),
    setPageActions: vi.fn(),
    setPageTitle: vi.fn(),
    setProject: vi.fn(),
    workspaceError: null,
    ...overrides,
  }
}

function renderPage(
  contextOverrides: Partial<ProjectWorkspaceContextValue> = {}
) {
  const value = makeContextValue(contextOverrides)
  const utils = render(
    <ProjectWorkspaceContext.Provider value={value}>
      <ProjectMaterialityPage />
    </ProjectWorkspaceContext.Provider>
  )
  return { ...utils, contextValue: value }
}

describe('ProjectMaterialityPage', () => {
  beforeEach(() => {
    mockFetchGriStandards.mockReset()
    mockFetchOdsGoals.mockReset()
    mockUpdateProject.mockReset()
    mockListExtractionSuggestions.mockReset()

    mockFetchGriStandards.mockResolvedValue([
      {
        code: 'GRI 301-1',
        family: '300',
        standard_text: 'Materiais utilizados por peso ou volume',
      },
      {
        code: 'GRI 305-1',
        family: '300',
        standard_text: 'Emissões diretas de GEE (Escopo 1)',
      },
      {
        code: 'GRI 401-1',
        family: '400',
        standard_text: 'Novas contratações de empregados e rotatividade',
      },
    ])
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
    mockListExtractionSuggestions.mockResolvedValue({ items: [], total: 0 })
  })

  it('renders pillars and GRI disclosures from the reference API', async () => {
    renderPage()

    expect(
      await screen.findByRole('heading', {
        level: 2,
        name: /materialidade & ods/i,
      })
    ).toBeInTheDocument()

    await waitFor(() => {
      expect(mockFetchGriStandards).toHaveBeenCalled()
    })

    await waitFor(() => {
      expect(screen.getByText('GRI 301-1')).toBeInTheDocument()
      expect(
        screen.getByText('Materiais utilizados por peso ou volume')
      ).toBeInTheDocument()
      expect(screen.getByText('GRI 401-1')).toBeInTheDocument()
    })
  })

  it('renders ODS cards fetched from the reference API', async () => {
    renderPage()

    fireEvent.click(await screen.findByRole('tab', { name: /^ODS$/i }))

    await waitFor(() => {
      expect(screen.getByText('ODS 7')).toBeInTheDocument()
      expect(screen.getByText('Energia Limpa e Acessível')).toBeInTheDocument()
      expect(screen.getByText('ODS 13')).toBeInTheDocument()
    })
  })

  it('saves selected material topics and SDG goals when Save is clicked', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('GRI 305-1')).toBeInTheDocument()
    })

    const topicCheckbox = screen.getByRole('checkbox', { name: /gri 305-1/i })
    fireEvent.click(topicCheckbox)

    await waitFor(() => {
      expect(topicCheckbox).toBeChecked()
    })

    fireEvent.click(screen.getByRole('button', { name: /^alta$/i }))

    fireEvent.click(screen.getByRole('tab', { name: /^ODS$/i }))

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
      { pillar: 'E', topic: 'GRI 305-1', priority: 'alta' },
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
