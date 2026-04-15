from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReportStatus


class ReportSectionPayload(BaseModel):
    """Single generated section, as stored inside Report.sections JSONB."""

    key: str
    title: str
    order: int
    heading_level: int
    content: str
    gri_codes_used: list[str] = Field(default_factory=list)
    word_count: int = 0
    status: Literal["completed", "sparse_data", "failed"] = "completed"
    audit: dict[str, Any] | None = None


class GriIndexEntry(BaseModel):
    """Single row of the Sumário GRI, stored inside Report.gri_index JSONB."""

    code: str
    family: str
    standard_text: str
    evidence_excerpt: str | None = None
    section_ref: str | None = None
    status: Literal["atendido", "parcial", "nao_atendido"] = "nao_atendido"
    found_in_text: bool = False


class ReportGapEntry(BaseModel):
    section_key: str | None = None
    group: (
        Literal[
            "vocabulary_warning",
            "content_gap",
            "generation_issue",
        ]
        | None
    ) = None
    category: Literal[
        "forbidden_term",
        "sparse_evidence",
        "missing_enquadramento",
        "missing_gri_code",
        "controlled_term_flag",
        "generation_error",
        "inline_gap_warning",
    ]
    detail: str
    title: str | None = None
    recommendation: str | None = None
    severity: Literal["info", "warning", "critical"] | None = None
    priority: Literal["low", "medium", "high"] | None = None
    missing_data_type: str | None = None
    suggested_document: str | None = None
    related_gri_codes: list[str] | None = None


class ReportListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    version: int
    status: ReportStatus
    created_at: datetime
    updated_at: datetime


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    version: int
    status: ReportStatus
    sections: list[dict[str, Any]] | None
    indicators: dict[str, Any] | list[Any] | None
    charts: dict[str, Any] | list[Any] | None
    gri_index: list[dict[str, Any]] | None
    gaps: list[dict[str, Any]] | None
    exported_docx_s3: str | None
    exported_pdf_s3: str | None
    llm_tokens_used: int | None
    created_at: datetime
    updated_at: datetime


class ReportSectionUpdateRequest(BaseModel):
    content: str = Field(min_length=1)


class GenerateReportRequest(BaseModel):
    """Optional body for POST /generate. If section_keys is provided,
    only those sections are generated. If omitted or empty, all sections run."""

    section_keys: list[str] | None = None
