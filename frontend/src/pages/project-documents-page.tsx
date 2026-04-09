import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { DocumentList } from '../components/document-list'
import { FileUploader, type PendingUpload } from '../components/file-uploader'
import { ProjectShell } from '../components/project-shell'
import {
  confirmProjectDocumentUpload,
  createProjectDocumentUpload,
  deleteProjectDocument,
  fetchProject,
  fetchProjectDocuments,
  uploadFileToPresignedUrl,
} from '../services/api-client'
import type { ProjectDocument, ProjectRecord } from '../types/project'

const COMPANY_PLACEHOLDER = 'Projeto atual'
const MAX_DOCUMENT_SIZE_BYTES = 50 * 1024 * 1024
const ALLOWED_EXTENSIONS = new Set(['pdf', 'xlsx', 'csv', 'docx'])

function getFileExtension(filename: string) {
  const extension = filename.split('.').pop()
  return extension?.toLowerCase() ?? ''
}

function getUploadId(file: File) {
  return `${file.name}-${file.size}-${file.lastModified}`
}

export function ProjectDocumentsPage() {
  const { projectId } = useParams()
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [project, setProject] = useState<ProjectRecord | null>(null)
  const [documents, setDocuments] = useState<ProjectDocument[]>([])
  const [uploads, setUploads] = useState<PendingUpload[]>([])
  const [validationMessage, setValidationMessage] = useState<string | null>(
    null
  )
  const [pageError, setPageError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [deletingDocumentId, setDeletingDocumentId] = useState<string | null>(
    null
  )

  useEffect(() => {
    if (!projectId) {
      setPageError('Projeto inválido.')
      setIsLoading(false)
      return
    }

    let active = true
    const currentProjectId = projectId

    async function loadProjectContext() {
      setIsLoading(true)

      try {
        const [projectResponse, documentsResponse] = await Promise.all([
          fetchProject(currentProjectId),
          fetchProjectDocuments(currentProjectId),
        ])

        if (!active) {
          return
        }

        setProject(projectResponse)
        setDocuments(documentsResponse)
        setPageError(null)
      } catch (error) {
        if (!active) {
          return
        }

        setPageError(
          error instanceof Error
            ? error.message
            : 'Não foi possível carregar os documentos do projeto.'
        )
      } finally {
        if (active) {
          setIsLoading(false)
        }
      }
    }

    void loadProjectContext()

    return () => {
      active = false
    }
  }, [projectId])

  async function refreshDocuments(currentProjectId: string) {
    const nextDocuments = await fetchProjectDocuments(currentProjectId)
    setDocuments(nextDocuments)
  }

  async function handleFilesSelected(files: File[]) {
    if (!projectId || files.length === 0) {
      return
    }

    const validFiles: File[] = []
    const validationErrors: string[] = []

    for (const file of files) {
      const extension = getFileExtension(file.name)

      if (!ALLOWED_EXTENSIONS.has(extension)) {
        validationErrors.push(
          `${file.name}: formato inválido. Use PDF, XLSX, CSV ou DOCX.`
        )
        continue
      }

      if (file.size > MAX_DOCUMENT_SIZE_BYTES) {
        validationErrors.push(`${file.name}: excede o limite de 50MB.`)
        continue
      }

      validFiles.push(file)
    }

    setValidationMessage(
      validationErrors.length > 0 ? validationErrors.join(' ') : null
    )

    if (validFiles.length === 0) {
      return
    }

    setIsUploading(true)
    setPageError(null)

    const initialUploads = validFiles.map((file) => ({
      fileName: file.name,
      id: getUploadId(file),
      progress: 0,
      status: 'uploading' as const,
    }))

    setUploads((current) => [...initialUploads, ...current])

    try {
      await Promise.all(
        validFiles.map(async (file) => {
          const uploadId = getUploadId(file)

          try {
            const uploadSession = await createProjectDocumentUpload(projectId, {
              filename: file.name,
              file_size_bytes: file.size,
            })

            await uploadFileToPresignedUrl(
              file,
              uploadSession.upload_url,
              uploadSession.content_type,
              (progress) => {
                setUploads((current) =>
                  current.map((upload) =>
                    upload.id === uploadId ? { ...upload, progress } : upload
                  )
                )
              }
            )

            await confirmProjectDocumentUpload(
              projectId,
              uploadSession.document_id
            )

            setUploads((current) =>
              current.filter((upload) => upload.id !== uploadId)
            )
          } catch (error) {
            const message =
              error instanceof Error
                ? error.message
                : 'Não foi possível concluir o upload.'

            setUploads((current) =>
              current.map((upload) =>
                upload.id === uploadId
                  ? {
                      ...upload,
                      error: message,
                      progress: 100,
                      status: 'error',
                    }
                  : upload
              )
            )
          }
        })
      )

      await refreshDocuments(projectId)
    } catch (error) {
      setPageError(
        error instanceof Error
          ? error.message
          : 'Não foi possível concluir o fluxo de upload.'
      )
    } finally {
      setIsUploading(false)
    }
  }

  async function handleDelete(documentId: string) {
    if (!projectId) {
      return
    }

    setDeletingDocumentId(documentId)
    setPageError(null)

    try {
      await deleteProjectDocument(projectId, documentId)
      setDocuments((current) =>
        current.filter((document) => document.id !== documentId)
      )
    } catch (error) {
      setPageError(
        error instanceof Error
          ? error.message
          : 'Não foi possível remover o documento.'
      )
    } finally {
      setDeletingDocumentId(null)
    }
  }

  return (
    <ProjectShell
      activeSidebarKey="documents"
      companyName={project?.org_name ?? COMPANY_PLACEHOLDER}
      documentsHref={projectId ? `/projects/${projectId}` : undefined}
      pageAction={{
        label: 'Selecionar arquivos',
        icon: 'upload_file',
        onClick: () => {
          fileInputRef.current?.click()
        },
      }}
      pageTitle="Documentos"
    >
      <div className="space-y-6 px-6 pt-4 pb-6 sm:px-10">
        <FileUploader
          disabled={isLoading || isUploading || !projectId}
          inputRef={fileInputRef}
          onFilesSelected={(files) => {
            void handleFilesSelected(files)
          }}
          uploads={uploads}
          validationMessage={validationMessage}
        />

        {pageError ? (
          <div className="rounded-lg border border-[#ffd0d0] bg-[#fff6f6] px-4 py-3 text-[12px] font-medium tracking-[-0.01em] text-[#d01f1f]">
            {pageError}
          </div>
        ) : null}

        {isLoading ? (
          <div className="rounded-lg border border-black/6 bg-white px-5 py-6">
            <p className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
              Carregando documentos do projeto...
            </p>
          </div>
        ) : (
          <DocumentList
            deletingDocumentId={deletingDocumentId}
            documents={documents}
            onDelete={(documentId) => {
              void handleDelete(documentId)
            }}
          />
        )}
      </div>
    </ProjectShell>
  )
}
