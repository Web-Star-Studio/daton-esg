from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project


async def list_projects_for_user(
    session: AsyncSession,
    user_id: UUID,
) -> list[Project]:
    result = await session.execute(
        select(Project)
        .where(Project.user_id == user_id)
        .order_by(Project.created_at.desc())
    )
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
