from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DocumentRagChunk
from app.schemas.knowledge import FrameworkReferenceChunk, RetrievedKnowledgeChunk
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.vector_store import VectorStore, get_vector_store


async def retrieve_project_context(
    session: AsyncSession,
    *,
    project_id: UUID,
    query: str,
    top_k: int = 8,
    directory_key: str | None = None,
    document_id: UUID | None = None,
    embedding_service: EmbeddingService | None = None,
    vector_store: VectorStore | None = None,
) -> list[RetrievedKnowledgeChunk]:
    current_embedding_service = embedding_service or get_embedding_service()
    current_vector_store = vector_store or get_vector_store()
    vector = await current_embedding_service.embed_query(query)
    metadata_filter: dict[str, object] | None = None
    if directory_key or document_id:
        metadata_filter = {}
        if directory_key:
            metadata_filter["directory_key"] = {"$eq": directory_key}
        if document_id:
            metadata_filter["document_id"] = {"$eq": str(document_id)}

    matches = await current_vector_store.query(
        namespace=str(project_id),
        vector=vector,
        top_k=top_k,
        metadata_filter=metadata_filter,
    )
    if not matches:
        return []

    pinecone_ids = [match.id for match in matches]
    chunk_rows = list(
        (
            await session.execute(
                select(DocumentRagChunk).where(
                    DocumentRagChunk.pinecone_id.in_(pinecone_ids)
                )
            )
        ).scalars()
    )
    rows_by_pinecone_id = {row.pinecone_id: row for row in chunk_rows}

    results: list[RetrievedKnowledgeChunk] = []
    for match in matches:
        row = rows_by_pinecone_id.get(match.id)
        if row is None:
            continue
        metadata = dict(row.metadata_payload or {})
        results.append(
            RetrievedKnowledgeChunk(
                document_id=row.document_id,
                filename=str(metadata.get("filename") or "__project_metadata__"),
                directory_key=row.directory_key,
                file_type=str(metadata.get("file_type") or row.source_type),
                content=row.content,
                score=match.score,
                chunk_index=row.chunk_index,
                source_type=row.source_type,
                source_locator=row.source_locator,
                metadata=row.metadata_payload,
            )
        )
    return results


async def retrieve_framework_reference(
    *,
    query: str,
    namespace: str,
    top_k: int = 3,
    metadata_filter: dict[str, Any] | None = None,
    embedding_service: EmbeddingService | None = None,
    vector_store: VectorStore | None = None,
) -> list[FrameworkReferenceChunk]:
    """Retrieve framework reference chunks (e.g., GRI Standards) from a shared
    Pinecone namespace. Unlike ``retrieve_project_context``, this does not join
    back to any DB table — framework content lives in Pinecone metadata.

    The caller is responsible for presenting the returned chunks to the LLM as
    conceptual framing, not as organization evidence.
    """
    if not namespace.startswith("__reference__"):
        raise ValueError(
            "retrieve_framework_reference refuses non-reference namespaces"
        )
    current_embedding_service = embedding_service or get_embedding_service()
    current_vector_store = vector_store or get_vector_store()
    vector = await current_embedding_service.embed_query(query)
    matches = await current_vector_store.query(
        namespace=namespace,
        vector=vector,
        top_k=top_k,
        metadata_filter=metadata_filter,
    )
    results: list[FrameworkReferenceChunk] = []
    for match in matches:
        metadata = dict(match.metadata or {})
        content = str(metadata.get("content") or "").strip()
        if not content:
            continue
        page_value = metadata.get("page")
        page = (
            int(page_value)
            if isinstance(page_value, (int, float)) and page_value is not None
            else None
        )
        results.append(
            FrameworkReferenceChunk(
                framework=str(metadata.get("framework") or ""),
                version=str(metadata.get("version") or ""),
                code=str(metadata.get("code") or "") or None,
                family=str(metadata.get("family") or "") or None,
                content=content,
                score=match.score,
                source=str(metadata.get("source") or "") or None,
                page=page,
            )
        )
    return results
