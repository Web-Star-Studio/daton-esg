import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { DocumentList } from '../components/document-list'
import { FileUploader, type PendingUpload } from '../components/file-uploader'
import {
  getDocumentDirectory,
  getVisibleDocumentDirectories,
  LEGACY_UNCATEGORIZED_DIRECTORY_KEY,
} from '../constants/document-directories'
import {
  confirmProjectDocumentUpload,
  createProjectDocumentUpload,
  deleteProjectDocument,
  fetchProjectDocuments,
  moveProjectDocument,
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

function FolderCard({
  count,
  href,
  label,
}: {
  count: number
  href: string
  label: string
}) {
  return (
    <Link
      to={href}
      className="apple-focus-ring rounded-[1rem] border border-black/6 bg-white p-5 transition-colors hover:border-primary/20 hover:bg-primary/[0.03]"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <p className="text-[14px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
            {label}
          </p>
          <p className="text-[12px] tracking-[-0.01em] text-[#86868b]">
            {count === 1 ? '1 documento' : `${count} documentos`}
          </p>
        </div>
        <span className="material-symbols-outlined text-[18px] text-[#86868b]">
          chevron_right
        </span>
      </div>
    </Link>
  )
}

export function ProjectDocumentsPage() {
  const { currentProjectId, isLoadingWorkspace, workspaceError } =
    useProjectWorkspace()
  const { directoryKey } = useParams()
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
  const [movingDocumentId, setMovingDocumentId] = useState<string | null>(null)

  const selectedDirectory = directoryKey
    ? getDocumentDirectory(directoryKey)
    : null
  const isInvalidDirectory = Boolean(directoryKey && !selectedDirectory)
  const isLegacyDirectory = selectedDirectory?.isLegacyOnly === true
  const canUploadToSelectedDirectory = Boolean(
    selectedDirectory && !selectedDirectory.isLegacyOnly
  )
  const hasLegacyUncategorizedDocuments = documents.some(
    (document) => document.directory_key === LEGACY_UNCATEGORIZED_DIRECTORY_KEY
  )
  const visibleDirectories = useMemo(
    () => getVisibleDocumentDirectories(hasLegacyUncategorizedDocuments),
    [hasLegacyUncategorizedDocuments]
  )
  const selectedFolderDocuments = useMemo(() => {
    if (!selectedDirectory) {
      return []
    }

    return documents.filter(
      (document) => document.directory_key === selectedDirectory.key
    )
  }, [documents, selectedDirectory])
  const isUploaderDisabled =
    isLoading || isLoadingWorkspace || isUploading || !currentProjectId
  const pageActions = useMemo(() => {
    if (!canUploadToSelectedDirectory) {
      return []
    }

    return [
      {
        disabled: isUploaderDisabled,
        icon: 'upload_file',
        label: 'Selecionar arquivos',
        onClick: () => {
          fileInputRef.current?.click()
        },
      },
    ]
  }, [canUploadToSelectedDirectory, isUploaderDisabled])
  const pageTitle = selectedDirectory?.label ?? 'Documentos'

  useProjectShellRegistration({
    activeSidebarKey: 'documents',
    pageActions,
    pageTitle,
  })

  useEffect(() => {
    if (!currentProjectId) {
      setDocuments([])
      setUploads([])
      uploadFilesRef.current = new Map()
      setValidationMessage(null)
      setPageError('Projeto inválido.')
      setIsLoading(false)
      return
    }

    if (isInvalidDirectory) {
      setDocuments([])
      setUploads([])
      uploadFilesRef.current = new Map()
      setValidationMessage(null)
      setPageError('Pasta inválida.')
      setIsLoading(false)
      return
    }

    let active = true

    async function loadDocuments() {
      setPageError(null)
      setValidationMessage(null)
      setUploads([])
      uploadFilesRef.current = new Map()
      setIsLoading(true)

      try {
        const documentsResponse = await fetchProjectDocuments(
          currentProjectId,
          {
            directory_key: selectedDirectory?.key,
          }
        )

        if (!active) {
          return
        }

        setDocuments(documentsResponse)
      } catch (error) {
        if (!active) {
          return
        }

        setDocuments([])
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

    void loadDocuments()

    return () => {
      active = false
    }
  }, [currentProjectId, isInvalidDirectory, selectedDirectory?.key])

  async function refreshDocuments() {
    if (!currentProjectId || isInvalidDirectory) {
      return
    }

    const nextDocuments = await fetchProjectDocuments(currentProjectId, {
      directory_key: selectedDirectory?.key,
    })
    setDocuments(nextDocuments)
  }

  async function uploadSingleFile(currentProjectIdValue: string, file: File) {
    if (!selectedDirectory) {
      return
    }

    const uploadId = getUploadId(file)

    try {
      const uploadSession = await createProjectDocumentUpload(
        currentProjectIdValue,
        {
          directory_key: selectedDirectory.key,
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
        currentProjectIdValue,
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
    if (
      !currentProjectId ||
      files.length === 0 ||
      !canUploadToSelectedDirectory
    ) {
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

      await refreshDocuments()
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
      await refreshDocuments()
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

  async function handleDeleteDocument(documentId: string) {
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

  async function handleMoveDocument(
    documentId: string,
    nextDirectoryKey: string
  ) {
    if (!currentProjectId) {
      return
    }

    const previousDocuments = documents
    setMovingDocumentId(documentId)
    setPageError(null)

    setDocuments((current) => {
      const updated = current.map((document) =>
        document.id === documentId
          ? { ...document, directory_key: nextDirectoryKey }
          : document
      )

      return selectedDirectory
        ? updated.filter(
            (document) => document.directory_key === selectedDirectory.key
          )
        : updated
    })

    try {
      await moveProjectDocument(currentProjectId, documentId, {
        directory_key: nextDirectoryKey,
      })
    } catch (error) {
      setDocuments(previousDocuments)
      setPageError(
        error instanceof Error
          ? error.message
          : 'Não foi possível mover o documento.'
      )
    } finally {
      setMovingDocumentId(null)
    }
  }

  const folderCounts = useMemo(
    () =>
      visibleDirectories.map((directory) => ({
        count: documents.filter(
          (document) => document.directory_key === directory.key
        ).length,
        directory,
      })),
    [documents, visibleDirectories]
  )

  return (
    <section className="flex h-full flex-col px-6 pb-6 pt-6">
      <div className="min-h-0 flex-1 space-y-5">
        {workspaceError ? (
          <div className="rounded-[0.95rem] border border-[#ffd8d8] bg-[#fff7f7] px-4 py-3 text-[13px] text-[#d01f1f]">
            {workspaceError}
          </div>
        ) : null}

        {pageError ? (
          <div className="rounded-[0.95rem] border border-[#ffd8d8] bg-[#fff7f7] px-4 py-3 text-[13px] text-[#d01f1f]">
            {pageError}
          </div>
        ) : null}

        {selectedDirectory ? (
          <div className="space-y-5">
            <div className="flex items-center gap-2 text-[13px] tracking-[-0.01em] text-[#86868b]">
              <Link
                to={`/projects/${currentProjectId}/documents`}
                className="apple-focus-ring rounded-[0.6rem] px-2 py-1 transition-colors hover:bg-black/[0.04] hover:text-[#1d1d1f]"
              >
                Todas as pastas
              </Link>
              <span>/</span>
              <span className="text-[#1d1d1f]">{selectedDirectory.label}</span>
            </div>

            {isLegacyDirectory ? (
              <div className="rounded-[1rem] border border-black/6 bg-[#f5f7f8] px-5 py-4">
                <p className="text-[14px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                  Pasta legada
                </p>
                <p className="mt-1 text-[13px] tracking-[-0.01em] text-[#86868b]">
                  Esta pasta existe apenas para documentos antigos que ainda não
                  foram realocados para uma das categorias oficiais.
                </p>
              </div>
            ) : (
              <FileUploader
                disabled={isUploaderDisabled}
                inputRef={fileInputRef}
                onFilesSelected={handleFilesSelected}
                onRemoveUpload={removeUpload}
                onRetryUpload={retryUpload}
                uploads={uploads}
                validationMessage={validationMessage}
              />
            )}

            {isLoading ? (
              <div className="rounded-[1rem] border border-black/6 bg-[#f5f7f8] px-5 py-8 text-[13px] text-[#86868b]">
                Carregando documentos...
              </div>
            ) : selectedFolderDocuments.length === 0 ? (
              <div className="rounded-[1rem] border border-black/6 bg-[#f5f7f8] px-5 py-8">
                <p className="text-[14px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                  Nenhum documento nesta pasta.
                </p>
                <p className="mt-1 text-[13px] tracking-[-0.01em] text-[#86868b]">
                  {isLegacyDirectory
                    ? 'Os documentos legados sem mapeamento aparecem aqui até serem movidos para uma categoria oficial.'
                    : 'Envie arquivos desta categoria ou mova documentos de outra pasta para organizar o projeto.'}
                </p>
              </div>
            ) : (
              <DocumentList
                availableDirectories={visibleDirectories}
                deletingDocumentId={deletingDocumentId}
                documents={selectedFolderDocuments}
                movingDocumentId={movingDocumentId}
                onDelete={handleDeleteDocument}
                onMove={handleMoveDocument}
              />
            )}
          </div>
        ) : (
          <div className="space-y-5">
            {isLoading ? (
              <div className="rounded-[1rem] border border-black/6 bg-[#f5f7f8] px-5 py-8 text-[13px] text-[#86868b]">
                Carregando pastas...
              </div>
            ) : (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {folderCounts.map(({ count, directory }) => (
                  <FolderCard
                    key={directory.key}
                    count={count}
                    href={`/projects/${currentProjectId}/documents/${directory.key}`}
                    label={directory.label}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
