import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ProjectWorkspaceLayout } from '../components/project-workspace-layout'
import { ProjectDocumentsPage } from '../pages/project-documents-page'
import {
  confirmProjectDocumentUpload,
  createProjectDocumentUpload,
  deleteProjectDocument,
  fetchProject,
  fetchProjects,
  fetchProjectDocuments,
  moveProjectDocument,
  uploadFileToPresignedUrl,
} from '../services/api-client'
import { useAuth } from '../hooks/use-auth'

vi.mock('../hooks/use-auth', () => ({
  useAuth: vi.fn(),
}))

vi.mock('../services/api-client', () => ({
  ApiError: class ApiError extends Error {
    status: number

    constructor(message: string, status: number) {
      super(message)
      this.name = 'ApiError'
      this.status = status
    }
  },
  confirmProjectDocumentUpload: vi.fn(),
  createProjectDocumentUpload: vi.fn(),
  deleteProjectDocument: vi.fn(),
  fetchProject: vi.fn(),
  fetchProjects: vi.fn(),
  fetchProjectDocuments: vi.fn(),
  moveProjectDocument: vi.fn(),
  uploadFileToPresignedUrl: vi.fn(),
}))

const mockUseAuth = vi.mocked(useAuth)
const mockFetchProject = vi.mocked(fetchProject)
const mockFetchProjects = vi.mocked(fetchProjects)
const mockFetchProjectDocuments = vi.mocked(fetchProjectDocuments)
const mockCreateProjectDocumentUpload = vi.mocked(createProjectDocumentUpload)
const mockConfirmProjectDocumentUpload = vi.mocked(confirmProjectDocumentUpload)
const mockDeleteProjectDocument = vi.mocked(deleteProjectDocument)
const mockMoveProjectDocument = vi.mocked(moveProjectDocument)
const mockUploadFileToPresignedUrl = vi.mocked(uploadFileToPresignedUrl)

function makeProjectDocument(
  overrides: Partial<import('../types/project').ProjectDocument> = {}
) {
  return {
    id: 'doc-1',
    project_id: 'project-1',
    filename: 'inventario.pdf',
    file_type: 'pdf' as const,
    s3_key: 'uploads/project-1/gestao-ambiental/doc-1/inventario.pdf',
    directory_key: 'gestao-ambiental',
    file_size_bytes: 2048,
    indexing_status: 'indexed' as const,
    indexing_error: null,
    indexed_at: '2026-04-06T00:00:00Z',
    created_at: '2026-04-06T00:00:00Z',
    ...overrides,
  }
}

function getAssertedFileInput(container: HTMLElement) {
  const input = container.querySelector('input[type="file"]')

  if (!(input instanceof HTMLInputElement)) {
    throw new Error('Expected a file input in ProjectDocumentsPage')
  }

  return input
}

function renderPage(initialEntry = '/projects/project-1/documents') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/projects/:projectId" element={<ProjectWorkspaceLayout />}>
          <Route path="documents" element={<ProjectDocumentsPage />} />
          <Route
            path="documents/:directoryKey"
            element={<ProjectDocumentsPage />}
          />
        </Route>
      </Routes>
    </MemoryRouter>
  )
}

const baseProject = {
  id: 'project-1',
  org_name: 'Acme Inc.',
  org_sector: 'Energia',
  org_size: null,
  org_location: null,
  base_year: 2025,
  scope: null,
  status: 'collecting',
  material_topics: null,
  sdg_goals: null,
  created_at: '2026-04-06T00:00:00Z',
  updated_at: '2026-04-06T00:00:00Z',
}

