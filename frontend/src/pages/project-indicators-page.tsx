import { useCallback, useEffect, useMemo, useState } from 'react'
import { PrimaryBtn } from '../components/primary-btn'
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
// Covers the v2 GRI-aligned catalog. Entries are keyed by `indicador`.
// ---------------------------------------------------------------------------

type HelpEntry = { definicao: string; fontes?: string; calculo?: string }

const INDICATOR_HELP: Record<string, HelpEntry> = {
  'Energia consumida — renovável': {
    definicao:
      'Energia (elétrica + térmica) consumida proveniente de fontes renováveis, conforme GRI 302-1.',
    fontes:
      'Contas de energia (com certificação I-REC/REC), registros de geração própria, PPA renovável.',
  },
  'Energia consumida — não-renovável': {
    definicao:
      'Energia consumida oriunda de fontes não-renováveis (combustíveis fósseis, rede convencional), conforme GRI 302-1.',
    fontes:
      'Contas de energia convencional, notas fiscais de combustíveis, registros de frota/caldeiras.',
    calculo:
      '\u03A3(Combustível \u00D7 Fator de conversão). Conversão: 1 L diesel \u2248 10,8 kWh (IPCC/MCTI).',
  },
  'Intensidade energética': {
    definicao:
      'Relação entre o consumo total de energia e a produção física ou de serviço (GRI 302-3).',
    calculo: 'Intensidade = Consumo total de energia / Produção total.',
  },
  'Emissões GEE — Escopo 1': {
    definicao:
      'Emissões diretas de GEE de fontes próprias ou controladas (GRI 305-1).',
    fontes:
      'Inventário GHG Protocol, fatores de emissão (MCTI, IPCC, DEFRA), consumos de combustíveis.',
    calculo:
      'Escopo 1 = \u03A3(Combustível consumido \u00D7 Fator de emissão).',
  },
  'Emissões GEE — Escopo 2': {
    definicao:
      'Emissões indiretas de GEE provenientes da eletricidade comprada (GRI 305-2).',
    calculo:
      'Escopo 2 = Eletricidade consumida (kWh) \u00D7 Fator de emissão da rede.',
  },
  'Emissões GEE — Escopo 3': {
    definicao:
      'Outras emissões indiretas — transporte terceirizado, resíduos, viagens corporativas (GRI 305-3).',
    calculo:
      'Escopo 3 = \u03A3(Atividade \u00D7 Fator de emissão por categoria).',
  },
  'Meta de redução de GEE': {
    definicao:
      'Percentual de redução de emissões em relação ao ano-base (GRI 305-5).',
    calculo:
      'Redução (%) = (Emissões ano-base \u2212 Emissões ano atual) / Emissões ano-base \u00D7 100.',
  },
  'Água captada — superficial': {
    definicao:
      'Volume de água captado de corpos d\u2019água superficiais (rios, lagos, barragens), conforme GRI 303-3.',
  },
  'Água captada — subterrânea': {
    definicao:
      'Volume captado de poços, aquíferos e águas subterrâneas (GRI 303-3).',
  },
  'Água captada — rede pública': {
    definicao:
      'Volume recebido de concessionária pública de abastecimento (GRI 303-3).',
    fontes: 'Contas de abastecimento, hidrômetros.',
  },
  'Água captada — água do mar': {
    definicao:
      'Volume captado do mar, para uso direto ou após dessalinização (GRI 303-3).',
  },
  'Água captada — produzida/terceiros': {
    definicao:
      'Água de processos (ex.: petróleo) ou recebida de terceiros (GRI 303-3).',
  },
  'Água descartada': {
    definicao:
      'Volume total de efluentes descartados em corpos d\u2019água, solo ou rede pública após tratamento (GRI 303-4).',
  },
  'Consumo de água': {
    definicao:
      'Volume efetivamente consumido pela operação (captado \u2212 descartado), conforme GRI 303-5.',
  },
  'Água reutilizada': {
    definicao:
      'Volume de água reutilizada em ciclos produtivos da organização (GRI 303-3 — informação adicional).',
  },
  'Intensidade hídrica': {
    definicao: 'Relação entre consumo de água e a produção (GRI 303-5).',
    calculo: 'Intensidade = Consumo de água / Produção total.',
  },
  'Resíduos — reciclagem': {
    definicao:
      'Massa de resíduos destinada à reciclagem por terceiros (GRI 306-4).',
    fontes:
      'MTRs (Manifesto de Transporte de Resíduos), notas fiscais de destinação.',
  },
  'Resíduos — reuso': {
    definicao:
      'Massa de resíduos reutilizada interna ou externamente (GRI 306-4).',
  },
  'Resíduos — compostagem': {
    definicao:
      'Massa de resíduos orgânicos destinados à compostagem (GRI 306-4).',
  },
  'Resíduos — incineração com recuperação': {
    definicao:
      'Massa incinerada com recuperação energética (GRI 306-4 — desvio de disposição).',
  },
  'Resíduos — incineração sem recuperação': {
    definicao:
      'Massa incinerada sem recuperação energética (GRI 306-5 — disposição).',
  },
  'Resíduos — aterro': {
    definicao: 'Massa destinada a aterro sanitário ou industrial (GRI 306-5).',
  },
  'Resíduos — outros destinos': {
    definicao: 'Outras formas de disposição final não elencadas (GRI 306-5).',
  },
  'Horas-homem trabalhadas': {
    definicao:
      'Total de horas trabalhadas pela força de trabalho no período — base de cálculo para taxas de acidentes (GRI 403-9).',
  },
  'Acidentes com afastamento': {
    definicao:
      'Quantidade absoluta de acidentes de trabalho que resultaram em afastamento (GRI 403-9).',
    fontes: 'CAT (Comunicação de Acidente de Trabalho), SESMT, CIPA.',
  },
  'Dias perdidos por acidentes': {
    definicao:
      'Total de dias de trabalho perdidos em decorrência de acidentes ocupacionais (GRI 403-9).',
  },
  'Taxa de frequência de acidentes (LTIFR)': {
    definicao:
      'Número de acidentes com afastamento por milhão de horas trabalhadas (GRI 403-9).',
    calculo:
      'LTIFR = (Acidentes com afastamento / Horas-homem trabalhadas) \u00D7 1.000.000.',
  },
  'Fatalidades relacionadas ao trabalho': {
    definicao:
      'Número absoluto de fatalidades decorrentes de lesões ou doenças relacionadas ao trabalho (GRI 403-9).',
  },
  'Taxa de fatalidades': {
    definicao:
      'Taxa de fatalidades por milhão de horas-homem trabalhadas (GRI 403-9).',
    calculo: 'Taxa = (Fatalidades / Horas-homem trabalhadas) \u00D7 1.000.000.',
  },
  'Total de colaboradores': {
    definicao:
      'Número total de empregados com vínculo direto no fim do período (GRI 2-7).',
  },
  'Taxa de rotatividade — total': {
    definicao:
      'Proporção de colaboradores que deixaram a organização no período (GRI 401-1).',
    calculo: 'Rotatividade = (Desligamentos / Quadro médio) \u00D7 100.',
  },
  'Número de denúncias recebidas': {
    definicao:
      'Quantidade de denúncias recebidas via canal de ética, ouvidoria ou compliance (GRI 2-26).',
    fontes: 'Relatórios de Compliance, canal de ética, ouvidoria.',
  },
  'Número de denúncias resolvidas': {
    definicao:
      'Quantidade de denúncias encerradas/resolvidas no período (GRI 2-26).',
    calculo:
      '% Resolução = (Denúncias resolvidas / Denúncias recebidas) \u00D7 100.',
  },
  'Valor econômico gerado e distribuído': {
    definicao:
      'Valor econômico total gerado e sua distribuição entre stakeholders (GRI 201-1).',
    calculo:
      'VEG&D = Receita Líquida \u2212 Custos Operacionais + Pagamentos e Investimentos Sociais. Componentes: receitas, custos operacionais, salários e benefícios, pagamentos a financiadores e governos, investimentos na comunidade.',
  },
}

// ---------------------------------------------------------------------------
// Numeric helpers (pt-BR friendly: accepts "1.234,56" or "1234.56")
// ---------------------------------------------------------------------------

const PT_BR_THOUSANDS_RE = /^\d{1,3}(?:\.\d{3})+$/

function parseNumber(value: string | undefined | null): number | null {
  if (value === undefined || value === null) return null
  const trimmed = value.trim()
  if (!trimmed) return null
  let normalized: string
  if (trimmed.includes(',')) {
    normalized = trimmed.replace(/\./g, '').replace(',', '.')
  } else if (PT_BR_THOUSANDS_RE.test(trimmed)) {
    // pt-BR thousands-only integer (e.g. "1.000" → 1000, "2.500.000" → 2500000).
    normalized = trimmed.replace(/\./g, '')
  } else {
    normalized = trimmed
  }
  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : null
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(
    value
  )
}

// ---------------------------------------------------------------------------
// Template grouping — split a tema's items into blocks of siblings sharing
// the same group_key, preserving display_order.
// ---------------------------------------------------------------------------

type TemplateBlock =
  | { kind: 'solo'; item: IndicatorTemplateRecord }
  | { kind: 'group'; groupKey: string; items: IndicatorTemplateRecord[] }

function buildBlocks(items: IndicatorTemplateRecord[]): TemplateBlock[] {
  const sorted = [...items].sort((a, b) => a.display_order - b.display_order)
  const blocks: TemplateBlock[] = []
  for (const item of sorted) {
    if (!item.group_key) {
      blocks.push({ kind: 'solo', item })
      continue
    }
    const last = blocks[blocks.length - 1]
    if (last && last.kind === 'group' && last.groupKey === item.group_key) {
      last.items.push(item)
    } else {
      blocks.push({ kind: 'group', groupKey: item.group_key, items: [item] })
    }
  }
  return blocks
}

// Compute the numeric value to display for a `computed_*` row, based on
// sibling `input` rows in the same group_key.
function computeDerivedValue(
  item: IndicatorTemplateRecord,
  siblings: IndicatorTemplateRecord[],
  values: Record<string, string>
): number | null {
  const inputs = siblings.filter((s) => s.kind === 'input')
  const numbers = inputs
    .map((s) => parseNumber(values[s.indicador]))
    .filter((n): n is number => n !== null)
  if (numbers.length === 0) return null
  if (item.kind === 'computed_sum') {
    return numbers.reduce((acc, n) => acc + n, 0)
  }
  if (item.kind === 'computed_pct') {
    const total = numbers.reduce((acc, n) => acc + n, 0)
    if (total <= 0) return null
    // Convention: numerator is the first input in display_order.
    const firstInput = inputs[0]
    const firstValue = firstInput
      ? parseNumber(values[firstInput.indicador])
      : null
    if (firstValue === null) return null
    return (firstValue / total) * 100
  }
  return null
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

  // Discard legacy indicator_values whose `indicador` no longer exists in
  // the catalog (mirrors the silent-drop policy used in materiality).
  useEffect(() => {
    if (!project) return
    const saved = project.indicator_values
    if (!Array.isArray(saved)) {
      setValues({})
      return
    }
    const validIndicators = new Set(
      templates.filter((t) => t.kind === 'input').map((t) => t.indicador)
    )
    const map: Record<string, string> = {}
    for (const entry of saved) {
      if (
        typeof entry === 'object' &&
        entry !== null &&
        'indicador' in entry &&
        'value' in entry
      ) {
        const key = (entry as { indicador: string }).indicador
        if (templates.length > 0 && !validIndicators.has(key)) continue
        map[key] = String((entry as { value: string }).value)
      }
    }
    setValues(map)
  }, [project, templates])

  const grouped = useMemo(() => {
    const groups: Record<string, IndicatorTemplateRecord[]> = {}
    for (const t of templates) {
      if (!groups[t.tema]) groups[t.tema] = []
      groups[t.tema].push(t)
    }
    return groups
  }, [templates])

  const temas = useMemo(() => Object.keys(grouped), [grouped])

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
          if (item.kind !== 'input') continue
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

  function renderRow(
    item: IndicatorTemplateRecord,
    siblings: IndicatorTemplateRecord[]
  ) {
    const help = INDICATOR_HELP[item.indicador]
    const isComputed = item.kind !== 'input'
    const rawValue = values[item.indicador]?.trim()

    let displayValue: string = values[item.indicador] ?? ''
    if (isComputed) {
      const derived = computeDerivedValue(item, siblings, values)
      displayValue = derived === null ? '—' : formatNumber(derived)
    }

    return (
      <div
        key={item.indicador}
        className="group rounded-xl px-5 py-3 transition-colors hover:bg-[#e8e8ed]/40"
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <label
              htmlFor={`ind-${item.indicador}`}
              className={`truncate text-[13px] font-medium tracking-[-0.01em] ${isComputed ? 'text-[#6b6b72]' : 'text-[#1d1d1f]'}`}
            >
              {item.indicador}
            </label>
            {item.gri_code ? (
              <span className="shrink-0 rounded-full bg-[#eef3fb] px-2 py-0.5 text-[10px] font-semibold tracking-[0.01em] text-[#0673e0]">
                {item.gri_code}
              </span>
            ) : null}
            {isComputed ? (
              <span className="shrink-0 rounded-full bg-[#f1f1f3] px-2 py-0.5 text-[10px] font-medium text-[#86868b]">
                calculado
              </span>
            ) : null}
          </div>
          <div className="flex items-center gap-3">
            <input
              id={`ind-${item.indicador}`}
              type="text"
              value={displayValue}
              onChange={(e) =>
                !isComputed && updateValue(item.indicador, e.target.value)
              }
              readOnly={isComputed}
              placeholder="—"
              className={`apple-focus-ring w-36 rounded border-0 px-4 py-1.5 text-right text-[13px] font-semibold text-[#1d1d1f] transition-all focus:ring-2 focus:ring-primary/20 ${isComputed ? 'cursor-default bg-[#f1f1f3] text-[#6b6b72]' : 'bg-[#e8e8ed]'}`}
            />
            <span className="w-20 text-[12px] font-medium text-[#86868b]">
              {item.unidade}
            </span>
          </div>
        </div>
        {help ? (
          <div className="mt-2 rounded-lg border border-black/5 bg-[#f9f9fb] px-4 py-3 text-[12px] leading-5 tracking-[-0.01em] text-[#6b6b72]">
            <p>
              <span className="font-medium text-[#3a3a3c]">Definição: </span>
              {help.definicao}
            </p>
            {help.fontes ? (
              <p className="mt-1">
                <span className="font-medium text-[#3a3a3c]">Fontes: </span>
                {help.fontes}
              </p>
            ) : null}
            {help.calculo ? (
              <p className="mt-1">
                <span className="font-medium text-[#3a3a3c]">Cálculo: </span>
                {help.calculo}
              </p>
            ) : null}
            {!isComputed && rawValue ? (
              <p className="mt-1.5 border-t border-black/5 pt-1.5">
                <span className="font-medium text-[#1d1d1f]">
                  Valor informado:{' '}
                </span>
                <span className="font-semibold text-[#1d1d1f]">{rawValue}</span>
                {item.unidade ? (
                  <span className="ml-1 text-[#86868b]">{item.unidade}</span>
                ) : null}
              </p>
            ) : null}
          </div>
        ) : null}
      </div>
    )
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
            {project ? ` de ${project.org_name}` : ''}. Campos marcados como{' '}
            <span className="font-medium text-[#3a3a3c]">calculado</span> são
            derivados automaticamente dos valores informados nos campos irmãos.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saveMessage ? (
            <span className="text-[12px] tracking-[-0.01em] text-[#2b8a3e]">
              {saveMessage}
            </span>
          ) : null}
          <PrimaryBtn
            onClick={() => void handleSave()}
            disabled={isSaving || isLoading || !currentProjectId}
          >
            {isSaving ? 'Salvando…' : 'Salvar'}
          </PrimaryBtn>
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
            const filledCount = items.filter(
              (i) => i.kind === 'input' && values[i.indicador]?.trim()
            ).length
            const totalInputs = items.filter((i) => i.kind === 'input').length
            const blocks = buildBlocks(items)
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
                      {filledCount}/{totalInputs}
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
                  <div className="flex flex-col gap-2">
                    {blocks.map((block) => {
                      if (block.kind === 'solo') {
                        return renderRow(block.item, [block.item])
                      }
                      return (
                        <div
                          key={`group:${tema}:${block.groupKey}`}
                          className="rounded-xl border border-black/5 bg-[#fafafc] p-1"
                        >
                          {block.items.map((child) =>
                            renderRow(child, block.items)
                          )}
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
