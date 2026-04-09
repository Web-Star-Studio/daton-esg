import { useEffect, useMemo, useRef, useState } from 'react'
import { DocumentList } from '../components/document-list'
import { FileUploader, type PendingUpload } from '../components/file-uploader'
import {
  confirmProjectDocumentUpload,
  createProjectDocumentUpload,
  deleteProjectDocument,
  fetchProjectDocuments,
  uploadFileToPresignedUrl,
} from '../services/api-client'
import {
  useProjectShellRegistration,
  useProjectWorkspace,
} from '../hooks/use-project-workspace'
import type { ProjectDocument } from '../types/project'

const MAX_DOCUMENT_SIZE_BYTES = 50 * 1024 * 1024
const ALLOWED_EXTENSIONS = new Set(['pdf', 'xlsx', 'csv', 'docx'])

function getFileExtension(filename: string) {
  const lastDotIndex = filename.lastIndexOf('.')

  if (lastDotIndex <= 0 || lastDotIndex === filename.length - 1) {
    return ''
  }

  return filename.slice(lastDotIndex + 1).toLowerCase()
}

function getUploadId(file: File) {
  return `${file.name}-${file.size}-${file.lastModified}`
}

export function ProjectDocumentsPage() {
  const { currentProjectId, isLoadingWorkspace, workspaceError } =
    useProjectWorkspace()
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const uploadFilesRef = useRef<Map<string, File>>(new Map())
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
  const isUploaderDisabled =
    isLoading || isLoadingWorkspace || isUploading || !currentProjectId
  const pageAction = useMemo(
    () => ({
      disabled: isUploaderDisabled,
      icon: 'upload_file',
      label: 'Selecionar arquivos',
      onClick: () => {
        fileInputRef.current?.click()
      },
    }),
    [isUploaderDisabled]
  )
  const pageActions = useMemo(() => [pageAction], [pageAction])

  useProjectShellRegistration({
    activeSidebarKey: 'documents',
    pageActions,
    pageTitle: 'Documentos',
  })

  useEffect(() => {
    if (!currentProjectId) {
      setDocuments([])
      setPageError('Projeto inválido.')
      setIsLoading(false)
      return
    }

    let active = true

    async function loadDocuments() {
      setDocuments([])
      setIsLoading(true)

      try {
        const documentsResponse = await fetchProjectDocuments(currentProjectId)

        if (!active) {
          return
        }

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
        setDocuments([])
      } finally {
        if (active) {
          setIsLoading(false)
        }
      }
    }

    void loadDocuments()

    return () => {
      active = false
    }
  }, [currentProjectId])

  async function refreshDocuments(currentProjectId: string) {
    try {
      const nextDocuments = await fetchProjectDocuments(currentProjectId)
      setDocuments(nextDocuments)
    } catch (error) {
      console.error('Failed to refresh project documents', error)
      throw new Error('Falha ao atualizar a lista de documentos do projeto.')
    }
  }

  async function uploadSingleFile(currentProjectId: string, file: File) {
    const uploadId = getUploadId(file)

    try {
      const uploadSession = await createProjectDocumentUpload(
        currentProjectId,
        {
          filename: file.name,
          file_size_bytes: file.size,
        }
      )

      setUploads((current) =>
        current.map((upload) =>
          upload.id === uploadId
            ? { ...upload, progress: 0, status: 'uploading', error: undefined }
            : upload
        )
      )

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
        currentProjectId,
        uploadSession.document_id
      )

      uploadFilesRef.current.delete(uploadId)
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
      throw error
    }
  }

  async function handleFilesSelected(files: File[]) {
    if (!currentProjectId || files.length === 0) {
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

    validFiles.forEach((file) => {
      uploadFilesRef.current.set(getUploadId(file), file)
    })

    setUploads((current) => [...initialUploads, ...current])

    try {
      await Promise.all(
        validFiles.map(async (file) => {
          try {
            await uploadSingleFile(currentProjectId, file)
          } catch {
            return
          }
        })
      )

      await refreshDocuments(currentProjectId)
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

  function removeUpload(uploadId: string) {
    uploadFilesRef.current.delete(uploadId)
    setUploads((current) => current.filter((upload) => upload.id !== uploadId))
  }

  async function retryUpload(uploadId: string) {
    if (!currentProjectId) {
      return
    }

    const file = uploadFilesRef.current.get(uploadId)
    if (!file) {
      setPageError('Não foi possível reenviar o arquivo selecionado.')
      return
    }

    setPageError(null)
    setIsUploading(true)
    setUploads((current) =>
      current.map((upload) =>
        upload.id === uploadId
          ? { ...upload, progress: 0, status: 'uploading', error: undefined }
          : upload
      )
    )

    try {
      await uploadSingleFile(currentProjectId, file)
      await refreshDocuments(currentProjectId)
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
    if (!currentProjectId) {
      return
    }

    setDeletingDocumentId(documentId)
    setPageError(null)

    try {
      await deleteProjectDocument(currentProjectId, documentId)
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
    <div className="space-y-6 px-6 pt-4 pb-6 sm:px-10">
      <FileUploader
        disabled={isUploaderDisabled}
        inputRef={fileInputRef}
        onFilesSelected={(files) => {
          void handleFilesSelected(files)
        }}
        onRemoveUpload={removeUpload}
        onRetryUpload={(uploadId) => {
          void retryUpload(uploadId)
        }}
        uploads={uploads}
        validationMessage={validationMessage}
      />

      {pageError || workspaceError ? (
        <div className="rounded-lg border border-[#ffd0d0] bg-[#fff6f6] px-4 py-3 text-[12px] font-medium tracking-[-0.01em] text-[#d01f1f]">
          {pageError ?? workspaceError}
        </div>
      ) : null}

      {isLoadingWorkspace || isLoading ? (
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
  )
}
