from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class KnowledgeStatusSummary(BaseModel):
    total_documents: int
    pending_documents: int
    processing_documents: int
    indexed_documents: int
    failed_documents: int
    total_chunks: int
    last_indexed_at: datetime | None


class KnowledgeReindexResponse(BaseModel):
    project_id: UUID
    queued_documents: int


class RetrievedKnowledgeChunk(BaseModel):
    document_id: UUID | None
    filename: str
    directory_key: str | None
    file_type: str
    content: str
    score: float
    chunk_index: int
    source_type: str
    source_locator: dict[str, object] | list[object] | None
    metadata: dict[str, object] | list[object] | None


class ProjectKnowledgeQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    top_k: int = 8
    directory_key: str | None = None
    document_id: UUID | None = None


class ProjectKnowledgeQueryResponse(BaseModel):
    chunks: list[RetrievedKnowledgeChunk]
