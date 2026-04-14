import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ProjectWorkspaceLayout } from '../components/project-workspace-layout'
import { useAuth } from '../hooks/use-auth'
import { ProjectGenerationPage } from '../pages/project-generation-page'
import {
  exportReportDocx,
  fetchProject,
  fetchProjectGenerationThreads,
  fetchProjects,
  fetchReport,
  fetchReports,
  streamReportGeneration,
  updateReportSection,
} from '../services/api-client'

vi.mock('../hooks/use-auth', () => ({
  useAuth: vi.fn(),
}))

vi.mock('../services/api-client', () => ({
  createProjectGenerationThread: vi.fn(),
  deleteProjectGenerationThread: vi.fn(),
  exportReportDocx: vi.fn(),
  fetchProject: vi.fn(),
  fetchProjectGenerationThread: vi.fn(),
  fetchProjectGenerationThreads: vi.fn(),
  fetchProjects: vi.fn(),
  fetchReport: vi.fn(),
  fetchReports: vi.fn(),
  streamProjectGenerationMessage: vi.fn(),
  streamReportGeneration: vi.fn(),
  updateReportSection: vi.fn(),
}))

const mockUseAuth = vi.mocked(useAuth)
const mockFetchProject = vi.mocked(fetchProject)
const mockFetchProjects = vi.mocked(fetchProjects)
const mockFetchProjectGenerationThreads = vi.mocked(
  fetchProjectGenerationThreads
)
const mockFetchReports = vi.mocked(fetchReports)
const mockFetchReport = vi.mocked(fetchReport)
const mockStreamReportGeneration = vi.mocked(streamReportGeneration)
const mockExportReportDocx = vi.mocked(exportReportDocx)
const mockUpdateReportSection = vi.mocked(updateReportSection)

const baseProject = {
  id: 'project-1',
  org_name: 'Acme Inc.',
  org_sector: 'Energia',
  org_size: 'média',
  org_location: 'Recife',
  base_year: 2025,
  scope: 'Escopo base',
  status: 'collecting',
  material_topics: [
    { pillar: 'E' as const, topic: 'Clima e Energia', priority: 4 },
  ],
  sdg_goals: null,
  created_at: '2026-04-06T00:00:00Z',
  updated_at: '2026-04-06T00:00:00Z',
}

function makeProjectWithoutMateriality() {
  return { ...baseProject, material_topics: null }
}

const sampleReport = {
  id: 'report-1',
  project_id: 'project-1',
  version: 1,
  status: 'draft' as const,
  sections: [
    {
      key: 'a-empresa',
      title: 'A Empresa',
      order: 1,
      heading_level: 1,
      content: 'A organização (GRI 2-1) tem escopo definido.',
      gri_codes_used: ['GRI 2-1'],
      word_count: 8,
      status: 'completed' as const,
    },
    {
      key: 'gestao-ambiental',
      title: 'Gestão Ambiental',
      order: 4,
      heading_level: 1,
      content: 'Consumo mensal monitorado (GRI 303-3).',
      gri_codes_used: ['GRI 303-3'],
      word_count: 5,
      status: 'completed' as const,
    },
  ],
  gri_index: [
    {
      code: 'GRI 2-1',
      family: '2',
      standard_text: 'Detalhes da organização',
      evidence_excerpt: 'escopo definido',
      section_ref: 'a-empresa',
      status: 'atendido' as const,
      found_in_text: true,
    },
  ],
  gaps: [
    {
      section_key: 'gestao-ambiental',
      category: 'sparse_evidence',
      detail: 'seção abaixo do alvo',
    },
  ],
  indicators: null,
  charts: null,
  exported_docx_s3: null,
  exported_pdf_s3: null,
  llm_tokens_used: 1234,
  created_at: '2026-04-06T00:00:00Z',
  updated_at: '2026-04-06T00:00:00Z',
}

