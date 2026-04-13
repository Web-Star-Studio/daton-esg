from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.models import Document, DocumentRagChunk, Project
from app.models.enums import DocumentIndexingStatus
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.storage_service import StorageService, get_storage_service
from app.services.text_extraction_service import (
    ExtractedTextChunk,
    extract_document_text_chunks,
)
from app.services.vector_store import VectorRecord, VectorStore, get_vector_store

logger = logging.getLogger(__name__)

INDEXING_FAILURE_MESSAGE = "Não foi possível indexar este documento."
PDF_TEXTLESS_FAILURE_MESSAGE = "O PDF não possui texto extraível para indexação."


def _project_namespace(project_id: UUID) -> str:
    return str(project_id)


def _document_pinecone_id(project_id: UUID, document_id: UUID, chunk_index: int) -> str:
    return f"project:{project_id}:document:{document_id}:chunk:{chunk_index}"


def _project_metadata_pinecone_id(project_id: UUID) -> str:
    return f"project:{project_id}:metadata"


def _build_project_metadata_content(project: Project) -> str:
    lines = [
        f"Projeto: {project.org_name}",
        f"Status: {project.status.value}",
        f"Ano-base: {project.base_year}",
    ]
    if project.org_sector:
        lines.append(f"Setor: {project.org_sector}")
    if project.org_size:
        lines.append(f"Porte: {project.org_size.value}")
    if project.org_location:
        lines.append(f"Localização: {project.org_location}")
    if project.scope:
        lines.append(f"Escopo: {project.scope}")
    if project.material_topics:
        lines.append(
            "Tópicos materiais: "
            + json.dumps(project.material_topics, ensure_ascii=False)
        )
    if project.sdg_goals:
        lines.append("ODS: " + json.dumps(project.sdg_goals, ensure_ascii=False))
    return "\n".join(lines)


def _build_project_metadata_chunk(project: Project) -> ExtractedTextChunk:
    return ExtractedTextChunk(
        chunk_index=0,
        content=_build_project_metadata_content(project),
        source_type="project_metadata",
        source_locator={"project_id": str(project.id)},
        metadata={"project_id": str(project.id)},
    )


def _build_vector_metadata(
    *,
    project: Project,
    document: Document | None,
    chunk: ExtractedTextChunk,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "project_id": str(project.id),
        "chunk_index": chunk.chunk_index,
        "source_type": chunk.source_type,
    }
    if document is None:
        metadata.update(
            {
                "filename": "__project_metadata__",
                "file_type": "project_metadata",
            }
        )
    else:
        metadata.update(
            {
                "document_id": str(document.id),
                "filename": document.filename,
                "directory_key": document.directory_key,
                "file_type": document.file_type.value,
            }
        )
    return metadata


def _build_chunk_row(
    *,
    project: Project,
    document: Document | None,
    chunk: ExtractedTextChunk,
    pinecone_id: str,
) -> DocumentRagChunk:
    metadata_payload = _build_vector_metadata(
        project=project,
        document=document,
        chunk=chunk,
    )
    return DocumentRagChunk(
        project_id=project.id,
        document_id=document.id if document else None,
        chunk_index=chunk.chunk_index,
        pinecone_id=pinecone_id,
        content=chunk.content,
        char_count=len(chunk.content),
        source_type=chunk.source_type,
        source_locator=chunk.source_locator,
        directory_key=document.directory_key if document else None,
        metadata_payload=metadata_payload,
    )


