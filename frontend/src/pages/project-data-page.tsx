import { useCallback, useEffect, useMemo, useState } from 'react'
import { SecondaryBtn } from '../components/secondary-btn'
import { PrimaryBtn } from '../components/primary-btn'
import {
  fetchProjectDataExtractions,
  fetchProjectDocuments,
  rebuildProjectClassification,
  updateProjectDataExtraction,
  validateProjectClassification,
} from '../services/api-client'
import {
  useProjectShellRegistration,
  useProjectWorkspace,
} from '../hooks/use-project-workspace'
import type { DocumentExtraction, ProjectDocument } from '../types/project'

type ExtractionDraft = {
  correction_reason: string
  corrected_esg_category: string
  corrected_period: string
  corrected_unit: string
  corrected_value: string
}

const ESG_CATEGORY_OPTIONS = [
  'Visão e Estratégia',
  'Governança',
  'Ambiental',
  'Social',
  'Econômico',
  'Stakeholders',
  'Inovação',
  'Normas',
  'Comunicação',
  'Auditorias',
] as const

const DEFAULT_ERROR_MESSAGE =
  'Não foi possível carregar os dados extraídos do projeto.'

function getConfidenceClasses(confidence: DocumentExtraction['confidence']) {
  switch (confidence) {
    case 'high':
      return 'bg-[#e8f5e8] text-[#1a7a1a]'
    case 'low':
      return 'bg-[#fff8e8] text-[#9a6700]'
    case 'medium':
    default:
      return 'bg-[#f0f0f5] text-[#5c5c61]'
  }
}

function getConfidenceLabel(confidence: DocumentExtraction['confidence']) {
  switch (confidence) {
    case 'high':
      return 'Alta'
    case 'low':
      return 'Baixa'
    case 'medium':
    default:
      return 'Média'
  }
}

function getReviewStatusLabel(status: DocumentExtraction['review_status']) {
  switch (status) {
    case 'approved':
      return 'Aprovado'
    case 'corrected':
      return 'Corrigido'
    case 'ignored':
      return 'Ignorado'
    case 'pending':
    default:
      return 'Pendente'
  }
}

function getReviewStatusClasses(status: DocumentExtraction['review_status']) {
  switch (status) {
    case 'approved':
      return 'bg-[#eef6ff] text-[#0b73da]'
    case 'corrected':
      return 'bg-[#f6eefc] text-[#8b3fd1]'
    case 'ignored':
      return 'bg-[#f0f0f5] text-[#86868b]'
    case 'pending':
    default:
      return 'bg-[#fff8e8] text-[#9a6700]'
  }
}

function getDocumentConfidenceLabel(
  confidence: ProjectDocument['classification_confidence']
) {
  switch (confidence) {
    case 'high':
      return 'Alta'
    case 'low':
      return 'Baixa'
    case 'medium':
      return 'Média'
    default:
      return 'Sem confiança'
  }
}

function createDraft(extraction: DocumentExtraction): ExtractionDraft {
  return {
    correction_reason: extraction.correction_reason ?? '',
    corrected_esg_category:
      extraction.corrected_esg_category ??
      extraction.original_esg_category ??
      '',
    corrected_period:
      extraction.corrected_period ?? extraction.original_period ?? '',
    corrected_unit: extraction.corrected_unit ?? extraction.original_unit ?? '',
    corrected_value:
      extraction.corrected_value ?? extraction.original_value ?? '',
  }
}

function buildCorrectionPayload(
  extraction: DocumentExtraction,
  draft: ExtractionDraft
) {
  const normCategory = draft.corrected_esg_category || null
  const normValue = draft.corrected_value || null
  const normUnit = draft.corrected_unit || null
  const normPeriod = draft.corrected_period || null

  const origCategory = extraction.original_esg_category ?? null
  const origValue = extraction.original_value ?? null
  const origUnit = extraction.original_unit ?? null
  const origPeriod = extraction.original_period ?? null

  const hasCategoryCorrection = normCategory !== origCategory
  const hasValueCorrection = normValue !== origValue
  const hasUnitCorrection = normUnit !== origUnit
  const hasPeriodCorrection = normPeriod !== origPeriod

  const hasCorrections =
    hasCategoryCorrection ||
    hasValueCorrection ||
    hasUnitCorrection ||
    hasPeriodCorrection

  return {
    corrected_esg_category: hasCategoryCorrection ? normCategory : null,
    corrected_period: hasPeriodCorrection ? normPeriod : null,
    corrected_unit: hasUnitCorrection ? normUnit : null,
    corrected_value: hasValueCorrection ? normValue : null,
    hasCorrections,
  }
}

export function ProjectDataPage() {
  const {
    currentProjectId,
    isLoadingWorkspace,
    project,
    setProject,
    workspaceError,
  } = useProjectWorkspace()
  const [documents, setDocuments] = useState<ProjectDocument[]>([])
  const [extractions, setExtractions] = useState<DocumentExtraction[]>([])
  const [drafts, setDrafts] = useState<Record<string, ExtractionDraft>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [pageError, setPageError] = useState<string | null>(null)
  const [pageMessage, setPageMessage] = useState<string | null>(null)
  const [isRebuilding, setIsRebuilding] = useState(false)
  const [isValidating, setIsValidating] = useState(false)
  const [savingExtractionId, setSavingExtractionId] = useState<string | null>(
    null
  )

  const loadData = useCallback(async (projectId: string) => {
    setIsLoading(true)

    try {
      const [documentsResponse, extractionsResponse] = await Promise.all([
        fetchProjectDocuments(projectId),
        fetchProjectDataExtractions(projectId),
      ])
      setDocuments(documentsResponse)
      setExtractions(extractionsResponse)
      setDrafts(
        Object.fromEntries(
          extractionsResponse.map((extraction) => [
            extraction.id,
            createDraft(extraction),
          ])
        )
      )
      setPageError(null)
    } catch (error) {
      setDocuments([])
      setExtractions([])
      setDrafts({})
      setPageError(
        error instanceof Error ? error.message : DEFAULT_ERROR_MESSAGE
      )
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!currentProjectId) {
      setDocuments([])
      setExtractions([])
      setDrafts({})
      setIsLoading(false)
      setPageError('Projeto inválido.')
      return
    }

    void loadData(currentProjectId)
  }, [currentProjectId, loadData])

  const hasPendingExtractions = extractions.some(
    (extraction) => extraction.review_status === 'pending'
  )
  const hasIncompleteDocuments = documents.some(
    (document) => document.parsing_status !== 'completed'
  )
  const canValidate =
    !isLoading &&
    !isLoadingWorkspace &&
    !isValidating &&
    !isRebuilding &&
    !!currentProjectId &&
    documents.length > 0 &&
    extractions.length > 0 &&
    !hasPendingExtractions &&
    !hasIncompleteDocuments

  const pageActions = useMemo(
    () => [
      {
        disabled:
          isLoading || isLoadingWorkspace || isRebuilding || !currentProjectId,
        icon: 'refresh',
        label: 'Reclassificar documentos',
        onClick: () => {
          if (!currentProjectId) {
            return
          }

          void (async () => {
            setIsRebuilding(true)
            setPageError(null)
            setPageMessage(null)

            try {
              const response =
                await rebuildProjectClassification(currentProjectId)
              await loadData(currentProjectId)
              setPageMessage(
                `${response.documents_processed} documento(s) reclassificado(s).`
              )
            } catch (error) {
              setPageError(
                error instanceof Error
                  ? error.message
                  : 'Não foi possível reclassificar os documentos.'
              )
            } finally {
              setIsRebuilding(false)
            }
          })()
        },
        variant: 'secondary' as const,
      },
      {
        disabled: !canValidate,
        icon: 'check_circle',
        label: 'Validar e Prosseguir',
        onClick: () => {
          if (!currentProjectId || !canValidate) {
            return
          }

          void (async () => {
            setIsValidating(true)
            setPageError(null)
            setPageMessage(null)

            try {
              const updatedProject =
                await validateProjectClassification(currentProjectId)
              setProject(updatedProject)
              setPageMessage(
                'Dados validados. O projeto foi marcado como pronto para a próxima etapa.'
              )
            } catch (error) {
              setPageError(
                error instanceof Error
                  ? error.message
                  : 'Não foi possível validar os dados do projeto.'
              )
            } finally {
              setIsValidating(false)
            }
          })()
        },
      },
    ],
    [
      canValidate,
      currentProjectId,
      isLoading,
      isLoadingWorkspace,
      isRebuilding,
      loadData,
      setProject,
    ]
  )

  useProjectShellRegistration({
    activeSidebarKey: 'data',
    pageActions,
    pageTitle: 'Dados',
  })

  const groupedDocuments = useMemo(() => {
    const groups = new Map<string, ProjectDocument[]>()

    for (const document of documents) {
      const category = document.esg_category ?? 'Sem categoria'
      const currentGroup = groups.get(category) ?? []
      currentGroup.push(document)
      groups.set(category, currentGroup)
    }

    return Array.from(groups.entries()).sort(([left], [right]) =>
      left.localeCompare(right, 'pt-BR')
    )
  }, [documents])

  const handleSaveExtraction = useCallback(
    async (
      extraction: DocumentExtraction,
      reviewStatus: 'approved' | 'corrected' | 'ignored'
    ) => {
      if (!currentProjectId) {
        return
      }

      const draft = drafts[extraction.id] ?? createDraft(extraction)
      const correctionPayload = buildCorrectionPayload(extraction, draft)
      setSavingExtractionId(extraction.id)
      setPageError(null)
      setPageMessage(null)

      try {
        await updateProjectDataExtraction(currentProjectId, extraction.id, {
          corrected_esg_category: correctionPayload.corrected_esg_category,
          corrected_period: correctionPayload.corrected_period,
          corrected_unit: correctionPayload.corrected_unit,
          corrected_value: correctionPayload.corrected_value,
          correction_reason:
            reviewStatus === 'corrected'
              ? draft.correction_reason || null
              : null,
          review_status:
            reviewStatus === 'approved'
              ? correctionPayload.hasCorrections
                ? 'corrected'
                : 'approved'
              : reviewStatus,
        })
        await loadData(currentProjectId)
      } catch (error) {
        setPageError(
          error instanceof Error
            ? error.message
            : 'Não foi possível salvar a revisão.'
        )
      } finally {
        setSavingExtractionId(null)
      }
    },
    [currentProjectId, drafts, loadData]
  )

  return (
    <div className="space-y-6 px-6 pt-4 pb-6 sm:px-10">
      {pageError || workspaceError ? (
        <div className="rounded-lg border border-[#ffd0d0] bg-[#fff6f6] px-4 py-3 text-[12px] font-medium tracking-[-0.01em] text-[#d01f1f]">
          {pageError ?? workspaceError}
        </div>
      ) : null}

      {pageMessage ? (
        <div className="rounded-lg border border-[#d9e8ff] bg-[#f5f9ff] px-4 py-3 text-[12px] font-medium tracking-[-0.01em] text-[#0b73da]">
          {pageMessage}
        </div>
      ) : null}

      <section className="rounded-lg border border-black/6 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <div className="rounded-full bg-[#f5f7f8] px-3 py-1 text-[12px] font-medium text-[#1d1d1f]">
            Projeto: {project?.org_name ?? 'Projeto atual'}
          </div>
          <div className="rounded-full bg-[#f5f7f8] px-3 py-1 text-[12px] font-medium text-[#1d1d1f]">
            Documentos: {documents.length}
          </div>
          <div className="rounded-full bg-[#f5f7f8] px-3 py-1 text-[12px] font-medium text-[#1d1d1f]">
            Extrações: {extractions.length}
          </div>
          <div
            className={`rounded-full px-3 py-1 text-[12px] font-medium ${
              hasPendingExtractions || hasIncompleteDocuments
                ? 'bg-[#fff8e8] text-[#9a6700]'
                : 'bg-[#e8f5e8] text-[#1a7a1a]'
            }`}
          >
            {hasPendingExtractions || hasIncompleteDocuments
              ? 'Revisão pendente'
              : 'Pronto para prosseguir'}
          </div>
        </div>
        <p className="mt-3 text-[13px] tracking-[-0.01em] text-[#86868b]">
          Revise a categoria ESG e os dados extraídos antes de liberar o projeto
          para a próxima etapa.
        </p>
      </section>

      {isLoading || isLoadingWorkspace ? (
        <div className="rounded-lg border border-black/6 bg-white px-5 py-6">
          <p className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
            Carregando classificações e extrações do projeto...
          </p>
        </div>
      ) : groupedDocuments.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[#d2d2d7] bg-[#f5f7f8] px-5 py-6">
          <p className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
            Nenhum dado classificado disponível.
          </p>
          <p className="mt-1 text-[12px] tracking-[-0.01em] text-[#86868b]">
            Envie documentos, aguarde o parsing e execute a classificação para
            começar a revisão manual.
          </p>
        </div>
      ) : (
        groupedDocuments.map(([category, categoryDocuments]) => (
          <section
            key={category}
            className="space-y-4 rounded-lg border border-black/6 bg-white p-6 shadow-sm"
          >
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-[16px] font-semibold tracking-[-0.015em] text-[#1d1d1f]">
                  {category}
                </h2>
                <p className="mt-1 text-[12px] tracking-[-0.01em] text-[#86868b]">
                  {categoryDocuments.length} documento(s) agrupado(s) nesta
                  categoria.
                </p>
              </div>
            </div>

            {categoryDocuments.map((document) => {
              const documentExtractions = extractions.filter(
                (extraction) => extraction.document_id === document.id
              )

              return (
                <article
                  key={document.id}
                  className="overflow-hidden rounded-xl border border-[#e5e5ea]"
                >
                  <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[#f0f0f2] bg-[#fafafc] px-5 py-4">
                    <div>
                      <h3 className="text-[14px] font-semibold tracking-[-0.01em] text-[#1d1d1f]">
                        {document.filename}
                      </h3>
                      <p className="mt-1 text-[12px] tracking-[-0.01em] text-[#86868b]">
                        {document.file_type.toUpperCase()} • Confiança do
                        documento:{' '}
                        {getDocumentConfidenceLabel(
                          document.classification_confidence
                        )}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="rounded-full bg-[#f0f0f5] px-2.5 py-0.5 text-[11px] font-medium text-[#5c5c61]">
                        {documentExtractions.length} extração(ões)
                      </span>
                    </div>
                  </header>

                  <div className="divide-y divide-[#f0f0f2]">
                    {documentExtractions.length === 0 ? (
                      <div className="px-5 py-5 text-[12px] text-[#86868b]">
                        Nenhuma extração estruturada foi gerada para este
                        documento.
                      </div>
                    ) : (
                      documentExtractions.map((extraction) => {
                        const draft =
                          drafts[extraction.id] ?? createDraft(extraction)

                        return (
                          <div
                            key={extraction.id}
                            className="space-y-4 px-5 py-5"
                          >
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div className="space-y-2">
                                <div className="flex flex-wrap items-center gap-2">
                                  <span
                                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${getConfidenceClasses(
                                      extraction.confidence
                                    )}`}
                                  >
                                    Confiança{' '}
                                    {getConfidenceLabel(extraction.confidence)}
                                  </span>
                                  <span
                                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${getReviewStatusClasses(
                                      extraction.review_status
                                    )}`}
                                  >
                                    {getReviewStatusLabel(
                                      extraction.review_status
                                    )}
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
                                  disabled={
                                    savingExtractionId === extraction.id
                                  }
                                  onChange={(event) => {
                                    const nextValue = event.target.value
                                    setDrafts((current) => ({
                                      ...current,
                                      [extraction.id]: {
                                        ...draft,
                                        corrected_esg_category: nextValue,
                                      },
                                    }))
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
                                  disabled={
                                    savingExtractionId === extraction.id
                                  }
                                  onChange={(event) => {
                                    const nextValue = event.target.value
                                    setDrafts((current) => ({
                                      ...current,
                                      [extraction.id]: {
                                        ...draft,
                                        corrected_value: nextValue,
                                      },
                                    }))
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
                                  disabled={
                                    savingExtractionId === extraction.id
                                  }
                                  onChange={(event) => {
                                    const nextValue = event.target.value
                                    setDrafts((current) => ({
                                      ...current,
                                      [extraction.id]: {
                                        ...draft,
                                        corrected_unit: nextValue,
                                      },
                                    }))
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
                                  disabled={
                                    savingExtractionId === extraction.id
                                  }
                                  onChange={(event) => {
                                    const nextValue = event.target.value
                                    setDrafts((current) => ({
                                      ...current,
                                      [extraction.id]: {
                                        ...draft,
                                        corrected_period: nextValue,
                                      },
                                    }))
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
                                disabled={savingExtractionId === extraction.id}
                                onChange={(event) => {
                                  const nextValue = event.target.value
                                  setDrafts((current) => ({
                                    ...current,
                                    [extraction.id]: {
                                      ...draft,
                                      correction_reason: nextValue,
                                    },
                                  }))
                                }}
                                rows={2}
                                className="apple-focus-ring w-full rounded-[0.7rem] border border-[#d2d2d7] bg-white px-3 py-2 text-[13px] text-[#1d1d1f] disabled:opacity-50"
                                placeholder="Explique a correção, se necessário."
                              />
                            </label>

                            <div className="flex flex-wrap items-center justify-end gap-2">
                              <SecondaryBtn
                                className="mt-0 px-3 py-1.5 text-[12px]"
                                disabled={savingExtractionId === extraction.id}
                                onClick={() => {
                                  void handleSaveExtraction(
                                    extraction,
                                    'ignored'
                                  )
                                }}
                                type="button"
                              >
                                Ignorar
                              </SecondaryBtn>
                              <PrimaryBtn
                                className="mt-0 px-3 py-1.5 text-[12px]"
                                disabled={savingExtractionId === extraction.id}
                                onClick={() => {
                                  void handleSaveExtraction(
                                    extraction,
                                    'approved'
                                  )
                                }}
                                type="button"
                              >
                                Salvar revisão
                              </PrimaryBtn>
                            </div>
                          </div>
                        )
                      })
                    )}
                  </div>
                </article>
              )
            })}
          </section>
        ))
      )}
    </div>
  )
}
