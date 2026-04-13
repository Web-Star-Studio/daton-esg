import type { AuthenticatedUser } from '../types/auth'
import type {
  CreateProjectDocumentUploadInput,
  MoveProjectDocumentInput,
  ProjectCreateInput,
  ProjectDocument,
  ProjectDocumentUploadSession,
  ProjectKnowledgeReindexResponse,
  ProjectKnowledgeStatus,
  ProjectRecord,
  ProjectUpdateInput,
} from '../types/project'

let authToken: string | null = null

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function setApiAuthToken(token: string | null) {
  authToken = token
}

async function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers)

  if (authToken) {
    headers.set('Authorization', `Bearer ${authToken}`)
  }

  return fetch(path, {
    ...init,
    headers,
  })
}

async function parseApiError(
  response: Response,
  fallbackMessage: string
): Promise<ApiError> {
  try {
    const payload = (await response.json()) as { detail?: string }
    return new ApiError(payload.detail ?? fallbackMessage, response.status)
  } catch {
    return new ApiError(fallbackMessage, response.status)
  }
}

export async function fetchCurrentUser() {
  const response = await apiFetch('/api/v1/auth/me')

  if (!response.ok) {
    const message =
      response.status === 401 || response.status === 403
        ? 'Não foi possível validar sua sessão no backend.'
        : `Falha ao carregar o usuário autenticado (${response.status}).`

    throw new ApiError(message, response.status)
  }

  return (await response.json()) as AuthenticatedUser
}

export async function fetchProject(projectId: string) {
  const response = await apiFetch(`/api/v1/projects/${projectId}`)

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao carregar o projeto (${response.status}).`
    )
  }

  return (await response.json()) as ProjectRecord
}

export async function fetchProjects(filters?: {
  search?: string
  status?: string
}) {
  const query = new URLSearchParams()

  if (filters?.search) {
    query.set('search', filters.search)
  }

  if (filters?.status) {
    query.set('status', filters.status)
  }

  const response = await apiFetch(
    `/api/v1/projects${query.size > 0 ? `?${query.toString()}` : ''}`
  )

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao carregar os projetos (${response.status}).`
    )
  }

  return (await response.json()) as ProjectRecord[]
}

export async function createProject(payload: ProjectCreateInput) {
  const response = await apiFetch('/api/v1/projects', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao criar o projeto (${response.status}).`
    )
  }

  return (await response.json()) as ProjectRecord
}

export async function updateProject(
  projectId: string,
  payload: ProjectUpdateInput
) {
  const response = await apiFetch(`/api/v1/projects/${projectId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao atualizar o projeto (${response.status}).`
    )
  }

  return (await response.json()) as ProjectRecord
}

export async function archiveProject(projectId: string) {
  const response = await apiFetch(`/api/v1/projects/${projectId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao arquivar o projeto (${response.status}).`
    )
  }
}

export async function fetchProjectDocuments(
  projectId: string,
  filters?: { directory_key?: string }
) {
  const query = new URLSearchParams()

  if (filters?.directory_key) {
    query.set('directory_key', filters.directory_key)
  }

  const response = await apiFetch(
    `/api/v1/projects/${projectId}/documents${
      query.size > 0 ? `?${query.toString()}` : ''
    }`
  )

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao carregar os documentos (${response.status}).`
    )
  }

  return (await response.json()) as ProjectDocument[]
}

export async function createProjectDocumentUpload(
  projectId: string,
  payload: CreateProjectDocumentUploadInput
) {
  const response = await apiFetch(`/api/v1/projects/${projectId}/documents`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao preparar o upload (${response.status}).`
    )
  }

  return (await response.json()) as ProjectDocumentUploadSession
}

export async function confirmProjectDocumentUpload(
  projectId: string,
  documentId: string
) {
  const response = await apiFetch(
    `/api/v1/projects/${projectId}/documents/${documentId}/confirm`,
    {
      method: 'POST',
    }
  )

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao confirmar o upload (${response.status}).`
    )
  }

  return (await response.json()) as ProjectDocument
}

export async function deleteProjectDocument(
  projectId: string,
  documentId: string
) {
  const response = await apiFetch(
    `/api/v1/projects/${projectId}/documents/${documentId}`,
    {
      method: 'DELETE',
    }
  )

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao remover o documento (${response.status}).`
    )
  }
}

export async function moveProjectDocument(
  projectId: string,
  documentId: string,
  payload: MoveProjectDocumentInput
) {
  const response = await apiFetch(
    `/api/v1/projects/${projectId}/documents/${documentId}`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    }
  )

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao mover o documento (${response.status}).`
    )
  }

  return (await response.json()) as ProjectDocument
}

export async function fetchProjectKnowledgeStatus(projectId: string) {
  const response = await apiFetch(
    `/api/v1/projects/${projectId}/knowledge/status`
  )

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao carregar o status da base de conhecimento (${response.status}).`
    )
  }

  return (await response.json()) as ProjectKnowledgeStatus
}

export async function reindexProjectKnowledge(projectId: string) {
  const response = await apiFetch(
    `/api/v1/projects/${projectId}/knowledge/reindex`,
    {
      method: 'POST',
    }
  )

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao reindexar a base de conhecimento (${response.status}).`
    )
  }

  return (await response.json()) as ProjectKnowledgeReindexResponse
}

export function uploadFileToPresignedUrl(
  file: File,
  uploadUrl: string,
  contentType: string,
  onProgress?: (progress: number) => void
) {
  return new Promise<void>((resolve, reject) => {
    const request = new XMLHttpRequest()

    request.open('PUT', uploadUrl)
    request.setRequestHeader('Content-Type', contentType)

    request.upload.addEventListener('progress', (event) => {
      if (!event.lengthComputable || !onProgress) {
        return
      }

      const progress = Math.round((event.loaded / event.total) * 100)
      onProgress(progress)
    })

    request.addEventListener('load', () => {
      if (request.status >= 200 && request.status < 300) {
        onProgress?.(100)
        resolve()
        return
      }

      reject(new Error(`Upload falhou com status ${request.status}.`))
    })

    request.addEventListener('error', () => {
      reject(new Error('Não foi possível enviar o arquivo para o storage.'))
    })

    request.addEventListener('abort', () => {
      onProgress?.(0)
      reject(new Error('Upload aborted'))
    })

    request.send(file)
  })
}
