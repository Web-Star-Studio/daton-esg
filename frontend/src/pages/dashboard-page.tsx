import { useMemo } from 'react'
import { useAuth } from '../hooks/use-auth'

const sidebarItems = [
  { label: 'Visão Geral', icon: 'bar_chart', active: false },
  { label: 'Documentos', icon: 'folder', active: false },
  { label: 'Dados', icon: 'database', active: false },
  { label: 'Materialidade & ODS', icon: 'ads_click', active: false },
  { label: 'Indicadores', icon: 'format_list_numbered', active: true },
  { label: 'Geração do Relatório', icon: 'picture_as_pdf', active: false },
  { label: 'Relatório', icon: 'description', active: false },
  { label: 'Gráficos & Tabelas', icon: 'pie_chart', active: false },
  { label: 'Índice GRI', icon: 'view_list', active: false },
  { label: 'Lacunas', icon: 'warning', active: false },
  { label: 'Exportações', icon: 'file_download', active: false },
  { label: 'Histórico & Versões', icon: 'history', active: false },
  { label: 'Identidade Visual', icon: 'palette', active: false },
] as const

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

function getInitials(
  name: string | null | undefined,
  email: string | undefined
) {
  if (name) {
    const parts = name
      .split(' ')
      .map((part) => part.trim())
      .filter(Boolean)
      .slice(0, 2)

    if (parts.length > 0) {
      return parts.map((part) => part[0]?.toUpperCase() ?? '').join('')
    }
  }

  return (email?.[0] ?? 'D').toUpperCase()
}

