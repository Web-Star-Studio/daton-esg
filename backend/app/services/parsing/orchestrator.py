from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Document
from app.models.enums import DocumentFileType, DocumentParsingStatus
from app.services.data_extraction_service import rebuild_document_extractions
from app.services.parsing import ParsedDocumentResult
from app.services.parsing.docx_parser import parse_docx_document
from app.services.parsing.excel_parser import (
    parse_csv_document,
    parse_xlsx_document,
)
from app.services.parsing.pdf_parser import (
    parse_pdf_document,
    should_use_local_pdf_parser,
)
from app.services.storage_service import StorageService, get_storage_service

logger = logging.getLogger(__name__)

MAX_PARSE_ATTEMPTS = 2
PARSING_FAILURE_MESSAGE = "Parsing failed"


async def _parse_document_by_type(
    document: Document,
    *,
    storage_service: StorageService,
) -> ParsedDocumentResult:
    if document.file_type == DocumentFileType.PDF:
        if should_use_local_pdf_parser(storage_service.settings):
            file_bytes = await storage_service.get_object_bytes(key=document.s3_key)
            return await parse_pdf_document(
                file_bytes=file_bytes,
                settings=storage_service.settings,
            )
        return await parse_pdf_document(
            bucket_name=storage_service.bucket_name,
            key=document.s3_key,
            settings=storage_service.settings,
        )

    file_bytes = await storage_service.get_object_bytes(key=document.s3_key)

    if document.file_type == DocumentFileType.XLSX:
        return parse_xlsx_document(file_bytes)
    if document.file_type == DocumentFileType.CSV:
        return parse_csv_document(file_bytes)
    if document.file_type == DocumentFileType.DOCX:
        return parse_docx_document(file_bytes)

    raise ValueError(f"Unsupported parser for file type {document.file_type}")


async def run_document_parsing(
    document_id: UUID,
    *,
    storage: StorageService | None = None,
) -> None:
    storage_service = storage or get_storage_service()

    for attempt in range(1, MAX_PARSE_ATTEMPTS + 1):
        async with SessionLocal() as session:
            async with session.begin():
                result = await session.execute(
                    select(Document).where(Document.id == document_id).with_for_update()
                )
                document = result.scalar_one_or_none()
                if document is None:
                    logger.warning(
                        "document_parsing.document_missing",
                        extra={"document_id": str(document_id)},
                    )
                    return

                if document.parsing_status in {
                    DocumentParsingStatus.PROCESSING,
                    DocumentParsingStatus.COMPLETED,
                }:
                    logger.info(
                        "document_parsing.already_terminal_or_processing",
                        extra={
                            "document_id": str(document.id),
                            "parsing_status": document.parsing_status.value,
                        },
                    )
                    return

                document.parsing_status = DocumentParsingStatus.PROCESSING
                document.parsing_error = None

            try:
                logger.info(
                    "document_parsing.started",
                    extra={
                        "attempt": attempt,
                        "document_id": str(document.id),
                        "file_type": document.file_type.value,
                    },
                )
                parsed_result = await _parse_document_by_type(
                    document,
                    storage_service=storage_service,
                )

                document.extracted_text = (
                    parsed_result.extracted_text or None
                )
                document.parsed_payload = parsed_result.parsed_payload
                document.parsing_error = None
                await session.commit()

                try:
                    await rebuild_document_extractions(
                        session,
                        document=document,
                        parsed_result=parsed_result,
                    )
                    await session.commit()
                except Exception as cls_exc:
                    await session.rollback()
                    logger.warning(
                        "document_parsing.classification_failed",
                        extra={
                            "document_id": str(document.id),
                            "error": str(cls_exc),
                        },
                    )
                    document.parsing_error = (
                        f"Classification failed: {cls_exc}"
                    )
                    await session.commit()

                document.parsing_status = (
                    DocumentParsingStatus.COMPLETED
                )
                await session.commit()

                logger.info(
                    "document_parsing.completed",
                    extra={"document_id": str(document.id)},
                )
                return
            except Exception as exc:
                await session.rollback()
                logger.exception(
                    "document_parsing.failed_attempt",
                    extra={
                        "attempt": attempt,
                        "document_id": str(document.id),
                    },
                )
                if attempt < MAX_PARSE_ATTEMPTS:
                    document.parsing_status = (
                        DocumentParsingStatus.PENDING
                    )
                    document.extracted_text = None
                    document.parsed_payload = None
                    document.parsing_error = None
                    await session.commit()
                    continue

                document.parsing_status = DocumentParsingStatus.FAILED
                document.extracted_text = None
                document.parsed_payload = None
                document.parsing_error = PARSING_FAILURE_MESSAGE
                await session.commit()
                logger.error(
                    "document_parsing.failed",
                    extra={
                        "document_id": str(document.id),
                        "error": str(exc),
                    },
                )
                return
