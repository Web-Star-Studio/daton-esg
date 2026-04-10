import type { ProjectDocument } from '../types/project'

type DocumentListProps = {
  deletingDocumentId: string | null
  documents: ProjectDocument[]
  onDelete?: (documentId: string) => void
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

function getParsingStatusColor(status: ProjectDocument['parsing_status']) {
  switch (status) {
    case 'completed':
      return 'bg-[#e8f5e8] text-[#1a7a1a]'
    case 'failed':
      return 'bg-[#fff0f0] text-[#d01f1f]'
    case 'processing':
      return 'bg-[#fff8e8] text-[#9a6700]'
    case 'pending':
    default:
      return 'bg-[#f0f0f5] text-[#86868b]'
  }
}

export function DocumentList({
  deletingDocumentId,
  documents,
  onDelete,
}: DocumentListProps) {
  if (documents.length === 0) {
    return null
  }

  return (
    <div className="overflow-hidden rounded-lg border border-black/6 bg-white">
      <table className="w-full border-collapse text-left">
        <thead className="sticky top-0 z-10 bg-white">
          <tr>
            <th className="h-10 w-[40%] border-b border-[#e5e5ea] px-6 align-middle text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
              Nome
            </th>
            <th className="h-10 w-[12%] border-b border-[#e5e5ea] px-6 align-middle text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
              Tipo
            </th>
            <th className="h-10 w-[15%] border-b border-[#e5e5ea] px-6 align-middle text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
              Tamanho
            </th>
            <th className="h-10 w-[18%] border-b border-[#e5e5ea] px-6 align-middle text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
              Status
            </th>
            {onDelete ? (
              <th className="h-10 w-[15%] border-b border-[#e5e5ea] px-6 align-middle text-right text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
                Ações
              </th>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {documents.map((document) => (
            <tr
              key={document.id}
              className="border-b border-[#f5f5f7] transition-colors last:border-none hover:bg-[#f5f5f7]"
            >
              <td className="h-12 px-6 align-middle">
                <p className="truncate text-sm font-medium text-[#1d1d1f]">
                  {document.filename}
                </p>
                {document.parsing_status === 'failed' &&
                document.parsing_error ? (
                  <p className="mt-0.5 truncate text-[11px] text-[#d01f1f]">
                    Erro no processamento
                  </p>
                ) : null}
              </td>
              <td className="h-12 px-6 align-middle text-sm text-[#1d1d1f]">
                {document.file_type.toUpperCase()}
              </td>
              <td className="h-12 px-6 align-middle text-sm text-[#86868b]">
                {formatFileSize(document.file_size_bytes)}
              </td>
              <td className="h-12 px-6 align-middle">
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium tracking-[-0.01em] ${getParsingStatusColor(document.parsing_status)}`}
                >
                  {getParsingStatusLabel(document.parsing_status)}
                </span>
              </td>
              {onDelete ? (
                <td className="h-12 px-6 align-middle text-right">
                  <button
                    type="button"
                    onClick={() => {
                      onDelete(document.id)
                    }}
                    disabled={deletingDocumentId === document.id}
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
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
