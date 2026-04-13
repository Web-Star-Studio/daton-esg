from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DocumentRagChunk
from app.schemas.knowledge import RetrievedKnowledgeChunk
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
