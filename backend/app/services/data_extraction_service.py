from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Document, DocumentExtraction, Project, User
from app.models.enums import (
    ClassificationConfidence,
    DocumentParsingStatus,
    ExtractionReviewStatus,
    ExtractionSourceKind,
    ProjectStatus,
)
from app.services.classification_service import (
    ClassificationInput,
    classify_document_extractions,
)
from app.services.parsing import ParsedDocumentResult

MAX_EXTRACTION_LIST_LIMIT = 1000


def _normalize_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def json_signature(value: dict[str, Any] | None) -> str:
    return json.dumps(value or {}, sort_keys=True, ensure_ascii=False)


def _row_to_snippet(
    header: list[str | None] | None,
    row: list[str | None],
) -> str:
    if header:
        pairs = []
        for index, cell in enumerate(row):
            header_value = (
                _normalize_string(header[index])
                if index < len(header)
                else None
            )
            cell_value = _normalize_string(cell)
            if not cell_value:
                continue
            if header_value:
                pairs.append(f"{header_value}: {cell_value}")
            else:
                pairs.append(cell_value)
        if pairs:
            return " | ".join(pairs)

    return " | ".join(
        cell for cell in (_normalize_string(item) for item in row) if cell
    )


def build_document_extractions(
    document: Document,
    parsed_result: ParsedDocumentResult,
) -> list[DocumentExtraction]:
    payload = parsed_result.parsed_payload
    extractions: list[DocumentExtraction] = []

    if "pages" in payload:
        for page in payload.get("pages", []):
            page_number = int(page.get("page_number", 1))
            page_text = _normalize_string(page.get("text"))
            if page_text:
                extractions.append(
                    DocumentExtraction(
                        project_id=document.project_id,
                        document_id=document.id,
                        source_kind=ExtractionSourceKind.PARAGRAPH,
                        source_locator={"page_number": page_number},
                        source_snippet=page_text,
                    )
                )

            for row_index, table in enumerate(page.get("tables", []), start=1):
                header = table.get("header") or []
                rows = table.get("rows") or []
                for data_index, row in enumerate(rows, start=1):
                    snippet = _row_to_snippet(header, row)
                    if not snippet:
                        continue
                    extractions.append(
                        DocumentExtraction(
                            project_id=document.project_id,
                            document_id=document.id,
                            source_kind=ExtractionSourceKind.TABLE_ROW,
                            source_locator={
                                "page_number": page_number,
                                "table_index": row_index,
                                "row_index": data_index,
                            },
                            source_snippet=snippet,
                        )
                    )
        return extractions

    if "blocks" in payload:
        for block_index, block in enumerate(payload.get("blocks", []), start=1):
            text = _normalize_string(block.get("text"))
            if not text:
                continue
            extractions.append(
                DocumentExtraction(
                    project_id=document.project_id,
                    document_id=document.id,
                    source_kind=ExtractionSourceKind.PARAGRAPH,
                    source_locator={
                        "block_index": block_index,
                        "block_type": block.get("type"),
                        "level": block.get("level"),
                    },
                    source_snippet=text,
                )
            )

        for table_index, table in enumerate(payload.get("tables", []), start=1):
            header = table.get("header") or []
            rows = table.get("rows") or []
            for row_index, row in enumerate(rows, start=1):
                snippet = _row_to_snippet(header, row)
                if not snippet:
                    continue
                extractions.append(
                    DocumentExtraction(
                        project_id=document.project_id,
                        document_id=document.id,
                        source_kind=ExtractionSourceKind.TABLE_ROW,
                        source_locator={
                            "table_index": table_index,
                            "row_index": row_index,
                        },
                        source_snippet=snippet,
                    )
                )
        return extractions

    if payload.get("format") == "xlsx":
        for sheet in payload.get("sheets", []):
            sheet_name = sheet.get("sheet_name")
            header = sheet.get("header") or []
            rows = sheet.get("rows") or []
            for row_index, row in enumerate(rows, start=1):
                snippet = _row_to_snippet(header, row)
                if not snippet:
                    continue
                extractions.append(
                    DocumentExtraction(
                        project_id=document.project_id,
                        document_id=document.id,
                        source_kind=ExtractionSourceKind.SHEET_ROW,
                        source_locator={
                            "sheet_name": sheet_name,
                            "row_index": row_index,
                        },
                        source_snippet=snippet,
                    )
                )
        return extractions

    if payload.get("format") == "csv":
        header = payload.get("header") or []
        rows = payload.get("rows") or []
        for row_index, row in enumerate(rows, start=1):
            snippet = _row_to_snippet(header, row)
            if not snippet:
                continue
            extractions.append(
                DocumentExtraction(
                    project_id=document.project_id,
                    document_id=document.id,
                    source_kind=ExtractionSourceKind.SHEET_ROW,
                    source_locator={"row_index": row_index},
                    source_snippet=snippet,
                )
            )
        return extractions

    return extractions


