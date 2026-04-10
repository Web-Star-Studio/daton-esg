import { SecondaryBtn } from '../secondary-btn'
import { PrimaryBtn } from '../primary-btn'
import type { DocumentExtraction, ProjectDocument } from '../../types/project'
import {
  ESG_CATEGORY_OPTIONS,
  getConfidenceClasses,
  getConfidenceLabel,
  getDocumentConfidenceLabel,
  getReviewStatusClasses,
  getReviewStatusLabel,
  type ExtractionDraft,
  createDraft,
} from './data-view-utils'

type ExtractionsViewProps = {
  document: ProjectDocument
  extractions: DocumentExtraction[]
  drafts: Record<string, ExtractionDraft>
  savingExtractionId: string | null
  onDraftChange: (extractionId: string, draft: ExtractionDraft) => void
  onSaveExtraction: (
    extraction: DocumentExtraction,
    status: 'approved' | 'corrected' | 'ignored'
  ) => void
}

export function ExtractionsView({
  document,
  extractions,
  drafts,
  savingExtractionId,
  onDraftChange,
  onSaveExtraction,
}: ExtractionsViewProps) {
  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-black/6 bg-white p-5 shadow-sm">
        <h3 className="text-[14px] font-semibold tracking-[-0.01em] text-[#1d1d1f]">
          {document.filename}
        </h3>
        <p className="mt-1 text-[12px] tracking-[-0.01em] text-[#86868b]">
          {document.file_type.toUpperCase()} • Confiança:{' '}
          {getDocumentConfidenceLabel(document.classification_confidence)} •{' '}
          {extractions.length} extração(ões)
        </p>
      </div>

      {extractions.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[#d2d2d7] bg-[#f5f7f8] px-5 py-6">
          <p className="text-[12px] tracking-[-0.01em] text-[#86868b]">
            Nenhuma extração estruturada foi gerada para este documento.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-black/6 bg-white shadow-sm">
          <div className="divide-y divide-[#f0f0f2]">
            {extractions.map((extraction) => {
              const draft = drafts[extraction.id] ?? createDraft(extraction)
              const isSaving = savingExtractionId === extraction.id

              return (
                <div key={extraction.id} className="space-y-4 px-5 py-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${getConfidenceClasses(extraction.confidence)}`}
                        >
                          Confiança {getConfidenceLabel(extraction.confidence)}
                        </span>
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${getReviewStatusClasses(extraction.review_status)}`}
                        >
                          {getReviewStatusLabel(extraction.review_status)}
                        </span>
                      </div>
                      <p className="max-w-4xl text-[13px] leading-6 tracking-[-0.01em] text-[#1d1d1f]">
                        {extraction.source_snippet}
                      </p>
                    </div>
                  </div>

                  <div className="grid gap-3 md:grid-cols-4">
                    <label className="space-y-1">
                      <span className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#86868b]">
                        Categoria ESG
                      </span>
                      <select
                        value={draft.corrected_esg_category}
                        disabled={isSaving}
                        onChange={(event) => {
                          onDraftChange(extraction.id, {
                            ...draft,
                            corrected_esg_category: event.target.value,
                          })
                        }}
                        className="apple-focus-ring w-full rounded-[0.7rem] border border-[#d2d2d7] bg-white px-3 py-2 text-[13px] text-[#1d1d1f] disabled:opacity-50"
                      >
                        <option value="">Sem categoria</option>
                        {ESG_CATEGORY_OPTIONS.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="space-y-1">
                      <span className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#86868b]">
                        Valor
                      </span>
                      <input
                        type="text"
                        value={draft.corrected_value}
                        disabled={isSaving}
                        onChange={(event) => {
                          onDraftChange(extraction.id, {
                            ...draft,
                            corrected_value: event.target.value,
                          })
                        }}
                        className="apple-focus-ring w-full rounded-[0.7rem] border border-[#d2d2d7] bg-white px-3 py-2 text-[13px] text-[#1d1d1f] disabled:opacity-50"
                      />
                    </label>

                    <label className="space-y-1">
                      <span className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#86868b]">
                        Unidade
                      </span>
                      <input
                        type="text"
                        value={draft.corrected_unit}
                        disabled={isSaving}
                        onChange={(event) => {
                          onDraftChange(extraction.id, {
                            ...draft,
                            corrected_unit: event.target.value,
                          })
                        }}
                        className="apple-focus-ring w-full rounded-[0.7rem] border border-[#d2d2d7] bg-white px-3 py-2 text-[13px] text-[#1d1d1f] disabled:opacity-50"
                      />
                    </label>

                    <label className="space-y-1">
                      <span className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#86868b]">
                        Período
                      </span>
                      <input
                        type="text"
                        value={draft.corrected_period}
                        disabled={isSaving}
                        onChange={(event) => {
                          onDraftChange(extraction.id, {
                            ...draft,
                            corrected_period: event.target.value,
                          })
                        }}
                        className="apple-focus-ring w-full rounded-[0.7rem] border border-[#d2d2d7] bg-white px-3 py-2 text-[13px] text-[#1d1d1f] disabled:opacity-50"
                      />
                    </label>
                  </div>

                  <label className="block space-y-1">
                    <span className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#86868b]">
                      Motivo da correção
                    </span>
                    <textarea
                      value={draft.correction_reason}
                      disabled={isSaving}
                      onChange={(event) => {
                        onDraftChange(extraction.id, {
                          ...draft,
                          correction_reason: event.target.value,
                        })
                      }}
                      rows={2}
                      className="apple-focus-ring w-full rounded-[0.7rem] border border-[#d2d2d7] bg-white px-3 py-2 text-[13px] text-[#1d1d1f] disabled:opacity-50"
                      placeholder="Explique a correção, se necessário."
                    />
                  </label>

                  <div className="flex flex-wrap items-center justify-end gap-2">
                    <SecondaryBtn
                      className="mt-0 px-3 py-1.5 text-[12px]"
                      disabled={isSaving}
                      onClick={() => {
                        onSaveExtraction(extraction, 'ignored')
                      }}
                      type="button"
                    >
                      Ignorar
                    </SecondaryBtn>
                    <PrimaryBtn
                      className="mt-0 px-3 py-1.5 text-[12px]"
                      disabled={isSaving}
                      onClick={() => {
                        onSaveExtraction(extraction, 'approved')
                      }}
                      type="button"
                    >
                      Salvar revisão
                    </PrimaryBtn>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
