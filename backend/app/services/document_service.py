import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from botocore.exceptions import ClientError
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentExtraction, Project
from app.models.enums import (
    DocumentFileType,
    DocumentParsingStatus,
    ExtractionReviewStatus,
)
from app.services.data_extraction_service import recalculate_document_classification
from app.services.storage_service import StorageObjectMetadata, StorageService

MAX_DOCUMENT_SIZE_BYTES = 50 * 1024 * 1024
MAX_DOCUMENT_LIST_LIMIT = 100

logger = logging.getLogger(__name__)

_DOCUMENT_TYPE_MAP: dict[str, tuple[DocumentFileType, str]] = {
    ".pdf": (DocumentFileType.PDF, "application/pdf"),
    ".xlsx": (
        DocumentFileType.XLSX,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ),
    ".csv": (DocumentFileType.CSV, "text/csv"),
    ".docx": (
        DocumentFileType.DOCX,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
}


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def normalize_filename(filename: str) -> str:
    normalized = Path(filename).name.strip()
    if not normalized:
        raise _bad_request("Filename is required")
    return normalized


def resolve_file_type_and_content_type(
    filename: str,
) -> tuple[DocumentFileType, str]:
    normalized = normalize_filename(filename)
    extension = Path(normalized).suffix.lower()
    file_type_and_content_type = _DOCUMENT_TYPE_MAP.get(extension)
    if file_type_and_content_type is None:
        raise _bad_request("Unsupported file type")
    return file_type_and_content_type


def validate_file_size(file_size_bytes: int) -> None:
    if file_size_bytes <= 0:
        raise _bad_request("File size must be greater than zero")
    if file_size_bytes > MAX_DOCUMENT_SIZE_BYTES:
        raise _bad_request("File exceeds the 50MB limit")


def build_document_s3_key(
    *,
    project_id: UUID,
    document_id: UUID,
    filename: str,
) -> str:
    return f"uploads/{project_id}/{document_id}/{normalize_filename(filename)}"


async def list_documents_for_project(
    session: AsyncSession,
    project_id: UUID,
    *,
    limit: int = MAX_DOCUMENT_LIST_LIMIT,
    offset: int = 0,
) -> list[Document]:
    normalized_limit = max(1, min(limit, MAX_DOCUMENT_LIST_LIMIT))
    normalized_offset = max(0, offset)

    result = await session.execute(
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(Document.created_at.desc())
        .limit(normalized_limit)
        .offset(normalized_offset)
    )
    return list(result.scalars().all())


async def get_document_for_project(
    session: AsyncSession,
    project_id: UUID,
    document_id: UUID,
) -> Document:
    result = await session.execute(
        select(Document).where(
            Document.project_id == project_id,
            Document.id == document_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


async def create_document_upload(
    session: AsyncSession,
    *,
    project: Project,
    filename: str,
    file_size_bytes: int,
    storage: StorageService,
) -> tuple[Document, str, str]:
    validate_file_size(file_size_bytes)
    file_type, content_type = resolve_file_type_and_content_type(filename)
    document_id = uuid4()
    s3_key = build_document_s3_key(
        project_id=project.id,
        document_id=document_id,
        filename=filename,
    )

    document = Document(
        id=document_id,
        project_id=project.id,
        filename=normalize_filename(filename),
        file_type=file_type,
        s3_key=s3_key,
        file_size_bytes=file_size_bytes,
        parsing_status=DocumentParsingStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
    upload_url = await storage.generate_presigned_upload_url(
        key=s3_key,
        content_type=content_type,
    )

    session.add(document)
    await session.commit()
    await session.refresh(document)

    return document, upload_url, content_type


async def confirm_document_upload(
    session: AsyncSession,
    *,
    document: Document,
    storage: StorageService,
    metadata_getter: Callable[[StorageService, str], Awaitable[StorageObjectMetadata]]
    | None = None,
) -> Document:
    if metadata_getter is None:
        try:
            metadata = await storage.get_object_metadata(key=document.s3_key)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in {"404", "NoSuchKey", "NotFound"}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Upload not found in storage",
                ) from exc
            raise
    else:
        metadata = await metadata_getter(storage, document.s3_key)

    if metadata.content_length is not None:
        document.file_size_bytes = metadata.content_length
        await session.commit()
        await session.refresh(document)

    return document


async def delete_document(
    session: AsyncSession,
    *,
    document: Document,
    storage: StorageService,
) -> None:
    await session.delete(document)
    await session.commit()
    try:
        await storage.delete_object(key=document.s3_key)
    except Exception:
        logger.exception(
            "Failed to delete document from storage after database removal",
            extra={"s3_key": document.s3_key},
        )
        # TODO: enqueue retry/cleanup once background jobs exist.


async def update_document_esg_category(
    session: AsyncSession,
    *,
    document: Document,
    esg_category: str | None,
) -> Document:
    stripped = esg_category.strip() if esg_category else ""
    normalized_category = stripped or None
    result = await session.execute(
        select(DocumentExtraction).where(DocumentExtraction.document_id == document.id)
    )
    extractions = list(result.scalars().all())

    if extractions and normalized_category:
        for extraction in extractions:
            if extraction.review_status == ExtractionReviewStatus.IGNORED:
                continue
            extraction.corrected_esg_category = normalized_category
            extraction.review_status = ExtractionReviewStatus.CORRECTED
        recalculate_document_classification(document, extractions)
    elif extractions and normalized_category is None:
        for extraction in extractions:
            extraction.corrected_esg_category = None
            if extraction.review_status == ExtractionReviewStatus.CORRECTED:
                extraction.review_status = ExtractionReviewStatus.PENDING
        recalculate_document_classification(document, extractions)
    else:
        document.esg_category = normalized_category or None
        if normalized_category is None:
            document.classification_confidence = None

    await session.commit()
    await session.refresh(document)
    return document