def recalculate_document_classification(
    document: Document,
    extractions: list[DocumentExtraction],
) -> None:
    effective_extractions = [
        extraction
        for extraction in extractions
        if extraction.review_status != ExtractionReviewStatus.IGNORED
        and extraction.effective_esg_category
    ]
    if not effective_extractions:
        document.esg_category = None
        document.classification_confidence = None
        return

    confidence_weights = {
        ClassificationConfidence.HIGH: 3,
        ClassificationConfidence.MEDIUM: 2,
        ClassificationConfidence.LOW: 1,
        None: 0,
    }
    category_scores: dict[str, int] = defaultdict(int)
    category_counts: dict[str, int] = defaultdict(int)

    for extraction in effective_extractions:
        category = extraction.effective_esg_category
        if not category:
            continue
        category_counts[category] += 1
        category_scores[category] += confidence_weights.get(extraction.confidence, 0)

    dominant_category = max(
        category_scores,
        key=lambda category: (
            category_scores[category],
            category_counts[category],
            category,
        ),
    )
    document.esg_category = dominant_category

    category_extractions = [
        extraction
        for extraction in effective_extractions
        if extraction.effective_esg_category == dominant_category
    ]
    average_score = sum(
        confidence_weights.get(extraction.confidence, 0)
        for extraction in category_extractions
    ) / max(len(category_extractions), 1)

    if average_score >= 2.5:
        document.classification_confidence = ClassificationConfidence.HIGH
    elif average_score >= 1.5:
        document.classification_confidence = ClassificationConfidence.MEDIUM
    else:
        document.classification_confidence = ClassificationConfidence.LOW


async def rebuild_document_extractions(
    session: AsyncSession,
    *,
    document: Document,
    parsed_result: ParsedDocumentResult,
) -> list[DocumentExtraction]:
    existing_result = await session.execute(
        select(DocumentExtraction).where(DocumentExtraction.document_id == document.id)
    )
    existing_extractions = list(existing_result.scalars().all())
    existing_by_signature = {
        (
            extraction.source_kind.value,
            json_signature(extraction.source_locator),
            extraction.source_snippet,
        ): extraction
        for extraction in existing_extractions
    }

    extractions = build_document_extractions(document, parsed_result)
    session.add_all(extractions)
    await session.flush()

    classified = await classify_document_extractions(
        [
            ClassificationInput(
                extraction_id=str(extraction.id),
                source_kind=extraction.source_kind.value,
                source_snippet=extraction.source_snippet,
                source_locator=extraction.source_locator,
            )
            for extraction in extractions
        ]
    )

    await session.execute(
        delete(DocumentExtraction).where(
            DocumentExtraction.document_id == document.id,
            DocumentExtraction.id.notin_(
                [e.id for e in extractions]
            ),
        )
    )
    classified_by_id = {result.extraction_id: result for result in classified}

    for extraction in extractions:
        classification = classified_by_id[str(extraction.id)]
        existing = existing_by_signature.get(
            (
                extraction.source_kind.value,
                json_signature(extraction.source_locator),
                extraction.source_snippet,
            )
        )
        extraction.label = classification.label
        extraction.original_value = classification.original_value
        extraction.original_unit = classification.original_unit
        extraction.original_period = classification.original_period
        extraction.original_esg_category = classification.original_esg_category
        extraction.confidence = classification.confidence
        if existing is not None:
            extraction.review_status = existing.review_status
            extraction.corrected_value = existing.corrected_value
            extraction.corrected_unit = existing.corrected_unit
            extraction.corrected_period = existing.corrected_period
            extraction.corrected_esg_category = existing.corrected_esg_category
            extraction.correction_reason = existing.correction_reason
            extraction.reviewed_by_user_id = existing.reviewed_by_user_id
            extraction.reviewed_at = existing.reviewed_at
        else:
            extraction.review_status = ExtractionReviewStatus.PENDING
            extraction.corrected_value = None
            extraction.corrected_unit = None
            extraction.corrected_period = None
            extraction.corrected_esg_category = None
            extraction.correction_reason = None
            extraction.reviewed_by_user_id = None
            extraction.reviewed_at = None

    recalculate_document_classification(document, extractions)
    return extractions


