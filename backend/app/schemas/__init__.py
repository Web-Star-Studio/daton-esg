"""Pydantic schema package placeholder for request and response models."""

from app.schemas.auth import AuthMeResponse
from app.schemas.document import (
    ClassificationRebuildResponse,
    DocumentExtractionResponse,
    DocumentExtractionUpdateRequest,
    DocumentResponse,
    DocumentUpdateRequest,
    DocumentUploadRequest,
    DocumentUploadResponse,
)
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

__all__ = [
    "AuthMeResponse",
    "ClassificationRebuildResponse",
    "DocumentExtractionResponse",
    "DocumentExtractionUpdateRequest",
    "DocumentResponse",
    "DocumentUpdateRequest",
    "DocumentUploadRequest",
    "DocumentUploadResponse",
    "ProjectCreate",
    "ProjectResponse",
    "ProjectUpdate",
]
