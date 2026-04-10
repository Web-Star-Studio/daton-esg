import { useMemo } from 'react'
import type { DocumentExtraction, ProjectDocument } from '../../types/project'
import { CATEGORY_ICONS, getConfidenceLabel } from './data-view-utils'

type CategoryCardsViewProps = {
  documents: ProjectDocument[]
  extractions: DocumentExtraction[]
  onSelectCategory: (category: string) => void
}

type CategoryStats = {
  category: string
  documentCount: number
  extractionCount: number
  pendingCount: number
  dominantConfidence: 'high' | 'medium' | 'low' | null
}

export function CategoryCardsView({
  documents,
  extractions,
  onSelectCategory,
}: CategoryCardsViewProps) {
  const categories = useMemo<CategoryStats[]>(() => {
    const docsByCategory = new Map<string, ProjectDocument[]>()
    for (const doc of documents) {
      const cat = doc.esg_category ?? 'Sem categoria'
      const group = docsByCategory.get(cat) ?? []
      group.push(doc)
      docsByCategory.set(cat, group)
    }

    const extractionsByDoc = new Map<string, DocumentExtraction[]>()
    for (const ext of extractions) {
      const group = extractionsByDoc.get(ext.document_id) ?? []
      group.push(ext)
      extractionsByDoc.set(ext.document_id, group)
    }

    const stats: CategoryStats[] = []
    for (const [category, docs] of docsByCategory) {
      let extractionCount = 0
      let pendingCount = 0
      const confidenceCounts = { high: 0, medium: 0, low: 0 }

      for (const doc of docs) {
        const docExtractions = extractionsByDoc.get(doc.id) ?? []
        extractionCount += docExtractions.length
        for (const ext of docExtractions) {
          if (ext.review_status === 'pending') pendingCount++
          if (ext.confidence) confidenceCounts[ext.confidence]++
        }
      }

      let dominantConfidence: 'high' | 'medium' | 'low' | null = null
      if (
        confidenceCounts.high >= confidenceCounts.medium &&
        confidenceCounts.high >= confidenceCounts.low &&
        confidenceCounts.high > 0
      ) {
        dominantConfidence = 'high'
      } else if (
        confidenceCounts.medium >= confidenceCounts.low &&
        confidenceCounts.medium > 0
      ) {
        dominantConfidence = 'medium'
      } else if (confidenceCounts.low > 0) {
        dominantConfidence = 'low'
      }

      stats.push({
        category,
        documentCount: docs.length,
        extractionCount,
        pendingCount,
        dominantConfidence,
      })
    }

    return stats.sort((a, b) => a.category.localeCompare(b.category, 'pt-BR'))
  }, [documents, extractions])

  if (categories.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-[#d2d2d7] bg-[#f5f7f8] px-5 py-6">
        <p className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
          Nenhum dado classificado disponível.
        </p>
        <p className="mt-1 text-[12px] tracking-[-0.01em] text-[#86868b]">
          Envie documentos, aguarde o parsing e execute a classificação para
          começar a revisão manual.
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {categories.map((stat) => {
        const icon = CATEGORY_ICONS[stat.category] ?? 'category'

        return (
          <button
            key={stat.category}
            type="button"
            onClick={() => onSelectCategory(stat.category)}
            className="apple-focus-ring flex flex-col gap-4 rounded-lg border border-black/6 bg-white p-5 text-left shadow-sm transition-all hover:border-[#d2d2d7] hover:shadow-md"
          >
            <div className="flex items-center gap-3">
              <span className="inline-flex size-9 items-center justify-center rounded-[0.7rem] bg-[#f5f7f8] text-[#86868b]">
                <span className="material-symbols-outlined text-[18px]">
                  {icon}
                </span>
              </span>
              <h3 className="text-[14px] font-semibold tracking-[-0.01em] text-[#1d1d1f]">
                {stat.category}
              </h3>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-[#f5f7f8] px-2.5 py-0.5 text-[11px] font-medium text-[#1d1d1f]">
                {stat.documentCount} doc(s)
              </span>
              <span className="rounded-full bg-[#f5f7f8] px-2.5 py-0.5 text-[11px] font-medium text-[#1d1d1f]">
                {stat.extractionCount} extração(ões)
              </span>
              {stat.dominantConfidence ? (
                <span className="rounded-full bg-[#f0f0f5] px-2.5 py-0.5 text-[11px] font-medium text-[#5c5c61]">
                  {getConfidenceLabel(stat.dominantConfidence)}
                </span>
              ) : null}
            </div>

            <div className="flex items-center justify-between">
              {stat.pendingCount > 0 ? (
                <span className="text-[11px] font-medium tracking-[-0.01em] text-[#9a6700]">
                  {stat.pendingCount} pendente(s)
                </span>
              ) : (
                <span className="text-[11px] font-medium tracking-[-0.01em] text-[#1a7a1a]">
                  Revisado
                </span>
              )}
              <span className="material-symbols-outlined text-[16px] text-[#86868b]">
                chevron_right
              </span>
            </div>
          </button>
        )
      })}
    </div>
  )
}
