from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models import User
from app.schemas import ProjectResponse
from app.services.project_service import get_project_for_user, list_projects_for_user

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ProjectResponse]:
    projects = await list_projects_for_user(session, current_user.id)
    return [ProjectResponse.model_validate(project) for project in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    project = await get_project_for_user(session, project_id, current_user.id)
    return ProjectResponse.model_validate(project)