export function DashboardPage() {
  const { logout, user } = useAuth()

  const initials = useMemo(
    () => getInitials(user?.name, user?.email),
    [user?.email, user?.name]
  )

  return (
    <div className="flex h-screen overflow-hidden bg-[#e8e8ed] font-display text-[#1d1d1f] antialiased">
      <aside className="no-scrollbar hidden h-full w-[260px] flex-shrink-0 flex-col overflow-y-auto bg-[#e8e8ed] md:flex">
        <div className="flex items-center gap-3 px-5 pb-6 pt-8">
          <div className="flex size-10 items-center justify-center rounded-full bg-[#0f1923] text-[13px] font-semibold tracking-tight text-white shadow-sm">
            AC
          </div>
          <div className="flex flex-col">
            <h1 className="text-[17px] font-semibold leading-tight tracking-[-0.015em] text-[#1d1d1f]">
              Acme Inc.
            </h1>
            <p className="flex cursor-default items-center gap-1 text-[13px] font-normal leading-tight text-[#86868b] transition-colors">
              Empresa
              <span
                aria-hidden="true"
                className="material-symbols-outlined text-[16px]"
              >
                expand_more
              </span>
            </p>
          </div>
        </div>

        <nav className="flex-1 space-y-0.5 px-3 pb-8">
          {sidebarItems.map((item) => (
            <button
              key={item.label}
              type="button"
              className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors ${
                item.active
                  ? 'bg-primary/10 text-primary'
                  : 'text-[#1d1d1f] hover:bg-black/5'
              }`}
            >
              <span
                aria-hidden="true"
                className={`material-symbols-outlined text-[20px] ${
                  item.active ? '' : 'text-[#86868b]'
                }`}
                style={
                  item.active
                    ? { fontVariationSettings: "'FILL' 1" }
                    : undefined
                }
              >
                {item.icon}
              </span>
              <span className="text-[14px] font-medium tracking-[-0.01em]">
                {item.label}
              </span>
            </button>
          ))}
        </nav>
      </aside>

      <main className="relative flex h-full min-w-0 flex-1 flex-col overflow-hidden">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-black/8 bg-white/80 px-4 backdrop-blur-md sm:px-5">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              className="apple-focus-ring inline-flex size-9 items-center justify-center rounded-full bg-white text-[#1d1d1f] shadow-sm transition-colors hover:bg-black/[0.03] md:hidden"
              aria-label="Abrir navegação"
            >
              <span aria-hidden="true" className="material-symbols-outlined">
                menu
              </span>
            </button>

            <div className="hidden min-w-0 items-center gap-2 rounded-full bg-white px-3 py-2 shadow-sm sm:flex sm:min-w-[320px] lg:min-w-[400px]">
              <span
                aria-hidden="true"
                className="material-symbols-outlined text-[18px] text-[#86868b]"
              >
                search
              </span>
              <input
                type="search"
                placeholder="Search Acme Inc."
                className="w-full border-0 bg-transparent p-0 text-[14px] tracking-[-0.01em] text-[#1d1d1f] placeholder:text-[#86868b] focus:outline-none focus:ring-0"
              />
              <span className="rounded-full bg-[#e8e8ed] px-2 py-0.5 text-[11px] font-medium tracking-tight text-[#86868b]">
                ⌘K
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              className="apple-focus-ring inline-flex size-9 items-center justify-center rounded-full bg-white text-[#86868b] shadow-sm transition-colors hover:text-[#1d1d1f]"
              aria-label="Notificações"
            >
              <span aria-hidden="true" className="material-symbols-outlined">
                notifications
              </span>
            </button>
            <button
              type="button"
              className="apple-focus-ring inline-flex size-9 items-center justify-center rounded-full bg-white text-[#86868b] shadow-sm transition-colors hover:text-[#1d1d1f]"
              aria-label="Ajuda"
            >
              <span aria-hidden="true" className="material-symbols-outlined">
                help
              </span>
            </button>
            <button
              type="button"
              className="apple-focus-ring hidden items-center gap-2 rounded-full bg-[#1d1d1f] px-4 py-2 text-[14px] font-medium tracking-[-0.01em] text-white transition-colors hover:bg-[#0f1923] sm:inline-flex"
            >
              <span
                aria-hidden="true"
                className="material-symbols-outlined text-[18px]"
              >
                smart_toy
              </span>
              AI Assistant
            </button>
            <div className="flex items-center gap-2 rounded-full bg-white px-2 py-1 shadow-sm">
              <div className="flex size-8 items-center justify-center rounded-full bg-[#0f1923] text-[12px] font-semibold tracking-tight text-white">
                {initials}
              </div>
              <span className="hidden max-w-[140px] truncate text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f] lg:inline">
                {user?.name ?? user?.email ?? 'Consultor'}
              </span>
            </div>
            <button
              type="button"
              onClick={() => {
                void logout()
              }}
              className="apple-focus-ring inline-flex items-center rounded-full bg-white px-3 py-2 text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f] shadow-sm transition-colors hover:bg-black/[0.03]"
            >
              Sair
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-hidden p-5">
          <div className="no-scrollbar relative flex h-full flex-col overflow-y-auto rounded-xl bg-white">
            <div className="sticky top-0 z-10 flex items-end justify-between bg-white/90 px-6 pb-6 pt-8 backdrop-blur-md sm:px-10 sm:pt-10">
              <div>
                <h2 className="text-[28px] font-semibold tracking-[-0.02em] text-[#1d1d1f]">
                  Indicadores
                </h2>
                <p className="mt-1 text-[15px] font-normal tracking-[-0.01em] text-[#86868b]">
                  Acompanhamento de métricas ESG granulares
                </p>
              </div>

              <button
                type="button"
                className="apple-focus-ring inline-flex items-center gap-2 rounded-full bg-primary px-6 py-2.5 text-[14px] font-medium tracking-[-0.01em] text-white transition-all hover:opacity-90 active:scale-95"
              >
                <span
                  aria-hidden="true"
                  className="material-symbols-outlined text-[18px]"
                >
                  save
                </span>
                Salvar Alterações
              </button>
            </div>

            <div className="space-y-12 px-6 pb-20 sm:px-10">
              {indicatorSections.map((section) => (
                <section key={section.title}>
                  <div className="sticky top-[96px] z-[1] mb-4 bg-white/95 py-3 backdrop-blur-sm">
                    <h3 className="flex items-center gap-2 text-[19px] font-medium tracking-[-0.015em] text-[#1d1d1f]">
                      <span
                        aria-hidden="true"
                        className={`size-2 rounded-full ${section.color}`}
                      />
                      {section.title}
                    </h3>
                  </div>

                  <div className="flex flex-col gap-1 rounded-xl bg-white/50 p-1">
                    {section.items.map((item) => (
                      <div
                        key={`${section.title}-${item.code}`}
                        className="group flex items-center justify-between rounded-xl px-5 py-4 transition-colors hover:bg-[#e8e8ed]/40"
                      >
                        <div className="flex flex-col">
                          <span className="text-[15px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                            {item.label}
                          </span>
                          <span className="text-[13px] text-[#86868b]">
                            {item.code}
                          </span>
                        </div>

                        <div className="flex items-center gap-4">
                          <input
                            type="text"
                            defaultValue={item.value}
                            placeholder="0"
                            className="apple-focus-ring w-40 rounded-full border-0 bg-[#e8e8ed] px-5 py-2 text-right text-[15px] font-semibold text-[#1d1d1f] transition-all focus:ring-2 focus:ring-primary/20"
                          />
                          <span className="w-12 text-[13px] font-medium text-[#86868b]">
                            {item.unit}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
