from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models import User
from app.schemas import (
    DocumentResponse,
    DocumentUpdateRequest,
    DocumentUploadRequest,
    DocumentUploadResponse,
)
from app.services.document_service import (
    confirm_document_upload,
    create_document_upload,
    delete_document,
    get_document_for_project,
    list_documents_for_project,
    move_document_to_directory,
)
from app.services.project_service import get_project_for_user
from app.services.rag_ingestion_service import (
    delete_document_rag_knowledge,
    run_document_rag_ingestion_task,
    sync_document_rag_metadata,
)
from app.services.storage_service import get_storage_service

router = APIRouter(prefix="/api/v1/projects/{project_id}/documents", tags=["documents"])


@router.post(
    "", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED
)
async def create_project_document_upload(
    project_id: UUID,
    payload: DocumentUploadRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentUploadResponse:
    project = await get_project_for_user(session, project_id, current_user.id)
    document, upload_url, content_type = await create_document_upload(
        session,
        project=project,
        filename=payload.filename,
        file_size_bytes=payload.file_size_bytes,
        directory_key=payload.directory_key,
        storage=get_storage_service(),
    )
    return DocumentUploadResponse(
        document_id=document.id,
        upload_url=upload_url,
        s3_key=document.s3_key,
        content_type=content_type,
    )


@router.post("/{document_id}/confirm", response_model=DocumentResponse)
async def confirm_project_document_upload(
    project_id: UUID,
    document_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    project = await get_project_for_user(session, project_id, current_user.id)
    document = await get_document_for_project(session, project.id, document_id)
    confirmed_document = await confirm_document_upload(
        session,
        document=document,
        storage=get_storage_service(),
    )
    background_tasks.add_task(run_document_rag_ingestion_task, confirmed_document.id)
    return DocumentResponse.model_validate(confirmed_document)


@router.get("", response_model=list[DocumentResponse])
async def list_project_documents(
    project_id: UUID,
    directory_key: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[DocumentResponse]:
    project = await get_project_for_user(session, project_id, current_user.id)
    documents = await list_documents_for_project(
        session,
        project.id,
        directory_key=directory_key,
        limit=limit,
        offset=offset,
    )
    return [DocumentResponse.model_validate(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_project_document(
    project_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    project = await get_project_for_user(session, project_id, current_user.id)
    document = await get_document_for_project(session, project.id, document_id)
    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_document(
    project_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    project = await get_project_for_user(session, project_id, current_user.id)
    document = await get_document_for_project(session, project.id, document_id)
    await delete_document_rag_knowledge(session, document=document)
    await delete_document(
        session,
        document=document,
        storage=get_storage_service(),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_project_document(
    project_id: UUID,
    document_id: UUID,
    payload: DocumentUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    project = await get_project_for_user(session, project_id, current_user.id)
    document = await get_document_for_project(session, project.id, document_id)
    updated_document = await move_document_to_directory(
        session,
        document=document,
        directory_key=payload.directory_key,
    )
    await sync_document_rag_metadata(session, document=updated_document)
    return DocumentResponse.model_validate(updated_document)
