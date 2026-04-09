from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentFileType, DocumentParsingStatus


class DocumentUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    file_size_bytes: int = Field(gt=0, le=50 * 1024 * 1024)


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
    file_size_bytes: int | None
    parsing_status: DocumentParsingStatus
    extracted_text: str | None
    esg_category: str | None
    created_at: datetime


class DocumentUpdateRequest(BaseModel):
    esg_category: str | None = Field(default=None, max_length=255)
