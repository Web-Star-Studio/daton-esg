"""add pinecone rag indexing support for project documents"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260413_0006"
down_revision = "20260413_0005"
branch_labels = None
depends_on = None


DOCUMENT_INDEXING_STATUS = postgresql.ENUM(
    "pending",
    "processing",
    "indexed",
    "failed",
    name="document_indexing_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    DOCUMENT_INDEXING_STATUS.create(bind, checkfirst=True)

    op.add_column(
        "documents",
        sa.Column(
            "indexing_status",
            DOCUMENT_INDEXING_STATUS,
            nullable=False,
            server_default=sa.text("'pending'::document_indexing_status"),
        ),
    )
    op.add_column(
        "documents",
        sa.Column("indexing_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_documents_indexing_status",
        "documents",
        ["indexing_status"],
        unique=False,
    )

    op.create_table(
        "document_rag_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("pinecone_id", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column(
            "source_locator",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("directory_key", sa.String(length=128), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pinecone_id"),
    )
    op.create_index(
        "ix_document_rag_chunks_project_id",
        "document_rag_chunks",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_rag_chunks_document_id",
        "document_rag_chunks",
        ["document_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_rag_chunks_document_id", table_name="document_rag_chunks"
    )
    op.drop_index("ix_document_rag_chunks_project_id", table_name="document_rag_chunks")
    op.drop_table("document_rag_chunks")
    op.drop_index("ix_documents_indexing_status", table_name="documents")
    op.drop_column("documents", "indexed_at")
    op.drop_column("documents", "indexing_error")
    op.drop_column("documents", "indexing_status")

    bind = op.get_bind()
    DOCUMENT_INDEXING_STATUS.drop(bind, checkfirst=True)
