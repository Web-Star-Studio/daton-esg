import { refreshAuthTokens } from './amplify-auth'
import type { AuthenticatedUser } from '../types/auth'
import type {
  CreateProjectDocumentUploadInput,
  GriStandardRecord,
  IndicatorTemplateRecord,
  MoveProjectDocumentInput,
  OdsGoalRecord,
  ProjectCreateInput,
  ProjectDocument,
  ProjectDocumentUploadSession,
  ProjectGenerationMessage,
  ProjectGenerationThread,
  ProjectGenerationThreadDetail,
  ProjectKnowledgeReindexResponse,
  ProjectKnowledgeStatus,
  ProjectRecord,
  ProjectUpdateInput,
  ReportListItem,
  ReportRecord,
  ReportSection,
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

  const response = await fetch(path, { ...init, headers })

  // On 401 try a transparent token refresh + single retry
  if (response.status === 401 && authToken) {
    const tokens = await refreshAuthTokens()
    const bearer = tokens?.idToken ?? tokens?.accessToken
    if (bearer) {
      authToken = bearer
      const retryHeaders = new Headers(init.headers)
      retryHeaders.set('Authorization', `Bearer ${bearer}`)
      return fetch(path, { ...init, headers: retryHeaders })
    }
  }

  return response
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

export async function deleteProject(projectId: string) {
  const response = await apiFetch(`/api/v1/projects/${projectId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao excluir o projeto (${response.status}).`
    )
  }
}

/** @deprecated Use deleteProject instead. */
export const archiveProject = deleteProject

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

export async function fetchGriStandards() {
  const response = await apiFetch('/api/v1/reference/gri-standards')
  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao carregar os padrões GRI (${response.status}).`
    )
  }
  return (await response.json()) as GriStandardRecord[]
}

export async function fetchOdsGoals() {
  const response = await apiFetch('/api/v1/reference/ods-goals')
  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao carregar os ODS (${response.status}).`
    )
  }
  return (await response.json()) as OdsGoalRecord[]
}

export async function fetchIndicatorTemplates() {
  const response = await apiFetch('/api/v1/reference/indicator-templates')
  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao carregar os indicadores de referência (${response.status}).`
    )
  }
  return (await response.json()) as IndicatorTemplateRecord[]
}

export async function fetchProjectGenerationThreads(projectId: string) {
  const response = await apiFetch(
    `/api/v1/projects/${projectId}/generation/threads`
  )

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao carregar as conversas do agente (${response.status}).`
    )
  }

  return (await response.json()) as ProjectGenerationThread[]
}

export async function createProjectGenerationThread(projectId: string) {
  const response = await apiFetch(
    `/api/v1/projects/${projectId}/generation/threads`,
    {
      method: 'POST',
    }
  )

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao criar a conversa (${response.status}).`
    )
  }

  return (await response.json()) as ProjectGenerationThread
}

export async function deleteProjectGenerationThread(
  projectId: string,
  threadId: string
) {
  const response = await apiFetch(
    `/api/v1/projects/${projectId}/generation/threads/${threadId}`,
    {
      method: 'DELETE',
    }
  )

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao remover a conversa (${response.status}).`
    )
  }
}

export async function fetchProjectGenerationThread(
  projectId: string,
  threadId: string
) {
  const response = await apiFetch(
    `/api/v1/projects/${projectId}/generation/threads/${threadId}`
  )

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao carregar a conversa (${response.status}).`
    )
  }

  return (await response.json()) as ProjectGenerationThreadDetail
}

export async function fetchProjectGenerationThreadMessages(
  projectId: string,
  threadId: string
) {
  const response = await apiFetch(
    `/api/v1/projects/${projectId}/generation/threads/${threadId}/messages`
  )

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao carregar as mensagens (${response.status}).`
    )
  }

  return (await response.json()) as ProjectGenerationMessage[]
}

type StreamProjectGenerationMessageHandlers = {
  onThread?: (thread: ProjectGenerationThread) => void
  onUserMessage?: (message: ProjectGenerationMessage) => void
  onToken?: (text: string) => void
  onAssistantMessage?: (message: ProjectGenerationMessage) => void
  onError?: (message: string) => void
  onDone?: () => void
}

