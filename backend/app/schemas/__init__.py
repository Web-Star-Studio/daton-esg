"""Pydantic schema package placeholder for request and response models."""

from app.schemas.auth import AuthMeResponse
from app.schemas.document import (
    DocumentResponse,
    DocumentUpdateRequest,
    DocumentUploadRequest,
    DocumentUploadResponse,
)
from app.schemas.knowledge import (
    KnowledgeReindexResponse,
    KnowledgeStatusSummary,
    ProjectKnowledgeQuery,
    ProjectKnowledgeQueryResponse,
)
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

__all__ = [
    "AuthMeResponse",
    "DocumentResponse",
    "DocumentUpdateRequest",
    "DocumentUploadRequest",
    "DocumentUploadResponse",
    "KnowledgeReindexResponse",
    "KnowledgeStatusSummary",
    "ProjectCreate",
    "ProjectKnowledgeQuery",
    "ProjectKnowledgeQueryResponse",
    "ProjectResponse",
    "ProjectUpdate",
]
