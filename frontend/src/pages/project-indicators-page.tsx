import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  useProjectShellRegistration,
  useProjectWorkspace,
} from '../hooks/use-project-workspace'
import { fetchIndicatorTemplates, updateProject } from '../services/api-client'
import type { IndicatorTemplateRecord, IndicatorValue } from '../types/project'

// ---------------------------------------------------------------------------
// Theme → pillar mapping (for color dots)
// ---------------------------------------------------------------------------

type Pillar = 'E' | 'S' | 'G'

const TEMA_TO_PILLAR: Record<string, Pillar> = {
  'Clima e Energia': 'E',
  Água: 'E',
  Resíduos: 'E',
  'Saúde e Segurança do Trabalho': 'S',
  'Capital Humano': 'S',
  'Governança / Ética': 'G',
  'Desempenho Econômico': 'G',
}

const PILLAR_COLORS: Record<Pillar, string> = {
  E: 'bg-emerald-500',
  S: 'bg-blue-500',
  G: 'bg-violet-500',
}

// ---------------------------------------------------------------------------
// Help text catalog — definitions, data sources, formulas
// ---------------------------------------------------------------------------

type HelpEntry = { definicao: string; fontes?: string; calculo?: string }

const INDICATOR_HELP: Record<string, HelpEntry> = {
  'Consumo total de energia': {
    definicao:
      'Quantidade total de energia elétrica e térmica consumida pela organização (12 meses), discriminando fontes renováveis e não renováveis.',
    fontes:
      'Contas de energia elétrica, registros de consumo de combustíveis (NFs, planilhas de frota/caldeiras), relatórios internos de eficiência energética.',
    calculo:
      'Energia total = Eletricidade (kWh) + \u03A3(Combustível \u00D7 Fator de conversão). Conversão: 1 L diesel \u2248 10,8 kWh (IPCC/MCTI).',
  },
  'Intensidade energética': {
    definicao:
      'Relação entre o consumo total de energia e a produção física ou de serviço (toneladas processadas, unidades fabricadas, km percorridos etc.).',
    calculo: 'Intensidade = Consumo total de energia / Produção total.',
  },
  'Emissões GEE – Scope 1': {
    definicao:
      'Emissões diretas de GEE de fontes próprias ou controladas (combustíveis, frotas, processos industriais).',
    fontes:
      'Inventário GHG Protocol, fatores de emissão (MCTI, IPCC, DEFRA), consumos de combustíveis.',
    calculo:
      'Escopo 1 = \u03A3(Combustível consumido \u00D7 Fator de emissão).',
  },
  'Emissões GEE – Scope 2': {
    definicao:
      'Emissões indiretas de GEE provenientes da eletricidade comprada.',
    calculo:
      'Escopo 2 = Eletricidade consumida (kWh) \u00D7 Fator de emissão da rede.',
  },
  'Emissões GEE – Scope 3': {
    definicao:
      'Outras emissões indiretas (transporte terceirizado, resíduos, viagens corporativas).',
    calculo:
      'Escopo 3 = \u03A3(Atividade \u00D7 Fator de emissão por categoria).',
  },
  'Metas de redução de GEE': {
    definicao: 'Percentual de redução de emissões em relação ao ano-base.',
    calculo:
      'Redução (%) = (Emissões ano-base \u2212 Emissões ano atual) / Emissões ano-base \u00D7 100.',
  },
  'Consumo total de água': {
    definicao:
      'Volume total de água captada de todas as fontes (rede pública, poços, rios, reuso).',
    fontes:
      'Contas de abastecimento, hidrômetros, relatórios de poço artesiano, registros internos.',
    calculo: 'Consumo total = \u03A3 volume por fonte.',
  },
  'Intensidade hídrica': {
    definicao: 'Relação entre consumo total de água e a produção.',
    calculo: 'Intensidade = Consumo total de água / Produção total.',
  },
  'Percentual de água reutilizada': {
    definicao: 'Proporção de água reutilizada em relação ao consumo total.',
    calculo: '% Reuso = (Volume reutilizado / Consumo total) \u00D7 100.',
  },
  'Total de resíduos gerados': {
    definicao: 'Massa total de resíduos gerados pela operação no período.',
    fontes:
      'MTRs (Manifesto de Transporte de Resíduos), notas fiscais de destinação, relatórios de coleta seletiva.',
    calculo: 'Total = \u03A3 massa por tipo de resíduo.',
  },
  'Percentual reciclado': {
    definicao: 'Proporção de resíduos destinados à reciclagem.',
    calculo:
      '% Reciclagem = (Resíduos reciclados / Total de resíduos) \u00D7 100.',
  },
  'Percentual destinado ao reuso': {
    definicao: 'Proporção de resíduos destinados ao reuso.',
    calculo:
      '% Reuso = (Resíduos reutilizados / Total de resíduos) \u00D7 100.',
  },
  'Percentual destinado ao aterro/incineração': {
    definicao:
      'Proporção de resíduos destinados a aterro sanitário ou incineração.',
    calculo:
      '% Aterro/Incineração = (Resíduos em aterro + incinerados) / Total \u00D7 100.',
  },
  'Taxa de frequência de acidentes (LTIFR)': {
    definicao:
      'Número de acidentes com afastamento por milhão de horas trabalhadas.',
    fontes: 'Registros de CAT, SESMT, CIPA.',
    calculo:
      'LTIFR = (N\u00BA de acidentes com afastamento / Horas-homem trabalhadas) \u00D7 1.000.000.',
  },
  'Dias perdidos por acidentes': {
    definicao:
      'Total de dias de trabalho perdidos em decorrência de acidentes ocupacionais.',
    calculo: 'Soma dos dias de afastamento registrados no período.',
  },
  'Número de acidentes com afastamento': {
    definicao:
      'Quantidade absoluta de acidentes que geraram afastamento do trabalho.',
    fontes:
      'Registros de CAT (Comunicação de Acidente de Trabalho), SESMT, CIPA.',
  },
  'Média de horas de treinamento por colaborador': {
    definicao:
      'Total de horas de treinamento dividido pelo número de colaboradores.',
    calculo:
      'Média = Total de horas de treinamento / N\u00BA total de colaboradores.',
  },
  'Percentual de diversidade – Diretoria': {
    definicao: 'Proporção de grupos sub-representados no nível de diretoria.',
    calculo:
      '% = (Colaboradores de grupos sub-representados na diretoria / Total na diretoria) \u00D7 100.',
  },
  'Percentual de diversidade – Gerência': {
    definicao: 'Proporção de grupos sub-representados no nível de gerência.',
    calculo:
      '% = (Colaboradores de grupos sub-representados na gerência / Total na gerência) \u00D7 100.',
  },
  'Percentual de diversidade – Operacional': {
    definicao: 'Proporção de grupos sub-representados no nível operacional.',
    calculo:
      '% = (Colaboradores de grupos sub-representados no operacional / Total no operacional) \u00D7 100.',
  },
  'Número de denúncias recebidas': {
    definicao:
      'Quantidade de denúncias recebidas via canal de ética, ouvidoria ou compliance.',
    fontes: 'Relatórios de Compliance, canal de ética, ouvidoria.',
  },
  'Número de denúncias resolvidas': {
    definicao: 'Quantidade de denúncias encerradas/resolvidas no período.',
    calculo:
      '% Resolução = (Denúncias resolvidas / Denúncias recebidas) \u00D7 100.',
  },
  'Investimentos em projetos sustentáveis (CAPEX/OPEX)': {
    definicao:
      'Total de CAPEX e OPEX destinados a projetos com benefícios ambientais ou sociais.',
    fontes: 'Controladoria, Planejamento, Contabilidade.',
    calculo: 'Total = CAPEX sustentável + OPEX sustentável.',
  },
  'Receita proveniente de produtos/serviços sustentáveis': {
    definicao:
      'Receita gerada por produtos ou serviços classificados como sustentáveis (ex: energia limpa, produtos reciclados, economia circular).',
    calculo:
      'Receita sustentável / Receita total \u00D7 100 (para percentual).',
  },
  'Valor econômico gerado e distribuído': {
    definicao:
      'Valor econômico total gerado pela organização e sua distribuição entre stakeholders.',
    calculo:
      'VEG&D = Receita Líquida \u2212 Custos Operacionais + Pagamentos e Investimentos Sociais. Componentes: receitas, custos operacionais, salários e benefícios, pagamentos a financiadores e governos, investimentos na comunidade.',
  },
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ProjectIndicatorsPage() {
  const { currentProjectId, project, setProject, workspaceError } =
    useProjectWorkspace()

  useProjectShellRegistration({
    activeSidebarKey: 'indicators',
    pageTitle: 'Indicadores',
  })

  const [templates, setTemplates] = useState<IndicatorTemplateRecord[]>([])
  const [values, setValues] = useState<Record<string, string>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  const [collapsedTemas, setCollapsedTemas] = useState<Set<string> | null>(null)

  // Load indicator templates
  useEffect(() => {
    let active = true
    async function load() {
      setIsLoading(true)
      setPageError(null)
      try {
        const data = await fetchIndicatorTemplates()
        if (!active) return
        setTemplates(data)
      } catch (error) {
        if (!active) return
        setPageError(
          error instanceof Error
            ? error.message
            : 'Não foi possível carregar os indicadores.'
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

  // Populate form from project.indicator_values
  useEffect(() => {
    if (!project) return
    const saved = project.indicator_values
    if (!Array.isArray(saved)) {
      setValues({})
      return
    }
    const map: Record<string, string> = {}
    for (const entry of saved) {
      if (
        typeof entry === 'object' &&
        entry !== null &&
        'indicador' in entry &&
        'value' in entry
      ) {
        const key = (entry as { indicador: string }).indicador
        map[key] = String((entry as { value: string }).value)
      }
    }
    setValues(map)
  }, [project])

  const grouped = useMemo(() => {
    const groups: Record<string, IndicatorTemplateRecord[]> = {}
    for (const t of templates) {
      if (!groups[t.tema]) groups[t.tema] = []
      groups[t.tema].push(t)
    }
    return groups
  }, [templates])

  const temas = useMemo(() => Object.keys(grouped), [grouped])

  // Start with all themes collapsed once templates are loaded
  useEffect(() => {
    if (temas.length > 0 && collapsedTemas === null) {
      setCollapsedTemas(new Set(temas))
    }
  }, [temas, collapsedTemas])

  const updateValue = useCallback((indicador: string, value: string) => {
    setValues((prev) => ({ ...prev, [indicador]: value }))
    setSaveMessage(null)
  }, [])

  const toggleTema = useCallback((tema: string) => {
    setCollapsedTemas((prev) => {
      const next = new Set(prev)
      if (next.has(tema)) next.delete(tema)
      else next.add(tema)
      return next
    })
  }, [])

  async function handleSave() {
    if (!currentProjectId || isSaving) return
    setIsSaving(true)
    setPageError(null)
    setSaveMessage(null)
    try {
      const indicatorValues: IndicatorValue[] = []
      for (const [tema, items] of Object.entries(grouped)) {
        for (const item of items) {
          const val = values[item.indicador]?.trim()
          if (val) {
            indicatorValues.push({
              tema,
              indicador: item.indicador,
              unidade: item.unidade,
              value: val,
            })
          }
        }
      }
      const updated = await updateProject(currentProjectId, {
        indicator_values: indicatorValues.length > 0 ? indicatorValues : null,
      })
      setProject(updated)
      setSaveMessage('Indicadores salvos.')
    } catch (error) {
      setPageError(
        error instanceof Error
          ? error.message
          : 'Não foi possível salvar os indicadores.'
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
            Indicadores ESG
          </h2>
          <p className="mt-1 max-w-[620px] text-[13px] leading-6 tracking-[-0.01em] text-[#6b6b72]">
            Preencha os indicadores quantitativos disponíveis
            {project ? ` de ${project.org_name}` : ''}. Esses dados alimentam
            diretamente a geração do relatório.
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
            onClick={() => void handleSave()}
            disabled={isSaving || isLoading || !currentProjectId}
            className="apple-focus-ring rounded-full bg-[#0f1923] px-4 py-2 text-[12px] font-medium text-white transition hover:bg-[#1a2632] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSaving ? 'Salvando…' : 'Salvar'}
          </button>
        </div>
      </header>

      {isLoading ? (
        <p className="text-[13px] tracking-[-0.01em] text-[#9b9ba1]">
          Carregando indicadores…
        </p>
      ) : (
        <div className="space-y-8">
          {temas.map((tema) => {
            const pillar = TEMA_TO_PILLAR[tema] ?? 'E'
            const color = PILLAR_COLORS[pillar]
            const items = grouped[tema]
            const isCollapsed = collapsedTemas?.has(tema) ?? true
            return (
              <section key={tema}>
                <button
                  type="button"
                  onClick={() => toggleTema(tema)}
                  className="mb-3 flex w-full items-center gap-2 text-left"
                >
                  <span
                    aria-hidden="true"
                    className={`size-2 shrink-0 rounded-full ${color}`}
                  />
                  <h3 className="flex-1 text-[14px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                    {tema}
                    <span className="ml-2 text-[12px] font-normal text-[#86868b]">
                      {items.filter((i) => values[i.indicador]?.trim()).length}/
                      {items.length}
                    </span>
                  </h3>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                    className={`size-4 shrink-0 text-[#86868b] transition-transform duration-150 ${isCollapsed ? '' : 'rotate-180'}`}
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M4.22 6.22a.75.75 0 0 1 1.06 0L8 8.94l2.72-2.72a.75.75 0 1 1 1.06 1.06l-3.25 3.25a.75.75 0 0 1-1.06 0L4.22 7.28a.75.75 0 0 1 0-1.06Z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
                {!isCollapsed && (
                  <div className="flex flex-col gap-0.5">
                    {items.map((item) => {
                      const help = INDICATOR_HELP[item.indicador]
                      const currentValue = values[item.indicador]?.trim()
                      return (
                        <div
                          key={item.indicador}
                          className="group rounded-xl px-5 py-3 transition-colors hover:bg-[#e8e8ed]/40"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex min-w-0 flex-1 flex-col">
                              <label
                                htmlFor={`ind-${item.indicador}`}
                                className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]"
                              >
                                {item.indicador}
                              </label>
                            </div>
                            <div className="flex items-center gap-3">
                              <input
                                id={`ind-${item.indicador}`}
                                type="text"
                                value={values[item.indicador] ?? ''}
                                onChange={(e) =>
                                  updateValue(item.indicador, e.target.value)
                                }
                                placeholder="—"
                                className="apple-focus-ring w-36 rounded border-0 bg-[#e8e8ed] px-4 py-1.5 text-right text-[13px] font-semibold text-[#1d1d1f] transition-all focus:ring-2 focus:ring-primary/20"
                              />
                              <span className="w-20 text-[12px] font-medium text-[#86868b]">
                                {item.unidade}
                              </span>
                            </div>
                          </div>
                          {help ? (
                            <div className="mt-2 rounded-lg border border-black/5 bg-[#f9f9fb] px-4 py-3 text-[12px] leading-5 tracking-[-0.01em] text-[#6b6b72]">
                              <p>
                                <span className="font-medium text-[#3a3a3c]">
                                  Definição:{' '}
                                </span>
                                {help.definicao}
                              </p>
                              {help.fontes ? (
                                <p className="mt-1">
                                  <span className="font-medium text-[#3a3a3c]">
                                    Fontes:{' '}
                                  </span>
                                  {help.fontes}
                                </p>
                              ) : null}
                              {help.calculo ? (
                                <p className="mt-1">
                                  <span className="font-medium text-[#3a3a3c]">
                                    Cálculo:{' '}
                                  </span>
                                  {help.calculo}
                                </p>
                              ) : null}
                              {currentValue ? (
                                <p className="mt-1.5 border-t border-black/5 pt-1.5">
                                  <span className="font-medium text-[#1d1d1f]">
                                    Valor informado:{' '}
                                  </span>
                                  <span className="font-semibold text-[#1d1d1f]">
                                    {currentValue}
                                  </span>
                                  {item.unidade ? (
                                    <span className="ml-1 text-[#86868b]">
                                      {item.unidade}
                                    </span>
                                  ) : null}
                                </p>
                              ) : null}
                            </div>
                          ) : null}
                        </div>
                      )
                    })}
                  </div>
                )}
              </section>
            )
          })}
        </div>
      )}
    </div>
  )
}