function processSseChunk(
  rawChunk: string,
  handlers: StreamProjectGenerationMessageHandlers
) {
  const normalizedChunk = rawChunk.replace(/\r/g, '')
  const lines = normalizedChunk.split('\n')
  let event = 'message'
  const dataLines: string[] = []

  for (const line of lines) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
      continue
    }

    if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trimStart())
    }
  }

  if (dataLines.length === 0) {
    return
  }

  const payload = JSON.parse(dataLines.join('\n')) as
    | ProjectGenerationThread
    | ProjectGenerationMessage
    | { text: string }
    | { message: string }
    | Record<string, never>

  if (event === 'thread') {
    handlers.onThread?.(payload as ProjectGenerationThread)
    return
  }

  if (event === 'user_message') {
    handlers.onUserMessage?.(payload as ProjectGenerationMessage)
    return
  }

  if (event === 'token') {
    handlers.onToken?.((payload as { text: string }).text ?? '')
    return
  }

  if (event === 'assistant_message') {
    handlers.onAssistantMessage?.(payload as ProjectGenerationMessage)
    return
  }

  if (event === 'error') {
    handlers.onError?.(
      (payload as { message: string }).message ??
        'Não foi possível obter resposta do agente.'
    )
    return
  }

  if (event === 'done') {
    handlers.onDone?.()
  }
}

export async function streamProjectGenerationMessage(
  projectId: string,
  threadId: string,
  payload: { content: string },
  handlers: StreamProjectGenerationMessageHandlers
) {
  const response = await apiFetch(
    `/api/v1/projects/${projectId}/generation/threads/${threadId}/messages/stream`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    }
  )

  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao enviar a mensagem ao agente (${response.status}).`
    )
  }

  if (!response.body) {
    throw new Error('O backend não retornou um stream válido.')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done })

    let boundaryIndex = buffer.indexOf('\n\n')
    while (boundaryIndex >= 0) {
      const rawChunk = buffer.slice(0, boundaryIndex).trim()
      buffer = buffer.slice(boundaryIndex + 2)

      if (rawChunk) {
        processSseChunk(rawChunk, handlers)
      }

      boundaryIndex = buffer.indexOf('\n\n')
    }

    if (done) {
      const finalChunk = buffer.trim()
      if (finalChunk) {
        processSseChunk(finalChunk, handlers)
      }
      break
    }
  }
}

export async function fetchReports(projectId: string) {
  const response = await apiFetch(`/api/v1/projects/${projectId}/reports`)
  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao carregar os relatórios (${response.status}).`
    )
  }
  return (await response.json()) as ReportListItem[]
}

export async function fetchReport(projectId: string, reportId: string) {
  const response = await apiFetch(
    `/api/v1/projects/${projectId}/reports/${reportId}`
  )
  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao carregar o relatório (${response.status}).`
    )
  }
  return (await response.json()) as ReportRecord
}

export async function updateReportSection(
  projectId: string,
  reportId: string,
  sectionKey: string,
  content: string
) {
  const response = await apiFetch(
    `/api/v1/projects/${projectId}/reports/${reportId}/sections/${sectionKey}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    }
  )
  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao atualizar a seção (${response.status}).`
    )
  }
  return (await response.json()) as ReportRecord
}

export async function deleteReport(projectId: string, reportId: string) {
  const response = await apiFetch(
    `/api/v1/projects/${projectId}/reports/${reportId}`,
    { method: 'DELETE' }
  )
  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao excluir o relatório (${response.status}).`
    )
  }
}

