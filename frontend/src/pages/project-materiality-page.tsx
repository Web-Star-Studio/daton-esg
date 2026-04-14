import { useEffect, useMemo, useState } from 'react'
import {
  useProjectShellRegistration,
  useProjectWorkspace,
} from '../hooks/use-project-workspace'
import {
  fetchIndicatorTemplates,
  fetchOdsGoals,
  updateProject,
} from '../services/api-client'
import type {
  IndicatorTemplateRecord,
  MaterialTopic,
  MaterialTopicPillar,
  OdsGoalRecord,
  SdgSelection,
} from '../types/project'

const PILLAR_LABELS: Record<MaterialTopicPillar, string> = {
  E: 'Ambiental (E)',
  S: 'Social (S)',
  G: 'Governança (G)',
}

// Map indicator `tema` (from the seed Indicadores ESG sheet) to an ESG pillar.
// Keys must match values seeded in indicator_templates.tema.
const TEMA_TO_PILLAR: Record<string, MaterialTopicPillar> = {
  'Clima e Energia': 'E',
  Água: 'E',
  'Resíduos': 'E',
  'Capital Humano': 'S',
  'Saúde e Segurança do Trabalho': 'S',
  'Desempenho Econômico': 'G',
  'Governança / Ética': 'G',
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
        (pillar === 'E' || pillar === 'S' || pillar === 'G') &&
        typeof topic === 'string' &&
        typeof priority === 'number'
      ) {
        out.push({ pillar, topic, priority })
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

type PillarTopic = {
  pillar: MaterialTopicPillar
  topic: string
}

export function ProjectMaterialityPage() {
  const { currentProjectId, project, setProject, workspaceError } =
    useProjectWorkspace()

  useProjectShellRegistration({
    activeSidebarKey: 'materiality',
    pageTitle: 'Materialidade & ODS',
  })

  const [indicatorTemplates, setIndicatorTemplates] = useState<
    IndicatorTemplateRecord[]
  >([])
  const [odsGoals, setOdsGoals] = useState<OdsGoalRecord[]>([])
  const [topicSelections, setTopicSelections] = useState<MaterialTopic[]>([])
  const [sdgSelections, setSdgSelections] = useState<SdgSelection[]>([])
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
        const [indicators, goals] = await Promise.all([
          fetchIndicatorTemplates(),
          fetchOdsGoals(),
        ])
        if (!active) return
        setIndicatorTemplates(indicators)
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
    setTopicSelections(normalizeMaterialTopics(project.material_topics))
    setSdgSelections(normalizeSdgGoals(project.sdg_goals))
  }, [project])

  const pillarTopics = useMemo<Record<MaterialTopicPillar, PillarTopic[]>>(
    () => {
      const grouped: Record<MaterialTopicPillar, PillarTopic[]> = {
        E: [],
        S: [],
        G: [],
      }
      for (const template of indicatorTemplates) {
        const pillar = TEMA_TO_PILLAR[template.tema]
        if (!pillar) continue
        const already = grouped[pillar].some(
          (entry) => entry.topic === template.tema
        )
        if (!already) {
          grouped[pillar].push({ pillar, topic: template.tema })
        }
      }
      return grouped
    },
    [indicatorTemplates]
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
          (selection) => selection.pillar === pillar && selection.topic === topic
        )
      ) {
        return current.filter(
          (selection) =>
            !(selection.pillar === pillar && selection.topic === topic)
        )
      }
      return [...current, { pillar, topic, priority: 3 }]
    })
  }

  function updatePriority(
    pillar: MaterialTopicPillar,
    topic: string,
    priority: number
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
      if (current.some((selection) => selection.ods_number === goal.ods_number)) {
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
        material_topics: topicSelections,
        sdg_goals: sdgSelections,
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
            Defina os temas materiais{project ? ` de ${project.org_name}` : ''}{' '}
            e os Objetivos de Desenvolvimento Sustentável prioritários. Essas
            escolhas guiam a geração do relatório.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saveMessage ? (
            <span className="text-[12px] tracking-[-0.01em] text-[#2b8a3e]">
              {saveMessage}
            </span>
          ) : null}
          <button
            type="button"
            onClick={() => {
              void handleSave()
            }}
            disabled={isSaving || isLoading || !currentProjectId}
            className="apple-focus-ring rounded-full bg-[#0f1923] px-4 py-2 text-[12px] font-medium text-white transition hover:bg-[#1a2632] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSaving ? 'Salvando…' : 'Salvar'}
          </button>
        </div>
      </header>

      {isLoading ? (
        <p className="text-[13px] tracking-[-0.01em] text-[#9b9ba1]">
          Carregando dados de referência…
        </p>
      ) : (
        <>
          <section className="mb-10">
            <h3 className="mb-3 text-[14px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
              Temas Materiais
            </h3>
            <p className="mb-4 text-[12px] leading-5 tracking-[-0.01em] text-[#6b6b72]">
              Marque os temas que a organização reconhece como materiais e
              atribua uma prioridade de 1 a 5.
            </p>
            <div className="grid gap-4 md:grid-cols-3">
              {(['E', 'S', 'G'] as MaterialTopicPillar[]).map((pillar) => (
                <div
                  key={pillar}
                  className="rounded-[1rem] border border-black/8 bg-[#fbfbfc] p-4"
                >
                  <h4 className="mb-3 text-[12px] font-semibold uppercase tracking-[0.08em] text-[#6b6b72]">
                    {PILLAR_LABELS[pillar]}
                  </h4>
                  <ul className="space-y-2">
                    {pillarTopics[pillar].length === 0 ? (
                      <li className="text-[12px] tracking-[-0.01em] text-[#9b9ba1]">
                        Nenhum tema disponível.
                      </li>
                    ) : null}
                    {pillarTopics[pillar].map((entry) => {
                      const selected = isTopicSelected(pillar, entry.topic)
                      const selection = topicSelections.find(
                        (sel) =>
                          sel.pillar === pillar && sel.topic === entry.topic
                      )
                      return (
                        <li key={`${pillar}-${entry.topic}`}>
                          <label className="flex cursor-pointer items-center gap-2 rounded-md px-1 py-1 text-[13px] tracking-[-0.01em] text-[#1d1d1f] hover:bg-black/[0.03]">
                            <input
                              type="checkbox"
                              checked={selected}
                              onChange={() => toggleTopic(pillar, entry.topic)}
                              className="h-4 w-4 accent-[#0673e0]"
                            />
                            <span className="flex-1">{entry.topic}</span>
                          </label>
                          {selected && selection ? (
                            <div className="ml-6 mt-1 flex items-center gap-2 text-[11px] text-[#6b6b72]">
                              <span>Prioridade</span>
                              <input
                                type="range"
                                min={1}
                                max={5}
                                value={selection.priority}
                                onChange={(event) =>
                                  updatePriority(
                                    pillar,
                                    entry.topic,
                                    Number(event.target.value)
                                  )
                                }
                                className="flex-1 accent-[#0673e0]"
                                aria-label={`Prioridade de ${entry.topic}`}
                              />
                              <span className="w-4 text-right font-medium text-[#1d1d1f]">
                                {selection.priority}
                              </span>
                            </div>
                          ) : null}
                        </li>
                      )
                    })}
                  </ul>
                </div>
              ))}
            </div>
          </section>

          <section>
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
        </>
      )}
    </div>
  )
}