describe('ProjectDocumentsPage', () => {
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
    mockFetchProject.mockResolvedValue(baseProject)
    mockFetchProjects.mockResolvedValue([baseProject])
    mockFetchProjectDocuments.mockResolvedValue([])
    mockCreateProjectDocumentUpload.mockReset()
    mockConfirmProjectDocumentUpload.mockReset()
    mockDeleteProjectDocument.mockReset()
    mockMoveProjectDocument.mockReset()
    mockUploadFileToPresignedUrl.mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders the drive root with the fixed folders and no uploader', async () => {
    mockFetchProjectDocuments.mockResolvedValue([makeProjectDocument()])

    renderPage()

    expect(
      await screen.findByRole('link', {
        name: /1\. visão estratégica de sustentabilidade/i,
      })
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /3\. gestão ambiental/i })
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', {
        name: /arraste arquivos aqui ou clique para selecionar/i,
      })
    ).not.toBeInTheDocument()
  })

  it('uploads a document inside the selected folder', async () => {
    const uploadedDocument = makeProjectDocument()

    mockFetchProjectDocuments
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([uploadedDocument])
    mockCreateProjectDocumentUpload.mockResolvedValue({
      document_id: 'doc-1',
      upload_url: 'http://localstack:4566/upload-url',
      s3_key: 'uploads/project-1/gestao-ambiental/doc-1/inventario.pdf',
      content_type: 'application/pdf',
      expires_in_seconds: 900,
    })
    mockUploadFileToPresignedUrl.mockImplementation(
      async (_file, _url, _contentType, onProgress) => {
        onProgress?.(25)
        onProgress?.(100)
      }
    )
    mockConfirmProjectDocumentUpload.mockResolvedValue(uploadedDocument)

    const { container } = renderPage(
      '/projects/project-1/documents/gestao-ambiental'
    )

    await waitFor(() => {
      expect(
        screen.getByRole('button', {
          name: /arraste arquivos aqui ou clique para selecionar/i,
        })
      ).toBeInTheDocument()
    })

    fireEvent.change(getAssertedFileInput(container), {
      target: {
        files: [
          new File(['pdf'], 'inventario.pdf', { type: 'application/pdf' }),
        ],
      },
    })

    await waitFor(() => {
      expect(mockCreateProjectDocumentUpload).toHaveBeenCalledWith(
        'project-1',
        {
          directory_key: 'gestao-ambiental',
          filename: 'inventario.pdf',
          file_size_bytes: 3,
        }
      )
    })

    await waitFor(() => {
      expect(screen.getByText('inventario.pdf')).toBeInTheDocument()
    })

    expect(mockConfirmProjectDocumentUpload).toHaveBeenCalledWith(
      'project-1',
      'doc-1'
    )
  })

  it('moves a document to another folder', async () => {
    mockFetchProjectDocuments.mockResolvedValue([makeProjectDocument()])
    mockMoveProjectDocument.mockResolvedValue(
      makeProjectDocument({
        directory_key: 'governanca-corporativa',
      })
    )

    renderPage('/projects/project-1/documents/gestao-ambiental')

    expect(await screen.findByText('inventario.pdf')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/mover documento/i), {
      target: { value: 'governanca-corporativa' },
    })

    await waitFor(() => {
      expect(mockMoveProjectDocument).toHaveBeenCalledWith(
        'project-1',
        'doc-1',
        {
          directory_key: 'governanca-corporativa',
        }
      )
    })

    await waitFor(() => {
      expect(screen.queryByText('inventario.pdf')).not.toBeInTheDocument()
    })
  })

  it('deletes a document from the current folder', async () => {
    mockFetchProjectDocuments.mockResolvedValue([makeProjectDocument()])
    mockDeleteProjectDocument.mockResolvedValue(undefined)

    renderPage('/projects/project-1/documents/gestao-ambiental')

    await waitFor(() => {
      expect(screen.getByText('inventario.pdf')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /remover/i }))

    await waitFor(() => {
      expect(mockDeleteProjectDocument).toHaveBeenCalledWith(
        'project-1',
        'doc-1'
      )
    })

    await waitFor(() => {
      expect(screen.queryByText('inventario.pdf')).not.toBeInTheDocument()
    })
  })
})
