from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    ClassificationConfidence,
    DocumentFileType,
    DocumentParsingStatus,
    ExtractionReviewStatus,
    ExtractionSourceKind,
)


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
    parsed_payload: dict[str, Any] | None
    parsing_error: str | None
    esg_category: str | None
    classification_confidence: ClassificationConfidence | None
    created_at: datetime


class DocumentExtractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    document_id: UUID
    document_filename: str | None
    source_kind: ExtractionSourceKind
    source_locator: dict[str, Any] | None
    source_snippet: str
    label: str | None
    original_value: str | None
    original_unit: str | None
    original_period: str | None
    original_esg_category: str | None
    corrected_value: str | None
    corrected_unit: str | None
    corrected_period: str | None
    corrected_esg_category: str | None
    effective_value: str | None
    effective_unit: str | None
    effective_period: str | None
    effective_esg_category: str | None
    confidence: ClassificationConfidence | None
    review_status: ExtractionReviewStatus
    correction_reason: str | None
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DocumentExtractionUpdateRequest(BaseModel):
    corrected_value: str | None = None
    corrected_unit: str | None = Field(default=None, max_length=64)
    corrected_period: str | None = Field(default=None, max_length=64)
    corrected_esg_category: str | None = Field(default=None, max_length=255)
    review_status: ExtractionReviewStatus
    correction_reason: str | None = None

    @field_validator(
        "corrected_value",
        "corrected_unit",
        "corrected_period",
        "corrected_esg_category",
        "correction_reason",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None


class ClassificationRebuildResponse(BaseModel):
    documents_processed: int
    extractions_created: int


class DocumentUpdateRequest(BaseModel):
    esg_category: str | None = Field(default=None, max_length=255)

    @field_validator("esg_category", mode="before")
    @classmethod
    def normalize_esg_category(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None
