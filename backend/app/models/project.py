import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import OrganizationSize, ProjectStatus


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    org_name: Mapped[str] = mapped_column(String(255), nullable=False)
    org_sector: Mapped[str | None] = mapped_column(String(255), nullable=True)
    org_size: Mapped[OrganizationSize | None] = mapped_column(
        Enum(
            OrganizationSize,
            name="organization_size",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=True,
    )
    org_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    base_year: Mapped[int] = mapped_column(Integer, nullable=False)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(
            ProjectStatus,
            name="project_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=ProjectStatus.PLANNING,
        server_default=text("'planning'::project_status"),
    )
    material_topics: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    sdg_goals: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB, nullable=True
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

    user = relationship("User", back_populates="projects")
    documents = relationship(
        "Document", back_populates="project", cascade="all, delete-orphan"
    )
    reports = relationship(
        "Report", back_populates="project", cascade="all, delete-orphan"
    )
    rag_chunks = relationship(
        "DocumentRagChunk",
        cascade="all, delete-orphan",
    )
