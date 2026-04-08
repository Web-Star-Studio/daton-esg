import {
  type FocusEvent,
  type MouseEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { createPortal } from 'react-dom'
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
  const [isProfileOpen, setIsProfileOpen] = useState(false)
  const [sidebarTooltip, setSidebarTooltip] = useState<{
    label: string
    top: number
    left: number
  } | null>(null)
  const profileMenuRef = useRef<HTMLDivElement | null>(null)
  const pageActionLabel = 'Salvar Alterações'
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

  const initials = useMemo(
    () => getInitials(user?.name, user?.email),
    [user?.email, user?.name]
  )
  const companyName = COMPANY_PLACEHOLDER

  useEffect(() => {
    if (!isProfileOpen) {
      return
    }

    function handlePointerDown(event: PointerEvent) {
      if (
        profileMenuRef.current &&
        !profileMenuRef.current.contains(event.target as Node)
      ) {
        setIsProfileOpen(false)
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
    }
  }, [isProfileOpen])

  useEffect(() => {
    if (!sidebarTooltip) {
      return
    }

    function handleWindowChange() {
      setSidebarTooltip(null)
    }

    window.addEventListener('scroll', handleWindowChange, true)
    window.addEventListener('resize', handleWindowChange)

    return () => {
      window.removeEventListener('scroll', handleWindowChange, true)
      window.removeEventListener('resize', handleWindowChange)
    }
  }, [sidebarTooltip])

  function showSidebarTooltip(
    event: MouseEvent<HTMLButtonElement> | FocusEvent<HTMLButtonElement>,
    label: string
  ) {
    const rect = event.currentTarget.getBoundingClientRect()

    setSidebarTooltip({
      label,
      left: rect.right + 12,
      top: rect.top + rect.height / 2,
    })
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#e8e8ed] font-display text-[#1d1d1f] antialiased">
      <div className="flex h-full min-w-0 flex-1 flex-col overflow-hidden bg-[#e8e8ed]">
        <header className="relative flex h-14 flex-shrink-0 items-center justify-between border-b border-black/8 bg-[#e8e8ed] px-4 sm:px-5">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              className="apple-focus-ring hidden items-center gap-1.5 rounded-[0.7rem] px-2 py-1.5 text-left text-[#1d1d1f] transition-colors hover:bg-black/[0.04] md:inline-flex"
              aria-label="Selecionar projeto"
            >
              <span className="whitespace-nowrap text-[13px] font-medium tracking-[-0.01em]">
                {companyName}
              </span>
              <span
                aria-hidden="true"
                className="material-symbols-outlined text-[16px] text-[#86868b]"
              >
                expand_more
              </span>
            </button>
            <div className="hidden items-center gap-2 text-[13px] tracking-[-0.01em] text-[#86868b] md:flex">
              <span aria-hidden="true" className="text-[#b0b0b4]">
                /
              </span>
              <h1 className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                Indicadores
              </h1>
            </div>
            <button
              type="button"
              className="apple-focus-ring inline-flex size-9 items-center justify-center rounded-[0.7rem] bg-white text-[#1d1d1f] shadow-sm transition-colors hover:bg-black/[0.03] md:hidden"
              aria-label="Abrir navegação"
            >
              <span aria-hidden="true" className="material-symbols-outlined">
                menu
              </span>
            </button>
          </div>

          <div className="pointer-events-none absolute inset-x-0 flex justify-center px-20">
            <div className="pointer-events-auto hidden min-w-[280px] items-center gap-2 rounded bg-white px-3 py-1.5 shadow-sm sm:flex lg:min-w-[360px]">
              <span
                aria-hidden="true"
                className="material-symbols-outlined text-[16px] text-[#86868b]"
              >
                search
              </span>
              <input
                type="search"
                placeholder="Buscar"
                className="w-full border-0 bg-transparent p-0 text-[13px] tracking-[-0.01em] text-[#1d1d1f] placeholder:text-[#86868b] focus:outline-none focus:ring-0"
              />
              <span className="rounded-full bg-[#e8e8ed] px-2 py-0.5 text-[10px] font-medium tracking-tight text-[#86868b]">
                ⌘K
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              className="apple-focus-ring inline-flex items-center gap-2 rounded-[0.7rem] bg-primary px-4 py-2 text-[12px] font-medium tracking-[-0.01em] text-white transition-all hover:opacity-90 active:scale-95"
            >
              <span
                aria-hidden="true"
                className="material-symbols-outlined text-[16px]"
              >
                save
              </span>
              {pageActionLabel}
            </button>
            <button
              type="button"
              className="apple-focus-ring inline-flex size-8 items-center justify-center text-[#86868b] transition-colors hover:text-[#1d1d1f]"
              aria-label="Notificações"
            >
              <span
                aria-hidden="true"
                className="material-symbols-outlined text-[18px]"
              >
                notifications
              </span>
            </button>
            <div ref={profileMenuRef} className="relative">
              <button
                type="button"
                onClick={() => {
                  setIsProfileOpen((current) => !current)
                }}
                className="apple-focus-ring inline-flex size-8 items-center justify-center rounded-full bg-[#0f1923] text-[11px] font-semibold tracking-tight text-white transition-transform hover:scale-[1.02]"
                aria-label="Abrir menu do perfil"
                aria-expanded={isProfileOpen}
              >
                {initials}
              </button>
              {isProfileOpen ? (
                <div className="absolute right-0 top-full z-30 mt-2 w-56 rounded-[0.7rem] bg-white p-2 shadow-[rgba(0,0,0,0.16)_0px_10px_30px]">
                  <div className="border-b border-black/8 px-2 pb-2 pt-1">
                    {user?.email ? (
                      <p className="truncate text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                        {user.email}
                      </p>
                    ) : (
                      <p className="truncate text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                        Usuário
                      </p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setIsProfileOpen(false)
                      void logout()
                    }}
                    className="apple-focus-ring mt-2 inline-flex w-full items-center gap-2 rounded-[0.7rem] px-2 py-2 text-left text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f] transition-colors hover:bg-black/[0.04]"
                  >
                    <span
                      aria-hidden="true"
                      className="material-symbols-outlined text-[16px] text-[#86868b]"
                    >
                      logout
                    </span>
                    Sair
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </header>

        <div className="flex min-h-0 flex-1 overflow-x-visible overflow-y-hidden">
          <aside className="relative z-30 hidden h-full w-[64px] flex-shrink-0 bg-[#e8e8ed] px-2 py-4 md:block">
            <nav className="no-scrollbar h-full space-y-1 overflow-x-visible overflow-y-auto pt-1">
              {sidebarItems.map((item) => (
                <div
                  key={item.label}
                  className="group relative flex justify-center"
                >
                  <button
                    type="button"
                    aria-label={item.label}
                    title={item.label}
                    onMouseEnter={(event) => {
                      showSidebarTooltip(event, item.label)
                    }}
                    onFocus={(event) => {
                      showSidebarTooltip(event, item.label)
                    }}
                    onMouseLeave={() => {
                      setSidebarTooltip(null)
                    }}
                    onBlur={() => {
                      setSidebarTooltip(null)
                    }}
                    className={`flex size-9 items-center justify-center rounded-[0.7rem] transition-colors ${
                      item.active
                        ? 'bg-primary/10 text-primary'
                        : 'text-[#1d1d1f] hover:bg-black/5'
                    }`}
                  >
                    <span
                      aria-hidden="true"
                      className={`material-symbols-outlined text-[18px] ${
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
                  </button>
                </div>
              ))}
            </nav>
          </aside>

          <main className="flex-1 overflow-hidden pb-5 pr-5">
            <div className="no-scrollbar relative flex h-full flex-col overflow-y-auto rounded-lg bg-white">
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
                                indicatorValues[
                                  `${section.title}-${item.code}`
                                ] ?? ''
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
            </div>
          </main>
        </div>
      </div>
      {sidebarTooltip && typeof document !== 'undefined'
        ? createPortal(
            <div
              className="pointer-events-none fixed z-[9999] -translate-y-1/2 rounded-full bg-[#1d1d1f] px-3 py-1 text-[11px] font-medium tracking-[-0.01em] text-white shadow-lg"
              style={{
                left: `${sidebarTooltip.left}px`,
                top: `${sidebarTooltip.top}px`,
              }}
            >
              {sidebarTooltip.label}
            </div>,
            document.body
          )
        : null}
    </div>
  )
}
