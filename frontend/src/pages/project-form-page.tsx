import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ProjectForm } from '../components/project-form'
import { projectRecordToFormValues } from '../components/project-form.utils'
import {
  createProject,
  fetchProject,
  updateProject,
} from '../services/api-client'
import type { ProjectRecord } from '../types/project'

type ProjectFormMode = 'create' | 'edit'

type ProjectFormPageProps = {
  mode: ProjectFormMode
}

export function ProjectFormPage({ mode }: ProjectFormPageProps) {
  const navigate = useNavigate()
  const { projectId } = useParams()
  const [project, setProject] = useState<ProjectRecord | null>(null)
  const [isLoading, setIsLoading] = useState(mode === 'edit')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)

  useEffect(() => {
    if (mode !== 'edit' || !projectId) {
      return
    }

    let active = true
    const currentProjectId = projectId

    async function loadProject() {
      setIsLoading(true)
      setProject(null)
      setPageError(null)

      try {
        const currentProject = await fetchProject(currentProjectId)
        if (!active) {
          return
        }

        setProject(currentProject)
        setPageError(null)
      } catch (error) {
        if (!active) {
          return
        }

        setPageError(
          error instanceof Error
            ? error.message
            : 'Não foi possível carregar o projeto para edição.'
        )
      } finally {
        if (active) {
          setIsLoading(false)
        }
      }
    }

    void loadProject()

    return () => {
      active = false
    }
  }, [mode, projectId])

  const title =
    mode === 'create' ? 'Novo projeto' : 'Editar informações do projeto'
  const description =
    mode === 'create'
      ? 'Cadastre os dados base da organização para iniciar o fluxo do relatório.'
      : 'Atualize os dados institucionais e o escopo do projeto.'
  const initialValues = useMemo(
    () => projectRecordToFormValues(project),
    [project]
  )

  return (
    <div className="min-h-screen bg-[#f5f7f8] font-display text-[#1d1d1f]">
      <main className="mx-auto w-full max-w-4xl px-6 py-8 lg:px-8">
        <div className="mb-6 flex items-center gap-2 text-[12px] tracking-[-0.01em] text-[#86868b]">
          <Link
            to="/dashboard"
            className="apple-focus-ring rounded px-1 hover:text-[#1d1d1f]"
          >
            Projetos
          </Link>
          <span aria-hidden="true">/</span>
          <span>
            {mode === 'create'
              ? 'Novo projeto'
              : (project?.org_name ?? 'Editar')}
          </span>
        </div>

        <section className="rounded-lg border border-black/6 bg-white p-6 shadow-sm">
          <header className="mb-6">
            <h1 className="text-[24px] font-semibold tracking-[-0.02em] text-[#1d1d1f]">
              {title}
            </h1>
            <p className="mt-1 text-[13px] tracking-[-0.01em] text-[#86868b]">
              {description}
            </p>
          </header>

          {pageError ? (
            <div className="mb-5 rounded border border-[#ffd0d0] bg-[#fff6f6] px-4 py-3 text-[12px] font-medium tracking-[-0.01em] text-[#d01f1f]">
              {pageError}
            </div>
          ) : null}

          {isLoading ? (
            <div className="rounded-lg border border-black/6 bg-[#f5f7f8] px-5 py-6">
              <p className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                Carregando projeto...
              </p>
            </div>
          ) : mode === 'create' || project ? (
            <ProjectForm
              key={`${mode}-${project?.id ?? 'new'}`}
              errorMessage={pageError}
              initialValues={initialValues}
              isSubmitting={isSubmitting}
              onSubmit={async (payload) => {
                setIsSubmitting(true)
                setPageError(null)

                try {
                  const nextProject =
                    mode === 'create'
                      ? await createProject(payload)
                      : await updateProject(projectId as string, payload)

                  navigate(`/projects/${nextProject.id}`)
                } catch (error) {
                  setPageError(
                    error instanceof Error
                      ? error.message
                      : 'Não foi possível salvar o projeto.'
                  )
                } finally {
                  setIsSubmitting(false)
                }
              }}
              submitLabel={
                mode === 'create' ? 'Criar projeto' : 'Salvar alterações'
              }
            />
          ) : (
            <div className="rounded-lg border border-black/6 bg-[#f5f7f8] px-5 py-6">
              <p className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
                {pageError ?? 'Projeto não encontrado para edição.'}
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
