import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import DocumentFileType, DocumentIndexingStatus


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[DocumentFileType] = mapped_column(
        Enum(
            DocumentFileType,
            name="document_file_type",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)
    directory_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    indexing_status: Mapped[DocumentIndexingStatus] = mapped_column(
        Enum(
            DocumentIndexingStatus,
            name="document_indexing_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=DocumentIndexingStatus.PENDING,
        server_default=text("'pending'::document_indexing_status"),
        index=True,
    )
    indexing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    project = relationship("Project", back_populates="documents")
    rag_chunks = relationship(
        "DocumentRagChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )
