import { useCallback, useEffect, useMemo, useState } from 'react'
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
import { CategoryCardsView } from '../components/project-data/category-cards-view'
import { DocumentsTableView } from '../components/project-data/documents-table-view'
import { ExtractionsView } from '../components/project-data/extractions-view'
import {
  buildCorrectionPayload,
  createDraft,
  type DrillDownView,
  type ExtractionDraft,
} from '../components/project-data/data-view-utils'

const DEFAULT_ERROR_MESSAGE =
  'Não foi possível carregar os dados extraídos do projeto.'

export function ProjectDataPage() {
  const {
    currentProjectId,
    isLoadingWorkspace,
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
  const [view, setView] = useState<DrillDownView>({ level: 'categories' })

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
          if (!currentProjectId) return

          void (async () => {
            setIsRebuilding(true)
            setPageError(null)
            setPageMessage(null)

            try {
              const response =
                await rebuildProjectClassification(currentProjectId)
              await loadData(currentProjectId)
              setView({ level: 'categories' })
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
          if (!currentProjectId || !canValidate) return

          void (async () => {
            setIsValidating(true)
            setPageError(null)
            setPageMessage(null)

            try {
              const updatedProject =
                await validateProjectClassification(currentProjectId)
              setProject(updatedProject)
              setView({ level: 'categories' })
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

  const handleSaveExtraction = useCallback(
    async (
      extraction: DocumentExtraction,
      reviewStatus: 'approved' | 'corrected' | 'ignored'
    ) => {
      if (!currentProjectId) return

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

  const handleDraftChange = useCallback(
    (extractionId: string, draft: ExtractionDraft) => {
      setDrafts((current) => ({ ...current, [extractionId]: draft }))
    },
    []
  )

  const selectedDocument = useMemo(() => {
    if (view.level !== 'extractions') return null
    return documents.find((d) => d.id === view.documentId) ?? null
  }, [view, documents])

  const filteredExtractions = useMemo(() => {
    if (view.level !== 'extractions') return []
    return extractions.filter((e) => e.document_id === view.documentId)
  }, [view, extractions])

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

      {view.level !== 'categories' ? (
        <nav className="flex items-center gap-2 text-[13px] tracking-[-0.01em]">
          <button
            type="button"
            onClick={() => setView({ level: 'categories' })}
            className="text-primary hover:underline"
          >
            Categorias
          </button>
          <span className="text-[#86868b]">/</span>
          {view.level === 'documents' ? (
            <span className="font-medium text-[#1d1d1f]">{view.category}</span>
          ) : (
            <>
              <button
                type="button"
                onClick={() =>
                  setView({ level: 'documents', category: view.category })
                }
                className="text-primary hover:underline"
              >
                {view.category}
              </button>
              <span className="text-[#86868b]">/</span>
              <span className="font-medium text-[#1d1d1f]">
                {view.documentName}
              </span>
            </>
          )}
        </nav>
      ) : null}

      {isLoading || isLoadingWorkspace ? (
        <div className="rounded-lg border border-black/6 bg-white px-5 py-6">
          <p className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
            Carregando classificações e extrações do projeto...
          </p>
        </div>
      ) : view.level === 'categories' ? (
        <CategoryCardsView
          documents={documents}
          extractions={extractions}
          onSelectCategory={(category) =>
            setView({ level: 'documents', category })
          }
        />
      ) : view.level === 'documents' ? (
        <DocumentsTableView
          category={view.category}
          documents={documents}
          extractions={extractions}
          onSelectDocument={(documentId, documentName) =>
            setView({
              level: 'extractions',
              category: view.category,
              documentId,
              documentName,
            })
          }
        />
      ) : selectedDocument ? (
        <ExtractionsView
          document={selectedDocument}
          extractions={filteredExtractions}
          drafts={drafts}
          savingExtractionId={savingExtractionId}
          onDraftChange={handleDraftChange}
          onSaveExtraction={(extraction, status) => {
            void handleSaveExtraction(extraction, status)
          }}
        />
      ) : null}
    </div>
  )
}
