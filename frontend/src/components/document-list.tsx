import type { DocumentDirectory } from '../constants/document-directories'
import { LEGACY_UNCATEGORIZED_DIRECTORY_KEY } from '../constants/document-directories'
import type { ProjectDocument } from '../types/project'

type DocumentListProps = {
  availableDirectories: DocumentDirectory[]
  deletingDocumentId: string | null
  documents: ProjectDocument[]
  movingDocumentId: string | null
  onDelete?: (documentId: string) => void
  onMove?: (documentId: string, directoryKey: string) => void
}

function formatFileSize(fileSizeBytes: number | null) {
  if (!fileSizeBytes) {
    return 'Tamanho pendente'
  }

  if (fileSizeBytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(fileSizeBytes / 1024))} KB`
  }

  return `${(fileSizeBytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatCreatedAt(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Data indisponível'
  }

  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(date)
}

export function DocumentList({
  availableDirectories,
  deletingDocumentId,
  documents,
  movingDocumentId,
  onDelete,
  onMove,
}: DocumentListProps) {
  if (documents.length === 0) {
    return null
  }

  return (
    <div className="overflow-hidden rounded-lg border border-black/6 bg-white">
      <table className="w-full border-collapse text-left">
        <thead className="sticky top-0 z-10 bg-white">
          <tr>
            <th className="h-10 w-[34%] border-b border-[#e5e5ea] px-6 align-middle text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
              Nome
            </th>
            <th className="h-10 w-[10%] border-b border-[#e5e5ea] px-6 align-middle text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
              Tipo
            </th>
            <th className="h-10 w-[13%] border-b border-[#e5e5ea] px-6 align-middle text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
              Tamanho
            </th>
            <th className="h-10 w-[13%] border-b border-[#e5e5ea] px-6 align-middle text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
              Adicionado em
            </th>
            <th className="h-10 w-[30%] border-b border-[#e5e5ea] px-6 align-middle text-right text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
              Ações
            </th>
          </tr>
        </thead>
        <tbody>
          {documents.map((document) => {
            const isDeleting = deletingDocumentId === document.id
            const isMoving = movingDocumentId === document.id
            const moveOptions =
              document.directory_key === LEGACY_UNCATEGORIZED_DIRECTORY_KEY
                ? availableDirectories
                : availableDirectories.filter(
                    (directory) => !directory.isLegacyOnly
                  )

            return (
              <tr
                key={document.id}
                className="border-b border-[#f5f5f7] transition-colors last:border-none hover:bg-[#f5f5f7]"
              >
                <td className="h-12 px-6 align-middle">
                  <p className="truncate text-sm font-medium text-[#1d1d1f]">
                    {document.filename}
                  </p>
                </td>
                <td className="h-12 px-6 align-middle text-sm text-[#1d1d1f]">
                  {document.file_type.toUpperCase()}
                </td>
                <td className="h-12 px-6 align-middle text-sm text-[#86868b]">
                  {formatFileSize(document.file_size_bytes)}
                </td>
                <td className="h-12 px-6 align-middle text-sm text-[#86868b]">
                  {formatCreatedAt(document.created_at)}
                </td>
                <td className="h-12 px-6 align-middle">
                  <div className="flex items-center justify-end gap-3">
                    {onMove ? (
                      <label
                        className="sr-only"
                        htmlFor={`directory-${document.id}`}
                      >
                        Mover documento
                      </label>
                    ) : null}
                    {onMove ? (
                      <select
                        id={`directory-${document.id}`}
                        value={document.directory_key}
                        onChange={(event) => {
                          const nextDirectoryKey = event.target.value
                          if (nextDirectoryKey === document.directory_key) {
                            return
                          }
                          onMove(document.id, nextDirectoryKey)
                        }}
                        disabled={isDeleting || isMoving}
                        className="apple-focus-ring min-w-[220px] rounded-[0.7rem] border border-black/8 bg-white px-3 py-2 text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f] disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {moveOptions.map((directory) => (
                          <option key={directory.key} value={directory.key}>
                            {directory.label}
                          </option>
                        ))}
                      </select>
                    ) : null}
                    {onDelete ? (
                      <button
                        type="button"
                        onClick={() => {
                          onDelete(document.id)
                        }}
                        disabled={isDeleting || isMoving}
                        className="apple-focus-ring inline-flex items-center gap-1.5 rounded-[0.7rem] px-2.5 py-1.5 text-[12px] font-medium tracking-[-0.01em] text-[#86868b] transition-colors hover:bg-black/[0.04] hover:text-[#1d1d1f] disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <span
                          aria-hidden="true"
                          className="material-symbols-outlined text-[15px]"
                        >
                          delete
                        </span>
                        Remover
                      </button>
                    ) : null}
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
