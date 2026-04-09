from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models import User
from app.models.enums import ProjectStatus
from app.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import (
    archive_project,
    create_project_for_user,
    get_project_for_user,
    list_projects_for_user,
    update_project,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    project = await create_project_for_user(
        session,
        user_id=current_user.id,
        payload=payload,
    )
    return ProjectResponse.model_validate(project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    search: str | None = Query(default=None),
    status_filter: ProjectStatus | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ProjectResponse]:
    projects = await list_projects_for_user(
        session,
        current_user.id,
        search=search,
        status_filter=status_filter,
    )
    return [ProjectResponse.model_validate(project) for project in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    project = await get_project_for_user(session, project_id, current_user.id)
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def patch_project(
    project_id: UUID,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    project = await get_project_for_user(session, project_id, current_user.id)
    updated_project = await update_project(
        session,
        project=project,
        payload=payload,
    )
    return ProjectResponse.model_validate(updated_project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    project = await get_project_for_user(session, project_id, current_user.id)
    await archive_project(session, project=project)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
