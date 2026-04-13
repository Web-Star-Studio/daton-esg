from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models import User
from app.schemas import KnowledgeReindexResponse, KnowledgeStatusSummary
from app.services.project_service import get_project_for_user
from app.services.rag_ingestion_service import (
    get_project_knowledge_status,
    list_project_document_ids_for_reindex,
    run_document_rag_ingestion_task,
)

router = APIRouter(prefix="/api/v1/projects/{project_id}/knowledge", tags=["knowledge"])


@router.get("/status", response_model=KnowledgeStatusSummary)
async def get_project_knowledge_status_endpoint(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeStatusSummary:
    project = await get_project_for_user(session, project_id, current_user.id)
    status_payload = await get_project_knowledge_status(session, project_id=project.id)
    return KnowledgeStatusSummary.model_validate(status_payload)


@router.post("/reindex", response_model=KnowledgeReindexResponse)
async def reindex_project_knowledge(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeReindexResponse:
    project = await get_project_for_user(session, project_id, current_user.id)
    document_ids = await list_project_document_ids_for_reindex(
        session,
        project_id=project.id,
    )
    for document_id in document_ids:
        background_tasks.add_task(run_document_rag_ingestion_task, document_id)
    return KnowledgeReindexResponse(
        project_id=project.id,
        queued_documents=len(document_ids),
    )
