import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ExtractionRunKind, ExtractionRunStatus

if TYPE_CHECKING:
    from app.models.extraction_suggestion import ExtractionSuggestion
    from app.models.project import Project
    from app.models.user import User


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[ExtractionRunKind] = mapped_column(
        Enum(
            ExtractionRunKind,
            name="extraction_run_kind",
            values_callable=lambda enum: [m.value for m in enum],
        ),
        nullable=False,
    )
    status: Mapped[ExtractionRunStatus] = mapped_column(
        Enum(
            ExtractionRunStatus,
            name="extraction_run_status",
            values_callable=lambda enum: [m.value for m in enum],
        ),
        nullable=False,
        default=ExtractionRunStatus.RUNNING,
        server_default=text("'running'::extraction_run_status"),
    )
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    model_used: Mapped[str | None] = mapped_column(String(128), nullable=True)
    documents_considered: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    summary_stats: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    project: Mapped["Project"] = relationship(
        "Project", back_populates="extraction_runs"
    )
    triggered_by_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[triggered_by]
    )
    suggestions: Mapped[list["ExtractionSuggestion"]] = relationship(
        "ExtractionSuggestion",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="ExtractionSuggestion.created_at",
    )
