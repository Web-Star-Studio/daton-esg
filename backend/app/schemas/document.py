from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import DocumentFileType, DocumentIndexingStatus
from app.services.document_directories import is_valid_directory_key


class DocumentUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    file_size_bytes: int = Field(gt=0, le=50 * 1024 * 1024)
    directory_key: str = Field(min_length=1, max_length=128)

    @field_validator("directory_key", mode="before")
    @classmethod
    def normalize_directory_key(cls, value: str) -> str:
        normalized = value.strip()
        if not is_valid_directory_key(normalized):
            raise ValueError("Unsupported document directory")
        return normalized


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    upload_url: str
    s3_key: str
    content_type: str
    expires_in_seconds: int = 900


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    filename: str
    file_type: DocumentFileType
    s3_key: str
    directory_key: str
    file_size_bytes: int | None
    indexing_status: DocumentIndexingStatus
    indexing_error: str | None
    indexed_at: datetime | None
    created_at: datetime


class DocumentUpdateRequest(BaseModel):
    directory_key: str = Field(min_length=1, max_length=128)

    @field_validator("directory_key", mode="before")
    @classmethod
    def normalize_directory_key(cls, value: str) -> str:
        normalized = value.strip()
        if not is_valid_directory_key(normalized):
            raise ValueError("Unsupported document directory")
        return normalized