def _sanitize_indexing_error(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        message = str(exc)
        if "extractable text" in message:
            return PDF_TEXTLESS_FAILURE_MESSAGE
    return INDEXING_FAILURE_MESSAGE


async def _load_document_for_indexing(
    session: AsyncSession,
    document_id: UUID,
) -> Document | None:
    result = await session.execute(
        select(Document)
        .options(selectinload(Document.project))
        .where(Document.id == document_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def _mark_document_processing(
    session: AsyncSession,
    document_id: UUID,
) -> Document | None:
    async with session.begin():
        document = await _load_document_for_indexing(session, document_id)
        if document is None:
            return None
        if document.indexing_status == DocumentIndexingStatus.PROCESSING:
            return None
        document.indexing_status = DocumentIndexingStatus.PROCESSING
        document.indexing_error = None
        document.indexed_at = None
    return document


async def _finalize_indexing_failure(
    session: AsyncSession,
    *,
    document_id: UUID,
    exc: Exception,
) -> None:
    await session.rollback()
    async with session.begin():
        document = await _load_document_for_indexing(session, document_id)
        if document is None:
            return
        document.indexing_status = DocumentIndexingStatus.FAILED
        document.indexing_error = _sanitize_indexing_error(exc)
        document.indexed_at = None


async def run_document_rag_ingestion(
    *,
    session: AsyncSession,
    document_id: UUID,
    storage: StorageService,
    vector_store: VectorStore,
    embedding_service: EmbeddingService,
) -> None:
    document = await _mark_document_processing(session, document_id)
    if document is None:
        return

    project = document.project
    if project is None:
        await _finalize_indexing_failure(
            session,
            document_id=document_id,
            exc=ValueError("Project not found for document indexing"),
        )
        return

    try:
        logger.info(
            "document_indexing.started",
            extra={"project_id": str(project.id), "document_id": str(document.id)},
        )
        file_bytes = await storage.get_object_bytes(key=document.s3_key)
        document_chunks = extract_document_text_chunks(document, file_bytes)
        metadata_chunk = _build_project_metadata_chunk(project)
        namespace = _project_namespace(project.id)
        all_chunks = document_chunks + [metadata_chunk]
        embeddings = await embedding_service.embed_texts(
            [chunk.content for chunk in all_chunks]
        )

        vector_records: list[VectorRecord] = []
        chunk_rows: list[DocumentRagChunk] = []
        for chunk, embedding in zip(document_chunks, embeddings[:-1], strict=True):
            pinecone_id = _document_pinecone_id(
                project.id, document.id, chunk.chunk_index
            )
            vector_records.append(
                VectorRecord(
                    id=pinecone_id,
                    values=embedding,
                    metadata=_build_vector_metadata(
                        project=project,
                        document=document,
                        chunk=chunk,
                    ),
                )
            )
            chunk_rows.append(
                _build_chunk_row(
                    project=project,
                    document=document,
                    chunk=chunk,
                    pinecone_id=pinecone_id,
                )
            )

        metadata_embedding = embeddings[-1]
        metadata_id = _project_metadata_pinecone_id(project.id)
        vector_records.append(
            VectorRecord(
                id=metadata_id,
                values=metadata_embedding,
                metadata=_build_vector_metadata(
                    project=project,
                    document=None,
                    chunk=metadata_chunk,
                ),
            )
        )
        metadata_row = _build_chunk_row(
            project=project,
            document=None,
            chunk=metadata_chunk,
            pinecone_id=metadata_id,
        )

        existing_rows = list(
            (
                await session.execute(
                    select(DocumentRagChunk).where(
                        DocumentRagChunk.project_id == project.id,
                        (
                            (DocumentRagChunk.document_id == document.id)
                            | (
                                DocumentRagChunk.document_id.is_(None)
                                & (DocumentRagChunk.source_type == "project_metadata")
                            )
                        ),
                    )
                )
            ).scalars()
        )
        existing_ids = {
            row.pinecone_id for row in existing_rows if row.document_id == document.id
        }

        await vector_store.upsert(namespace=namespace, records=vector_records)
        new_document_ids = {
            _document_pinecone_id(project.id, document.id, chunk.chunk_index)
            for chunk in document_chunks
        }
        stale_document_ids = sorted(existing_ids - new_document_ids)
        if stale_document_ids:
            await vector_store.delete(namespace=namespace, ids=stale_document_ids)

        await session.execute(
            delete(DocumentRagChunk).where(
                DocumentRagChunk.project_id == project.id,
                (
                    (DocumentRagChunk.document_id == document.id)
                    | (
                        DocumentRagChunk.document_id.is_(None)
                        & (DocumentRagChunk.source_type == "project_metadata")
                    )
                ),
            )
        )
        session.add_all([*chunk_rows, metadata_row])
        document.indexing_status = DocumentIndexingStatus.INDEXED
        document.indexing_error = None
        document.indexed_at = datetime.now(timezone.utc)
        await session.commit()
        logger.info(
            "document_indexing.completed",
            extra={
                "project_id": str(project.id),
                "document_id": str(document.id),
                "chunk_count": len(document_chunks),
            },
        )
    except Exception as exc:
        logger.exception(
            "document_indexing.failed",
            extra={"document_id": str(document_id)},
        )
        await _finalize_indexing_failure(session, document_id=document_id, exc=exc)


async def run_document_rag_ingestion_task(document_id: UUID) -> None:
    async with SessionLocal() as session:
        try:
            vector_store = get_vector_store()
            embedding_service = get_embedding_service()
        except Exception as exc:
            logger.exception(
                "document_indexing.bootstrap_failed",
                extra={"document_id": str(document_id)},
            )
            await _finalize_indexing_failure(session, document_id=document_id, exc=exc)
            return

        await run_document_rag_ingestion(
            session=session,
            document_id=document_id,
            storage=get_storage_service(),
            vector_store=vector_store,
            embedding_service=embedding_service,
        )


async def delete_document_rag_knowledge(
    session: AsyncSession,
    *,
    document: Document,
) -> None:
    chunk_rows = list(
        (
            await session.execute(
                select(DocumentRagChunk).where(
                    DocumentRagChunk.document_id == document.id
                )
            )
        ).scalars()
    )
    if not chunk_rows:
        return
    try:
        await get_vector_store().delete(
            namespace=_project_namespace(document.project_id),
            ids=[row.pinecone_id for row in chunk_rows],
        )
    except RuntimeError:
        logger.info(
            "document_indexing.vector_store_unavailable_on_delete",
            extra={"document_id": str(document.id)},
        )
    except Exception:
        logger.exception(
            "document_indexing.delete_vectors_failed",
            extra={"document_id": str(document.id)},
        )


async def sync_document_rag_metadata(
    session: AsyncSession,
    *,
    document: Document,
) -> None:
    chunk_rows = list(
        (
            await session.execute(
                select(DocumentRagChunk).where(
                    DocumentRagChunk.document_id == document.id
                )
            )
        ).scalars()
    )
    if not chunk_rows:
        return

    for row in chunk_rows:
        row.directory_key = document.directory_key
        metadata_payload = dict(row.metadata_payload or {})
        metadata_payload["directory_key"] = document.directory_key
        row.metadata_payload = metadata_payload
    await session.commit()

    try:
        await get_vector_store().update_metadata(
            namespace=_project_namespace(document.project_id),
            ids=[row.pinecone_id for row in chunk_rows],
            metadata={"directory_key": document.directory_key},
        )
    except RuntimeError:
        logger.info(
            "document_indexing.vector_store_unavailable_on_move",
            extra={"document_id": str(document.id)},
        )
    except Exception:
        logger.exception(
            "document_indexing.update_metadata_failed",
            extra={"document_id": str(document.id)},
        )


async def get_project_knowledge_status(
    session: AsyncSession,
    *,
    project_id: UUID,
) -> dict[str, Any]:
    documents = list(
        (
            await session.execute(
                select(Document).where(Document.project_id == project_id)
            )
        ).scalars()
    )
    total_chunks = (
        await session.execute(
            select(func.count(DocumentRagChunk.id)).where(
                DocumentRagChunk.project_id == project_id
            )
        )
    ).scalar_one()

    indexed_at_values = [
        document.indexed_at for document in documents if document.indexed_at
    ]
    return {
        "total_documents": len(documents),
        "pending_documents": sum(
            document.indexing_status == DocumentIndexingStatus.PENDING
            for document in documents
        ),
        "processing_documents": sum(
            document.indexing_status == DocumentIndexingStatus.PROCESSING
            for document in documents
        ),
        "indexed_documents": sum(
            document.indexing_status == DocumentIndexingStatus.INDEXED
            for document in documents
        ),
        "failed_documents": sum(
            document.indexing_status == DocumentIndexingStatus.FAILED
            for document in documents
        ),
        "total_chunks": int(total_chunks or 0),
        "last_indexed_at": max(indexed_at_values) if indexed_at_values else None,
    }


async def list_project_document_ids_for_reindex(
    session: AsyncSession,
    *,
    project_id: UUID,
) -> list[UUID]:
    result = await session.execute(
        select(Document.id).where(Document.project_id == project_id)
    )
    return list(result.scalars())
