import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ProjectWorkspaceLayout } from '../components/project-workspace-layout'
import { useAuth } from '../hooks/use-auth'
import { ProjectDetailPage } from '../pages/project-detail-page'
import {
  createProjectGenerationThread,
  deleteProjectGenerationThread,
  fetchProject,
  fetchProjectGenerationThread,
  fetchProjectGenerationThreads,
  fetchProjects,
  streamProjectGenerationMessage,
} from '../services/api-client'

vi.mock('../hooks/use-auth', () => ({
  useAuth: vi.fn(),
}))

vi.mock('../services/api-client', () => ({
  createProjectGenerationThread: vi.fn(),
  deleteProjectGenerationThread: vi.fn(),
  fetchProject: vi.fn(),
  fetchProjectGenerationThread: vi.fn(),
  fetchProjectGenerationThreads: vi.fn(),
  fetchProjects: vi.fn(),
  streamProjectGenerationMessage: vi.fn(),
}))

const mockUseAuth = vi.mocked(useAuth)
const mockCreateProjectGenerationThread = vi.mocked(
  createProjectGenerationThread
)
const mockDeleteProjectGenerationThread = vi.mocked(
  deleteProjectGenerationThread
)
const mockFetchProject = vi.mocked(fetchProject)
const mockFetchProjectGenerationThread = vi.mocked(fetchProjectGenerationThread)
const mockFetchProjectGenerationThreads = vi.mocked(
  fetchProjectGenerationThreads
)
const mockFetchProjects = vi.mocked(fetchProjects)
const mockStreamProjectGenerationMessage = vi.mocked(
  streamProjectGenerationMessage
)

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

function renderWorkspace(initialPath = '/projects/project-1') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/projects/:projectId" element={<ProjectWorkspaceLayout />}>
          <Route index element={<ProjectDetailPage />} />
        </Route>
      </Routes>
    </MemoryRouter>
  )
}

async function openDrawer() {
  const [trigger] = await screen.findAllByRole('button', {
    name: /abrir agente/i,
  })
  fireEvent.click(trigger)
  await waitFor(() => {
    expect(screen.getByRole('dialog', { name: /agente/i })).toBeInTheDocument()
  })
}

