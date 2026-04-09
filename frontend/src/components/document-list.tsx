import type { ProjectDocument } from '../types/project'

type DocumentListProps = {
  deletingDocumentId: string | null
  documents: ProjectDocument[]
  onDelete: (documentId: string) => void
}

function formatFileSize(fileSizeBytes: number | null) {
  if (!fileSizeBytes) {
    return 'Tamanho pendente'
  }

  if (fileSizeBytes < 1024 * 1024) {
    return `${Math.round(fileSizeBytes / 1024)} KB`
  }

  return `${(fileSizeBytes / (1024 * 1024)).toFixed(1)} MB`
}

function getParsingStatusLabel(status: ProjectDocument['parsing_status']) {
  switch (status) {
    case 'completed':
      return 'Processado'
    case 'failed':
      return 'Falhou'
    case 'processing':
      return 'Processando'
    case 'pending':
    default:
      return 'Pendente'
  }
}

export function DocumentList({
  deletingDocumentId,
  documents,
  onDelete,
}: DocumentListProps) {
  if (documents.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-[#d2d2d7] bg-[#f5f7f8] px-5 py-6">
        <p className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
          Nenhum documento enviado ainda.
        </p>
        <p className="mt-1 text-[12px] tracking-[-0.01em] text-[#86868b]">
          Use a área acima para subir evidências e planilhas do projeto.
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-lg border border-black/6 bg-white">
      <ul className="divide-y divide-black/6">
        {documents.map((document) => (
          <li
            key={document.id}
            className="flex items-center justify-between gap-4 px-5 py-4"
          >
            <div className="min-w-0 space-y-1">
              <p className="truncate text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                {document.filename}
              </p>
              <div className="flex flex-wrap items-center gap-2 text-[12px] tracking-[-0.01em] text-[#86868b]">
                <span>{document.file_type.toUpperCase()}</span>
                <span aria-hidden="true">•</span>
                <span>{formatFileSize(document.file_size_bytes)}</span>
                <span aria-hidden="true">•</span>
                <span>{getParsingStatusLabel(document.parsing_status)}</span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => {
                onDelete(document.id)
              }}
              disabled={deletingDocumentId === document.id}
              className="apple-focus-ring inline-flex items-center gap-2 rounded-[0.7rem] px-3 py-2 text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f] transition-colors hover:bg-black/[0.04] disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span
                aria-hidden="true"
                className="material-symbols-outlined text-[16px] text-[#86868b]"
              >
                delete
              </span>
              Remover
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
