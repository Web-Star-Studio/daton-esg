import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import (
    ExtractionConfidence,
    ExtractionSuggestionStatus,
    ExtractionTargetKind,
)

if TYPE_CHECKING:
    from app.models.extraction_run import ExtractionRun
    from app.models.project import Project
    from app.models.user import User


class ExtractionSuggestion(Base):
    __tablename__ = "extraction_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extraction_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_kind: Mapped[ExtractionTargetKind] = mapped_column(
        Enum(
            ExtractionTargetKind,
            name="extraction_target_kind",
            values_callable=lambda enum: [m.value for m in enum],
        ),
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[ExtractionConfidence] = mapped_column(
        Enum(
            ExtractionConfidence,
            name="extraction_confidence",
            values_callable=lambda enum: [m.value for m in enum],
        ),
        nullable=False,
    )
    confidence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    provenance: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    conflict_with_existing: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    existing_value_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    status: Mapped[ExtractionSuggestionStatus] = mapped_column(
        Enum(
            ExtractionSuggestionStatus,
            name="extraction_suggestion_status",
            values_callable=lambda enum: [m.value for m in enum],
        ),
        nullable=False,
        default=ExtractionSuggestionStatus.PENDING,
        server_default=text("'pending'::extraction_suggestion_status"),
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    run: Mapped["ExtractionRun"] = relationship(
        "ExtractionRun", back_populates="suggestions"
    )
    project: Mapped["Project"] = relationship(
        "Project", back_populates="extraction_suggestions"
    )
    reviewer: Mapped["User | None"] = relationship("User", foreign_keys=[reviewed_by])