describe('agent drawer', () => {
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
    mockCreateProjectGenerationThread.mockReset()
    mockDeleteProjectGenerationThread.mockReset()
    mockFetchProject.mockReset()
    mockFetchProjectGenerationThread.mockReset()
    mockFetchProjectGenerationThreads.mockReset()
    mockFetchProjects.mockReset()
    mockStreamProjectGenerationMessage.mockReset()
  })

  it('loads threads and renders selected thread messages when opened', async () => {
    mockFetchProject.mockResolvedValue(baseProject)
    mockFetchProjects.mockResolvedValue([baseProject])
    mockFetchProjectGenerationThreads.mockResolvedValue([
      {
        id: 'thread-1',
        project_id: 'project-1',
        title: 'Resumo executivo',
        created_at: '2026-04-13T10:00:00Z',
        updated_at: '2026-04-13T10:05:00Z',
      },
    ])
    mockFetchProjectGenerationThread.mockResolvedValue({
      thread: {
        id: 'thread-1',
        project_id: 'project-1',
        title: 'Resumo executivo',
        created_at: '2026-04-13T10:00:00Z',
        updated_at: '2026-04-13T10:05:00Z',
      },
      messages: [
        {
          id: 'assistant-1',
          thread_id: 'thread-1',
          project_id: 'project-1',
          role: 'assistant',
          content: 'Há evidências na base sobre estratégia e governança.',
          citations: [
            {
              document_id: 'doc-1',
              filename: 'plano.pdf',
              directory_key: 'visao-estrategica-de-sustentabilidade',
              chunk_index: 0,
              source_type: 'pdf_page',
              score: 0.91,
              snippet: 'Trecho indexado do plano estratégico.',
            },
          ],
          created_at: '2026-04-13T10:00:00Z',
        },
      ],
    })

    renderWorkspace()
    await openDrawer()

    await waitFor(() => {
      expect(screen.getByText('Resumo executivo')).toBeInTheDocument()
    })

    await waitFor(() => {
      expect(
        screen.getByText('Há evidências na base sobre estratégia e governança.')
      ).toBeInTheDocument()
    })

    expect(screen.getByText('Evidências utilizadas')).toBeInTheDocument()
    expect(screen.getByText('plano.pdf')).toBeInTheDocument()
  })

  it('creates a thread from the empty drawer state and selects it', async () => {
    mockFetchProject.mockResolvedValue(baseProject)
    mockFetchProjects.mockResolvedValue([baseProject])
    mockFetchProjectGenerationThreads.mockResolvedValue([])
    mockCreateProjectGenerationThread.mockResolvedValue({
      id: 'thread-2',
      project_id: 'project-1',
      title: 'Nova conversa',
      created_at: '2026-04-13T10:00:00Z',
      updated_at: '2026-04-13T10:00:00Z',
    })
    mockFetchProjectGenerationThread.mockResolvedValue({
      thread: {
        id: 'thread-2',
        project_id: 'project-1',
        title: 'Nova conversa',
        created_at: '2026-04-13T10:00:00Z',
        updated_at: '2026-04-13T10:00:00Z',
      },
      messages: [],
    })

    renderWorkspace()
    await openDrawer()

    await waitFor(() => {
      expect(screen.getByText(/nenhuma conversa ainda/i)).toBeInTheDocument()
    })

    fireEvent.click(
      screen.getByRole('button', { name: /criar primeira conversa/i })
    )

    await waitFor(() => {
      expect(mockCreateProjectGenerationThread).toHaveBeenCalledWith(
        'project-1'
      )
    })

    await waitFor(() => {
      expect(screen.getByText('Nova conversa')).toBeInTheDocument()
    })
  })

  it('streams a new message and renders the final assistant response', async () => {
    mockFetchProject.mockResolvedValue(baseProject)
    mockFetchProjects.mockResolvedValue([baseProject])
    mockFetchProjectGenerationThreads.mockResolvedValue([
      {
        id: 'thread-1',
        project_id: 'project-1',
        title: 'Resumo executivo',
        created_at: '2026-04-13T10:00:00Z',
        updated_at: '2026-04-13T10:05:00Z',
      },
    ])
    mockFetchProjectGenerationThread.mockResolvedValue({
      thread: {
        id: 'thread-1',
        project_id: 'project-1',
        title: 'Resumo executivo',
        created_at: '2026-04-13T10:00:00Z',
        updated_at: '2026-04-13T10:05:00Z',
      },
      messages: [],
    })
    mockStreamProjectGenerationMessage.mockImplementation(
      async (_projectId, _threadId, _payload, handlers) => {
        handlers.onUserMessage?.({
          id: 'user-1',
          thread_id: 'thread-1',
          project_id: 'project-1',
          role: 'user',
          content: 'Quais evidências já foram indexadas?',
          citations: [],
          created_at: '2026-04-13T10:00:00Z',
        })
        handlers.onToken?.('Já há ')
        handlers.onToken?.('evidências indexadas.')
        handlers.onAssistantMessage?.({
          id: 'assistant-1',
          thread_id: 'thread-1',
          project_id: 'project-1',
          role: 'assistant',
          content: 'Já há evidências indexadas.',
          citations: [],
          created_at: '2026-04-13T10:00:03Z',
        })
        handlers.onDone?.()
      }
    )

    renderWorkspace()
    await openDrawer()

    await waitFor(() => {
      expect(screen.getByText('Resumo executivo')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByLabelText(/escreva sua mensagem/i), {
      target: { value: 'Quais evidências já foram indexadas?' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^enviar$/i }))

    await waitFor(() => {
      expect(mockStreamProjectGenerationMessage).toHaveBeenCalledWith(
        'project-1',
        'thread-1',
        {
          content: 'Quais evidências já foram indexadas?',
        },
        expect.any(Object)
      )
    })

    await waitFor(() => {
      expect(
        screen.getByText('Já há evidências indexadas.')
      ).toBeInTheDocument()
    })
  })

  it('reloads threads when the workspace project changes', async () => {
    mockFetchProject.mockImplementation(async (projectId: string) =>
      projectId === 'project-2' ? secondProject : baseProject
    )
    mockFetchProjects.mockResolvedValue([baseProject, secondProject])
    mockFetchProjectGenerationThreads.mockImplementation(
      async (projectId: string) => [
        {
          id: `thread-${projectId}`,
          project_id: projectId,
          title: `Conversa ${projectId}`,
          created_at: '2026-04-13T10:00:00Z',
          updated_at: '2026-04-13T10:05:00Z',
        },
      ]
    )
    mockFetchProjectGenerationThread.mockImplementation(
      async (projectId: string, threadId: string) => ({
        thread: {
          id: threadId,
          project_id: projectId,
          title: `Conversa ${projectId}`,
          created_at: '2026-04-13T10:00:00Z',
          updated_at: '2026-04-13T10:05:00Z',
        },
        messages: [
          {
            id: `assistant-${projectId}`,
            thread_id: threadId,
            project_id: projectId,
            role: 'assistant',
            content:
              projectId === 'project-2'
                ? 'Resposta do projeto Gabarado.'
                : 'Resposta do projeto Acme Inc.',
            citations: [],
            created_at: '2026-04-13T10:00:00Z',
          },
        ],
      })
    )

    renderWorkspace()
    await openDrawer()

    await waitFor(() => {
      expect(
        screen.getByText('Resposta do projeto Acme Inc.')
      ).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /selecionar projeto/i }))
    fireEvent.click(screen.getByRole('link', { name: /gabarado/i }))

    await waitFor(() => {
      expect(
        screen.getByText('Resposta do projeto Gabarado.')
      ).toBeInTheDocument()
    })
  })

  it('deletes a thread from the picker after confirmation', async () => {
    mockFetchProject.mockResolvedValue(baseProject)
    mockFetchProjects.mockResolvedValue([baseProject])
    mockFetchProjectGenerationThreads.mockResolvedValue([
      {
        id: 'thread-1',
        project_id: 'project-1',
        title: 'Resumo executivo',
        created_at: '2026-04-13T10:00:00Z',
        updated_at: '2026-04-13T10:05:00Z',
      },
      {
        id: 'thread-2',
        project_id: 'project-1',
        title: 'Análise de materialidade',
        created_at: '2026-04-13T09:00:00Z',
        updated_at: '2026-04-13T09:05:00Z',
      },
    ])
    mockFetchProjectGenerationThread.mockImplementation(
      async (_projectId: string, threadId: string) => ({
        thread: {
          id: threadId,
          project_id: 'project-1',
          title:
            threadId === 'thread-2'
              ? 'Análise de materialidade'
              : 'Resumo executivo',
          created_at: '2026-04-13T10:00:00Z',
          updated_at: '2026-04-13T10:05:00Z',
        },
        messages: [],
      })
    )
    mockDeleteProjectGenerationThread.mockResolvedValue(undefined)

    renderWorkspace()
    await openDrawer()

    await waitFor(() => {
      expect(screen.getByText('Resumo executivo')).toBeInTheDocument()
    })

    // Open the thread picker.
    fireEvent.click(
      screen.getByRole('button', { name: /selecionar conversa/i })
    )

    await waitFor(() => {
      expect(screen.getByText('Análise de materialidade')).toBeInTheDocument()
    })

    // Click trash on the non-active thread.
    fireEvent.click(
      screen.getByRole('button', {
        name: /excluir conversa análise de materialidade/i,
      })
    )

    // Confirm.
    fireEvent.click(
      screen.getByRole('button', {
        name: /confirmar exclusão de análise de materialidade/i,
      })
    )

    await waitFor(() => {
      expect(mockDeleteProjectGenerationThread).toHaveBeenCalledWith(
        'project-1',
        'thread-2'
      )
    })

    await waitFor(() => {
      expect(
        screen.queryByText('Análise de materialidade')
      ).not.toBeInTheDocument()
    })

    // Active thread stayed selected.
    expect(screen.getAllByText('Resumo executivo').length).toBeGreaterThan(0)
  })

  it('deleting the active thread switches to the next remaining one', async () => {
    mockFetchProject.mockResolvedValue(baseProject)
    mockFetchProjects.mockResolvedValue([baseProject])
    mockFetchProjectGenerationThreads.mockResolvedValue([
      {
        id: 'thread-1',
        project_id: 'project-1',
        title: 'Resumo executivo',
        created_at: '2026-04-13T10:00:00Z',
        updated_at: '2026-04-13T10:05:00Z',
      },
      {
        id: 'thread-2',
        project_id: 'project-1',
        title: 'Análise de materialidade',
        created_at: '2026-04-13T09:00:00Z',
        updated_at: '2026-04-13T09:05:00Z',
      },
    ])
    mockFetchProjectGenerationThread.mockImplementation(
      async (_projectId: string, threadId: string) => ({
        thread: {
          id: threadId,
          project_id: 'project-1',
          title:
            threadId === 'thread-2'
              ? 'Análise de materialidade'
              : 'Resumo executivo',
          created_at: '2026-04-13T10:00:00Z',
          updated_at: '2026-04-13T10:05:00Z',
        },
        messages: [
          {
            id: `msg-${threadId}`,
            thread_id: threadId,
            project_id: 'project-1',
            role: 'assistant',
            content:
              threadId === 'thread-2'
                ? 'Conteúdo de materialidade.'
                : 'Conteúdo do resumo.',
            citations: [],
            created_at: '2026-04-13T10:00:00Z',
          },
        ],
      })
    )
    mockDeleteProjectGenerationThread.mockResolvedValue(undefined)

    renderWorkspace()
    await openDrawer()

    await waitFor(() => {
      expect(screen.getByText('Conteúdo do resumo.')).toBeInTheDocument()
    })

    fireEvent.click(
      screen.getByRole('button', { name: /selecionar conversa/i })
    )

    await waitFor(() => {
      expect(screen.getByText('Análise de materialidade')).toBeInTheDocument()
    })

    fireEvent.click(
      screen.getByRole('button', {
        name: /excluir conversa resumo executivo/i,
      })
    )
    fireEvent.click(
      screen.getByRole('button', {
        name: /confirmar exclusão de resumo executivo/i,
      })
    )

    await waitFor(() => {
      expect(mockDeleteProjectGenerationThread).toHaveBeenCalledWith(
        'project-1',
        'thread-1'
      )
    })

    await waitFor(() => {
      expect(screen.getByText('Conteúdo de materialidade.')).toBeInTheDocument()
    })
  })
})
