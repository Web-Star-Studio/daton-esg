from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project
from app.models.enums import ProjectStatus
from app.schemas.project import ProjectCreate, ProjectUpdate


async def list_projects_for_user(
    session: AsyncSession,
    user_id: UUID,
    *,
    search: str | None = None,
    status_filter: ProjectStatus | None = None,
) -> list[Project]:
    query: Select[tuple[Project]] = select(Project).where(Project.user_id == user_id)

    if status_filter is not None:
        query = query.where(Project.status == status_filter)

    if search:
        query = query.where(Project.org_name.ilike(f"%{search.strip()}%"))

    result = await session.execute(query.order_by(Project.created_at.desc()))
    return list(result.scalars().all())


async def get_project_for_user(
    session: AsyncSession,
    project_id: UUID,
    user_id: UUID,
) -> Project:
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == user_id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


async def create_project_for_user(
    session: AsyncSession,
    *,
    user_id: UUID,
    payload: ProjectCreate,
) -> Project:
    project = Project(
        user_id=user_id,
        org_name=payload.org_name,
        org_sector=payload.org_sector,
        org_size=payload.org_size,
        org_location=payload.org_location,
        base_year=payload.base_year,
        scope=payload.scope,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def update_project(
    session: AsyncSession,
    *,
    project: Project,
    payload: ProjectUpdate,
) -> Project:
    updates = payload.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(project, field, value)

    await session.commit()
    await session.refresh(project)
    return project


async def archive_project(
    session: AsyncSession,
    *,
    project: Project,
) -> Project:
    project.status = ProjectStatus.ARCHIVED
    await session.commit()
    await session.refresh(project)
    return project
