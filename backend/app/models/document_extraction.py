import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import (
    ClassificationConfidence,
    ExtractionReviewStatus,
    ExtractionSourceKind,
)


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_kind: Mapped[ExtractionSourceKind] = mapped_column(
        Enum(
            ExtractionSourceKind,
            name="extraction_source_kind",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    source_locator: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    source_snippet: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    original_period: Mapped[str | None] = mapped_column(String(64), nullable=True)
    original_esg_category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    corrected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    corrected_period: Mapped[str | None] = mapped_column(String(64), nullable=True)
    corrected_esg_category: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    confidence: Mapped[ClassificationConfidence | None] = mapped_column(
        Enum(
            ClassificationConfidence,
            name="classification_confidence",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=True,
    )
    review_status: Mapped[ExtractionReviewStatus] = mapped_column(
        Enum(
            ExtractionReviewStatus,
            name="extraction_review_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=ExtractionReviewStatus.PENDING,
        server_default=text("'pending'::extraction_review_status"),
    )
    correction_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    document = relationship("Document", back_populates="extractions")
    project = relationship("Project", back_populates="document_extractions")
    reviewed_by = relationship("User")

    @property
    def effective_value(self) -> str | None:
        return self.corrected_value if self.corrected_value is not None else self.original_value

    @property
    def effective_unit(self) -> str | None:
        return self.corrected_unit if self.corrected_unit is not None else self.original_unit

    @property
    def effective_period(self) -> str | None:
        return (
            self.corrected_period
            if self.corrected_period is not None
            else self.original_period
        )

    @property
    def effective_esg_category(self) -> str | None:
        return (
            self.corrected_esg_category
            if self.corrected_esg_category is not None
            else self.original_esg_category
        )

    @property
    def document_filename(self) -> str | None:
        return self.document.filename if self.document else None
