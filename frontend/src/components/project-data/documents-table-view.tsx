import { useMemo } from 'react'
import type { DocumentExtraction, ProjectDocument } from '../../types/project'
import { formatFileSize, getDocumentConfidenceLabel } from './data-view-utils'

type DocumentsTableViewProps = {
  category: string
  documents: ProjectDocument[]
  extractions: DocumentExtraction[]
  onSelectDocument: (documentId: string, documentName: string) => void
}

function getConfidenceBadgeClasses(
  confidence: ProjectDocument['classification_confidence']
) {
  switch (confidence) {
    case 'high':
      return 'bg-[#e8f5e8] text-[#1a7a1a]'
    case 'low':
      return 'bg-[#fff8e8] text-[#9a6700]'
    case 'medium':
      return 'bg-[#f0f0f5] text-[#5c5c61]'
    default:
      return 'bg-[#f0f0f5] text-[#86868b]'
  }
}

export function DocumentsTableView({
  category,
  documents,
  extractions,
  onSelectDocument,
}: DocumentsTableViewProps) {
  const filteredDocuments = useMemo(
    () =>
      documents.filter(
        (doc) => (doc.esg_category ?? 'Sem categoria') === category
      ),
    [documents, category]
  )

  const extractionCounts = useMemo(() => {
    const counts = new Map<string, number>()
    for (const ext of extractions) {
      counts.set(ext.document_id, (counts.get(ext.document_id) ?? 0) + 1)
    }
    return counts
  }, [extractions])

  if (filteredDocuments.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-[#d2d2d7] bg-[#f5f7f8] px-5 py-6">
        <p className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
          Nenhum documento nesta categoria.
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-lg border border-black/6 bg-white">
      <table className="w-full border-collapse text-left">
        <thead className="sticky top-0 z-10 bg-white">
          <tr>
            <th className="h-10 w-[35%] border-b border-[#e5e5ea] px-6 align-middle text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
              Nome
            </th>
            <th className="h-10 w-[10%] border-b border-[#e5e5ea] px-6 align-middle text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
              Tipo
            </th>
            <th className="h-10 w-[15%] border-b border-[#e5e5ea] px-6 align-middle text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
              Tamanho
            </th>
            <th className="h-10 w-[15%] border-b border-[#e5e5ea] px-6 align-middle text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
              Confiança
            </th>
            <th className="h-10 w-[10%] border-b border-[#e5e5ea] px-6 align-middle text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
              Extrações
            </th>
            <th className="h-10 w-[15%] border-b border-[#e5e5ea] px-6 align-middle text-right text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          {filteredDocuments.map((doc) => (
            <tr
              key={doc.id}
              onClick={() => onSelectDocument(doc.id, doc.filename)}
              className="cursor-pointer border-b border-[#f5f5f7] transition-colors last:border-none hover:bg-[#f5f5f7]"
            >
              <td className="h-12 px-6 align-middle text-sm font-medium text-[#1d1d1f]">
                {doc.filename}
              </td>
              <td className="h-12 px-6 align-middle text-sm text-[#1d1d1f]">
                {doc.file_type.toUpperCase()}
              </td>
              <td className="h-12 px-6 align-middle text-sm text-[#86868b]">
                {formatFileSize(doc.file_size_bytes)}
              </td>
              <td className="h-12 px-6 align-middle">
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${getConfidenceBadgeClasses(doc.classification_confidence)}`}
                >
                  {getDocumentConfidenceLabel(doc.classification_confidence)}
                </span>
              </td>
              <td className="h-12 px-6 align-middle text-sm text-[#86868b]">
                {extractionCounts.get(doc.id) ?? 0}
              </td>
              <td className="h-12 px-6 align-middle text-right text-sm text-[#86868b]">
                {doc.parsing_status === 'completed'
                  ? 'Processado'
                  : doc.parsing_status === 'processing'
                    ? 'Processando'
                    : doc.parsing_status === 'failed'
                      ? 'Falhou'
                      : 'Pendente'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
