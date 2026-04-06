import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ReportStatus


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(
            ReportStatus,
            name="report_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=ReportStatus.GENERATING,
        server_default=text("'generating'::report_status"),
    )
    sections: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)
    indicators: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)
    charts: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)
    gri_index: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)
    gaps: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)
    exported_docx_s3: Mapped[str | None] = mapped_column(String(512), nullable=True)
    exported_pdf_s3: Mapped[str | None] = mapped_column(String(512), nullable=True)
    llm_tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
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

    project = relationship("Project", back_populates="reports")
