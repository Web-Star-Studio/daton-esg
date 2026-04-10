import { useState } from 'react'
import { ProjectTimeline } from '../components/project-timeline'
import { updateProject } from '../services/api-client'
import {
  useProjectShellRegistration,
  useProjectWorkspace,
} from '../hooks/use-project-workspace'

export function ProjectDetailPage() {
  const { isLoadingWorkspace, project, setProject, workspaceError } =
    useProjectWorkspace()
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)
  useProjectShellRegistration({
    activeSidebarKey: 'overview',
    pageTitle: 'Visão Geral',
  })

  async function handleStatusChange(newStatus: string) {
    if (!project) return

    setIsUpdatingStatus(true)
    setPageError(null)

    try {
      const updatedProject = await updateProject(project.id, {
        status: newStatus,
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
  }

  return (
    <div className="space-y-6 px-6 pt-6 pb-6 sm:px-10">
      {pageError || workspaceError ? (
        <div className="rounded-lg border border-[#ffd0d0] bg-[#fff6f6] px-4 py-3 text-[12px] font-medium tracking-[-0.01em] text-[#d01f1f]">
          {pageError ?? workspaceError}
        </div>
      ) : null}

      {isLoadingWorkspace ? (
        <p className="text-[13px] font-medium tracking-[-0.01em] text-[#1d1d1f]">
          Carregando projeto...
        </p>
      ) : project ? (
        <div className="flex items-center gap-x-6">
          <div className="flex shrink-0 items-center gap-x-6">
            <div className="flex items-center gap-2">
              <span className="text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
                Setor
              </span>
              <span className="text-sm text-[#1d1d1f]">
                {project.org_sector ?? 'Não informado'}
              </span>
            </div>
            <span className="text-[#d2d2d7]" aria-hidden="true">
              |
            </span>
            <div className="flex items-center gap-2">
              <span className="text-[12px] font-medium uppercase tracking-[0.5px] text-[#86868b]">
                Ano-base
              </span>
              <span className="text-sm text-[#1d1d1f]">
                {project.base_year}
              </span>
            </div>
          </div>

          <div className="ml-auto">
            <ProjectTimeline
              currentStatus={project.status}
              disabled={isUpdatingStatus}
              onStatusChange={(status) => {
                void handleStatusChange(status)
              }}
            />
          </div>
        </div>
      ) : null}
    </div>
  )
}
