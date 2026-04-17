import { useCallback, useEffect, useMemo, useState } from 'react'
import { ExtractionSuggestionsPanel } from '../components/extraction-suggestions-panel'
import { PrimaryBtn } from '../components/primary-btn'
import { useExtractionSuggestions } from '../hooks/use-extraction-suggestions'
import {
  useProjectShellRegistration,
  useProjectWorkspace,
} from '../hooks/use-project-workspace'
import {
  fetchGriStandards,
  fetchOdsGoals,
  fetchProject,
  updateProject,
} from '../services/api-client'
import type { ExtractionSuggestion } from '../types/extraction'
import type {
  GriStandardRecord,
  MaterialTopic,
  MaterialTopicPillar,
  MaterialTopicPriority,
  OdsGoalRecord,
  SdgSelection,
} from '../types/project'

const PILLAR_LABELS: Record<MaterialTopicPillar, string> = {
  E: 'Ambiental (E)',
  S: 'Social (S)',
}

const PRIORITY_LEVELS: { key: MaterialTopicPriority; label: string }[] = [
  { key: 'alta', label: 'Alta' },
  { key: 'media', label: 'Média' },
  { key: 'baixa', label: 'Baixa' },
]

function familyToPillar(family: string): MaterialTopicPillar | null {
  if (family === '300') return 'E'
  if (family === '400') return 'S'
  return null
}

/** Returns the three-digit GRI topic number (e.g. "301" from "GRI 301-1"). */
function parseGriGroupNumber(code: string): string | null {
  const m = code.match(/^GRI\s+(\d{3})-\d+/i)
  return m ? m[1] : null
}

function compareDisclosureCodes(a: string, b: string): number {
  const ma = a.match(/^GRI\s+\d+-(\d+)/i)
  const mb = b.match(/^GRI\s+\d+-(\d+)/i)
  if (!ma || !mb) return a.localeCompare(b)
  return Number(ma[1]) - Number(mb[1])
}

type MaterialityTab = 'material' | 'ods'

type GriGroup = {
  groupNum: string
  label: string
  disclosures: GriStandardRecord[]
}

function buildGroups(
  standards: GriStandardRecord[],
  pillar: MaterialTopicPillar
): GriGroup[] {
  const filtered = standards.filter((s) => familyToPillar(s.family) === pillar)
  const byGroup = new Map<string, GriStandardRecord[]>()
  for (const s of filtered) {
    const gn = parseGriGroupNumber(s.code)
    if (!gn) continue
    if (!byGroup.has(gn)) byGroup.set(gn, [])
    byGroup.get(gn)!.push(s)
  }
  const sortedKeys = [...byGroup.keys()].sort((a, b) => Number(a) - Number(b))
  return sortedKeys.map((gn) => ({
    groupNum: gn,
    label: `GRI ${gn}`,
    disclosures: (byGroup.get(gn) ?? []).sort((a, b) =>
      compareDisclosureCodes(a.code, b.code)
    ),
  }))
}

function normalizeMaterialTopics(raw: unknown): MaterialTopic[] {
  if (!Array.isArray(raw)) {
    return []
  }
  const out: MaterialTopic[] = []
  for (const item of raw) {
    if (
      typeof item === 'object' &&
      item !== null &&
      'pillar' in item &&
      'topic' in item &&
      'priority' in item
    ) {
      const { pillar, topic, priority } = item as {
        pillar: unknown
        topic: unknown
        priority: unknown
      }
      if (
        (pillar === 'E' || pillar === 'S') &&
        typeof topic === 'string' &&
        (priority === 'alta' || priority === 'media' || priority === 'baixa')
      ) {
        out.push({
          pillar,
          topic: topic.trim(),
          priority,
        })
      }
    }
  }
  return out
}

function normalizeSdgGoals(raw: unknown): SdgSelection[] {
  if (!Array.isArray(raw)) {
    return []
  }
  const out: SdgSelection[] = []
  for (const item of raw) {
    if (
      typeof item === 'object' &&
      item !== null &&
      'ods_number' in item &&
      'objetivo' in item
    ) {
      const record = item as {
        ods_number: unknown
        objetivo: unknown
        acao?: unknown
        indicador?: unknown
        resultado?: unknown
      }
      if (
        typeof record.ods_number === 'number' &&
        typeof record.objetivo === 'string'
      ) {
        out.push({
          ods_number: record.ods_number,
          objetivo: record.objetivo,
          acao: typeof record.acao === 'string' ? record.acao : '',
          indicador:
            typeof record.indicador === 'string' ? record.indicador : '',
          resultado:
            typeof record.resultado === 'string' ? record.resultado : '',
        })
      }
    }
  }
  return out
}

export function ProjectMaterialityPage() {
  const { currentProjectId, project, setProject, workspaceError } =
    useProjectWorkspace()
  const [isExtractionPanelOpen, setIsExtractionPanelOpen] = useState(false)
  const extraction = useExtractionSuggestions(currentProjectId, {
    targetKind: ['material_topic', 'sdg_goal'],
  })

  const openExtractionPanel = useCallback(() => {
    setIsExtractionPanelOpen(true)
  }, [])

  const pageActions = useMemo(
    () => [
      {
        label: 'Auto-preencher com IA',
        icon: 'auto_awesome',
        variant: 'secondary' as const,
        onClick: openExtractionPanel,
      },
    ],
    [openExtractionPanel]
  )

  useProjectShellRegistration({
    activeSidebarKey: 'materiality',
    pageTitle: 'Materialidade & ODS',
    pageActions,
  })

  const [griStandards, setGriStandards] = useState<GriStandardRecord[]>([])
  const [odsGoals, setOdsGoals] = useState<OdsGoalRecord[]>([])
  const [topicSelections, setTopicSelections] = useState<MaterialTopic[]>([])
  const [sdgSelections, setSdgSelections] = useState<SdgSelection[]>([])
  const [activeTab, setActiveTab] = useState<MaterialityTab>('material')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    async function load() {
      setIsLoading(true)
      setPageError(null)
      try {
        const [standards, goals] = await Promise.all([
          fetchGriStandards(),
          fetchOdsGoals(),
        ])
        if (!active) return
        setGriStandards(standards)
        setOdsGoals(goals)
      } catch (error) {
        if (!active) return
        setPageError(
          error instanceof Error
            ? error.message
            : 'Não foi possível carregar os dados de referência.'
        )
      } finally {
        if (active) setIsLoading(false)
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!project) return
    let next = normalizeMaterialTopics(project.material_topics)
    if (griStandards.length > 0) {
      const valid = new Set(griStandards.map((s) => s.code))
      next = next.filter((t) => valid.has(t.topic))
    }
    setTopicSelections(next)
    setSdgSelections(normalizeSdgGoals(project.sdg_goals))
  }, [project, griStandards])

  const groupsByPillar = useMemo(
    () => ({
      E: buildGroups(griStandards, 'E'),
      S: buildGroups(griStandards, 'S'),
    }),
    [griStandards]
  )

  function isTopicSelected(pillar: MaterialTopicPillar, topic: string) {
    return topicSelections.some(
      (selection) => selection.pillar === pillar && selection.topic === topic
    )
  }

  function toggleTopic(pillar: MaterialTopicPillar, topic: string) {
    setTopicSelections((current) => {
      if (
        current.some(
          (selection) =>
            selection.pillar === pillar && selection.topic === topic
        )
      ) {
        return current.filter(
          (selection) =>
            !(selection.pillar === pillar && selection.topic === topic)
        )
      }
      return [...current, { pillar, topic, priority: 'media' }]
    })
  }

  function setPriorityLevel(
    pillar: MaterialTopicPillar,
    topic: string,
    priority: MaterialTopicPriority
  ) {
    setTopicSelections((current) =>
      current.map((selection) =>
        selection.pillar === pillar && selection.topic === topic
          ? { ...selection, priority }
          : selection
      )
    )
  }

  function isSdgSelected(odsNumber: number) {
    return sdgSelections.some((selection) => selection.ods_number === odsNumber)
  }

  function toggleSdg(goal: OdsGoalRecord) {
    setSdgSelections((current) => {
      if (
        current.some((selection) => selection.ods_number === goal.ods_number)
      ) {
        return current.filter(
          (selection) => selection.ods_number !== goal.ods_number
        )
      }
      return [
        ...current,
        {
          ods_number: goal.ods_number,
          objetivo: goal.objetivo,
          acao: '',
          indicador: '',
          resultado: '',
        },
      ]
    })
  }

  function updateSdgField(
    odsNumber: number,
    field: 'acao' | 'indicador' | 'resultado',
    value: string
  ) {
    setSdgSelections((current) =>
      current.map((selection) =>
        selection.ods_number === odsNumber
          ? { ...selection, [field]: value }
          : selection
      )
    )
  }

  async function handleSave() {
    if (!currentProjectId || isSaving) return
    setIsSaving(true)
    setPageError(null)
    setSaveMessage(null)
    try {
      const updated = await updateProject(currentProjectId, {
        material_topics: topicSelections.length > 0 ? topicSelections : null,
        sdg_goals: sdgSelections.length > 0 ? sdgSelections : null,
      })
      setProject(updated)
      setSaveMessage('Seleções salvas.')
    } catch (error) {
      setPageError(
        error instanceof Error
          ? error.message
          : 'Não foi possível salvar as seleções.'
      )
    } finally {
      setIsSaving(false)
    }
  }

  const refreshProjectAfterApply = useCallback(async () => {
    if (!currentProjectId) return
    try {
      const refreshed = await fetchProject(currentProjectId)
      setProject(refreshed)
    } catch {
      /* keep previous state on failure */
    }
  }, [currentProjectId, setProject])

  const handleAcceptSuggestion = useCallback(
    async (suggestion: ExtractionSuggestion) => {
      const updated = await extraction.updateSuggestion(suggestion.id, {
        action: 'accept',
      })
      if (updated) {
        await refreshProjectAfterApply()
      }
    },
    [extraction, refreshProjectAfterApply]
  )

  const handleRejectSuggestion = useCallback(
    async (suggestion: ExtractionSuggestion) => {
      await extraction.updateSuggestion(suggestion.id, { action: 'reject' })
    },
    [extraction]
  )

  const handleAcceptAll = useCallback(
    async (ids: string[]) => {
      const result = await extraction.bulkUpdate({
        ids,
        action: 'accept_all',
      })
      if (result && result.succeeded.length > 0) {
        await refreshProjectAfterApply()
      }
    },
    [extraction, refreshProjectAfterApply]
  )

  const handleRejectAll = useCallback(
    async (ids: string[]) => {
      await extraction.bulkUpdate({ ids, action: 'reject_all' })
    },
    [extraction]
  )

  const handleStartExtraction = useCallback(() => {
    void extraction.startRun('materiality')
  }, [extraction])

  return (
    <div className="flex h-full min-h-0 flex-col overflow-y-auto bg-white px-6 pt-6 pb-10 sm:px-10">
      {workspaceError || pageError ? (
        <div className="mb-4 rounded-lg border border-[#ffd0d0] bg-[#fff6f6] px-4 py-3 text-[12px] font-medium tracking-[-0.01em] text-[#d01f1f]">
          {workspaceError ?? pageError}
        </div>
      ) : null}

      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-[18px] font-medium tracking-[-0.015em] text-[#1d1d1f]">
            Materialidade & ODS
          </h2>
          <p className="mt-1 max-w-[620px] text-[13px] leading-6 tracking-[-0.01em] text-[#6b6b72]">
            Defina os disclosures GRI materiais
            {project ? ` de ${project.org_name}` : ''} e os Objetivos de
            Desenvolvimento Sustentável prioritários. Essas escolhas guiam a
            geração do relatório.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saveMessage ? (
            <span className="text-[12px] tracking-[-0.01em] text-[#2b8a3e]">
              {saveMessage}
            </span>
          ) : null}
          <PrimaryBtn
            type="button"
            onClick={() => {
              void handleSave()
            }}
            disabled={isSaving || isLoading || !currentProjectId}
            className="rounded-full px-4 py-2 text-[12px]"
          >
            {isSaving ? 'Salvando…' : 'Salvar'}
          </PrimaryBtn>
        </div>
      </header>

      {isLoading ? (
        <p className="text-[13px] tracking-[-0.01em] text-[#9b9ba1]">
          Carregando dados de referência…
        </p>
      ) : (
        <>
          <div
            className="mb-6 flex items-center gap-2 border-b border-black/6 pb-2"
            role="tablist"
            aria-label="Seções de materialidade"
          >
            {(['material', 'ods'] as const).map((tab) => {
              const label = tab === 'material' ? 'Temas materiais' : 'ODS'
              const isActive = activeTab === tab
              return (
                <button
                  key={tab}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  id={`materiality-tab-${tab}`}
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

          {activeTab === 'material' ? (
            <section
              className="mb-4"
              role="tabpanel"
              aria-labelledby="materiality-tab-material"
            >
              <h3 className="mb-3 text-[14px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                Temas materiais (GRI)
              </h3>
              <p className="mb-4 text-[12px] leading-5 tracking-[-0.01em] text-[#6b6b72]">
                Marque os disclosures que a organização reconhece como materiais
                e defina a prioridade como Alta, Média ou Baixa.
              </p>
              <div className="grid items-start gap-8 md:grid-cols-2">
                {(['E', 'S'] as MaterialTopicPillar[]).map((pillar) => (
                  <div key={pillar}>
                    <h4 className="mb-4 border-b border-black/5 pb-2 text-[12px] font-semibold uppercase tracking-[0.08em] text-[#6b6b72]">
                      {PILLAR_LABELS[pillar]}
                    </h4>
                    {groupsByPillar[pillar].length === 0 ? (
                      <p className="text-[12px] tracking-[-0.01em] text-[#9b9ba1]">
                        Nenhum disclosure disponível.
                      </p>
                    ) : (
                      <div className="space-y-6">
                        {groupsByPillar[pillar].map((group) => (
                          <div
                            key={`${pillar}-${group.groupNum}`}
                            className="border-b border-black/5 pb-5 last:border-b-0 last:pb-0"
                          >
                            <p className="mb-2 text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                              {group.label}
                            </p>
                            <ul className="space-y-3">
                              {group.disclosures.map((row) => {
                                const selected = isTopicSelected(
                                  pillar,
                                  row.code
                                )
                                const selection = topicSelections.find(
                                  (sel) =>
                                    sel.pillar === pillar &&
                                    sel.topic === row.code
                                )
                                const rowInputId = `${pillar}-${row.code.replace(/\s+/g, '-')}`
                                return (
                                  <li key={row.code} className="flex gap-2">
                                    <input
                                      id={rowInputId}
                                      type="checkbox"
                                      checked={selected}
                                      onChange={() =>
                                        toggleTopic(pillar, row.code)
                                      }
                                      className="mt-1 h-4 w-4 shrink-0 accent-[#0673e0]"
                                      aria-label={row.code}
                                    />
                                    <div className="min-w-0 flex-1">
                                      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                                        <label
                                          htmlFor={rowInputId}
                                          className="cursor-pointer text-[13px] font-semibold tracking-[-0.01em] text-[#1d1d1f]"
                                        >
                                          {row.code}
                                        </label>
                                        {selected && selection ? (
                                          <div className="flex shrink-0 flex-wrap justify-end gap-1.5">
                                            {PRIORITY_LEVELS.map(
                                              ({ key, label }) => (
                                                <button
                                                  key={key}
                                                  type="button"
                                                  onClick={() =>
                                                    setPriorityLevel(
                                                      pillar,
                                                      row.code,
                                                      key
                                                    )
                                                  }
                                                  className={[
                                                    'apple-focus-ring rounded-full border px-2.5 py-1 text-[11px] font-medium tracking-[-0.01em] transition',
                                                    selection.priority === key
                                                      ? 'border-[#0673e0] bg-[#0673e0] text-white'
                                                      : 'border-black/10 bg-white text-[#1d1d1f] hover:border-black/20',
                                                  ].join(' ')}
                                                >
                                                  {label}
                                                </button>
                                              )
                                            )}
                                          </div>
                                        ) : null}
                                      </div>
                                      <p className="mt-0.5 text-[12px] font-normal leading-snug tracking-[-0.01em] text-[#86868b]">
                                        {row.standard_text}
                                      </p>
                                    </div>
                                  </li>
                                )
                              })}
                            </ul>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          ) : (
            <section role="tabpanel" aria-labelledby="materiality-tab-ods">
              <h3 className="mb-3 text-[14px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                Objetivos de Desenvolvimento Sustentável (ODS) Prioritários
              </h3>
              <p className="mb-4 text-[12px] leading-5 tracking-[-0.01em] text-[#6b6b72]">
                Selecione os ODS aos quais a organização se alinha
                estrategicamente e descreva brevemente ações, indicadores e
                resultados.
              </p>
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {odsGoals.map((goal) => {
                  const selected = isSdgSelected(goal.ods_number)
                  const selection = sdgSelections.find(
                    (sel) => sel.ods_number === goal.ods_number
                  )
                  return (
                    <article
                      key={goal.ods_number}
                      className={`rounded-[1rem] border p-4 transition ${
                        selected
                          ? 'border-[#0673e0] bg-[#f4f8fd]'
                          : 'border-black/8 bg-[#fbfbfc] hover:border-black/15'
                      }`}
                    >
                      <label className="flex cursor-pointer items-start gap-2">
                        <input
                          type="checkbox"
                          checked={selected}
                          onChange={() => toggleSdg(goal)}
                          className="mt-1 h-4 w-4 accent-[#0673e0]"
                        />
                        <span className="flex-1">
                          <span className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-[#6b6b72]">
                            ODS {goal.ods_number}
                          </span>
                          <span className="mt-0.5 block text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                            {goal.objetivo}
                          </span>
                        </span>
                      </label>
                      {selected && selection ? (
                        <div className="mt-3 space-y-2 text-[12px] tracking-[-0.01em] text-[#1d1d1f]">
                          {(
                            [
                              ['acao', 'Ação'],
                              ['indicador', 'Indicador'],
                              ['resultado', 'Resultado'],
                            ] as const
                          ).map(([field, label]) => (
                            <label key={field} className="block">
                              <span className="mb-1 block text-[10px] font-medium uppercase tracking-[0.08em] text-[#6b6b72]">
                                {label}
                              </span>
                              <textarea
                                value={selection[field]}
                                onChange={(event) =>
                                  updateSdgField(
                                    goal.ods_number,
                                    field,
                                    event.target.value
                                  )
                                }
                                rows={2}
                                className="apple-focus-ring w-full resize-none rounded-md border border-black/10 bg-white px-2 py-1.5 text-[12px] tracking-[-0.01em] text-[#1d1d1f] placeholder:text-[#9b9ba1]"
                                placeholder={`Descreva ${label.toLowerCase()}…`}
                              />
                            </label>
                          ))}
                        </div>
                      ) : null}
                    </article>
                  )
                })}
              </div>
            </section>
          )}
        </>
      )}
      <ExtractionSuggestionsPanel
        isOpen={isExtractionPanelOpen}
        onClose={() => setIsExtractionPanelOpen(false)}
        title="Sugestões de Materialidade & ODS"
        suggestions={extraction.suggestions}
        isStreaming={extraction.isStreaming}
        isLoading={extraction.isLoading}
        error={extraction.error}
        onAccept={handleAcceptSuggestion}
        onReject={handleRejectSuggestion}
        onAcceptAll={handleAcceptAll}
        onRejectAll={handleRejectAll}
        onStart={handleStartExtraction}
      />
    </div>
  )
}