async def list_data_extractions_for_project(
    session: AsyncSession,
    *,
    project_id: UUID,
    document_id: UUID | None = None,
    category: str | None = None,
    confidence: ClassificationConfidence | None = None,
    review_status: ExtractionReviewStatus | None = None,
    search: str | None = None,
    limit: int = MAX_EXTRACTION_LIST_LIMIT,
    offset: int = 0,
) -> list[DocumentExtraction]:
    normalized_limit = max(1, min(limit, MAX_EXTRACTION_LIST_LIMIT))
    normalized_offset = max(0, offset)
    query = (
        select(DocumentExtraction)
        .options(selectinload(DocumentExtraction.document))
        .where(DocumentExtraction.project_id == project_id)
        .order_by(DocumentExtraction.created_at.asc())
    )

    if document_id is not None:
        query = query.where(DocumentExtraction.document_id == document_id)
    if category:
        query = query.where(
            func.coalesce(
                DocumentExtraction.corrected_esg_category,
                DocumentExtraction.original_esg_category,
            )
            == category
        )
    if confidence is not None:
        query = query.where(DocumentExtraction.confidence == confidence)
    if review_status is not None:
        query = query.where(DocumentExtraction.review_status == review_status)
    if search:
        normalized_search = f"%{search.strip()}%"
        query = query.where(
            DocumentExtraction.source_snippet.ilike(normalized_search)
            | DocumentExtraction.label.ilike(normalized_search)
        )

    result = await session.execute(
        query.limit(normalized_limit).offset(normalized_offset)
    )
    return list(result.scalars().all())


async def get_data_extraction_for_project(
    session: AsyncSession,
    *,
    project_id: UUID,
    extraction_id: UUID,
) -> DocumentExtraction:
    result = await session.execute(
        select(DocumentExtraction)
        .options(selectinload(DocumentExtraction.document))
        .where(
            DocumentExtraction.project_id == project_id,
            DocumentExtraction.id == extraction_id,
        )
    )
    extraction = result.scalar_one_or_none()
    if extraction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data extraction not found",
        )
    return extraction


async def update_data_extraction_review(
    session: AsyncSession,
    *,
    extraction: DocumentExtraction,
    project: Project,
    reviewer: User,
    corrected_value: str | None,
    corrected_unit: str | None,
    corrected_period: str | None,
    corrected_esg_category: str | None,
    review_status: ExtractionReviewStatus,
    correction_reason: str | None,
) -> DocumentExtraction:
    extraction.corrected_value = corrected_value
    extraction.corrected_unit = corrected_unit
    extraction.corrected_period = corrected_period
    extraction.corrected_esg_category = corrected_esg_category
    extraction.review_status = review_status
    extraction.correction_reason = correction_reason
    extraction.reviewed_by_user_id = reviewer.id
    extraction.reviewed_at = datetime.now(timezone.utc)

    document = extraction.document
    if document is None:
        document_result = await session.execute(
            select(Document).where(Document.id == extraction.document_id)
        )
        document = document_result.scalar_one()

    extraction_result = await session.execute(
        select(DocumentExtraction).where(
            DocumentExtraction.document_id == extraction.document_id
        )
    )
    document_extractions = list(extraction_result.scalars().all())
    recalculate_document_classification(document, document_extractions)
    await session.commit()
    await session.refresh(extraction)
    await session.refresh(document)
    await session.refresh(project)
    return extraction


async def rebuild_project_classification(
    session: AsyncSession,
    *,
    project: Project,
) -> tuple[int, int]:
    result = await session.execute(
        select(Document).where(
            Document.project_id == project.id,
            Document.parsing_status == DocumentParsingStatus.COMPLETED,
        )
    )
    documents = list(result.scalars().all())
    extractions_created = 0

    for document in documents:
        parsed_payload = document.parsed_payload or {}
        parsed_result = ParsedDocumentResult(
            extracted_text=document.extracted_text or "",
            parsed_payload=parsed_payload,
        )
        extractions = await rebuild_document_extractions(
            session,
            document=document,
            parsed_result=parsed_result,
        )
        extractions_created += len(extractions)

    await session.commit()
    return len(documents), extractions_created


async def validate_project_classification(
    session: AsyncSession,
    *,
    project: Project,
) -> Project:
    document_result = await session.execute(
        select(Document).where(Document.project_id == project.id)
    )
    documents = list(document_result.scalars().all())
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Envie ao menos um documento antes de validar os dados.",
        )

    has_unprocessed = any(
        document.parsing_status != DocumentParsingStatus.COMPLETED
        for document in documents
    )
    if has_unprocessed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Todos os documentos precisam estar processados antes da validação.",
        )

    pending_result = await session.execute(
        select(func.count(DocumentExtraction.id)).where(
            DocumentExtraction.project_id == project.id,
            DocumentExtraction.review_status == ExtractionReviewStatus.PENDING,
        )
    )
    pending_count = pending_result.scalar_one()
    if pending_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Revise todas as extrações antes de prosseguir.",
        )

    total_result = await session.execute(
        select(func.count(DocumentExtraction.id)).where(
            DocumentExtraction.project_id == project.id
        )
    )
    total_extractions = total_result.scalar_one()
    if total_extractions == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nenhum dado extraído está disponível para validação.",
        )

    project.status = ProjectStatus.PRELIMINARY_REPORT
    await session.commit()
    await session.refresh(project)
    return project
