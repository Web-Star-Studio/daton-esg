import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { DocumentList } from '../components/document-list'
import type { PageAction } from '../components/project-shell'
import { ProjectStatusBadge } from '../components/project-status-badge'
import { fetchProjectDocuments, updateProject } from '../services/api-client'
import {
  useProjectShellRegistration,
  useProjectWorkspace,
} from '../hooks/use-project-workspace'
import type { ProjectDocument } from '../types/project'

const STATUS_OPTIONS = [
  { label: 'Em coleta', value: 'collecting' },
  { label: 'Em geração', value: 'generating' },
  { label: 'Em revisão', value: 'reviewing' },
  { label: 'Finalizado', value: 'finalized' },
  { label: 'Arquivado', value: 'archived' },
] as const

export function ProjectDetailPage() {
  const navigate = useNavigate()
  const {
    currentProjectId,
    isLoadingWorkspace,
    project,
    setProject,
    workspaceError,
  } = useProjectWorkspace()
  const [documents, setDocuments] = useState<ProjectDocument[]>([])
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true)
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)
  const canGenerateReport = documents.length > 0
  const pageActions = useMemo<PageAction[]>(
    () =>
      project
        ? [
            {
              icon: 'edit',
              label: 'Editar',
              onClick: (): void => {
                navigate(`/projects/${project.id}/edit`)
              },
              variant: 'secondary' as const,
            },
            {
              icon: 'upload_file',
              label: 'Upload de Documentos',
              onClick: (): void => {
                navigate(`/projects/${project.id}/documents`)
              },
            },
            {
              disabled: !canGenerateReport,
              icon: 'auto_awesome',
              label: 'Gerar Relatório',
              onClick: () => undefined,
            },
          ]
        : [],
    [canGenerateReport, navigate, project]
  )

  useProjectShellRegistration({
    activeSidebarKey: 'overview',
    pageActions,
    pageTitle: 'Visão Geral',
  })

  useEffect(() => {
    if (!currentProjectId) {
      setPageError('Projeto inválido.')
      setIsLoadingDocuments(false)
      return
    }

    let active = true

    async function loadDocuments() {
      setIsLoadingDocuments(true)

      try {
        const documentsResponse = await fetchProjectDocuments(currentProjectId)

        if (!active) {
          return
        }

        setDocuments(documentsResponse)
        setPageError(null)
      } catch (error) {
        if (!active) {
          return
        }

        setPageError(
          error instanceof Error
            ? error.message
            : 'Não foi possível carregar o projeto.'
        )
      } finally {
        if (active) {
          setIsLoadingDocuments(false)
        }
      }
    }

    void loadDocuments()

    return () => {
      active = false
    }
  }, [currentProjectId])

  return (
    <div className="space-y-6 px-6 pt-6 pb-6 sm:px-10">
      {pageError || workspaceError ? (
        <div className="rounded-lg border border-[#ffd0d0] bg-[#fff6f6] px-4 py-3 text-[12px] font-medium tracking-[-0.01em] text-[#d01f1f]">
          {pageError ?? workspaceError}
        </div>
      ) : null}

      {isLoadingWorkspace ? (
        <div className="rounded-lg border border-black/6 bg-white px-5 py-6">
          <p className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
            Carregando projeto...
          </p>
        </div>
      ) : project ? (
        <>
          <header className="rounded-lg border border-black/6 bg-white p-6 shadow-sm">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <h1 className="text-[24px] font-semibold tracking-[-0.02em] text-[#1d1d1f]">
                  {project.org_name}
                </h1>
                <ProjectStatusBadge status={project.status} />
              </div>
              <p className="text-[13px] tracking-[-0.01em] text-[#86868b]">
                {project.org_sector ?? 'Setor não informado'} • Ano-base{' '}
                {project.base_year}
              </p>
            </div>
          </header>

          <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-lg border border-black/6 bg-white p-6 shadow-sm">
              <div className="mb-5 flex items-center justify-between">
                <h2 className="text-[16px] font-semibold tracking-[-0.015em] text-[#1d1d1f]">
                  Informações Gerais
                </h2>
                <div className="flex items-center gap-3">
                  <label
                    htmlFor="project-status"
                    className="text-[12px] font-medium tracking-[-0.01em] text-[#86868b]"
                  >
                    Status
                  </label>
                  <select
                    id="project-status"
                    value={project.status}
                    disabled={isUpdatingStatus}
                    onChange={async (event) => {
                      setIsUpdatingStatus(true)
                      setPageError(null)

                      try {
                        const updatedProject = await updateProject(project.id, {
                          status: event.target.value,
                        })
                        setProject(updatedProject)
                      } catch (error) {
                        setPageError(
                          error instanceof Error
                            ? error.message
                            : 'Não foi possível atualizar o status do projeto.'
                        )
                      } finally {
                        setIsUpdatingStatus(false)
                      }
                    }}
                    className="apple-focus-ring rounded border border-[#d2d2d7] bg-white px-3 py-2 text-[12px] tracking-[-0.01em] text-[#1d1d1f]"
                  >
                    {STATUS_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <dl className="grid gap-4 md:grid-cols-2">
                <div>
                  <dt className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#86868b]">
                    Nome
                  </dt>
                  <dd className="mt-1 text-[13px] tracking-[-0.01em] text-[#1d1d1f]">
                    {project.org_name}
                  </dd>
                </div>
                <div>
                  <dt className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#86868b]">
                    Setor
                  </dt>
                  <dd className="mt-1 text-[13px] tracking-[-0.01em] text-[#1d1d1f]">
                    {project.org_sector ?? 'Não informado'}
                  </dd>
                </div>
                <div>
                  <dt className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#86868b]">
                    Porte
                  </dt>
                  <dd className="mt-1 text-[13px] tracking-[-0.01em] text-[#1d1d1f]">
                    {project.org_size ?? 'Não informado'}
                  </dd>
                </div>
                <div>
                  <dt className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#86868b]">
                    Localização
                  </dt>
                  <dd className="mt-1 text-[13px] tracking-[-0.01em] text-[#1d1d1f]">
                    {project.org_location ?? 'Não informada'}
                  </dd>
                </div>
                <div>
                  <dt className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#86868b]">
                    Ano-base
                  </dt>
                  <dd className="mt-1 text-[13px] tracking-[-0.01em] text-[#1d1d1f]">
                    {project.base_year}
                  </dd>
                </div>
                <div>
                  <dt className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#86868b]">
                    Atualizado em
                  </dt>
                  <dd className="mt-1 text-[13px] tracking-[-0.01em] text-[#1d1d1f]">
                    {new Date(project.updated_at).toLocaleDateString('pt-BR')}
                  </dd>
                </div>
                <div className="md:col-span-2">
                  <dt className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#86868b]">
                    Abrangência
                  </dt>
                  <dd className="mt-1 text-[13px] tracking-[-0.01em] text-[#1d1d1f]">
                    {project.scope ?? 'Não informada'}
                  </dd>
                </div>
              </dl>
            </div>

            <div className="space-y-4">
              <section className="rounded-lg border border-black/6 bg-white p-6 shadow-sm">
                <h2 className="text-[16px] font-semibold tracking-[-0.015em] text-[#1d1d1f]">
                  Navegação
                </h2>
                <div className="mt-4 grid gap-2">
                  <Link
                    to={`/projects/${project.id}/documents`}
                    className="apple-focus-ring inline-flex items-center justify-between rounded-[0.7rem] bg-[#f5f7f8] px-3 py-3 text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f] transition-colors hover:bg-[#e8e8ed]"
                  >
                    Documentos
                    <span
                      aria-hidden="true"
                      className="material-symbols-outlined text-[16px] text-[#86868b]"
                    >
                      chevron_right
                    </span>
                  </Link>
                  <Link
                    to={`/projects/${project.id}/indicators`}
                    className="apple-focus-ring inline-flex items-center justify-between rounded-[0.7rem] bg-[#f5f7f8] px-3 py-3 text-[12px] font-medium tracking-[-0.01em] text-[#1d1d1f] transition-colors hover:bg-[#e8e8ed]"
                  >
                    Indicadores
                    <span
                      aria-hidden="true"
                      className="material-symbols-outlined text-[16px] text-[#86868b]"
                    >
                      chevron_right
                    </span>
                  </Link>
                </div>
              </section>

              <section className="rounded-lg border border-black/6 bg-white p-6 shadow-sm">
                <h2 className="text-[16px] font-semibold tracking-[-0.015em] text-[#1d1d1f]">
                  Resumo de Documentos
                </h2>
                <p className="mt-1 text-[12px] tracking-[-0.01em] text-[#86868b]">
                  {documents.length} documento(s) associado(s) ao projeto.
                </p>
              </section>
            </div>
          </section>

          <section className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-lg border border-black/6 bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-[16px] font-semibold tracking-[-0.015em] text-[#1d1d1f]">
                  Documentos recentes
                </h2>
                <Link
                  to={`/projects/${project.id}/documents`}
                  className="apple-focus-ring text-[12px] font-medium tracking-[-0.01em] text-primary"
                >
                  Ver todos
                </Link>
              </div>
              {isLoadingDocuments ? (
                <div className="rounded-lg border border-black/6 bg-[#f5f7f8] px-5 py-6">
                  <p className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                    Carregando documentos do projeto...
                  </p>
                </div>
              ) : (
                <DocumentList
                  deletingDocumentId={null}
                  documents={documents.slice(0, 5)}
                />
              )}
            </div>

            <div className="rounded-lg border border-black/6 bg-white p-6 shadow-sm">
              <h2 className="text-[16px] font-semibold tracking-[-0.015em] text-[#1d1d1f]">
                Relatórios
              </h2>
              <p className="mt-1 text-[12px] tracking-[-0.01em] text-[#86868b]">
                Os relatórios gerados para este projeto aparecerão aqui.
              </p>
              <div className="mt-4 rounded-lg border border-dashed border-[#d2d2d7] bg-[#f5f7f8] px-4 py-5">
                <p className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                  Nenhum relatório gerado ainda.
                </p>
                <p className="mt-1 text-[12px] tracking-[-0.01em] text-[#86868b]">
                  O botão de geração será liberado assim que o projeto tiver ao
                  menos um documento enviado.
                </p>
              </div>
            </div>
          </section>
        </>
      ) : null}
    </div>
  )
}
