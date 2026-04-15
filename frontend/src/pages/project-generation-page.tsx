import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  useProjectShellRegistration,
  useProjectWorkspace,
} from '../hooks/use-project-workspace'
import {
  exportReportDocx,
  fetchReport,
  fetchReports,
  streamReportGeneration,
  streamSectionRegeneration,
  updateReportSection,
} from '../services/api-client'
import type {
  GriIndexEntry,
  ReportListItem,
  ReportRecord,
  ReportSection,
  ReportStatus,
} from '../types/project'

// ---------- helpers ----------

type PipelineSection = {
  key: string
  title: string
  order: number
  state: 'pending' | 'running' | 'completed' | 'failed'
  wordCount?: number
  griCodesUsed?: string[]
  streamingText: string
}

const ALL_SECTION_KEYS: Array<{ key: string; title: string; order: number }> = [
  { key: 'a-empresa', title: 'A Empresa', order: 1 },
  { key: 'visao-estrategia', title: 'Visao e Estrategia', order: 2 },
  { key: 'governanca', title: 'Governanca Corporativa', order: 3 },
  { key: 'gestao-ambiental', title: 'Gestao Ambiental', order: 4 },
  { key: 'desempenho-social', title: 'Desempenho Social', order: 5 },
  { key: 'desempenho-economico', title: 'Desempenho Economico', order: 6 },
  { key: 'stakeholders', title: 'Stakeholders', order: 7 },
  { key: 'inovacao', title: 'Inovacao', order: 8 },
  { key: 'auditorias', title: 'Auditorias', order: 9 },
  { key: 'comunicacao', title: 'Comunicacao', order: 10 },
  { key: 'temas-materiais', title: 'Temas Materiais', order: 11 },
  { key: 'plano-acao', title: 'Plano de Acao', order: 12 },
  { key: 'alinhamento-ods', title: 'Alinhamento ODS', order: 13 },
  { key: 'sumario-gri', title: 'Sumario GRI', order: 14 },
]

const STATUS_LABELS: Record<ReportStatus, string> = {
  generating: 'Gerando',
  failed: 'Falhou',
  draft: 'Rascunho',
  reviewed: 'Revisado',
  exported: 'Exportado',
}

const STATUS_COLORS: Record<ReportStatus, string> = {
  generating: 'bg-[#fff6d9] text-[#8a6200]',
  failed: 'bg-[#ffd0d0] text-[#d01f1f]',
  draft: 'bg-[#e6f1fc] text-[#0673e0]',
  reviewed: 'bg-[#e6f5ec] text-[#2b8a3e]',
  exported: 'bg-black/5 text-[#1d1d1f]',
}

function formatDateTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

// ---------- GRI index table ----------