export async function exportReportDocx(projectId: string, reportId: string) {
  const response = await apiFetch(
    `/api/v1/projects/${projectId}/reports/${reportId}/export/docx`,
    { method: 'POST' }
  )
  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao exportar o relatório (${response.status}).`
    )
  }
  return (await response.json()) as { download_url: string }
}

export type ReportStreamHandlers = {
  onReportStarted?: (data: {
    report_id: string
    version: number
    total_sections: number
    sections: Array<{ key: string; title: string; order: number }>
  }) => void
  onSectionStarted?: (data: {
    section_key: string
    title: string
    order: number
    target_words: number
  }) => void
  onSectionToken?: (data: { section_key: string; text: string }) => void
  onSectionCompleted?: (data: {
    section_key: string
    word_count: number
    gri_codes_used: string[]
    status: ReportSection['status']
  }) => void
  onSectionFailed?: (data: { section_key: string; error: string }) => void
  onGriSummaryBuilt?: (data: { total_codes: number }) => void
  onReportCompleted?: (data: { report: ReportRecord | null }) => void
  onReportFailed?: (data: { message: string }) => void
}

function _processReportSseChunk(
  rawChunk: string,
  handlers: ReportStreamHandlers
): void {
  const normalized = rawChunk.replace(/\r/g, '')
  const lines = normalized.split('\n')
  let event = 'message'
  const dataLines: string[] = []
  for (const line of lines) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
      continue
    }
    if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trimStart())
    }
  }
  if (dataLines.length === 0) {
    return
  }
  const payload = JSON.parse(dataLines.join('\n')) as Record<string, unknown>
  switch (event) {
    case 'report_started':
      handlers.onReportStarted?.(payload as never)
      return
    case 'section_started':
      handlers.onSectionStarted?.(payload as never)
      return
    case 'section_token':
      handlers.onSectionToken?.(payload as never)
      return
    case 'section_completed':
      handlers.onSectionCompleted?.(payload as never)
      return
    case 'section_failed':
      handlers.onSectionFailed?.(payload as never)
      return
    case 'gri_summary_built':
      handlers.onGriSummaryBuilt?.(payload as never)
      return
    case 'report_completed':
      handlers.onReportCompleted?.(payload as never)
      return
    case 'report_failed':
      handlers.onReportFailed?.(payload as never)
      return
    default:
      return
  }
}

export async function streamReportGeneration(
  projectId: string,
  handlers: ReportStreamHandlers,
  sectionKeys?: string[]
) {
  const body =
    sectionKeys && sectionKeys.length > 0
      ? JSON.stringify({ section_keys: sectionKeys })
      : undefined
  const response = await apiFetch(
    `/api/v1/projects/${projectId}/reports/generate`,
    {
      method: 'POST',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body,
    }
  )
  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao iniciar a geração do relatório (${response.status}).`
    )
  }
  if (!response.body) {
    throw new Error('O backend não retornou um stream válido.')
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done })
    let boundary = buffer.indexOf('\n\n')
    while (boundary >= 0) {
      const rawChunk = buffer.slice(0, boundary).trim()
      buffer = buffer.slice(boundary + 2)
      if (rawChunk) {
        _processReportSseChunk(rawChunk, handlers)
      }
      boundary = buffer.indexOf('\n\n')
    }
    if (done) {
      const finalChunk = buffer.trim()
      if (finalChunk) {
        _processReportSseChunk(finalChunk, handlers)
      }
      break
    }
  }
}

export async function streamSectionRegeneration(
  projectId: string,
  reportId: string,
  sectionKey: string,
  handlers: ReportStreamHandlers
) {
  const response = await apiFetch(
    `/api/v1/projects/${projectId}/reports/${reportId}/sections/${sectionKey}/generate`,
    { method: 'POST' }
  )
  if (!response.ok) {
    throw await parseApiError(
      response,
      `Falha ao regenerar a seção (${response.status}).`
    )
  }
  if (!response.body) {
    throw new Error('O backend não retornou um stream válido.')
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done })
    let boundary = buffer.indexOf('\n\n')
    while (boundary >= 0) {
      const rawChunk = buffer.slice(0, boundary).trim()
      buffer = buffer.slice(boundary + 2)
      if (rawChunk) {
        _processReportSseChunk(rawChunk, handlers)
      }
      boundary = buffer.indexOf('\n\n')
    }
    if (done) {
      const finalChunk = buffer.trim()
      if (finalChunk) {
        _processReportSseChunk(finalChunk, handlers)
      }
      break
    }
  }
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