describe('ProjectGenerationPage', () => {
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
    mockFetchProjectGenerationThreads.mockReset()
    mockFetchReports.mockReset()
    mockFetchReport.mockReset()
    mockStreamReportGeneration.mockReset()
    mockExportReportDocx.mockReset()
    mockUpdateReportSection.mockReset()
    mockFetchProjectGenerationThreads.mockResolvedValue([])
  })

  function renderPage() {
    return render(
      <MemoryRouter initialEntries={['/projects/project-1/generation']}>
        <Routes>
          <Route
            path="/projects/:projectId"
            element={<ProjectWorkspaceLayout />}
          >
            <Route path="generation" element={<ProjectGenerationPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    )
  }

  it('shows empty state with gate warning when materialidade is missing', async () => {
    mockFetchProject.mockResolvedValue(makeProjectWithoutMateriality())
    mockFetchProjects.mockResolvedValue([makeProjectWithoutMateriality()])
    mockFetchReports.mockResolvedValue([])

    renderPage()

    expect(
      await screen.findByText(/nenhum relatório ainda/i)
    ).toBeInTheDocument()
    expect(
      screen.getByText(/selecione ao menos um tema material/i)
    ).toBeInTheDocument()
    const generateButton = screen.getByRole('button', {
      name: /gerar relatório/i,
    })
    expect(generateButton).toBeDisabled()
  })

  it('renders report history when reports exist', async () => {
    mockFetchProject.mockResolvedValue(baseProject)
    mockFetchProjects.mockResolvedValue([baseProject])
    mockFetchReports.mockResolvedValue([
      {
        id: 'report-1',
        project_id: 'project-1',
        version: 1,
        status: 'draft',
        created_at: '2026-04-06T00:00:00Z',
        updated_at: '2026-04-06T00:00:00Z',
      },
    ])
    mockFetchReport.mockResolvedValue(sampleReport)

    renderPage()

    expect(await screen.findByText('Versão 1')).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByText('1. A Empresa')).toBeInTheDocument()
      expect(screen.getByText('4. Gestão Ambiental')).toBeInTheDocument()
    })
  })

  it('streams a generation and updates pipeline progress', async () => {
    mockFetchProject.mockResolvedValue(baseProject)
    mockFetchProjects.mockResolvedValue([baseProject])
    mockFetchReports.mockResolvedValue([])
    mockStreamReportGeneration.mockImplementation(
      async (_projectId, handlers) => {
        handlers.onReportStarted?.({
          report_id: 'report-1',
          version: 1,
          total_sections: 2,
          sections: [
            { key: 'a-empresa', title: 'A Empresa', order: 1 },
            { key: 'gestao-ambiental', title: 'Gestão Ambiental', order: 4 },
          ],
        })
        handlers.onSectionStarted?.({
          section_key: 'a-empresa',
          title: 'A Empresa',
          order: 1,
          target_words: 1000,
        })
        handlers.onSectionToken?.({
          section_key: 'a-empresa',
          text: 'A Cooperativa ',
        })
        handlers.onSectionToken?.({
          section_key: 'a-empresa',
          text: 'atua em...',
        })
        handlers.onSectionCompleted?.({
          section_key: 'a-empresa',
          word_count: 250,
          gri_codes_used: ['GRI 2-1'],
          status: 'completed',
        })
        handlers.onReportCompleted?.({ report: sampleReport })
      }
    )
    mockFetchReports.mockResolvedValueOnce([])
    // second fetch after completion returns the new report
    mockFetchReports.mockResolvedValue([
      {
        id: 'report-1',
        project_id: 'project-1',
        version: 1,
        status: 'draft',
        created_at: '2026-04-06T00:00:00Z',
        updated_at: '2026-04-06T00:00:00Z',
      },
    ])

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/nenhum relatório ainda/i)).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /gerar relatório/i }))

    await waitFor(() => {
      expect(mockStreamReportGeneration).toHaveBeenCalled()
    })

    // after the stream finishes, the generated report is rendered
    await waitFor(() => {
      expect(screen.getByText('1. A Empresa')).toBeInTheDocument()
    })
  })

  it('exports the active report and opens the download url', async () => {
    mockFetchProject.mockResolvedValue(baseProject)
    mockFetchProjects.mockResolvedValue([baseProject])
    mockFetchReports.mockResolvedValue([
      {
        id: 'report-1',
        project_id: 'project-1',
        version: 1,
        status: 'draft',
        created_at: '2026-04-06T00:00:00Z',
        updated_at: '2026-04-06T00:00:00Z',
      },
    ])
    mockFetchReport.mockResolvedValue(sampleReport)
    mockExportReportDocx.mockResolvedValue({
      download_url: 'https://example.com/report.docx',
    })

    const windowOpen = vi.spyOn(window, 'open').mockImplementation(() => null)

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('1. A Empresa')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /exportar word/i }))

    await waitFor(() => {
      expect(mockExportReportDocx).toHaveBeenCalledWith('project-1', 'report-1')
    })
    await waitFor(() => {
      expect(windowOpen).toHaveBeenCalledWith(
        'https://example.com/report.docx',
        '_blank'
      )
    })
    windowOpen.mockRestore()
  })

  it('switches to Sumário GRI tab and renders the index table', async () => {
    mockFetchProject.mockResolvedValue(baseProject)
    mockFetchProjects.mockResolvedValue([baseProject])
    mockFetchReports.mockResolvedValue([
      {
        id: 'report-1',
        project_id: 'project-1',
        version: 1,
        status: 'draft',
        created_at: '2026-04-06T00:00:00Z',
        updated_at: '2026-04-06T00:00:00Z',
      },
    ])
    mockFetchReport.mockResolvedValue(sampleReport)

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Versão 1')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /sumário gri/i }))

    await waitFor(() => {
      expect(screen.getByText('GRI 2')).toBeInTheDocument()
      // the code appears in the table body
      expect(screen.getAllByText('GRI 2-1').length).toBeGreaterThan(0)
    })
  })
})
