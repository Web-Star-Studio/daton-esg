import { useState } from 'react'
import { ProjectShell } from '../components/project-shell'

const COMPANY_PLACEHOLDER = 'Projeto atual'

const indicatorSections = [
  {
    color: 'bg-emerald-500',
    title: 'Ambiental (E)',
    items: [
      {
        code: 'GRI 302-1',
        label: 'Consumo de Energia Elétrica',
        unit: 'kWh',
        value: '14.500',
      },
      {
        code: 'GRI 305-1',
        label: 'Emissões Escopo 1',
        unit: 'tCO₂e',
        value: '2.340',
      },
      {
        code: 'GRI 303-5',
        label: 'Consumo de Água',
        unit: 'm³',
        value: '',
      },
    ],
  },
  {
    color: 'bg-blue-500',
    title: 'Social (S)',
    items: [
      {
        code: 'GRI 405-1',
        label: 'Diversidade no Quadro (Mulheres)',
        unit: '%',
        value: '42,5',
      },
      {
        code: 'GRI 404-1',
        label: 'Horas de Treinamento',
        unit: 'h/ano',
        value: '24',
      },
    ],
  },
  {
    color: 'bg-violet-500',
    title: 'Governança (G)',
    items: [
      {
        code: 'GRI 205-3',
        label: 'Violações de Compliance',
        unit: 'un',
        value: '0',
      },
      {
        code: 'GRI 102-22',
        label: 'Conselheiros Independentes',
        unit: '%',
        value: '60',
      },
    ],
  },
] as const

export function DashboardPage() {
  const [indicatorValues, setIndicatorValues] = useState<
    Record<string, string>
  >(() =>
    Object.fromEntries(
      indicatorSections.flatMap((section) =>
        section.items.map((item) => [
          `${section.title}-${item.code}`,
          item.value,
        ])
      )
    )
  )

  return (
    <ProjectShell
      activeSidebarKey="indicators"
      companyName={COMPANY_PLACEHOLDER}
      pageAction={{
        label: 'Salvar Alterações',
        icon: 'save',
        onClick: () => undefined,
      }}
      pageTitle="Indicadores"
    >
      <div className="space-y-8 px-6 pt-9 pb-6 sm:px-10">
        {indicatorSections.map((section) => (
          <section key={section.title} className="space-y-4">
            <h3 className="flex items-center gap-2 text-[16px] font-medium tracking-[-0.015em] text-[#1d1d1f]">
              <span
                aria-hidden="true"
                className={`size-2 rounded-full ${section.color}`}
              />
              {section.title}
            </h3>

            <div className="flex flex-col gap-1">
              {section.items.map((item) => (
                <div
                  key={`${section.title}-${item.code}`}
                  className="group flex items-center justify-between rounded-xl px-5 py-3.5 transition-colors hover:bg-[#e8e8ed]/40"
                >
                  <div className="flex flex-col">
                    <span className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                      {item.label}
                    </span>
                    <span className="text-[12px] text-[#86868b]">
                      {item.code}
                    </span>
                  </div>

                  <div className="flex items-center gap-4">
                    <input
                      type="text"
                      value={
                        indicatorValues[`${section.title}-${item.code}`] ?? ''
                      }
                      onChange={(event) => {
                        const nextValue = event.target.value
                        setIndicatorValues((current) => ({
                          ...current,
                          [`${section.title}-${item.code}`]: nextValue,
                        }))
                      }}
                      placeholder="0"
                      className="apple-focus-ring w-36 rounded border-0 bg-[#e8e8ed] px-4 py-1.5 text-right text-[13px] font-semibold text-[#1d1d1f] transition-all focus:ring-2 focus:ring-primary/20"
                    />
                    <span className="w-12 text-[12px] font-medium text-[#86868b]">
                      {item.unit}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </ProjectShell>
  )
}
