import {
  type FocusEvent,
  type MouseEvent,
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/use-auth'

type SidebarItemKey =
  | 'overview'
  | 'documents'
  | 'data'
  | 'materiality'
  | 'indicators'
  | 'generation'
  | 'report'
  | 'charts'
  | 'gri'
  | 'gaps'
  | 'exports'
  | 'history'
  | 'branding'

type PageAction = {
  disabled?: boolean
  label: string
  icon: string
  onClick: () => void
}

type ProjectShellProps = {
  activeSidebarKey: SidebarItemKey
  children: ReactNode
  companyName: string
  documentsHref?: string
  pageAction?: PageAction
  pageTitle: string
}

const sidebarItems: Array<{
  icon: string
  key: SidebarItemKey
  label: string
}> = [
  { key: 'overview', label: 'Visão Geral', icon: 'bar_chart' },
  { key: 'documents', label: 'Documentos', icon: 'folder' },
  { key: 'data', label: 'Dados', icon: 'database' },
  { key: 'materiality', label: 'Materialidade & ODS', icon: 'ads_click' },
  { key: 'indicators', label: 'Indicadores', icon: 'format_list_numbered' },
  {
    key: 'generation',
    label: 'Geração do Relatório',
    icon: 'picture_as_pdf',
  },
  { key: 'report', label: 'Relatório', icon: 'description' },
  { key: 'charts', label: 'Gráficos & Tabelas', icon: 'pie_chart' },
  { key: 'gri', label: 'Índice GRI', icon: 'view_list' },
  { key: 'gaps', label: 'Lacunas', icon: 'warning' },
  { key: 'exports', label: 'Exportações', icon: 'file_download' },
  { key: 'history', label: 'Histórico & Versões', icon: 'history' },
  { key: 'branding', label: 'Identidade Visual', icon: 'palette' },
]

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

function getSidebarHref(
  itemKey: SidebarItemKey,
  documentsHref: string | undefined
) {
  if (itemKey === 'indicators') {
    return '/dashboard'
  }

  if (itemKey === 'documents') {
    return documentsHref
  }

  return undefined
}

export function ProjectShell({
  activeSidebarKey,
  children,
  companyName,
  documentsHref,
  pageAction,
  pageTitle,
}: ProjectShellProps) {
  const { logout, user } = useAuth()
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false)
  const [isProfileOpen, setIsProfileOpen] = useState(false)
  const [sidebarTooltip, setSidebarTooltip] = useState<{
    label: string
    top: number
    left: number
  } | null>(null)
  const profileMenuRef = useRef<HTMLDivElement | null>(null)
  const searchInputRef = useRef<HTMLInputElement | null>(null)
  const initials = useMemo(
    () => getInitials(user?.name, user?.email),
    [user?.email, user?.name]
  )

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

  useEffect(() => {
    function handleWindowKeyDown(event: KeyboardEvent) {
      const isShortcut =
        (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k'

      if (!isShortcut) {
        return
      }

      const target = event.target
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        (target instanceof HTMLElement && target.isContentEditable)
      ) {
        return
      }

      event.preventDefault()
      searchInputRef.current?.focus()
    }

    window.addEventListener('keydown', handleWindowKeyDown)

    return () => {
      window.removeEventListener('keydown', handleWindowKeyDown)
    }
  }, [])

  function showSidebarTooltip(
    event:
      | MouseEvent<HTMLAnchorElement | HTMLButtonElement>
      | FocusEvent<HTMLAnchorElement | HTMLButtonElement>,
    label: string
  ) {
    const rect = event.currentTarget.getBoundingClientRect()

    setSidebarTooltip({
      label,
      left: rect.right + 12,
      top: rect.top + rect.height / 2,
    })
  }

  function handleToggleMobileNav() {
    setIsMobileNavOpen((current) => !current)
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
                {pageTitle}
              </h1>
            </div>
            <button
              type="button"
              onClick={handleToggleMobileNav}
              className="apple-focus-ring inline-flex size-9 items-center justify-center rounded-[0.7rem] bg-white text-[#1d1d1f] shadow-sm transition-colors hover:bg-black/[0.03] md:hidden"
              aria-label="Abrir navegação"
              aria-expanded={isMobileNavOpen}
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
                ref={searchInputRef}
                type="search"
                placeholder="Buscar"
                aria-label="Buscar no workspace"
                className="w-full border-0 bg-transparent p-0 text-[13px] tracking-[-0.01em] text-[#1d1d1f] placeholder:text-[#86868b] focus:outline-none focus:ring-0"
              />
              <span className="rounded-full bg-[#e8e8ed] px-2 py-0.5 text-[10px] font-medium tracking-tight text-[#86868b]">
                ⌘K
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {pageAction ? (
              <button
                type="button"
                onClick={pageAction.onClick}
                className="apple-focus-ring inline-flex items-center gap-2 rounded-[0.7rem] bg-primary px-4 py-2 text-[12px] font-medium tracking-[-0.01em] text-white transition-all hover:opacity-90 active:scale-95 disabled:cursor-not-allowed disabled:opacity-55 disabled:hover:opacity-55 disabled:active:scale-100"
                disabled={pageAction.disabled}
              >
                <span
                  aria-hidden="true"
                  className="material-symbols-outlined text-[16px]"
                >
                  {pageAction.icon}
                </span>
                {pageAction.label}
              </button>
            ) : null}
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
                    <p className="truncate text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                      {user?.email ?? 'Usuário'}
                    </p>
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
              {sidebarItems.map((item) => {
                const isActive = item.key === activeSidebarKey
                const href = getSidebarHref(item.key, documentsHref)
                const commonProps = {
                  'aria-label': item.label,
                  className: `flex size-9 items-center justify-center rounded-[0.7rem] transition-colors ${
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-[#1d1d1f] hover:bg-black/5'
                  }`,
                  onBlur: () => {
                    setSidebarTooltip(null)
                  },
                  onFocus: (
                    event: FocusEvent<HTMLAnchorElement | HTMLButtonElement>
                  ) => {
                    showSidebarTooltip(event, item.label)
                  },
                  onMouseEnter: (
                    event: MouseEvent<HTMLAnchorElement | HTMLButtonElement>
                  ) => {
                    showSidebarTooltip(event, item.label)
                  },
                  onMouseLeave: () => {
                    setSidebarTooltip(null)
                  },
                }

                const icon = (
                  <span
                    aria-hidden="true"
                    className={`material-symbols-outlined text-[18px] ${
                      isActive ? '' : 'text-[#86868b]'
                    }`}
                    style={
                      isActive
                        ? { fontVariationSettings: "'FILL' 1" }
                        : undefined
                    }
                  >
                    {item.icon}
                  </span>
                )

                return (
                  <div
                    key={item.key}
                    className="group relative flex justify-center"
                  >
                    {href ? (
                      <Link to={href} {...commonProps}>
                        {icon}
                      </Link>
                    ) : (
                      <button type="button" {...commonProps}>
                        {icon}
                      </button>
                    )}
                  </div>
                )
              })}
            </nav>
          </aside>

          <main className="flex-1 overflow-hidden pb-5 pr-5">
            <div className="no-scrollbar relative flex h-full flex-col overflow-y-auto rounded-lg bg-white">
              {children}
            </div>
          </main>
        </div>
      </div>
      {isMobileNavOpen ? (
        <div className="fixed inset-0 z-40 flex md:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/20"
            aria-label="Fechar navegação"
            onClick={() => {
              setIsMobileNavOpen(false)
            }}
          />
          <div className="relative z-10 flex h-full w-[248px] flex-col bg-white px-3 py-4 shadow-xl">
            <div className="mb-4 flex items-center justify-between px-2">
              <p className="truncate text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                {companyName}
              </p>
              <button
                type="button"
                className="apple-focus-ring inline-flex size-8 items-center justify-center rounded-[0.7rem] text-[#86868b] hover:bg-black/[0.04] hover:text-[#1d1d1f]"
                aria-label="Fechar navegação"
                onClick={() => {
                  setIsMobileNavOpen(false)
                }}
              >
                <span
                  aria-hidden="true"
                  className="material-symbols-outlined text-[18px]"
                >
                  close
                </span>
              </button>
            </div>
            <nav className="space-y-1">
              {sidebarItems.map((item) => {
                const isActive = item.key === activeSidebarKey
                const href = getSidebarHref(item.key, documentsHref)
                const navContent = (
                  <>
                    <span
                      aria-hidden="true"
                      className={`material-symbols-outlined text-[18px] ${
                        isActive ? 'text-primary' : 'text-[#86868b]'
                      }`}
                      style={
                        isActive
                          ? { fontVariationSettings: "'FILL' 1" }
                          : undefined
                      }
                    >
                      {item.icon}
                    </span>
                    <span>{item.label}</span>
                  </>
                )

                const className = `apple-focus-ring flex w-full items-center gap-3 rounded-[0.7rem] px-3 py-2 text-left text-[13px] font-medium tracking-[-0.01em] transition-colors ${
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-[#1d1d1f] hover:bg-black/[0.04]'
                }`

                if (href) {
                  return (
                    <Link
                      key={item.key}
                      to={href}
                      className={className}
                      onClick={() => {
                        setIsMobileNavOpen(false)
                      }}
                    >
                      {navContent}
                    </Link>
                  )
                }

                return (
                  <button
                    key={item.key}
                    type="button"
                    className={className}
                    onClick={() => {
                      setIsMobileNavOpen(false)
                    }}
                  >
                    {navContent}
                  </button>
                )
              })}
            </nav>
          </div>
        </div>
      ) : null}
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