function GriIndexTable({ entries }: { entries: GriIndexEntry[] | null }) {
  const grouped = useMemo(() => {
    const by: Record<string, GriIndexEntry[]> = {}
    for (const entry of entries ?? []) {
      const family = entry.family || 'outros'
      if (!by[family]) by[family] = []
      by[family].push(entry)
    }
    return by
  }, [entries])

  if (!entries || entries.length === 0) {
    return (
      <p className="text-[13px] leading-6 tracking-[-0.01em] text-[#9b9ba1]">
        Nenhum sumário GRI disponível ainda. Ele é gerado ao final da produção
        do relatório.
      </p>
    )
  }

  const families = Object.keys(grouped).sort((a, b) => {
    const order = ['2', '3', '200', '300', '400']
    const rankA = order.indexOf(a) === -1 ? order.length : order.indexOf(a)
    const rankB = order.indexOf(b) === -1 ? order.length : order.indexOf(b)
    return rankA - rankB || a.localeCompare(b)
  })

  return (
    <div className="space-y-6">
      {families.map((family) => (
        <section key={family}>
          <h4 className="mb-2 text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
            GRI {family}
          </h4>
          <div className="overflow-x-auto rounded-[0.9rem] border border-black/6">
            <table className="w-full text-[12px] tracking-[-0.01em]">
              <thead className="bg-[#fbfbfc] text-[#6b6b72]">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Código</th>
                  <th className="px-3 py-2 text-left font-medium">
                    Divulgação
                  </th>
                  <th className="px-3 py-2 text-left font-medium">
                    Evidência / Localização
                  </th>
                  <th className="px-3 py-2 text-left font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {grouped[family].map((entry) => (
                  <tr
                    key={entry.code}
                    className="border-t border-black/6 align-top"
                  >
                    <td className="px-3 py-2 font-medium text-[#1d1d1f]">
                      {entry.code}
                    </td>
                    <td className="px-3 py-2 text-[#3a3a3c]">
                      {entry.standard_text}
                    </td>
                    <td className="px-3 py-2 text-[#6b6b72]">
                      {entry.evidence_excerpt ? (
                        <>
                          <span className="block">
                            {entry.evidence_excerpt}
                          </span>
                          {entry.section_ref ? (
                            <span className="text-[10px] uppercase tracking-[0.08em] text-[#9b9ba1]">
                              ({entry.section_ref})
                            </span>
                          ) : null}
                        </>
                      ) : (
                        <span className="text-[#9b9ba1]">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.08em] ${
                          entry.status === 'atendido'
                            ? 'bg-[#e6f5ec] text-[#2b8a3e]'
                            : entry.status === 'parcial'
                              ? 'bg-[#fff6d9] text-[#8a6200]'
                              : 'bg-black/5 text-[#6b6b72]'
                        }`}
                      >
                        {entry.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  )
}

// ---------- section editor ----------

type SectionEditorHandle = {
  flush: () => Promise<void>
}

type SectionEditorProps = {
  section: ReportSection
  onSave: (content: string) => Promise<void>
  onRegenerate?: () => void
  isRegenerating?: boolean
  handleRef?: React.MutableRefObject<SectionEditorHandle | null>
}

function SectionEditor({
  section,
  onSave,
  onRegenerate,
  isRegenerating,
  handleRef,
}: SectionEditorProps) {
  const [draft, setDraft] = useState(section.content)
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const savedRef = useRef(section.content)

  useEffect(() => {
    setDraft(section.content)
    savedRef.current = section.content
  }, [section.key, section.content])

  // expose flush handle so parent can await save before export
  useEffect(() => {
    if (handleRef) {
      handleRef.current = {
        flush: async () => {
          if (draft !== savedRef.current && !isSaving) {
            setIsSaving(true)
            setSaveError(null)
            try {
              await onSave(draft)
              savedRef.current = draft
            } catch (error) {
              setSaveError(
                error instanceof Error
                  ? error.message
                  : 'Falha ao salvar a seção.'
              )
            } finally {
              setIsSaving(false)
            }
          }
        },
      }
    }
  })

  async function handleBlur() {
    if (draft === savedRef.current || isSaving) return
    setIsSaving(true)
    setSaveError(null)
    try {
      await onSave(draft)
      savedRef.current = draft
    } catch (error) {
      setSaveError(
        error instanceof Error ? error.message : 'Falha ao salvar a seção.'
      )
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3
            id={`section-heading-${section.key}`}
            className="text-[16px] font-medium tracking-[-0.015em] text-[#1d1d1f]"
          >
            {section.title}
          </h3>
          <p className="mt-0.5 text-[11px] tracking-[-0.01em] text-[#9b9ba1]">
            {section.word_count} palavras
            {section.gri_codes_used.length > 0
              ? ` · ${section.gri_codes_used.length} códigos GRI`
              : ''}
            {section.status === 'sparse_data'
              ? ' · evidências fracas'
              : section.status === 'failed'
                ? ' · geração falhou'
                : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] tracking-[-0.01em] text-[#9b9ba1]">
            {isSaving
              ? 'Salvando…'
              : isRegenerating
                ? 'Regenerando…'
                : 'Alterações são salvas ao sair do campo'}
          </span>
          {onRegenerate ? (
            <button
              type="button"
              onClick={onRegenerate}
              disabled={isRegenerating || isSaving}
              className="apple-focus-ring inline-flex items-center gap-1 rounded-full border border-black/10 px-2.5 py-1 text-[11px] font-medium tracking-[-0.01em] text-[#1d1d1f] transition hover:border-black/20 hover:bg-black/[0.03] disabled:cursor-not-allowed disabled:opacity-40"
              aria-label={`Regenerar seção ${section.title}`}
            >
              <span
                aria-hidden="true"
                className={`material-symbols-outlined text-[14px] ${isRegenerating ? 'animate-spin' : ''}`}
              >
                refresh
              </span>
              Regenerar
            </button>
          ) : null}
        </div>
      </div>
      {saveError ? (
        <p className="mb-2 text-[11px] font-medium tracking-[-0.01em] text-[#d01f1f]">
          {saveError}
        </p>
      ) : null}
      <textarea
        aria-labelledby={`section-heading-${section.key}`}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={handleBlur}
        spellCheck={false}
        className="apple-focus-ring min-h-[420px] flex-1 resize-y rounded-[0.9rem] border border-black/10 bg-white px-4 py-3 font-mono text-[12.5px] leading-6 tracking-[-0.01em] text-[#1d1d1f] focus:border-black/25 focus:shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
      />
      {section.gri_codes_used.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {section.gri_codes_used.map((code) => (
            <span
              key={code}
              className="rounded-full bg-[#e6f1fc] px-2 py-0.5 text-[10px] font-medium tracking-[-0.01em] text-[#0673e0]"
            >
              {code}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  )
}

// ---------- generation progress ----------

function GenerationProgress({
  pipeline,
  activeKey,
}: {
  pipeline: PipelineSection[]
  activeKey: string | null
}) {
  const active = pipeline.find((p) => p.key === activeKey)
  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_1fr] gap-4">
      <div className="rounded-[1rem] border border-black/6 bg-[#fbfbfc] p-4">
        <h3 className="text-[14px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
          Gerando relatório…
        </h3>
        <p className="mt-1 text-[12px] leading-5 tracking-[-0.01em] text-[#6b6b72]">
          O agente está produzindo cada seção com base nas evidências indexadas.
          Mantenha esta aba aberta até a conclusão.
        </p>
      </div>
      <div className="grid min-h-0 grid-cols-[260px_1fr] gap-4">
        <ol className="min-h-0 space-y-1 overflow-y-auto rounded-[1rem] border border-black/6 p-2">
          {pipeline.map((entry) => {
            const isActive = entry.key === activeKey
            const colors = {
              pending: 'text-[#9b9ba1]',
              running: 'text-[#0673e0]',
              completed: 'text-[#2b8a3e]',
              failed: 'text-[#d01f1f]',
            }[entry.state]
            const icon = {
              pending: '○',
              running: '◐',
              completed: '●',
              failed: '✕',
            }[entry.state]
            return (
              <li
                key={entry.key}
                className={`flex items-center gap-2 rounded-md px-2 py-1.5 ${
                  isActive ? 'bg-black/5' : ''
                }`}
              >
                <span
                  aria-hidden="true"
                  className={`w-4 text-center text-[13px] ${colors}`}
                >
                  {icon}
                </span>
                <span className="flex-1 truncate text-[12px] tracking-[-0.01em] text-[#1d1d1f]">
                  {entry.title}
                </span>
                {entry.wordCount ? (
                  <span className="text-[10px] tracking-[-0.01em] text-[#9b9ba1]">
                    {entry.wordCount}w
                  </span>
                ) : null}
              </li>
            )
          })}
        </ol>
        <div className="min-h-0 overflow-y-auto rounded-[1rem] border border-black/6 bg-white p-4 font-mono text-[12px] leading-6 tracking-[-0.01em] text-[#3a3a3c]">
          {active ? (
            active.streamingText ? (
              <pre className="whitespace-pre-wrap break-words">
                {active.streamingText}
              </pre>
            ) : (
              <p className="text-[#9b9ba1]">
                Recuperando contexto e preparando a seção…
              </p>
            )
          ) : (
            <p className="text-[#9b9ba1]">Aguardando primeira seção iniciar…</p>
          )}
        </div>
      </div>
    </div>
  )
}

// ---------- page ----------

type Tab = 'sections' | 'gri' | 'gaps'

export function ProjectGenerationPage() {
  const { currentProjectId, project, workspaceError } = useProjectWorkspace()

  useProjectShellRegistration({
    activeSidebarKey: 'generation',
    pageTitle: 'Geração do Relatório',
  })

  const [reports, setReports] = useState<ReportListItem[]>([])
  const [activeReport, setActiveReport] = useState<ReportRecord | null>(null)
  const [isLoadingReports, setIsLoadingReports] = useState(true)
  const [isLoadingActive, setIsLoadingActive] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)
  const [pipeline, setPipeline] = useState<PipelineSection[]>([])
  const [activeSectionKey, setActiveSectionKey] = useState<string | null>(null)
  const [selectedSectionKey, setSelectedSectionKey] = useState<string | null>(
    null
  )
  const [activeTab, setActiveTab] = useState<Tab>('sections')
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)
  const [isExporting, setIsExporting] = useState(false)
  const [regeneratingKey, setRegeneratingKey] = useState<string | null>(null)
  const [selectedSectionKeys, setSelectedSectionKeys] = useState<Set<string>>(
    () => new Set(ALL_SECTION_KEYS.map((s) => s.key))
  )
  const [showSectionPicker, setShowSectionPicker] = useState(false)
  const sectionPickerRef = useRef<HTMLDivElement>(null)
  const editorHandleRef = useRef<SectionEditorHandle | null>(null)

  useEffect(() => {
    if (!showSectionPicker) return
    function handlePointerDown(event: PointerEvent) {
      if (
        sectionPickerRef.current &&
        !sectionPickerRef.current.contains(event.target as Node)
      ) {
        setShowSectionPicker(false)
      }
    }
    document.addEventListener('pointerdown', handlePointerDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
    }
  }, [showSectionPicker])

  const materialTopics = Array.isArray(project?.material_topics)
    ? project.material_topics
    : []
  const hasMaterialTopics = materialTopics.length > 0

  const loadReports = useCallback(
    async (selectMostRecent: boolean) => {
      if (!currentProjectId) return
      setIsLoadingReports(true)
      try {
        const list = await fetchReports(currentProjectId)
        setReports(list)
        if (selectMostRecent && list.length > 0) {
          setIsLoadingActive(true)
          try {
            const detail = await fetchReport(currentProjectId, list[0].id)
            setActiveReport(detail)
            const firstKey = detail.sections?.[0]?.key ?? null
            setSelectedSectionKey(firstKey)
          } finally {
            setIsLoadingActive(false)
          }
        } else if (list.length === 0) {
          setActiveReport(null)
          setSelectedSectionKey(null)
          setDownloadUrl(null)
        }
      } catch (error) {
        setPageError(
          error instanceof Error
            ? error.message
            : 'Falha ao carregar relatórios.'
        )
      } finally {
        setIsLoadingReports(false)
      }
    },
    [currentProjectId]
  )

  useEffect(() => {
    if (!currentProjectId) return
    void loadReports(true)
  }, [currentProjectId, loadReports])

  async function handleSelectReport(reportId: string) {
    if (!currentProjectId) return
    setIsLoadingActive(true)
    setDownloadUrl(null)
    try {
      const detail = await fetchReport(currentProjectId, reportId)
      setActiveReport(detail)
      const firstKey = detail.sections?.[0]?.key ?? null
      setSelectedSectionKey(firstKey)
      setActiveTab('sections')
    } catch (error) {
      setPageError(
        error instanceof Error
          ? error.message
          : 'Falha ao carregar o relatório.'
      )
    } finally {
      setIsLoadingActive(false)
    }
  }

  async function handleGenerate() {
    if (!currentProjectId || isGenerating) return
    setIsGenerating(true)
    setPageError(null)
    setPipeline([])
    setActiveSectionKey(null)
    try {
      const keysToGenerate =
        selectedSectionKeys.size < ALL_SECTION_KEYS.length
          ? [...selectedSectionKeys]
          : undefined
      await streamReportGeneration(
        currentProjectId,
        {
          onReportStarted: (data) => {
            setPipeline(
              data.sections.map((section) => ({
                key: section.key,
                title: section.title,
                order: section.order,
                state: 'pending',
                streamingText: '',
              }))
            )
          },
          onSectionStarted: (data) => {
            setActiveSectionKey(data.section_key)
            setPipeline((current) =>
              current.map((entry) =>
                entry.key === data.section_key
                  ? { ...entry, state: 'running', streamingText: '' }
                  : entry
              )
            )
          },
          onSectionToken: (data) => {
            setPipeline((current) =>
              current.map((entry) =>
                entry.key === data.section_key
                  ? {
                      ...entry,
                      streamingText: entry.streamingText + data.text,
                    }
                  : entry
              )
            )
          },
          onSectionCompleted: (data) => {
            setPipeline((current) =>
              current.map((entry) =>
                entry.key === data.section_key
                  ? {
                      ...entry,
                      state: data.status === 'failed' ? 'failed' : 'completed',
                      wordCount: data.word_count,
                      griCodesUsed: data.gri_codes_used,
                    }
                  : entry
              )
            )
          },
          onReportCompleted: (data) => {
            if (data.report) {
              setActiveReport(data.report)
              const firstKey = data.report.sections?.[0]?.key ?? null
              setSelectedSectionKey(firstKey)
              setActiveTab('sections')
            }
            void loadReports(false)
          },
          onReportFailed: (data) => {
            setPageError(data.message)
          },
        },
        keysToGenerate
      )
    } catch (error) {
      setPageError(
        error instanceof Error
          ? error.message
          : 'Falha ao iniciar a geração do relatório.'
      )
    } finally {
      setIsGenerating(false)
    }
  }

  async function handleSaveSection(sectionKey: string, content: string) {
    if (!currentProjectId || !activeReport) return
    const updated = await updateReportSection(
      currentProjectId,
      activeReport.id,
      sectionKey,
      content
    )
    setActiveReport(updated)
  }

  async function handleRegenerateSection(sectionKey: string) {
    if (!currentProjectId || !activeReport || regeneratingKey) return
    setRegeneratingKey(sectionKey)
    setPageError(null)
    try {
      await streamSectionRegeneration(
        currentProjectId,
        activeReport.id,
        sectionKey,
        {
          onSectionToken: () => {
            // streaming preview could be added here
          },
          onSectionCompleted: () => {},
          onReportCompleted: (data) => {
            if (data.report) {
              setActiveReport(data.report)
            }
          },
          onReportFailed: (data) => {
            setPageError(data.message)
          },
        }
      )
      // Refresh the report to get the updated section
      if (currentProjectId && activeReport) {
        const refreshed = await fetchReport(currentProjectId, activeReport.id)
        setActiveReport(refreshed)
      }
    } catch (error) {
      setPageError(
        error instanceof Error ? error.message : 'Falha ao regenerar a secao.'
      )
    } finally {
      setRegeneratingKey(null)
    }
  }

  async function handleExport() {
    if (!currentProjectId || !activeReport || isExporting) return
    setIsExporting(true)
    setPageError(null)
    try {
      // flush any pending section edit before exporting
      if (editorHandleRef.current) {
        await editorHandleRef.current.flush()
      }
      const response = await exportReportDocx(currentProjectId, activeReport.id)
      setDownloadUrl(response.download_url)
      window.open(response.download_url, '_blank')
    } catch (error) {
      setPageError(
        error instanceof Error
          ? error.message
          : 'Falha ao exportar o relatório.'
      )
    } finally {
      setIsExporting(false)
    }
  }

  const selectedSection = activeReport?.sections?.find(
    (section) => section.key === selectedSectionKey
  )

  return (
    <div className="flex h-full min-h-0 flex-col bg-white px-6 pt-6 pb-6 sm:px-10">
      {workspaceError || pageError ? (
        <div className="mb-4 rounded-lg border border-[#ffd0d0] bg-[#fff6f6] px-4 py-3 text-[12px] font-medium tracking-[-0.01em] text-[#d01f1f]">
          {workspaceError ?? pageError}
        </div>
      ) : null}

      <header className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-[18px] font-medium tracking-[-0.015em] text-[#1d1d1f]">
            Geração do Relatório
          </h2>
          <p className="mt-1 text-[12px] tracking-[-0.01em] text-[#6b6b72]">
            Produza a versão preliminar do relatório de sustentabilidade
            {project ? ` de ${project.org_name}` : ''} a partir das evidências
            indexadas e dos temas materiais selecionados.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {activeReport && activeReport.status !== 'generating' ? (
            <button
              type="button"
              onClick={handleExport}
              disabled={isExporting}
              className="apple-focus-ring rounded-full border border-black/10 px-3 py-1.5 text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f] transition hover:border-black/20 hover:bg-black/[0.03] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isExporting ? 'Gerando…' : 'Exportar Word'}
            </button>
          ) : null}
          <div ref={sectionPickerRef} className="relative">
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={handleGenerate}
                disabled={
                  isGenerating ||
                  !hasMaterialTopics ||
                  !currentProjectId ||
                  selectedSectionKeys.size === 0
                }
                className="apple-focus-ring rounded-l-full bg-[#0f1923] px-4 py-2 text-[12px] font-medium text-white transition hover:bg-[#1a2632] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isGenerating
                  ? 'Gerando…'
                  : selectedSectionKeys.size < ALL_SECTION_KEYS.length
                    ? `Gerar ${selectedSectionKeys.size} seções`
                    : 'Gerar Relatório'}
              </button>
              <button
                type="button"
                onClick={() => setShowSectionPicker((v) => !v)}
                disabled={isGenerating}
                className="apple-focus-ring rounded-r-full border-l border-white/20 bg-[#0f1923] px-2 py-2 text-white transition hover:bg-[#1a2632] disabled:cursor-not-allowed disabled:opacity-50"
                aria-label="Selecionar seções para gerar"
              >
                <span
                  aria-hidden="true"
                  className="material-symbols-outlined text-[14px]"
                >
                  expand_more
                </span>
              </button>
            </div>
            {showSectionPicker ? (
              <div className="absolute right-0 top-full z-20 mt-2 w-[300px] rounded-lg border border-black/10 bg-white p-3 shadow-[rgba(0,0,0,0.12)_0px_8px_24px]">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#6b6b72]">
                    Seções a gerar
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      if (
                        selectedSectionKeys.size === ALL_SECTION_KEYS.length
                      ) {
                        setSelectedSectionKeys(new Set())
                      } else {
                        setSelectedSectionKeys(
                          new Set(ALL_SECTION_KEYS.map((s) => s.key))
                        )
                      }
                    }}
                    className="text-[10px] font-medium text-[#0673e0] hover:underline"
                  >
                    {selectedSectionKeys.size === ALL_SECTION_KEYS.length
                      ? 'Desmarcar todas'
                      : 'Marcar todas'}
                  </button>
                </div>
                <ul className="max-h-[320px] space-y-0.5 overflow-y-auto">
                  {ALL_SECTION_KEYS.map((s) => (
                    <li key={s.key}>
                      <label className="flex cursor-pointer items-center gap-2 rounded-md px-1.5 py-1 text-[12px] tracking-[-0.01em] text-[#1d1d1f] hover:bg-black/[0.03]">
                        <input
                          type="checkbox"
                          checked={selectedSectionKeys.has(s.key)}
                          onChange={() => {
                            setSelectedSectionKeys((prev) => {
                              const next = new Set(prev)
                              if (next.has(s.key)) {
                                next.delete(s.key)
                              } else {
                                next.add(s.key)
                              }
                              return next
                            })
                          }}
                          className="h-3.5 w-3.5 accent-[#0673e0]"
                        />
                        <span>
                          {s.order}. {s.title}
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </div>
      </header>

      {!hasMaterialTopics ? (
        <div className="mb-4 rounded-[0.9rem] border border-[#ffecc2] bg-[#fff9e6] px-4 py-3 text-[12px] leading-5 tracking-[-0.01em] text-[#6b5200]">
          Selecione ao menos um tema material antes de gerar o relatório.{' '}
          {currentProjectId ? (
            <Link
              to={`/projects/${currentProjectId}/materiality`}
              className="font-medium underline decoration-[#8a6200]/40 underline-offset-2 hover:decoration-[#8a6200]"
            >
              Abrir Materialidade & ODS
            </Link>
          ) : null}
        </div>
      ) : null}

      {downloadUrl ? (
        <div className="mb-4 rounded-[0.9rem] border border-black/10 bg-[#fbfbfc] px-4 py-3 text-[12px] tracking-[-0.01em] text-[#1d1d1f]">
          Arquivo pronto.{' '}
          <a
            href={downloadUrl}
            target="_blank"
            rel="noreferrer"
            className="font-medium text-[#0673e0] underline decoration-[#0673e0]/40 underline-offset-2 hover:decoration-[#0673e0]"
          >
            Baixar novamente
          </a>
        </div>
      ) : null}

      <div className="flex min-h-0 flex-1 gap-6">
        <aside className="w-[260px] shrink-0 overflow-y-auto border-r border-black/6 pr-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
              Versões
            </h3>
          </div>
          {isLoadingReports ? (
            <p className="text-[12px] tracking-[-0.01em] text-[#9b9ba1]">
              Carregando…
            </p>
          ) : reports.length === 0 ? (
            <p className="text-[12px] leading-5 tracking-[-0.01em] text-[#9b9ba1]">
              Nenhum relatório gerado. Clique em "Gerar Relatório" para produzir
              a primeira versão preliminar.
            </p>
          ) : (
            <ul className="space-y-0.5">
              {reports.map((report) => {
                const isActive = report.id === activeReport?.id
                return (
                  <li key={report.id}>
                    <button
                      type="button"
                      onClick={() => {
                        void handleSelectReport(report.id)
                      }}
                      className={`apple-focus-ring flex w-full flex-col rounded-md px-2 py-1.5 text-left transition ${
                        isActive ? 'bg-black/5' : 'hover:bg-black/[0.03]'
                      }`}
                    >
                      <span className="flex items-center justify-between gap-2">
                        <span className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                          Versão {report.version}
                        </span>
                        <span
                          className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.08em] ${
                            STATUS_COLORS[report.status]
                          }`}
                        >
                          {STATUS_LABELS[report.status]}
                        </span>
                      </span>
                      <span className="mt-0.5 text-[10px] tracking-[-0.01em] text-[#9b9ba1]">
                        {formatDateTime(report.created_at)}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </aside>

        <section className="flex min-h-0 flex-1 flex-col">
          {isGenerating ? (
            <GenerationProgress
              pipeline={pipeline}
              activeKey={activeSectionKey}
            />
          ) : isLoadingActive ? (
            <p className="text-[13px] tracking-[-0.01em] text-[#9b9ba1]">
              Carregando relatório…
            </p>
          ) : activeReport ? (
            <div className="flex min-h-0 flex-1 flex-col">
              <div className="mb-4 flex items-center gap-2 border-b border-black/6 pb-2">
                {(['sections', 'gri', 'gaps'] as Tab[]).map((tab) => {
                  const label = {
                    sections: 'Seções',
                    gri: 'Sumário GRI',
                    gaps: `Lacunas (${activeReport.gaps?.length ?? 0})`,
                  }[tab]
                  const isActive = activeTab === tab
                  return (
                    <button
                      key={tab}
                      type="button"
                      onClick={() => setActiveTab(tab)}
                      className={`apple-focus-ring rounded-full px-3 py-1 text-[12px] font-medium tracking-[-0.01em] transition ${
                        isActive
                          ? 'bg-[#0f1923] text-white'
                          : 'text-[#3a3a3c] hover:bg-black/[0.04]'
                      }`}
                    >
                      {label}
                    </button>
                  )
                })}
              </div>
              {activeTab === 'sections' ? (
                <div className="flex min-h-0 flex-1 gap-4">
                  <ol className="w-[220px] shrink-0 space-y-0.5 overflow-y-auto">
                    {(activeReport.sections ?? [])
                      .slice()
                      .sort((a, b) => a.order - b.order)
                      .map((section) => {
                        const isActive = section.key === selectedSectionKey
                        return (
                          <li key={section.key}>
                            <button
                              type="button"
                              onClick={() => setSelectedSectionKey(section.key)}
                              className={`apple-focus-ring flex w-full flex-col rounded-md px-2 py-1.5 text-left transition ${
                                isActive
                                  ? 'bg-black/5'
                                  : 'hover:bg-black/[0.03]'
                              }`}
                            >
                              <span className="text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                                {section.order}. {section.title}
                              </span>
                              <span className="mt-0.5 text-[10px] tracking-[-0.01em] text-[#9b9ba1]">
                                {section.word_count} palavras
                                {section.status === 'sparse_data'
                                  ? ' · evidências fracas'
                                  : section.status === 'failed'
                                    ? ' · falhou'
                                    : ''}
                              </span>
                            </button>
                          </li>
                        )
                      })}
                  </ol>
                  <div className="flex min-h-0 flex-1 flex-col">
                    {selectedSection ? (
                      <SectionEditor
                        key={selectedSection.key}
                        section={selectedSection}
                        onSave={(content) =>
                          handleSaveSection(selectedSection.key, content)
                        }
                        onRegenerate={() =>
                          handleRegenerateSection(selectedSection.key)
                        }
                        isRegenerating={regeneratingKey === selectedSection.key}
                        handleRef={editorHandleRef}
                      />
                    ) : (
                      <p className="text-[13px] tracking-[-0.01em] text-[#9b9ba1]">
                        Selecione uma seção para editar.
                      </p>
                    )}
                  </div>
                </div>
              ) : activeTab === 'gri' ? (
                <div className="min-h-0 flex-1 overflow-y-auto pr-2">
                  <GriIndexTable entries={activeReport.gri_index} />
                </div>
              ) : (
                <div className="min-h-0 flex-1 overflow-y-auto pr-2">
                  {(activeReport.gaps?.length ?? 0) === 0 ? (
                    <p className="text-[13px] tracking-[-0.01em] text-[#9b9ba1]">
                      Nenhuma lacuna registrada nesta versão.
                    </p>
                  ) : (
                    <ul className="space-y-2">
                      {activeReport.gaps?.map((gap, index) => (
                        <li
                          key={`${gap.section_key}-${index}`}
                          className="rounded-[0.9rem] border border-black/6 bg-[#fbfbfc] px-3 py-2"
                        >
                          <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#9b9ba1]">
                            {gap.category}
                            {gap.section_key ? ` · ${gap.section_key}` : ''}
                          </p>
                          <p className="mt-1 text-[12px] leading-5 tracking-[-0.01em] text-[#3a3a3c]">
                            {gap.detail}
                          </p>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="flex h-full items-center justify-center text-center">
              <div className="max-w-[360px] space-y-3">
                <p className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                  Nenhum relatório ainda.
                </p>
                <p className="text-[12px] leading-5 tracking-[-0.01em] text-[#9b9ba1]">
                  Defina os temas materiais, carregue documentos nas pastas
                  correspondentes e clique em "Gerar Relatório" para produzir a
                  primeira versão preliminar.
                </p>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
