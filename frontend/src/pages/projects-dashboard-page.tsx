import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ProjectForm } from '../components/project-form'
import { projectRecordToFormValues } from '../components/project-form.utils'
import { useAuth } from '../hooks/use-auth'
import { PrimaryBtn } from '../components/primary-btn'
import { ProjectStatusBadge } from '../components/project-status-badge'
import { createProject, fetchProjects } from '../services/api-client'
import type { ProjectRecord } from '../types/project'

const STATUS_FILTER_OPTIONS = [
  { label: 'Todos', value: '' },
  { label: 'Em coleta', value: 'collecting' },
  { label: 'Em geração', value: 'generating' },
  { label: 'Em revisão', value: 'reviewing' },
  { label: 'Finalizado', value: 'finalized' },
  { label: 'Arquivado', value: 'archived' },
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

function formatUpdatedAt(value: string) {
  const date = new Date(value)
  const now = new Date()
  const isSameDay = date.toDateString() === now.toDateString()
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  const isYesterday = date.toDateString() === yesterday.toDateString()

  if (isSameDay) {
    return `Hoje, ${date.toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
    })}`
  }

  if (isYesterday) {
    return `Ontem, ${date.toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
    })}`
  }

  return date.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: 'short',
  })
}

export function ProjectsDashboardPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { logout, user } = useAuth()
  const [projects, setProjects] = useState<ProjectRecord[]>([])
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isCreatingProject, setIsCreatingProject] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isProfileOpen, setIsProfileOpen] = useState(false)
  const [modalError, setModalError] = useState<string | null>(null)
  const [pageError, setPageError] = useState<string | null>(null)
  const profileMenuRef = useRef<HTMLDivElement | null>(null)
  const searchInputRef = useRef<HTMLInputElement | null>(null)

  const search = searchParams.get('search') ?? ''
  const status = searchParams.get('status') ?? ''
  const initials = useMemo(
    () => getInitials(user?.name, user?.email),
    [user?.email, user?.name]
  )

  useEffect(() => {
    if (!isProfileOpen) {
      return
    }

    function handlePointerDown(event: PointerEvent) {
      const target = event.target as Node

      if (profileMenuRef.current && !profileMenuRef.current.contains(target)) {
        setIsProfileOpen(false)
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
    }
  }, [isProfileOpen])

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

  useEffect(() => {
    let active = true

    async function loadProjects() {
      setIsLoading(true)

      try {
        const projectList = await fetchProjects({
          search: search || undefined,
          status: status || undefined,
        })

        if (!active) {
          return
        }

        setProjects(projectList)
        setPageError(null)
      } catch (error) {
        if (!active) {
          return
        }

        setPageError(
          error instanceof Error
            ? error.message
            : 'Não foi possível carregar os projetos.'
        )
      } finally {
        if (active) {
          setIsLoading(false)
        }
      }
    }

    void loadProjects()

    return () => {
      active = false
    }
  }, [search, status])

  return (
    <div className="h-screen overflow-hidden bg-[#e8e8ed] font-display text-[#1d1d1f] antialiased">
      <div
        className={`flex h-full min-w-0 flex-1 flex-col overflow-hidden bg-[#e8e8ed] transition-[filter] ${
          isCreateModalOpen ? 'pointer-events-none blur-[6px]' : ''
        }`}
      >
        <header className="relative flex h-14 flex-shrink-0 items-center justify-between border-b border-black/8 bg-[#e8e8ed] px-4 sm:px-5">
          <div className="w-10 shrink-0" aria-hidden="true" />

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
                value={search}
                placeholder="Buscar organização..."
                aria-label="Buscar organização"
                onChange={(event) => {
                  const nextParams = new URLSearchParams(searchParams)
                  const nextValue = event.target.value

                  if (nextValue) {
                    nextParams.set('search', nextValue)
                  } else {
                    nextParams.delete('search')
                  }

                  setSearchParams(nextParams, { replace: true })
                }}
                className="w-full border-0 bg-transparent p-0 text-[13px] tracking-[-0.01em] text-[#1d1d1f] placeholder:text-[#86868b] focus:outline-none focus:ring-0"
              />
              <span className="rounded-full bg-[#e8e8ed] px-2 py-0.5 text-[10px] font-medium tracking-tight text-[#86868b]">
                ⌘K
              </span>
            </div>
          </div>

          <div className="ml-auto flex items-center gap-2">
            <PrimaryBtn
              onClick={() => {
                setModalError(null)
                setIsCreateModalOpen(true)
              }}
              className="mt-0 h-8 shadow-sm"
            >
              Novo Projeto
            </PrimaryBtn>
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

        <main className="h-full overflow-hidden px-6 pb-6">
          <h1 className="sr-only">Projetos</h1>
          <div className="flex h-full flex-col overflow-hidden rounded-md bg-white">
            <header className="flex h-16 shrink-0 items-center justify-between border-b border-[#e5e5ea] px-6">
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-1">
                  <span className="sr-only">Filtrar projetos por status</span>
                  <span className="text-sm font-medium text-[#1d1d1f]">
                    Status:
                  </span>
                  <select
                    value={status}
                    aria-label="Filtrar projetos por status"
                    onChange={(event) => {
                      const nextParams = new URLSearchParams(searchParams)
                      const nextValue = event.target.value

                      if (nextValue) {
                        nextParams.set('status', nextValue)
                      } else {
                        nextParams.delete('status')
                      }

                      setSearchParams(nextParams, { replace: true })
                    }}
                    className="apple-focus-ring rounded-lg border-none bg-transparent py-1 pl-1 pr-6 text-sm font-medium text-[#1d1d1f] transition-colors hover:bg-[#f5f5f7]"
                  >
                    {STATUS_FILTER_OPTIONS.map((option) => (
                      <option key={option.value || 'all'} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </header>

            <div className="flex-1 overflow-auto">
              {pageError ? (
                <div className="px-6 py-6">
                  <div className="rounded border border-[#ffd0d0] bg-[#fff6f6] px-4 py-3 text-[12px] font-medium tracking-[-0.01em] text-[#d01f1f]">
                    {pageError}
                  </div>
                </div>
              ) : isLoading ? (
                <div className="px-6 py-6">
                  <div className="rounded border border-black/6 bg-white px-5 py-6">
                    <p className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                      Carregando projetos...
                    </p>
                  </div>
                </div>
              ) : projects.length === 0 ? (
                <div className="flex h-full items-center justify-center px-6 py-6 text-center">
                  <div>
                    <p className="text-[14px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                      Nenhum projeto encontrado.
                    </p>
                    <p className="mt-1 text-[12px] tracking-[-0.01em] text-[#86868b]">
                      Ajuste a busca/filtro ou crie o primeiro projeto para
                      começar.
                    </p>
                  </div>
                </div>
              ) : (
                <table className="w-full border-collapse text-left">
                  <thead className="sticky top-0 z-10 bg-white">
                    <tr>
                      <th className="h-10 w-[30%] border-b border-[#e5e5ea] px-6 align-middle text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
                        Organização
                      </th>
                      <th className="h-10 w-[25%] border-b border-[#e5e5ea] px-6 align-middle text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
                        Setor
                      </th>
                      <th className="h-10 w-[25%] border-b border-[#e5e5ea] px-6 align-middle text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
                        Status
                      </th>
                      <th className="h-10 w-[20%] border-b border-[#e5e5ea] px-6 align-middle text-right text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
                        Atualização
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {projects.map((project) => {
                      const isArchived = project.status === 'archived'

                      return (
                        <tr
                          key={project.id}
                          tabIndex={0}
                          role="link"
                          onClick={() => {
                            navigate(`/projects/${project.id}`)
                          }}
                          onKeyDown={(event) => {
                            if (event.key === 'Enter' || event.key === ' ') {
                              event.preventDefault()
                              navigate(`/projects/${project.id}`)
                            }
                          }}
                          className={`group cursor-pointer border-b border-[#f5f5f7] transition-colors last:border-none hover:bg-[#f5f5f7] focus:outline-none focus-visible:bg-[#f5f5f7] ${
                            isArchived ? 'opacity-70' : ''
                          }`}
                        >
                          <td className="h-12 px-6 align-middle text-sm font-medium text-[#1d1d1f]">
                            {project.org_name}
                          </td>
                          <td className="h-12 px-6 align-middle text-sm text-[#1d1d1f]">
                            {project.org_sector ?? 'Não informado'}
                          </td>
                          <td className="h-12 px-6 align-middle">
                            <ProjectStatusBadge status={project.status} />
                          </td>
                          <td className="h-12 px-6 align-middle text-right text-sm text-[#86868b]">
                            {formatUpdatedAt(project.updated_at)}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </main>
      </div>
      {isCreateModalOpen ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20 px-4 py-6">
          <button
            type="button"
            className="absolute inset-0"
            aria-label="Fechar modal de novo projeto"
            onClick={() => {
              if (isCreatingProject) {
                return
              }

              setIsCreateModalOpen(false)
              setModalError(null)
            }}
          />
          <section className="relative z-10 w-full max-w-2xl rounded-lg bg-white shadow-[rgba(0,0,0,0.18)_0px_24px_80px]">
            <header className="border-b border-[#e5e5ea] px-6 py-4 text-center">
              <h2 className="text-[18px] font-semibold tracking-[-0.02em] text-[#1d1d1f]">
                Criar Novo Projeto
              </h2>
            </header>

            <div className="max-h-[calc(100vh-160px)] overflow-y-auto px-6 py-5">
              <ProjectForm
                cancelLabel="Cancelar"
                errorMessage={modalError}
                initialValues={projectRecordToFormValues(null)}
                isSubmitting={isCreatingProject}
                onCancel={() => {
                  if (isCreatingProject) {
                    return
                  }

                  setIsCreateModalOpen(false)
                  setModalError(null)
                }}
                onSubmit={async (payload) => {
                  setIsCreatingProject(true)
                  setModalError(null)

                  try {
                    const nextProject = await createProject(payload)
                    setIsCreateModalOpen(false)
                    navigate(`/projects/${nextProject.id}`)
                  } catch (error) {
                    setModalError(
                      error instanceof Error
                        ? error.message
                        : 'Não foi possível criar o projeto.'
                    )
                  } finally {
                    setIsCreatingProject(false)
                  }
                }}
                submitLabel="Criar"
              />
            </div>
          </section>
        </div>
      ) : null}
    </div>
  )
}
