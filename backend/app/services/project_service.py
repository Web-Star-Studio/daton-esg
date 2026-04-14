import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project
from app.models.enums import ProjectStatus
from app.schemas.project import ProjectCreate, ProjectUpdate

logger = logging.getLogger(__name__)


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
    else:
        query = query.where(Project.status != ProjectStatus.ARCHIVED)

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


async def delete_project_cascade(
    session: AsyncSession,
    *,
    project: Project,
) -> None:
    """Hard-delete a project with full cascade: wipe Pinecone namespace,
    delete S3 objects, then delete the DB row (cascading to all children).

    Pinecone/S3 errors are logged but do not block the DB delete — the
    project data should not be left orphaned in the DB just because an
    external service is temporarily unavailable.
    """
    project_id = str(project.id)

    # 1. Wipe Pinecone namespace (all indexed vectors for this project)
    try:
        from app.services.vector_store import get_vector_store

        store = get_vector_store()
        await store.delete_namespace(namespace=project_id)
        logger.info(
            "project.pinecone_namespace_deleted",
            extra={"project_id": project_id},
        )
    except Exception:
        logger.exception(
            "project.pinecone_namespace_delete_failed",
            extra={"project_id": project_id},
        )

    # 2. Delete S3 objects (documents + report exports)
    try:
        from app.services.storage_service import get_storage_service

        storage = get_storage_service()
        doc_prefix = f"projects/{project_id}/"
        report_prefix = f"reports/{project_id}/"
        doc_count = await storage.delete_objects_by_prefix(prefix=doc_prefix)
        report_count = await storage.delete_objects_by_prefix(prefix=report_prefix)
        logger.info(
            "project.s3_objects_deleted",
            extra={
                "project_id": project_id,
                "documents_deleted": doc_count,
                "reports_deleted": report_count,
            },
        )
    except Exception:
        logger.exception(
            "project.s3_delete_failed",
            extra={"project_id": project_id},
        )

    # 3. Hard-delete from DB (cascades to documents, reports, threads,
    #    messages, rag_chunks via SQLAlchemy cascade="all, delete-orphan")
    await session.delete(project)
    await session.commit()
