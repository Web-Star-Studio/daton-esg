import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ProjectDocumentsPage } from '../pages/project-documents-page'
import {
  confirmProjectDocumentUpload,
  createProjectDocumentUpload,
  deleteProjectDocument,
  fetchProject,
  fetchProjectDocuments,
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
  fetchProjectDocuments: vi.fn(),
  uploadFileToPresignedUrl: vi.fn(),
}))

const mockUseAuth = vi.mocked(useAuth)
const mockFetchProject = vi.mocked(fetchProject)
const mockFetchProjectDocuments = vi.mocked(fetchProjectDocuments)
const mockCreateProjectDocumentUpload = vi.mocked(createProjectDocumentUpload)
const mockConfirmProjectDocumentUpload = vi.mocked(confirmProjectDocumentUpload)
const mockDeleteProjectDocument = vi.mocked(deleteProjectDocument)
const mockUploadFileToPresignedUrl = vi.mocked(uploadFileToPresignedUrl)

function getAssertedFileInput(container: HTMLElement) {
  const input = container.querySelector('input[type="file"]')

  if (!(input instanceof HTMLInputElement)) {
    throw new Error('Expected a file input in ProjectDocumentsPage')
  }

  return input
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/projects/project-1']}>
      <Routes>
        <Route path="/projects/:projectId" element={<ProjectDocumentsPage />} />
      </Routes>
    </MemoryRouter>
  )
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
    mockFetchProject.mockResolvedValue({
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
    })
    mockFetchProjectDocuments.mockResolvedValue([])
    mockCreateProjectDocumentUpload.mockReset()
    mockConfirmProjectDocumentUpload.mockReset()
    mockDeleteProjectDocument.mockReset()
    mockUploadFileToPresignedUrl.mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('loads the project and renders the documents empty state', async () => {
    renderPage()

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /documentos/i })
      ).toBeInTheDocument()
    })

    expect(
      screen.getByText(/nenhum documento enviado ainda/i)
    ).toBeInTheDocument()
    expect(mockFetchProject).toHaveBeenCalledWith('project-1')
    expect(mockFetchProjectDocuments).toHaveBeenCalledWith('project-1')
  })

  it('shows a validation error for unsupported file types', async () => {
    const { container } = renderPage()

    await waitFor(() => {
      expect(
        screen.getByText(/nenhum documento enviado ainda/i)
      ).toBeInTheDocument()
    })

    const fileInput = getAssertedFileInput(container)

    fireEvent.change(fileInput, {
      target: {
        files: [new File(['abc'], 'notas.txt', { type: 'text/plain' })],
      },
    })

    expect(screen.getByText(/notas.txt: formato inválido/i)).toBeInTheDocument()
    expect(mockCreateProjectDocumentUpload).not.toHaveBeenCalled()
  })

  it('uploads a document and refreshes the list', async () => {
    const uploadedDocument = {
      id: 'doc-1',
      project_id: 'project-1',
      filename: 'inventario.pdf',
      file_type: 'pdf' as const,
      s3_key: 'uploads/project-1/doc-1/inventario.pdf',
      file_size_bytes: 2048,
      parsing_status: 'pending' as const,
      extracted_text: null,
      esg_category: null,
      created_at: '2026-04-06T00:00:00Z',
    }

    mockFetchProjectDocuments
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([uploadedDocument])
    mockCreateProjectDocumentUpload.mockResolvedValue({
      document_id: 'doc-1',
      upload_url: 'http://localstack:4566/upload-url',
      s3_key: 'uploads/project-1/doc-1/inventario.pdf',
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

    const { container } = renderPage()

    await waitFor(() => {
      expect(
        screen.getByText(/nenhum documento enviado ainda/i)
      ).toBeInTheDocument()
    })

    const fileInput = getAssertedFileInput(container)

    fireEvent.change(fileInput, {
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
    expect(mockFetchProjectDocuments).toHaveBeenCalledTimes(2)
  })

  it('deletes a document from the list', async () => {
    mockFetchProjectDocuments.mockResolvedValue([
      {
        id: 'doc-1',
        project_id: 'project-1',
        filename: 'inventario.pdf',
        file_type: 'pdf',
        s3_key: 'uploads/project-1/doc-1/inventario.pdf',
        file_size_bytes: 2048,
        parsing_status: 'pending',
        extracted_text: null,
        esg_category: null,
        created_at: '2026-04-06T00:00:00Z',
      },
    ])
    mockDeleteProjectDocument.mockResolvedValue(undefined)

    renderPage()

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
