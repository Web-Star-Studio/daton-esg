import { useCallback, useEffect, useMemo, useState } from 'react'
import { Outlet, useLocation, useNavigate, useParams } from 'react-router-dom'
import { fetchProject, fetchProjects } from '../services/api-client'
import type { ProjectRecord, ProjectShellOption } from '../types/project'
import {
  ProjectShell,
  type PageAction,
  type SidebarItemKey,
} from './project-shell'
import { ProjectWorkspaceContext } from '../hooks/use-project-workspace'

const COMPANY_PLACEHOLDER = 'Projeto atual'

function getRouteShellDefaults(pathname: string): {
  activeSidebarKey: SidebarItemKey
  pageTitle: string
} {
  if (pathname.endsWith('/documents')) {
    return {
      activeSidebarKey: 'documents',
      pageTitle: 'Documentos',
    }
  }

  if (pathname.endsWith('/data')) {
    return {
      activeSidebarKey: 'data',
      pageTitle: 'Dados',
    }
  }

  if (pathname.endsWith('/indicators')) {
    return {
      activeSidebarKey: 'indicators',
      pageTitle: 'Indicadores',
    }
  }

  return {
    activeSidebarKey: 'overview',
    pageTitle: 'Visão Geral',
  }
}

export function ProjectWorkspaceLayout() {
  const { projectId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const routeDefaults = useMemo(
    () => getRouteShellDefaults(location.pathname),
    [location.pathname]
  )
  const [project, setProject] = useState<ProjectRecord | null>(null)
  const [projects, setProjects] = useState<ProjectRecord[]>([])
  const [isLoadingWorkspace, setIsLoadingWorkspace] = useState(true)
  const [workspaceError, setWorkspaceError] = useState<string | null>(null)
  const [pageActions, setPageActions] = useState<PageAction[]>([])
  const [pageTitle, setPageTitle] = useState(routeDefaults.pageTitle)
  const [activeSidebarKey, setActiveSidebarKey] = useState<SidebarItemKey>(
    routeDefaults.activeSidebarKey
  )

  useEffect(() => {
    setPageTitle(routeDefaults.pageTitle)
    setActiveSidebarKey(routeDefaults.activeSidebarKey)
    setPageActions([])
  }, [routeDefaults])

  useEffect(() => {
    if (!projectId) {
      setProject(null)
      setProjects([])
      setWorkspaceError('Projeto inválido.')
      setIsLoadingWorkspace(false)
      return
    }

    let active = true
    const currentProjectId = projectId

    async function loadProjectWorkspace() {
      setIsLoadingWorkspace(true)

      try {
        const [projectResponse, projectList] = await Promise.all([
          fetchProject(currentProjectId),
          fetchProjects(),
        ])

        if (!active) {
          return
        }

        setProject(projectResponse)
        setProjects(projectList)
        setWorkspaceError(null)
      } catch (error) {
        if (!active) {
          return
        }

        setProject(null)
        setProjects([])
        setWorkspaceError(
          error instanceof Error
            ? error.message
            : 'Não foi possível carregar o projeto.'
        )
      } finally {
        if (active) {
          setIsLoadingWorkspace(false)
        }
      }
    }

    void loadProjectWorkspace()

    return () => {
      active = false
    }
  }, [projectId])

  const buildProjectHref = useCallback(
    (nextProjectId: string) => {
      const currentPath = projectId ? `/projects/${projectId}` : ''
      const suffix =
        currentPath && location.pathname.startsWith(currentPath)
          ? location.pathname.slice(currentPath.length)
          : ''

      return `/projects/${nextProjectId}${suffix}`
    },
    [location.pathname, projectId]
  )

  const projectOptions = useMemo<ProjectShellOption[]>(
    () =>
      projects.map((projectItem) => ({
        id: projectItem.id,
        href: buildProjectHref(projectItem.id),
        name: projectItem.org_name,
      })),
    [buildProjectHref, projects]
  )

  const navigateToProject = useCallback(
    (nextProjectId: string) => {
      navigate(buildProjectHref(nextProjectId))
    },
    [buildProjectHref, navigate]
  )

  return (
    <ProjectWorkspaceContext.Provider
      value={{
        currentProjectId: projectId ?? '',
        isLoadingWorkspace,
        navigateToProject,
        project,
        projects,
        setActiveSidebarKey,
        setPageActions,
        setPageTitle,
        setProject,
        workspaceError,
      }}
    >
      <ProjectShell
        activeSidebarKey={activeSidebarKey}
        companyName={project?.org_name ?? COMPANY_PLACEHOLDER}
        currentProjectId={project?.id ?? projectId}
        dataHref={projectId ? `/projects/${projectId}/data` : undefined}
        documentsHref={
          projectId ? `/projects/${projectId}/documents` : undefined
        }
        indicatorsHref={
          projectId ? `/projects/${projectId}/indicators` : undefined
        }
        overviewHref={projectId ? `/projects/${projectId}` : undefined}
        pageActions={pageActions}
        pageTitle={pageTitle}
        projectOptions={projectOptions}
      >
        <Outlet />
      </ProjectShell>
    </ProjectWorkspaceContext.Provider>
  )
}
