from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    ExtractionConfidence,
    ExtractionRunKind,
    ExtractionRunStatus,
    ExtractionSuggestionStatus,
    ExtractionTargetKind,
)

# ---------------------------------------------------------------------------
# LLM-internal models — used with ChatOpenAI.with_structured_output(...)
# ---------------------------------------------------------------------------


class ProvenanceItem(BaseModel):
    """Pointer back to the document chunk that supports a suggestion."""

    document_id: UUID = Field(description="ID of the source Document row.")
    document_name: str = Field(description="Original filename for display.")
    chunk_index: int = Field(description="Index of the chunk inside the document.")
    excerpt: str = Field(
        description="Short verbatim quote (≤400 chars) supporting the extraction.",
        max_length=400,
    )


class MaterialTopicSuggestion(BaseModel):
    """A material topic extracted from the documents."""

    pillar: Literal["E", "S"] = Field(description="E for environmental, S for social.")
    topic: str = Field(
        description=(
            "GRI disclosure code in the format 'GRI X-Y' (e.g. 'GRI 302-1'). "
            "Must be a real GRI code present in the standards reference."
        ),
        min_length=1,
        max_length=64,
    )
    priority: Literal["alta", "media", "baixa"] = Field(
        description="Priority based on signal strength found in the documents."
    )
    confidence: ExtractionConfidence
    reasoning: str = Field(
        description="One sentence explaining why this topic was extracted.",
        max_length=500,
    )
    provenance: list[ProvenanceItem] = Field(min_length=1)


class SdgSuggestion(BaseModel):
    """A priority SDG (Sustainable Development Goal) extracted from documents."""

    ods_number: int = Field(ge=1, le=17)
    objetivo: str = Field(
        description="Short title of the SDG (Portuguese).",
        min_length=1,
        max_length=255,
    )
    acao: str = Field(
        default="",
        description="Concrete action found in the documents (optional).",
        max_length=2000,
    )
    indicador: str = Field(
        default="",
        description="Indicator that tracks this SDG action (optional).",
        max_length=2000,
    )
    resultado: str = Field(
        default="",
        description="Reported result/outcome (optional).",
        max_length=2000,
    )
    confidence: ExtractionConfidence
    reasoning: str = Field(max_length=500)
    provenance: list[ProvenanceItem] = Field(min_length=1)


class IndicatorValueSuggestion(BaseModel):
    """A numeric value extracted to fill an IndicatorTemplate row."""

    template_id: int = Field(
        description="Primary key of the IndicatorTemplate this value belongs to."
    )
    tema: str = Field(min_length=1, max_length=64)
    indicador: str = Field(min_length=1, max_length=255)
    unidade: str = Field(
        description="Unit found in the source. Should match the template's unidade.",
        max_length=64,
    )
    value: str = Field(
        description=(
            "Value as found in the source, normalized to a plain number string "
            "(no thousands separators, dot as decimal). Empty string if no usable "
            "value was found — in that case do NOT emit this suggestion."
        ),
        min_length=1,
        max_length=255,
    )
    period: str | None = Field(
        default=None,
        description="Reporting period (e.g. '2024', 'FY2024'). Optional.",
        max_length=64,
    )
    scope: str | None = Field(
        default=None,
        description="Optional scope qualifier (e.g. 'Escopo 1' for emissions).",
        max_length=64,
    )
    confidence: ExtractionConfidence
    reasoning: str = Field(max_length=500)
    provenance: list[ProvenanceItem] = Field(min_length=1)


class MaterialityExtraction(BaseModel):
    """Top-level structured output for the materiality extractor."""

    material_topics: list[MaterialTopicSuggestion] = Field(default_factory=list)
    sdg_goals: list[SdgSuggestion] = Field(default_factory=list)


class IndicatorsExtraction(BaseModel):
    """Top-level structured output for the indicators extractor."""

    values: list[IndicatorValueSuggestion] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# API schemas — request/response
# ---------------------------------------------------------------------------


class StartExtractionRequest(BaseModel):
    kind: ExtractionRunKind = ExtractionRunKind.BOTH


class ExtractionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    kind: ExtractionRunKind
    status: ExtractionRunStatus
    triggered_by: UUID | None
    model_used: str | None
    documents_considered: list[Any] | None
    summary_stats: dict[str, Any] | None
    error: str | None
    started_at: datetime
    completed_at: datetime | None


class ExtractionSuggestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    project_id: UUID
    target_kind: ExtractionTargetKind
    payload: dict[str, Any]
    confidence: ExtractionConfidence
    confidence_score: Decimal | None
    provenance: list[Any]
    conflict_with_existing: bool
    existing_value_snapshot: dict[str, Any] | None
    status: ExtractionSuggestionStatus
    reviewed_at: datetime | None
    reviewed_by: UUID | None
    reviewer_notes: str | None
    created_at: datetime


class UpdateSuggestionRequest(BaseModel):
    action: Literal["accept", "reject", "edit"]
    payload: dict[str, Any] | None = None
    notes: str | None = None


class BulkUpdateRequest(BaseModel):
    ids: list[UUID] = Field(min_length=1)
    action: Literal["accept_all", "reject_all"]


class ExtractionSuggestionList(BaseModel):
    items: list[ExtractionSuggestionResponse]
    total: int
