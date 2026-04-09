import {
  createContext,
  useContext,
  useEffect,
  type Dispatch,
  type SetStateAction,
} from 'react'
import type { ProjectRecord } from '../types/project'
import type { PageAction, SidebarItemKey } from '../components/project-shell'

export type ProjectWorkspaceContextValue = {
  currentProjectId: string
  isLoadingWorkspace: boolean
  navigateToProject: (projectId: string) => void
  project: ProjectRecord | null
  projects: ProjectRecord[]
  setActiveSidebarKey: Dispatch<SetStateAction<SidebarItemKey>>
  setPageActions: Dispatch<SetStateAction<PageAction[]>>
  setPageTitle: Dispatch<SetStateAction<string>>
  setProject: Dispatch<SetStateAction<ProjectRecord | null>>
  workspaceError: string | null
}

export const ProjectWorkspaceContext =
  createContext<ProjectWorkspaceContextValue | null>(null)

export function useProjectWorkspace() {
  const context = useContext(ProjectWorkspaceContext)

  if (!context) {
    throw new Error(
      'useProjectWorkspace must be used within ProjectWorkspaceContext.'
    )
  }

  return context
}

type ProjectShellRegistrationOptions = {
  activeSidebarKey: SidebarItemKey
  pageActions?: PageAction[]
  pageTitle: string
}

export function useProjectShellRegistration({
  activeSidebarKey,
  pageActions = [],
  pageTitle,
}: ProjectShellRegistrationOptions) {
  const { setActiveSidebarKey, setPageActions, setPageTitle } =
    useProjectWorkspace()

  useEffect(() => {
    setActiveSidebarKey(activeSidebarKey)
    setPageTitle(pageTitle)
    setPageActions(pageActions)

    return () => {
      setPageActions([])
    }
  }, [
    activeSidebarKey,
    pageActions,
    pageTitle,
    setActiveSidebarKey,
    setPageActions,
    setPageTitle,
  ])
}
